from engine.services.result import ActionResult
from engine.services.skill_service import SkillService
from engine.services.empath_saf_service import EmpathSafService


class WoundTransferService:
    # DRG-EMPATH-MECHANIC-001: directengine_canon implementation of the
    # canonical Empath transfer seam described in
    # /memories/repo/repo-memory-empath-canon-mechanic.md.
    MAX_TRANSFER_PER_CYCLE = 20
    FATIGUE_RATIO_BLOCK = 0.85

    @staticmethod
    def touch(empath, patient):
        if not hasattr(empath, "touch_empath_target"):
            return ActionResult.fail(errors=["You fail to form a diagnostic link."], data={"reason": "missing_touch_hook"})
        ok, lines = empath.touch_empath_target(patient)
        return WoundTransferService._tuple_result(ok, lines, patient=patient)

    @staticmethod
    def link(empath, patient, persistent=False):
        if not hasattr(empath, "link_empath_target"):
            return ActionResult.fail(errors=["You fail to deepen the bond."], data={"reason": "missing_link_hook"})
        ok, lines = empath.link_empath_target(patient, persistent=persistent)
        return WoundTransferService._tuple_result(ok, lines, patient=patient)

    @staticmethod
    def mend_self(empath):
        if not hasattr(empath, "mend_empath_self"):
            return ActionResult.fail(errors=["You cannot mend yourself."], data={"reason": "missing_mend_hook"})
        ok, lines = empath.mend_empath_self()
        return WoundTransferService._tuple_result(ok, lines)

    @classmethod
    def transfer(
        cls,
        empath,
        patient=None,
        wound_type="",
        location=None,
        amount=None,
        selector=None,
        requested_fraction=None,
        requested_rate=None,
        learning_action=None,
    ):
        profession_error = cls._validate_profession(empath)
        if profession_error:
            return profession_error
        posture_error = cls._validate_posture(empath)
        if posture_error:
            return posture_error
        fatigue_error = cls._validate_fatigue(empath)
        if fatigue_error:
            return fatigue_error
        normalized_wound_type = str(wound_type or "").strip().lower()
        if normalized_wound_type == "shock":
            return cls._transfer_shock(empath, patient)
        saf_error = EmpathSafService.get_transfer_block_result(empath)
        if saf_error is not None:
            return saf_error
        empathy_error = cls._validate_empathy_skill(empath, wound_type=wound_type, selector=selector or location)
        if empathy_error:
            return empathy_error

        link_state = empath.get_empath_link_state(require_local=True, emit_break_messages=True) if hasattr(empath, "get_empath_link_state") else None
        if not link_state:
            return ActionResult.fail(errors=["You are not linked to a patient."], data={"reason": "missing_link"})
        linked_patient = link_state.get("target") if isinstance(link_state, dict) else None
        if patient is None:
            patient = linked_patient
        if patient is None:
            return ActionResult.fail(errors=["You are not linked to a patient."], data={"reason": "missing_patient"})
        if linked_patient is not patient:
            return ActionResult.fail(errors=["You are not linked to that patient."], data={"reason": "wrong_patient"})
        if getattr(patient, "location", None) != getattr(empath, "location", None):
            return ActionResult.fail(errors=["They are not here."], data={"reason": "patient_not_present"})
        if not hasattr(empath, "take_empath_wound"):
            return ActionResult.fail(errors=["You cannot take that wound right now."], data={"reason": "missing_transfer_hook"})

        normalized_amount, capped = cls._normalize_amount_spec(patient, wound_type, amount, selector, requested_fraction, requested_rate, location)
        before_wounds = cls._snapshot_empath_wounds(patient)
        ok, lines = empath.take_empath_wound(
            wound_type,
            normalized_amount,
            target=patient,
            selector=selector or location,
            requested_fraction=requested_fraction,
            requested_rate=requested_rate,
            learning_action=learning_action or "canonical_progression",
        )
        transferred_amount, transferred_wound_type = cls._resolve_transferred_amount(
            patient,
            before_wounds=before_wounds,
            fallback_wound_type=wound_type,
        )
        result = cls._tuple_result(
            ok,
            lines,
            patient=patient,
            data={
                "wound_type": str(wound_type or "").strip().lower(),
                "transferred_wound_type": transferred_wound_type,
                "transferred_amount": transferred_amount,
                "selector": str(selector or location or "").strip().lower(),
                "requested_rate": str(requested_rate or "").strip().lower(),
                "requested_fraction": requested_fraction,
                "amount_spec": normalized_amount,
                "capped": capped,
                "deferred_gates": ["concentration"],
                "substituted_gate": "empathy_for_transference",
            },
        )
        if result.success:
            cls._apply_canonical_progression_awards(
                empath,
                patient,
                wound_type=transferred_wound_type,
                amount=transferred_amount,
            )
            cls._emit_patient_transfer_message(patient, wound_type, selector or location, requested_fraction, requested_rate)
        return result

    @classmethod
    def _transfer_shock(cls, empath, patient):
        if patient is None:
            return ActionResult.fail(errors=["They are not here."], data={"reason": "missing_patient"})
        if getattr(patient, "location", None) != getattr(empath, "location", None):
            return ActionResult.fail(errors=["They are not here."], data={"reason": "patient_not_present"})

        shock_result = EmpathSafService.transfer_shock(empath, patient)
        if shock_result.success or str((shock_result.data or {}).get("reason") or "") != "no_spiritual_shock":
            return shock_result

        if not hasattr(empath, "take_empath_shock"):
            return shock_result
        ok, lines = empath.take_empath_shock(patient)
        return cls._tuple_result(ok, lines, patient=patient, data={"wound_type": "shock", "transferred_wound_type": "shock"})

    @staticmethod
    def _snapshot_empath_wounds(patient):
        if patient is None or not hasattr(patient, "get_empath_wounds"):
            return {}
        wounds = patient.get_empath_wounds()
        if not isinstance(wounds, dict):
            return {}
        return {str(key or "").strip().lower(): max(0, int(value or 0)) for key, value in wounds.items()}

    @classmethod
    def _resolve_transferred_amount(cls, patient, before_wounds=None, fallback_wound_type=""):
        before = dict(before_wounds or {})
        after = cls._snapshot_empath_wounds(patient)
        deltas = []
        for wound_key in set(before) | set(after):
            delta = max(0, int(before.get(wound_key, 0) or 0) - int(after.get(wound_key, 0) or 0))
            if delta > 0:
                deltas.append((wound_key, delta))
        if not deltas:
            normalized_fallback = str(fallback_wound_type or "").strip().lower()
            return 0, normalized_fallback
        wound_key, amount = max(deltas, key=lambda item: item[1])
        return int(amount or 0), str(wound_key or "").strip().lower()

    @classmethod
    def _apply_canonical_progression_awards(cls, empath, patient, wound_type="", amount=0):
        transferred_amount = max(0, int(amount or 0))
        if transferred_amount <= 0:
            return

        cls._apply_canonical_transfer_fatigue(empath, transferred_amount)

        # DRG-EMPATH-PROGRESSION-001: canonical class-internal limitation per
        # S00524 - no XP awarded when patient is another Empath.
        # provenance: gsl_2004
        if cls._is_empath_patient(patient):
            return

        primary_magic_xp = (transferred_amount * 80 // 100) + 1
        perception_xp = (transferred_amount * 20 // 100) + 1
        empathy_rank = int(empath.get_skill("empathy") if hasattr(empath, "get_skill") else 0)
        empath_level = cls._get_empath_progression_level(empath)

        # DRG-EMPATH-PROGRESSION-001: canonical Transference skill (GSL skill 96)
        # is mapped to DireEngine Empathy skill per MECHANIC-001 Q2 hybrid_design.
        # XP awards go to Empathy here following the canonical scaling formula.
        # provenance: gsl_2004 (Transference→Empathy hybrid_design)
        transference_scale = max(1, min(8, empathy_rank // empath_level))
        normalized_wound_type = str(wound_type or "").strip().lower()
        if normalized_wound_type == "poison":
            transference_scale += 4
        elif normalized_wound_type == "disease":
            transference_scale += 6
        empathy_xp = transferred_amount * transference_scale

        cls._award_skill_xp_if_supported(empath, "primary_magic", primary_magic_xp)
        cls._award_skill_xp_if_supported(empath, "perception", perception_xp)
        cls._award_skill_xp_if_supported(empath, "empathy", empathy_xp)

    @staticmethod
    def _award_skill_xp_if_supported(character, skill_name, amount):
        if character is None:
            return
        if not hasattr(character, "_sync_exp_skill_state") and not hasattr(character, "award_skill_experience"):
            return
        SkillService.award_xp(character, skill_name, amount)

    @staticmethod
    def _apply_canonical_transfer_fatigue(empath, amount):
        fatigue_cost = max(0, int(amount or 0) // 3)
        if fatigue_cost <= 0:
            return
        if hasattr(empath, "get_fatigue"):
            current_fatigue, _max_fatigue = empath.get_fatigue()
            updated = max(0, int(current_fatigue or 0) - fatigue_cost)
            if hasattr(empath, "set_fatigue"):
                empath.set_fatigue(updated)
                return
        db = getattr(empath, "db", None)
        if db is not None:
            current = int(getattr(db, "fatigue", 0) or 0)
            setattr(db, "fatigue", max(0, current - fatigue_cost))

    @staticmethod
    def _get_empath_progression_level(empath):
        if hasattr(empath, "get_circle"):
            return max(1, int(empath.get_circle() or 1))
        db = getattr(empath, "db", None)
        if db is not None:
            circle = getattr(db, "circle", getattr(db, "level", 1))
            return max(1, int(circle or 1))
        return 1

    @staticmethod
    def _is_empath_patient(patient):
        if patient is None:
            return False
        if hasattr(patient, "get_profession"):
            return str(patient.get_profession() or "").strip().lower() == "empath"
        if hasattr(patient, "is_empath"):
            return bool(patient.is_empath())
        return False

    @staticmethod
    def _tuple_result(ok, payload, patient=None, data=None):
        lines = payload if isinstance(payload, list) else [str(payload)]
        result_data = dict(data or {})
        if patient is not None:
            result_data.setdefault("patient_key", getattr(patient, "key", "someone"))
        if ok:
            return ActionResult.ok(data=result_data, messages=lines)
        return ActionResult.fail(errors=lines, data=result_data)

    @staticmethod
    def _validate_profession(empath):
        if not getattr(empath, "is_empath", lambda: False)():
            return ActionResult.fail(errors=["You cannot draw another's wounds into yourself."], data={"reason": "not_empath"})
        return None

    @staticmethod
    def _validate_posture(empath):
        if str(getattr(getattr(empath, "db", None), "position", "standing") or "standing").strip().lower() == "prone":
            return ActionResult.fail(errors=["You can't heal while lying down on the job!"], data={"reason": "prone"})
        return None

    @classmethod
    def _validate_fatigue(cls, empath):
        if hasattr(empath, "get_fatigue"):
            fatigue, max_fatigue = empath.get_fatigue()
        else:
            fatigue = getattr(getattr(empath, "db", None), "fatigue", 0)
            max_fatigue = getattr(getattr(empath, "db", None), "max_fatigue", 100)
        fatigue = int(fatigue or 0)
        max_fatigue = max(1, int(max_fatigue or 100))
        if float(fatigue) / float(max_fatigue) >= cls.FATIGUE_RATIO_BLOCK:
            return ActionResult.fail(
                errors=["You collapse from fatigue, unable to keep the link open."],
                data={"reason": "fatigue", "fatigue": fatigue, "max_fatigue": max_fatigue},
            )
        return None

    @staticmethod
    def _validate_empathy_skill(empath, wound_type="", selector=None):
        skill = int(empath.get_skill("empathy") if hasattr(empath, "get_skill") else 0)
        normalized_wound = str(wound_type or "").strip().lower()
        normalized_selector = str(selector or "").strip().lower()
        if normalized_wound in {"", "bleeding", "vitality"} or normalized_selector:
            return None
        if skill <= 0:
            return ActionResult.fail(
                errors=["You do not yet have the empathy to control that transfer."],
                data={"reason": "empathy_too_low", "skill": skill},
            )
        return None

    @classmethod
    def _normalize_amount_spec(cls, patient, wound_type, amount, selector, requested_fraction, requested_rate, location):
        if requested_fraction is not None or requested_rate:
            return "", False
        selector_value = str(selector or location or "").strip()
        amount_value = str(amount or "").strip().lower()
        if selector_value:
            return "", False
        if not amount_value:
            return "", False
        if amount_value == "all":
            return str(cls.MAX_TRANSFER_PER_CYCLE), True
        try:
            numeric_amount = int(amount_value)
        except (TypeError, ValueError):
            return amount_value, False
        capped_amount = max(1, min(cls.MAX_TRANSFER_PER_CYCLE, numeric_amount))
        return str(capped_amount), capped_amount != numeric_amount

    @staticmethod
    def _emit_patient_transfer_message(patient, wound_type, selector, requested_fraction, requested_rate):
        if not hasattr(patient, "msg"):
            return
        selector_value = str(selector or "").strip().lower()
        if requested_fraction is not None:
            if selector_value:
                patient.msg("You feel only part of the hurt ease from that place.")
            else:
                patient.msg("You feel only part of your pain lessen.")
            return
        if requested_rate == "slow":
            patient.msg("You feel your pain ease in a slow, careful draw.")
            return
        if requested_rate == "fast":
            patient.msg("You feel your pain wrench sharply away.")
            return
        if selector_value:
            patient.msg("You feel a focused thread of pain lessen.")
            return
        patient.msg("You feel your pain lessen.")