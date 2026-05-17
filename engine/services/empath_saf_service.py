import time

from engine.services.result import ActionResult


class EmpathSafService:
    BASE_DURATION = 10800
    MAX_DURATION = 999999
    PERMASHOCK_DURATION = 999999
    PERMASHOCK_BURDEN = 999
    PERMASHOCK_THRESHOLD = 499
    RESCUE_MIN_CIRCLE = 10
    TRANSFER_BLOCK_MESSAGE = "You feel a sudden spiritual shock as the link shatters."
    GIFT_OF_LIFE_BLOCK_MESSAGE = "You have lost your sensitivity by harming others, so Gift of Life cannot take hold."
    PERMASHOCK_MESSAGE = (
        "Your empathic abilities have disappeared, seemingly forever. All your special senses have been cut off, "
        "leaving a great void separating you from the vibrant life forces that once surrounded you like a warm lover's arms. "
        "A feeling of great loneliness settles upon you."
    )
    TIER_CONFIG = {
        0: {
            "burden_gain": 3,
            "duration_gain": BASE_DURATION,
            "stun_seconds": 30,
            "prone": False,
            "message": "You feel a pain deep in your soul that has shattered the delicate balance of your empathic skills. You go into shock!",
        },
        1: {
            "burden_gain": 10,
            "duration_gain": BASE_DURATION + 600,
            "stun_seconds": 120,
            "prone": True,
            "message": "You collapse from an intense pain deep in your soul that has shattered the delicate balance of your empathic skills. You go into heavy shock!",
        },
        2: {
            "burden_gain": 20,
            "duration_gain": BASE_DURATION + 1200,
            "stun_seconds": 240,
            "prone": True,
            "message": "You collapse from an excruciating pain deep in your soul that has shattered the delicate balance of your empathic skills. You go into extreme shock!",
        },
        3: {
            "burden_gain": PERMASHOCK_BURDEN,
            "duration_gain": PERMASHOCK_DURATION,
            "stun_seconds": 750,
            "prone": True,
            "message": "Your entire being explodes with unimaginable pain. Just as you black out a bleakness covers your soul like a seductive black abyss drawing you to give in and fall into its eternal depths.",
        },
    }

    @classmethod
    def _ensure_defaults(cls, character):
        db = getattr(character, "db", None)
        if db is None:
            return
        if getattr(db, "empath_saf_duration", None) is None:
            db.empath_saf_duration = 0
        if getattr(db, "empath_saf_burden", None) is None:
            db.empath_saf_burden = 0
        if getattr(db, "empath_permashock", None) is None:
            db.empath_permashock = False
        if getattr(db, "stunned_until", None) is None:
            db.stunned_until = 0.0

    @classmethod
    def get_state(cls, character):
        cls._ensure_defaults(character)
        db = getattr(character, "db", None)
        return {
            "duration": max(0, int(getattr(db, "empath_saf_duration", 0) or 0)),
            "burden": max(0, int(getattr(db, "empath_saf_burden", 0) or 0)),
            "permashocked": bool(getattr(db, "empath_permashock", False)),
        }

    @classmethod
    def is_blocked(cls, character):
        state = cls.get_state(character)
        return bool(state["permashocked"] or state["duration"] > 0)

    @classmethod
    def get_transfer_block_result(cls, character):
        if not cls.is_blocked(character):
            return None
        return ActionResult.fail(
            errors=[cls.TRANSFER_BLOCK_MESSAGE],
            data={"reason": "saf", **cls.get_state(character)},
        )

    @classmethod
    def get_gift_of_life_block_result(cls, character):
        if not cls.is_blocked(character):
            return None
        return ActionResult.fail(
            errors=[cls.GIFT_OF_LIFE_BLOCK_MESSAGE],
            data={"reason": "saf", **cls.get_state(character)},
        )

    @classmethod
    def register_offense(cls, attacker, target=None, *, hit=False, damage=0, killed=False):
        if not getattr(attacker, "is_empath", lambda: False)():
            return None
        if target is None or target == attacker:
            return None
        if not hasattr(target, "set_hp"):
            return None
        tier = cls._classify_tier(hit=hit, damage=damage, killed=killed)
        return cls._apply_tier(attacker, tier)

    @classmethod
    def _classify_tier(cls, *, hit=False, damage=0, killed=False):
        if killed:
            return 3
        if (not hit) or int(damage or 0) <= 0:
            return 0
        if int(damage or 0) < 10:
            return 1
        return 2

    @classmethod
    def _apply_tier(cls, character, tier):
        cls._ensure_defaults(character)
        config = dict(cls.TIER_CONFIG.get(int(tier), cls.TIER_CONFIG[0]))
        db = getattr(character, "db", None)
        db.empath_saf_duration = min(
            cls.MAX_DURATION,
            max(0, int(getattr(db, "empath_saf_duration", 0) or 0)) + int(config.get("duration_gain", 0) or 0),
        )
        db.empath_saf_burden = min(
            cls.PERMASHOCK_BURDEN,
            max(0, int(getattr(db, "empath_saf_burden", 0) or 0)) + int(config.get("burden_gain", 0) or 0),
        )
        cls._apply_shock_state(character, int(config.get("stun_seconds", 0) or 0), prone=bool(config.get("prone", False)))
        cls._emit(character, str(config.get("message", "") or ""))
        if tier == 3 or int(getattr(db, "empath_saf_burden", 0) or 0) > cls.PERMASHOCK_THRESHOLD:
            cls._apply_permashock(character)
        cls._sync(character)
        return cls.get_state(character)

    @classmethod
    def _apply_permashock(cls, character):
        cls._ensure_defaults(character)
        db = getattr(character, "db", None)
        db.empath_permashock = True
        db.empath_saf_duration = cls.PERMASHOCK_DURATION
        db.empath_saf_burden = cls.PERMASHOCK_BURDEN
        cls._apply_shock_state(character, 750, prone=True)
        cls._emit(character, cls.PERMASHOCK_MESSAGE)

    @classmethod
    def _apply_shock_state(cls, character, stun_seconds, *, prone=False):
        cls._ensure_defaults(character)
        db = getattr(character, "db", None)
        now = time.time()
        db.stunned = True
        db.stunned_until = max(float(getattr(db, "stunned_until", 0.0) or 0.0), now + max(0, int(stun_seconds or 0)))
        if prone:
            db.position = "prone"

    @classmethod
    def tick(cls, character, now=None):
        _now = now
        if not getattr(character, "is_empath", lambda: False)():
            return False
        cls._ensure_defaults(character)
        db = getattr(character, "db", None)
        if bool(getattr(db, "empath_permashock", False)):
            return False
        duration = max(0, int(getattr(db, "empath_saf_duration", 0) or 0))
        burden = max(0, int(getattr(db, "empath_saf_burden", 0) or 0))
        if duration <= 0 and burden <= 0:
            return False
        decay = 2000 if duration > 1000 else 1000
        burden_decay = 2 if burden > 1 else 1
        db.empath_saf_duration = max(0, duration - decay)
        db.empath_saf_burden = max(0, burden - burden_decay)
        cls._sync(character)
        return True

    @classmethod
    def transfer_shock(cls, rescuer, patient):
        cls._ensure_defaults(rescuer)
        cls._ensure_defaults(patient)
        if not getattr(rescuer, "is_empath", lambda: False)():
            return ActionResult.fail(errors=["You cannot take on shock that way."], data={"reason": "not_empath"})
        if rescuer == patient:
            return ActionResult.fail(errors=["You cannot take your own spiritual shock this way."], data={"reason": "self_target"})
        if int(rescuer.get_circle() if hasattr(rescuer, "get_circle") else getattr(getattr(rescuer, "db", None), "circle", 0) or 0) < cls.RESCUE_MIN_CIRCLE:
            return ActionResult.fail(errors=["You are not yet seasoned enough to take on another Empath's spiritual shock."], data={"reason": "circle_too_low"})
        if not getattr(patient, "is_empath", lambda: False)():
            return ActionResult.fail(errors=["Only another Empath can be rescued from spiritual shock."], data={"reason": "patient_not_empath"})

        patient_state = cls.get_state(patient)
        if not patient_state["permashocked"] and patient_state["duration"] <= 0:
            return ActionResult.fail(errors=["They are carrying no spiritual shock."], data={"reason": "no_spiritual_shock"})

        rescuer_db = getattr(rescuer, "db", None)
        patient_db = getattr(patient, "db", None)
        rescuer_db.empath_saf_duration = min(
            cls.MAX_DURATION,
            max(int(getattr(rescuer_db, "empath_saf_duration", 0) or 0), max(cls.BASE_DURATION, int(patient_state["duration"] or 0))),
        )
        rescuer_db.empath_saf_burden = min(
            cls.PERMASHOCK_THRESHOLD,
            max(int(getattr(rescuer_db, "empath_saf_burden", 0) or 0), min(cls.PERMASHOCK_THRESHOLD, int(patient_state["burden"] or 0))),
        )
        rescuer_db.empath_permashock = False
        cls._apply_shock_state(rescuer, 240, prone=True)

        patient_db.empath_saf_duration = 0
        patient_db.empath_saf_burden = 0
        patient_db.empath_permashock = False
        if hasattr(patient, "msg"):
            patient.msg("Your empathic senses return in a ragged rush.")
        cls._emit(rescuer, "You take the spiritual shock into yourself.")
        cls._sync(rescuer)
        cls._sync(patient)
        return ActionResult.ok(
            messages=["You take the spiritual shock into yourself."],
            data={"reason": "shock_rescue", "patient_key": getattr(patient, "key", "someone"), **cls.get_state(rescuer)},
        )

    @staticmethod
    def _emit(character, message):
        if message and hasattr(character, "msg"):
            character.msg(message)

    @staticmethod
    def _sync(character):
        if hasattr(character, "sync_client_state"):
            character.sync_client_state()