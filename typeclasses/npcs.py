import random
import time
from collections.abc import Mapping
import importlib.util
from pathlib import Path

from django.utils.text import slugify
from evennia.utils.search import search_object

from domain.spells.spell_definitions import SPELL_REGISTRY
from engine.services.result import ActionResult
from engine.services.ranger_saf_service import RangerSafService
from engine.services.spellbook_service import SpellbookService
from server.systems.loot.loot_runtime import on_npc_defeated

from typeclasses.characters import Character
from world.systems.ranger.companion import (
    COMPANION_STATE_DISMISSED,
    COMPANION_STATE_PRESENT,
    COMPANION_STATE_RETURNING,
    COMPANION_STATE_SEARCHING,
    COMPANION_STATE_WANDERING,
    get_companion_profile,
    normalize_ranger_companion,
    resolve_companion_type_id,
    validate_companion_type,
)


def _normalize_spell_query(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


# DRG-CLERIC-09: Esuin teaches the shipped canonical Cleric spellbook only.
_CLERIC_CANONICAL_TEACHING_IDS = {
    "aesrela_everild", "bless", "divine_radiance", "halo", "hand_of_tenemlor",
    "holy_light", "major_physical_protection", "mass_rejuvenation", "minor_physical_protection",
    "protection_from_evil", "rejuvenation", "revelation", "spirit_beacon", "uncurse",
}

# DRG-EMPATH-FOUNDATION-001: Merla teaches the current Empath-only registry rows.
_EMPATH_CANONICAL_TEACHING_IDS = {
    spell.id
    for spell in SPELL_REGISTRY.values()
    if {SpellbookService._normalize_profession(entry) for entry in (spell.allowed_professions or [])} == {"empath"}
}

_RANGER_CANONICAL_TEACHING_IDS = {
    spell.id
    for spell in SPELL_REGISTRY.values()
    if {SpellbookService._normalize_profession(entry) for entry in (spell.allowed_professions or [])} == {"ranger"}
}


def _resolve_teachable_spell(spell_name, profession):
    query = _normalize_spell_query(spell_name)
    wanted_profession = SpellbookService._normalize_profession(profession)
    for spell in SPELL_REGISTRY.values():
        allowed = {SpellbookService._normalize_profession(entry) for entry in (spell.allowed_professions or [])}
        if allowed and wanted_profession not in allowed:
            continue
        if query in {_normalize_spell_query(spell.id), _normalize_spell_query(spell.name)}:
            return spell
    return None


def _teach_guild_spell(teacher, actor, spell_name, *, taught_spell_ids=None, enforce_circle=False):
    profession = getattr(getattr(teacher, "db", None), "trains_profession", None) or getattr(getattr(teacher, "db", None), "leads_profession", None)
    if profession and (not hasattr(actor, "is_profession") or not actor.is_profession(profession)):
        profession_name = str(profession).replace("_", " ").title()
        return ActionResult.fail(
            messages=[f"Only {profession_name}s may train here."],
            errors=[f"Only {profession_name}s may train here."],
        )
    spell = _resolve_teachable_spell(spell_name, profession)
    taught_ids = {str(spell_id or "").strip().lower() for spell_id in (taught_spell_ids or ())}
    if spell is None or (taught_ids and spell.id not in taught_ids):
        return ActionResult.fail(
            messages=[f"I do not teach a spell called '{spell_name}'."],
            errors=[f"I do not teach a spell called '{spell_name}'."],
        )
    if enforce_circle:
        actor_circle = SpellbookService._get_circle(actor)
        required_circle = max(1, int(getattr(spell, "min_circle", 1) or 1))
        if actor_circle < required_circle:
            return ActionResult.fail(
                messages=[f"You are not yet ready for {spell.name}. Return when you have reached Circle {required_circle}."],
                errors=[f"You are not yet ready for {spell.name}. Return when you have reached Circle {required_circle}."],
            )
    return SpellbookService.learn_spell(actor, spell.id, "npc")


class NPC(Character):
    COMBAT_AI_INTERVAL = 1.0
    IDLE_AI_INTERVAL = 8.0
    ASSIST_SAME_ROOM_ONLY = True

    def at_object_creation(self):
        super().at_object_creation()
        if not self.db.world_id:
            self.db.world_id = slugify(self.key)
        self.db.is_npc = True
        self.db.is_trainer = False
        self.db.trains_profession = None
        self.db.is_shopkeeper = False
        self.db.coin_min = 0
        self.db.coin_max = 0
        self.db.drops_box = False
        self.db.blocked_professions = []
        self.db.suspects = {}
        self.db.witnessed_crime = False
        if self.db.last_seen_target is None:
            self.db.last_seen_target = None
        if self.db.assist is None:
            self.db.assist = False
        if self.db.assist_source is None:
            self.db.assist_source = None
        if getattr(self.ndb, "threat_table", None) is None:
            self.ndb.threat_table = {}
        if self.db.loot_table is None:
            self.db.loot_table = None
        if self.db.interaction_type is None:
            self.db.interaction_type = None

    def get_on_click_command(self, caller=None):
        _caller = caller
        interaction_type = str(getattr(self.db, "interaction_type", "") or "").strip().lower()
        if not interaction_type:
            return None
        return f"__clicknpc__ {int(getattr(self, 'id', 0) or 0)}"

    def get_interaction_hint(self, looker=None):
        _looker = looker
        interaction_type = str(getattr(self.db, "interaction_type", "") or "").strip().lower()
        if interaction_type == "vendor":
            return "(Click to browse wares)"
        if interaction_type:
            return "(Click to interact)"
        return ""

    def get_display_name(self, looker=None, **kwargs):
        base_name = super().get_display_name(looker, **kwargs)
        command = self.get_on_click_command(looker)
        if not command:
            return base_name
        return f"|lc{command}|lt[{base_name}]|le"

    def at_object_receive_click(self, caller):
        return self.handle_interaction(caller)

    def handle_interaction(self, caller):
        interaction_type = str(getattr(self.db, "interaction_type", "") or "").strip().lower()
        if interaction_type == "vendor":
            return self.open_vendor_ui(caller)
        if caller:
            caller.msg(f"{self.key} acknowledges you but has nothing to offer yet.")
        return False

    def open_vendor_ui(self, caller):
        if caller is None:
            return False
        caller.msg(f"{self.key} looks up as you approach.")
        if hasattr(caller, "record_vendor_visit"):
            caller.record_vendor_visit(self)
        if hasattr(self, "get_vendor_greeting_lines"):
            for line in list(self.get_vendor_greeting_lines(caller) or []):
                normalized_line = str(line or "").strip()
                if normalized_line:
                    caller.msg(normalized_line)
        if hasattr(caller, "open_vendor_ui"):
            return bool(caller.open_vendor_ui(self))
        return False

    def set_target(self, target):
        super().set_target(target)
        if target is None:
            self.db.last_seen_target = None
            self.db.assist_source = None
            if hasattr(self, "clear_state"):
                self.clear_state("last_seen_target")
            return
        self.db.last_seen_target = getattr(target, "id", None)
        if hasattr(self, "set_state") and getattr(target, "id", None):
            self.set_state("last_seen_target", target.id)

    def clear_target(self):
        self.set_target(None)

    def _get_threat_table(self):
        threat_table = getattr(getattr(self, "ndb", None), "threat_table", None)
        if not isinstance(threat_table, dict):
            threat_table = getattr(self.db, "threat_table", None)
        if not isinstance(threat_table, dict):
            threat_table = {}
        if getattr(self, "ndb", None) is not None:
            self.ndb.threat_table = dict(threat_table)
        return {str(key): int(value or 0) for key, value in threat_table.items() if str(key or "").strip()}

    def _resolve_threat_target(self, target_id):
        normalized_target_id = str(target_id or "").strip()
        if not normalized_target_id or not self.location:
            return None
        for obj in list(getattr(self.location, "contents", []) or []):
            if str(getattr(obj, "id", "") or "").strip() == normalized_target_id:
                return obj
        return None

    def get_threat(self, target):
        target_id = str(getattr(target, "id", "") or "").strip()
        if not target_id:
            return 0
        return int(self._get_threat_table().get(target_id, 0) or 0)

    def add_threat(self, target, amount):
        if not target or target == self:
            return 0
        if not bool(getattr(target, "has_account", False)):
            return 0
        target_id = str(getattr(target, "id", "") or "").strip()
        if not target_id:
            return 0
        threat_table = dict(self._get_threat_table())
        next_value = min(1000, max(0, int(threat_table.get(target_id, 0) or 0) + int(amount or 0)))
        if next_value > 0:
            threat_table[target_id] = next_value
        else:
            threat_table.pop(target_id, None)
        if getattr(self, "ndb", None) is not None:
            self.ndb.threat_table = threat_table
        return next_value

    def clear_threat(self):
        if getattr(self, "ndb", None) is not None:
            self.ndb.threat_table = {}

    def remove_target(self, target):
        target_id = str(getattr(target, "id", "") or target or "").strip()
        if not target_id:
            return
        threat_table = dict(self._get_threat_table())
        threat_table.pop(target_id, None)
        if getattr(self, "ndb", None) is not None:
            self.ndb.threat_table = threat_table

    def prune_threat_table(self):
        threat_table = dict(self._get_threat_table())
        if not threat_table:
            return {}
        kept = {}
        for target_id, threat_value in threat_table.items():
            target = self._resolve_threat_target(target_id)
            if target is None:
                continue
            if target == self:
                continue
            if not bool(getattr(target, "has_account", False)):
                continue
            if hasattr(target, "is_alive") and not target.is_alive():
                continue
            if getattr(target, "location", None) != self.location:
                continue
            kept[str(target_id)] = int(threat_value or 0)
        if getattr(self, "ndb", None) is not None:
            self.ndb.threat_table = kept
        return kept

    def get_highest_threat(self):
        threat_table = self.prune_threat_table()
        if not threat_table:
            return None
        target_id = max(threat_table, key=lambda key: int(threat_table.get(key, 0) or 0))
        return self._resolve_threat_target(target_id)

    def can_assist(self):
        return bool(getattr(self.db, "assist", False))

    def emit_assist_event(self, target):
        if not self.location or not target:
            return
        for obj in list(getattr(self.location, "contents", []) or []):
            if obj == self or not hasattr(obj, "receive_assist_event"):
                continue
            if hasattr(obj, "can_assist") and not obj.can_assist():
                continue
            obj.receive_assist_event(self, target)

    def receive_assist_event(self, source, target):
        if source is None or source == self:
            return False
        if not self.can_assist() or self.is_dead():
            return False
        if self.get_target() or getattr(self.db, "target", None) is not None:
            return False
        if not target or target == self:
            return False
        if not bool(getattr(target, "has_account", False)):
            return False
        if hasattr(target, "is_alive") and not target.is_alive():
            return False
        if hasattr(source, "is_alive") and not source.is_alive():
            return False
        if self.ASSIST_SAME_ROOM_ONLY:
            if not self.location or getattr(target, "location", None) != self.location or getattr(source, "location", None) != self.location:
                return False
        self.add_threat(target, 5)
        self.set_target(target)
        self.db.assist_source = getattr(source, "id", None) or getattr(source, "key", None)
        if self.location:
            self.location.msg_contents(f"{self.key} rushes to assist!")
        return True

    def is_combat_loop_active(self):
        target = self.get_target()
        return bool(getattr(self.db, "in_combat", False) and target is not None and getattr(target, "location", None) == self.location)

    def disengage(self, *, emit_message=True):
        had_target = bool(getattr(self.db, "target", None) or self.get_target())
        self.clear_threat()
        self.clear_target()
        if hasattr(self, "clear_state"):
            self.clear_state("combat_timer")
        if emit_message and had_target and self.location:
            self.location.msg_contents(f"{self.key} loses interest.")

    def should_auto_engage_actor(self, actor):
        if not actor or actor == self:
            return False
        if self.is_dead():
            return False
        if not bool(getattr(self.db, "aggressive", False)):
            return False
        if not bool(getattr(actor, "has_account", False)):
            return False
        if getattr(actor, "location", None) != self.location or self.location is None:
            return False
        if hasattr(actor, "is_alive") and not actor.is_alive():
            return False
        active_effects = actor.get_state("active_effects") if hasattr(actor, "get_state") else {}
        utility_effects = dict((active_effects or {}).get("utility", {}) or {}) if isinstance(active_effects, Mapping) else {}
        searchable = " ".join(
            [
                str(getattr(self, "key", "") or "").lower(),
                str(getattr(getattr(self, "db", None), "desc", "") or "").lower(),
                str(getattr(getattr(self, "db", None), "creature_type", "") or "").lower(),
                str(getattr(getattr(self, "db", None), "npc_type", "") or "").lower(),
                str(getattr(getattr(self, "db", None), "species", "") or "").lower(),
                str(getattr(getattr(self, "db", None), "race", "") or "").lower(),
            ]
        )
        is_undead = any(keyword in searchable for keyword in ("undead", "zombie", "skeleton", "ghost", "wraith"))
        if not is_undead and (utility_effects.get("innocence") or bool(getattr(getattr(actor, "db", None), "innocence_active", False))):
            return False
        return True

    def at_attacked(self, attacker):
        if not attacker or attacker == self:
            return
        if not bool(getattr(attacker, "has_account", False)):
            return
        current_target = getattr(self.db, "target", None) or self.get_target()
        if current_target == attacker:
            return
        if current_target is not None:
            if getattr(current_target, "location", None) == self.location and getattr(current_target, "has_account", False):
                return
        self.set_target(attacker)
        if self.location:
            self.location.msg_contents(f"{self.key} turns on {attacker.key}!")
        self.emit_assist_event(attacker)

    def maybe_auto_engage_actor(self, actor):
        if not self.should_auto_engage_actor(actor):
            return False
        current_target = getattr(self.db, "target", None) or self.get_target()
        if current_target == actor:
            return False
        if current_target is not None:
            if getattr(current_target, "location", None) == self.location and getattr(current_target, "has_account", False):
                return False
        self.set_target(actor)
        if self.location:
            self.location.msg_contents(f"{self.key} snarls and attacks {actor.key}!")
        self.emit_assist_event(actor)
        return True

    def at_death(self, cause=None, death_type="vitality"):
        room = getattr(self, "location", None)
        corpse = super().at_death(cause=cause, death_type=death_type)
        if corpse is not None:
            on_npc_defeated(self, room=room)
        return corpse

    def is_shopkeeper(self):
        return bool(getattr(self.db, "is_shopkeeper", False))

    def get_suspects(self):
        suspects = getattr(self.db, "suspects", None)
        if not isinstance(suspects, dict):
            suspects = {}
            self.db.suspects = suspects
        return suspects

    def get_suspicion_for(self, actor):
        if not actor or not getattr(actor, "id", None):
            return 0
        suspects = self.get_suspects()
        return int(suspects.get(str(actor.id), 0) or 0)

    def adjust_suspicion_for(self, actor, amount, maximum=15):
        if not actor or not getattr(actor, "id", None):
            return 0
        suspects = dict(self.get_suspects())
        key = str(actor.id)
        current = int(suspects.get(key, 0) or 0)
        updated = max(0, min(int(maximum or 0), current + int(amount or 0)))
        if updated > 0:
            suspects[key] = updated
        elif key in suspects:
            suspects.pop(key, None)
        self.db.suspects = suspects
        return updated

    def react_to(self, actor, context="presence"):
        if not actor or actor == self or not hasattr(actor, "get_profession_reaction_message"):
            if context == "presence":
                self.maybe_auto_engage_actor(actor)
            return None
        reaction = actor.get_profession_reaction_message(context=context, observer=self)
        if reaction:
            actor.msg(f"{self.key} {reaction}")
        if context == "presence":
            self.maybe_auto_engage_actor(actor)
        return reaction

    def can_trade(self, actor):
        if hasattr(actor, "can_trade") and not actor.can_trade():
            return False, "The shopkeeper refuses to deal with you until your debts are settled."

        blocked = {
            str(entry).strip().lower().replace("-", "_").replace(" ", "_")
            for entry in (getattr(self.db, "blocked_professions", None) or [])
            if str(entry or "").strip()
        }
        profession = actor.get_profession() if hasattr(actor, "get_profession") else None
        if profession in blocked:
            return False, f"{self.key} refuses to deal with your kind here."

        location = getattr(self, "location", None)
        alert_level = int(getattr(getattr(location, "db", None), "alert_level", 0) or 0)
        if self.is_shopkeeper() and profession == "thief" and (bool(getattr(actor.db, "crime_flag", False)) or alert_level > 0):
            return False, f"{self.key} narrows their eyes. 'No trade with thieves today.'"

        self.react_to(actor, context="trade")
        return True, ""

    def ai_tick(self):
        if not self.db.is_npc:
            return

        if bool(getattr(self.db, "is_training_dummy", False)):
            return

        if self.is_dead():
            return

        if self.is_in_roundtime():
            return

        best_target = self.get_highest_threat()
        current_target = self.get_target()
        if best_target is not None and best_target != current_target:
            self.set_target(best_target)

        raw_target = getattr(self.db, "target", None)
        if raw_target is not None:
            if hasattr(raw_target, "is_alive") and not raw_target.is_alive():
                self.disengage(emit_message=False)
                return
            if getattr(raw_target, "location", None) != self.location:
                self.disengage()
                return
        elif bool(getattr(self.db, "in_combat", False)):
            self.disengage(emit_message=False)
            return

        if self.is_surprised():
            self.clear_surprise()
            self.msg("You are too startled to react!")
            return

        target = self.get_target()
        has_pursuit_state = bool(self.get_state("last_seen_target") or self.get_state("empath_manipulated"))
        if not target and not has_pursuit_state:
            return

        now = time.time()
        interval = self.COMBAT_AI_INTERVAL if target else self.IDLE_AI_INTERVAL
        next_tick_at = float(getattr(self.ndb, "next_ai_tick_at", 0.0) or 0.0)
        if now < next_tick_at:
            return
        self.ndb.next_ai_tick_at = now + interval

        combat_timer = int(self.get_state("combat_timer") or 0)
        if target:
            if combat_timer <= 0:
                self.set_state("combat_timer", 5)
        elif combat_timer > 0:
            combat_timer -= 1
            if combat_timer > 0:
                self.set_state("combat_timer", combat_timer)
            else:
                self.clear_state("combat_timer")

        self.process_ai_decision()

    def process_ai_decision(self):
        manipulated = self.get_state("empath_manipulated") if hasattr(self, "get_state") else None
        if isinstance(manipulated, Mapping):
            expires_at = float(manipulated.get("expires_at", 0) or 0)
            if expires_at and time.time() >= expires_at:
                self.clear_state("empath_manipulated")
            else:
                if self.get_target():
                    self.set_target(None)
                self.db.in_combat = False
                return

        target = self.get_target()

        if not target:
            last_seen_target = self.get_state("last_seen_target")
            if last_seen_target and self.location:
                for obj in self.location.contents:
                    if getattr(obj, "id", None) == last_seen_target:
                        self.set_target(obj)
                        target = obj
                        break

        if not target:
            if bool(getattr(self.db, "in_combat", False)):
                self.disengage(emit_message=False)
            return

        if not target.is_alive():
            self.disengage(emit_message=False)
            return

        if target.is_hidden():
            self.set_awareness("searching")
            self.ai_search()
            return

        self.evaluate_combat_state(target)

    def evaluate_combat_state(self, target):
        hp = self.db.hp or 0
        max_hp = self.db.max_hp or 0
        hp_ratio = hp / max_hp if max_hp else 1

        if not self.is_engaged_with(target):
            self.ai_advance(target)
            return

        if hp_ratio < 0.2:
            self.msg("The creature panics!")
            self.ai_retreat(target)
            return

        if hp_ratio < 0.3:
            self.ai_retreat(target)
        else:
            self.ai_attack(target)

    def ai_attack(self, target):
        self.set_state("last_seen_target", target.id)
        self.execute_cmd(f"attack {target.key}")

    def ai_advance(self, target):
        self.execute_cmd(f"advance {target.key}")

    def ai_search(self):
        self.execute_cmd("search")

    def ai_retreat(self, target):
        if random.random() < 0.6:
            self.execute_cmd("retreat")
            if target and target.db.in_combat:
                npc_hp = self.db.hp or 0
                npc_max_hp = self.db.max_hp or 1
                target_hp = target.db.hp or 0
                target_max_hp = target.db.max_hp or 1
                npc_hp_ratio = npc_hp / npc_max_hp if npc_max_hp else 1
                target_hp_ratio = target_hp / target_max_hp if target_max_hp else 1
                follow_chance = 60
                if npc_hp_ratio > target_hp_ratio:
                    follow_chance -= 10
                else:
                    follow_chance += 10
                if random.randint(1, 100) <= follow_chance:
                    target.execute_cmd(f"advance {self.key}")
        else:
            self.msg("You fail to break away!")

    def npc_combat_tick(self):
        self.ai_tick()

    def is_winning(self, target):
        return (self.db.hp or 0) > (target.db.hp or 0)

    def attempt_pursue(self, target):
        if not target or self.get_range(target) == "melee" or not self.is_winning(target):
            return False
        if random.randint(1, 100) >= 70:
            return False

        self.set_range(target, "near" if self.get_range(target) == "far" else "melee")
        self.set_roundtime(1.5)
        if self.location:
            self.location.msg_contents(f"{self.key} rushes forward to keep {target.key} engaged!")
        return True

    def attempt_retreat(self, target):
        if not target:
            return False
        if (self.db.hp or 0) >= ((self.db.max_hp or 1) * 0.3):
            return False
        if random.randint(1, 100) >= 30:
            return False

        self.set_range(target, "far")
        self.set_roundtime(1.5)
        if self.location:
            self.location.msg_contents(f"{self.key} attempts to flee!")
        return True

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if not normalized:
            return None

        responses = getattr(self.db, "inquiry_responses", None) or {}
        if isinstance(responses, dict):
            exact = responses.get(normalized)
            if exact:
                return str(exact)
            for key, value in responses.items():
                aliases = {part.strip().lower() for part in str(key or "").split("|") if part.strip()}
                if normalized in aliases:
                    return str(value)

        return getattr(self.db, "default_inquiry_response", None)


class EmpathGuildleader(NPC):
    # DRG-EMPATH-03: Merla is the grandfathered directengine_canon Empath
    # guildmaster seam for The Crossing guildhall. DRG-EMPATH-FOUNDATION-001
    # repaired the teaching allowlist; DRG-EMPATH-03 verified the world
    # content placement and preserved metadata.
    def at_object_creation(self):
        super().at_object_creation()
        self.db.guild_role = "guildmaster"
        self.db.trains_profession = "empath"
        self.db.default_inquiry_response = "Merla says, 'If you mean to join us, prove you can stand where the work is done first.'"

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if normalized in {"join", "guild", "empath", "healing"}:
            return "Merla says, 'Empaths do not join by wanting to be kind. You join by accepting another person's hurt and mastering your own.'"
        if normalized in {"patient", "training", "lesson"}:
            return "Merla says, 'The patient is in the training room. Touch the patient, read the wound, take it cleanly, then bear what you chose.'"
        return super().handle_inquiry(actor, topic)

    def teach_spell(self, actor, spell_name):
        return _teach_guild_spell(
            self,
            actor,
            spell_name,
            taught_spell_ids=_EMPATH_CANONICAL_TEACHING_IDS,
            enforce_circle=True,
        )


class RangerGuildleader(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.key = "Kalika"
        for alias in ["guildleader", "ranger guildleader", "kalika", "leader"]:
            self.aliases.add(alias)
        self.db.guild_role = "guildmaster"
        self.db.trains_profession = "ranger"
        self.db.default_inquiry_response = "Kalika says, 'Ask plainly. The wild does not waste breath, and neither will I.'"

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if normalized in {"join", "joining", "guild", "ranger"}:
            return (
                "Kalika says, 'Rangers aren't your run-of-the-mill types. Mostly we don't much like the city, since we have dedicated ourselves to the world outside of civilization. Ya see, when everyone got together and started building places like this city, there were a few -- a very rare few -- who saw that if everyone got together and huddled inside their villages and towns, there'd be no one to keep back the very things outside that they were running from.'\n\n"
                "Kalika says, 'So some of us gave up the water wells, the firesides, the feather beds and instead took it unto ourselves to preserve the glory of the meadows and the silent beauty of the forests. Our mattresses are the soft moss between the roots of the great oaks, our hearths a roaring campfire, our wells the rushing streams. Those of us who have become accustomed to the world outside of the city limits have grown to love it, and many have fought, and died, to preserve that which we have sworn to protect... even if it means that we sacrifice our very souls to save the soul of the wild lands.'\n\n"
                "Kalika says, 'Above all else, we are free. More free than the Trader forced to be ever moving, more free than the Empath bound to their patients. We are the wind, the hawk on the wing, the soaring spirit of the sky and the patient spirit of the earth. Our gold is sunlight, our gems are flowers, and our life... is the world's.'"
            )
        if normalized in {"advancement", "advance", "circle", "training"}:
            if not hasattr(actor, "is_profession") or not actor.is_profession("ranger"):
                return "Kalika says, 'The next trail can wait. First decide whether you mean to stand with us at all.'"
            eligible, reasons = actor.can_advance_ranger() if hasattr(actor, "can_advance_ranger") else (False, ["You are not ready."])
            if not eligible:
                detail = "; ".join(str(reason) for reason in (reasons or []) if str(reason).strip())
                return f"Kalika says, 'Not yet. {detail}'"
            current_circle = max(1, int(getattr(getattr(actor, 'db', None), 'circle', 1) or 1))
            actor.db.circle = current_circle + 1
            actor.db.ranger_circle = max(current_circle + 1, int(getattr(getattr(actor, 'db', None), 'ranger_circle', 1) or 1))
            return "Kalika says, 'Good. You have taken the first true step. Keep gathering from the wild and sharpen your awareness, because the land favors those who keep listening.'"
        if normalized in {"magic", "spell", "spells", "old ways"}:
            return "Kalika says, 'A Ranger's magic is the old ways remembered rather than mastered. Learn the land before you try to command anything within it.'"
        return super().handle_inquiry(actor, topic)

    def teach_spell(self, actor, spell_name):
        return _teach_guild_spell(
            self,
            actor,
            spell_name,
            taught_spell_ids=_RANGER_CANONICAL_TEACHING_IDS,
            enforce_circle=True,
        )


class RangerCompanion(NPC):
    """provenance: gsl_2004 — companion canonical model via DireLore audit (DRG-RANGER-COMPANION-CANON-AUDIT-001)"""

    ASSIST_SAME_ROOM_ONLY = False

    def __init__(self, *args, species=None, type_id=None, **kwargs):
        if species is not None:
            validate_companion_type(species)
        if type_id is not None:
            validate_companion_type(type_id)
        super().__init__(*args, **kwargs)

    def at_object_creation(self):
        super().at_object_creation()
        profile = get_companion_profile()
        self.db.is_ranger_companion = True
        self.db.companion_type_id = profile["type_id"]
        self.db.companion_state = COMPANION_STATE_DISMISSED
        self.db.owner_id = None
        self.db.bond = 50
        self.db.last_room_id = None
        self.db.companion_birth_time = time.time()
        self.db.companion_age = 0
        self.db.hunger = 0
        self.db.loneliness = 0
        self.db.assist = False
        self.db.aggressive = False
        self.db.follow_owner = True
        self.db.posture = "standing"
        self.db.is_hidden_companion = False
        self.db.last_owner_room_id = None
        self.db.last_search_target_id = None
        self.db.last_corpse_id = None
        self.key = profile["label"]

    def get_owner(self):
        owner_id = getattr(getattr(self, "db", None), "owner_id", None)
        if not owner_id:
            return None
        result = search_object(f"#{int(owner_id)}")
        return result[0] if result else None

    def set_owner(self, owner):
        self.db.owner_id = getattr(owner, "id", None) if owner is not None else None
        return self.get_owner()

    def clear_owner(self):
        self.db.owner_id = None
        self.db.companion_state = COMPANION_STATE_DISMISSED

    def set_companion_type(self, value):
        type_id = validate_companion_type(value)
        profile = get_companion_profile(type_id)
        self.db.companion_type_id = type_id
        self.key = profile["label"]
        return profile

    def set_companion_state(self, state):
        record = normalize_ranger_companion({"state": state, "type_id": getattr(self.db, "companion_type_id", None), "bond": getattr(self.db, "bond", 50)})
        self.db.companion_state = record["state"]
        return self.db.companion_state

    def configure_companion(self, *, owner, type_id, bond=50, state=COMPANION_STATE_PRESENT):
        profile = self.set_companion_type(type_id)
        self.set_owner(owner)
        self.db.bond = max(0, min(100, int(bond or 0)))
        self.set_companion_state(state)
        self.db.last_room_id = getattr(getattr(owner, "location", None), "id", None)
        self.db.last_owner_room_id = getattr(getattr(owner, "location", None), "id", None)
        self.db.follow_owner = True
        self.db.posture = "standing"
        self.db.is_hidden_companion = False
        self.db.assist = True
        self.db.aggressive = profile["type"] == "wolf"
        return profile

    def get_companion_record(self):
        return normalize_ranger_companion(
            {
                "type_id": getattr(self.db, "companion_type_id", None),
                "state": getattr(self.db, "companion_state", None),
                "bond": getattr(self.db, "bond", None),
                "entity_id": getattr(self, "id", None),
                "owner_id": getattr(self.db, "owner_id", None),
            }
        )

    def at_after_move(self, source_location, **kwargs):
        super().at_after_move(source_location, **kwargs)
        self.db.last_room_id = getattr(getattr(self, "location", None), "id", None)

    def can_assist(self):
        return bool(getattr(self.db, "assist", False)) and self.get_owner() is not None

    def get_profile(self):
        return get_companion_profile(getattr(self.db, "companion_type_id", None))

    def is_following_owner(self):
        return bool(getattr(self.db, "follow_owner", True))

    def set_follow_owner(self, value):
        self.db.follow_owner = bool(value)
        return self.db.follow_owner

    def _matches_owner(self, actor):
        owner = self.get_owner()
        return owner is not None and getattr(owner, "id", None) == getattr(actor, "id", None)

    def _is_present_and_available(self):
        if self.is_dead():
            return False
        state = str(getattr(self.db, "companion_state", "") or "").strip().lower()
        return state != COMPANION_STATE_DISMISSED

    def _move_to_room(self, room, *, move_type="companion"):
        if room is None:
            return False
        if getattr(self, "location", None) == room:
            return True
        return bool(self.move_to(room, quiet=True, move_type=move_type))

    def _find_named_object(self, collection, query):
        normalized = str(query or "").strip().lower()
        if not normalized:
            return None
        for obj in list(collection or []):
            names = {str(getattr(obj, "key", "") or "").strip().lower()}
            aliases = getattr(obj, "aliases", None)
            if aliases is not None:
                try:
                    names.update(str(alias or "").strip().lower() for alias in aliases.all())
                except Exception:
                    pass
            if normalized in names:
                return obj
            if any(normalized in name for name in names if name):
                return obj
        return None

    def _find_tease_item(self, actor):
        inventory = actor.get_visible_carried_items() if hasattr(actor, "get_visible_carried_items") else list(getattr(actor, "contents", []) or [])
        required = str(self.get_profile().get("bait_item", "") or "").strip().lower()
        if not required:
            return None
        for item in list(inventory or []):
            key = str(getattr(item, "key", "") or "").strip().lower()
            if required in key:
                return item
        return None

    def get_command_record(self):
        record = self.get_companion_record()
        record["following_owner"] = self.is_following_owner()
        record["posture"] = str(getattr(self.db, "posture", "standing") or "standing")
        record["hidden"] = bool(getattr(self.db, "is_hidden_companion", False))
        return record

    def command_follow(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        if not self._is_present_and_available():
            return False, "Your companion cannot answer you right now."
        self.set_follow_owner(True)
        self.db.is_hidden_companion = False
        self.set_companion_state(COMPANION_STATE_PRESENT)
        self.db.last_owner_room_id = getattr(getattr(actor, "location", None), "id", None)
        self._move_to_room(getattr(actor, "location", None), move_type="follow")
        return True, self.get_profile()["follow_message"]

    def command_stay(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        if not self._is_present_and_available():
            return False, "Your companion cannot answer you right now."
        self.set_follow_owner(False)
        self.set_companion_state(COMPANION_STATE_PRESENT)
        return True, self.get_profile()["stay_message"]

    def command_return(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        if not self._is_present_and_available():
            return False, "Your companion cannot answer you right now."
        self.set_follow_owner(True)
        self.db.is_hidden_companion = False
        self.set_companion_state(COMPANION_STATE_RETURNING)
        self._move_to_room(getattr(actor, "location", None), move_type="return")
        self.set_companion_state(COMPANION_STATE_PRESENT)
        self.db.last_owner_room_id = getattr(getattr(actor, "location", None), "id", None)
        return True, self.get_profile()["return_message"]

    def command_whistle(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the whistle."
        if not self._is_present_and_available():
            return False, "No answering movement comes from the wild."
        return self.command_return(actor)

    def command_find(self, actor, target=None):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        if not self._is_present_and_available():
            return False, "Your companion cannot answer you right now."

        destination = None
        subject = target or actor
        if subject == actor and hasattr(actor, "is_dead") and actor.is_dead() and hasattr(actor, "get_death_corpse"):
            corpse = actor.get_death_corpse()
            if corpse is not None:
                subject = corpse
        destination = getattr(subject, "location", None)
        if destination is None:
            return False, "Your companion has nothing to track there."

        self.set_follow_owner(False)
        self.set_companion_state(COMPANION_STATE_SEARCHING)
        self.db.last_search_target_id = getattr(subject, "id", None)
        self._move_to_room(destination, move_type="find")
        target_name = getattr(subject, "key", "your trail")
        return True, f"Your {self.get_profile()['type']} ranges out and finds {target_name}."

    def command_sit(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        self.db.posture = "sitting"
        return True, self.get_profile()["sit_message"]

    def command_stand(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        self.db.posture = "standing"
        return True, self.get_profile()["stand_message"]

    def command_hide(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        self.db.is_hidden_companion = True
        return True, self.get_profile()["hide_message"]

    def command_unhide(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        self.db.is_hidden_companion = False
        return True, self.get_profile()["unhide_message"]

    def command_hunt(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        self.set_follow_owner(False)
        self.set_companion_state(COMPANION_STATE_WANDERING)
        return True, self.get_profile()["hunt_message"]

    def command_get(self, actor, item_name):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        item = self._find_named_object(list(getattr(getattr(actor, "location", None), "contents", []) or []), item_name)
        if item is None or item == self or item == actor:
            return False, "Your companion cannot find that here."
        item.move_to(self, quiet=True, move_type="companion_get")
        return True, f"Your {self.get_profile()['type']} picks up {item.key}."

    def command_drop(self, actor, item_name):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        item = self._find_named_object(list(getattr(self, "contents", []) or []), item_name)
        if item is None:
            return False, "Your companion is not carrying that."
        item.move_to(getattr(actor, "location", None) or getattr(self, "location", None), quiet=True, move_type="companion_drop")
        return True, f"Your {self.get_profile()['type']} drops {item.key}."

    def command_give(self, actor, item_name, recipient=None):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        item = self._find_named_object(list(getattr(self, "contents", []) or []), item_name)
        if item is None:
            return False, "Your companion is not carrying that."
        recipient = recipient or actor
        if getattr(recipient, "location", None) != getattr(self, "location", None):
            return False, "Your companion cannot reach that target."
        item.move_to(recipient, quiet=True, move_type="companion_give")
        return True, f"Your {self.get_profile()['type']} brings {item.key} to {recipient.key}."

    def assist_owner(self, target, *, owner=None, reason="attack"):
        owner = owner or self.get_owner()
        if owner is None or not self._matches_owner(owner):
            return False, "Your companion has no bond to answer."
        if not self._is_present_and_available():
            return False, "Your companion cannot enter the fight."
        if target is None or target == self:
            return False, "Your companion needs a living target."
        if hasattr(target, "is_alive") and not target.is_alive():
            return False, "Your companion needs a living target."
        if getattr(target, "location", None) != getattr(owner, "location", None):
            return False, "Your companion cannot reach that target."

        self._move_to_room(getattr(owner, "location", None), move_type="assist")
        self.db.is_hidden_companion = False
        self.set_companion_state(COMPANION_STATE_PRESENT)
        self.add_threat(target, 15 if self.get_profile()["type"] == "wolf" else 8)
        self.set_target(target)
        if hasattr(self, "set_range"):
            self.set_range(target, "melee")
        return True, self.get_profile()["attack_message"].format(target=getattr(target, "key", "your foe"))

    def command_attack(self, actor, target):
        if not self._matches_owner(actor):
            return False, "Your companion ignores the order."
        return self.assist_owner(target, owner=actor, reason="command")

    def command_tease(self, actor):
        if not self._matches_owner(actor):
            return False, "Your companion ignores you."
        profile = self.get_profile()
        if not RangerSafService.is_companion_tease_enabled(actor):
            return False, profile["tease_blocked_message"]
        item = self._find_tease_item(actor)
        if item is None:
            return False, profile["tease_wrong_item_message"]
        self.db.bond = max(0, min(100, int(getattr(self.db, "bond", 50) or 50) + 1))
        return True, f"{profile['tease_ready_message']} {item.key.title()} disappears in a quick snap of jaws or paws."

    def handle_owner_move(self, owner, *, origin=None, destination=None):
        if not self._matches_owner(owner):
            return False
        self.db.last_owner_room_id = getattr(destination, "id", None)
        if not self.is_following_owner():
            return False
        if str(getattr(self.db, "companion_state", "") or "") == COMPANION_STATE_WANDERING:
            return False
        if destination is None or self.is_dead():
            return False
        self._move_to_room(destination, move_type="follow")
        self.set_companion_state(COMPANION_STATE_PRESENT)
        return True

    def handle_owner_death(self, owner, *, corpse=None):
        if not self._matches_owner(owner):
            return False, "Your companion does not answer that loss."
        if not self._is_present_and_available():
            return False, "No companion remains to search for you."
        subject = corpse or (owner.get_death_corpse() if hasattr(owner, "get_death_corpse") else None) or owner
        destination = getattr(subject, "location", None)
        if destination is None:
            return False, "Your companion cannot find your trail."
        self.set_follow_owner(False)
        self.set_companion_state(COMPANION_STATE_SEARCHING)
        self.db.last_corpse_id = getattr(subject, "id", None)
        self._move_to_room(destination, move_type="rescue")
        if destination is not None:
            destination.msg_contents(self.get_profile()["rescue_message"], exclude=[self])
        return True, self.get_profile()["rescue_message"]


class StatTrainerNPC(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_trainer = True
        self.db.trains_stat = None
        self.db.greeting = (
            "The trainer regards you thoughtfully, ready to assess your potential for improvement."
        )

    def handle_inquiry(self, actor, topic):
        if topic is None:
            return self.db.greeting
        return f"The {self.key} listens but says nothing in response to that yet."


class GuildLeaderNPC(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_guild_leader = True
        self.db.guild_role = "leader"
        self.db.leads_profession = None
        self.db.greeting = (
            "The guild leader inclines their head in greeting, appraising you with experienced eyes."
        )

    def handle_inquiry(self, actor, topic):
        if topic is None:
            return self.db.greeting
        return "The guild leader listens but says nothing in response to that yet."

    def teach_spell(self, actor, spell_name):
        return _teach_guild_spell(self, actor, spell_name)


class HealerNPC(NPC):
    # DRG-EMPATH-03: House healers are grandfathered directengine_canon
    # support NPCs used by the Empath guildhall's recovery and triage
    # spaces, not a separate canonical class-progression seam.
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_house_healer = True
        self.db.healing_fee = 25
        self.db.default_inquiry_response = "The healer says, 'If you need treatment, ask for healing plainly.'"

    def get_treatable_wound_total(self, actor):
        if not actor or not hasattr(actor, "get_empath_wounds"):
            return 0
        wounds = actor.get_empath_wounds()
        return sum(int(wounds.get(key, 0) or 0) for key in ("vitality", "bleeding", "poison", "disease"))

    def quote_healing_cost(self, actor):
        treatable = self.get_treatable_wound_total(actor)
        if treatable <= 0:
            return False, 0, "You have no treatable wounds."
        cost = max(1, int(getattr(self.db, "healing_fee", 25) or 25))
        return True, cost, f"{self.key} studies your condition and says, 'Treatment will cost {cost} coins. Type REQUEST HEALING CONFIRM if you wish to proceed.'"

    def perform_healing(self, actor):
        if not actor or not hasattr(actor, "set_empath_wound"):
            return False, "The healer cannot help you."
        changed = False
        for key in ("vitality", "bleeding", "poison", "disease"):
            current = int(actor.get_empath_wound(key) if hasattr(actor, "get_empath_wound") else 0)
            if current > 0:
                actor.set_empath_wound(key, 0)
                changed = True
        if changed:
            actor.msg(f"{self.key} treats your wounds with practiced detachment.")
            return True, f"{self.key} finishes the work without ceremony."
        return False, "You have no treatable wounds."

    def get_tip_response(self, amount):
        value = max(0, int(amount or 0))
        if value >= 25:
            return f"{self.key} inclines their head with visible approval. 'A thoughtful gesture.'"
        return f"{self.key} accepts the tip with clinical reserve. 'Noted.'"


class EmpathTutorialPatient(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_training_dummy = True
        self.db.is_tutorial_patient = True
        self.db.default_inquiry_response = None

    def get_vendor_interaction_lines(self, actor, action="shop"):
        attr_name = f"{str(action or 'shop').strip().lower()}_intro_lines"
        lines = getattr(self.db, attr_name, None)
        if isinstance(lines, (list, tuple)):
            return [str(line) for line in lines if str(line or "").strip()]
        if str(lines or "").strip():
            return [str(lines)]
        return []

    def get_vendor_sale_message(self, actor, item, value):
        template = str(getattr(self.db, "sale_message", "") or "").strip()
        if not template:
            return None
        return template.format(
            actor=getattr(actor, "key", "someone"),
            item=getattr(item, "key", "item"),
            value=actor.format_coins(value) if hasattr(actor, "format_coins") else str(value),
        )

    def get_vendor_purchase_message(self, actor, item_name, price):
        template = str(getattr(self.db, "purchase_message", "") or "").strip()
        if not template:
            return None
        return template.format(
            actor=getattr(actor, "key", "someone"),
            item=item_name,
            value=actor.format_coins(price) if hasattr(actor, "format_coins") else str(price),
        )


# DRG-CLERIC-03: ClericGuildmaster is directengine_canon per
# DRG-CANON-POLICY-001. This is the grandfathered guildmaster seam for
# the Crossing Cleric guildhall and remains the live training anchor.
class ClericGuildmaster(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.key = "Guildleader Esuin"
        for alias in ["guildleader", "cleric guildleader", "esuin", "leader"]:
            self.aliases.add(alias)
        self.db.is_trainer = True
        self.db.trains_profession = "cleric"
        self.db.guild_role = "guildmaster"
        self.db.desc = (
            "A grave, composed cleric stands with the settled authority of someone long accustomed to prayer, duty, and the burdens that follow both. "
            "Esuin's attention feels exacting, but never theatrical."
        )
        self.db.default_inquiry_response = "Esuin says, 'Ask plainly. Faith dislikes evasions nearly as much as the dead do.'"

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if not normalized:
            return super().handle_inquiry(actor, topic)

        if normalized in {"join", "joining", "guild", "cleric", "oath"}:
            if hasattr(actor, "is_profession") and actor.is_profession("cleric"):
                return "Esuin says, 'You already stand in service. See that your conduct keeps pace with your vows.'"
            return (
                "Esuin says, 'A cleric's path is not ornament. It is duty, devotion, and the willingness to stand where death and fear test weaker vows. "
                "If you would take that burden, speak the joining plainly.'"
            )

        if normalized in {"magic", "mana", "study", "training"}:
            return (
                "Esuin says, 'You will begin with discipline before grandeur. Learn prayer, theurgy, and the ordered use of holy power. "
                "Miracles without devotion are only badly aimed appetite.'"
            )

        return super().handle_inquiry(actor, topic)

    def teach_spell(self, actor, spell_name):
        return _teach_guild_spell(
            self,
            actor,
            spell_name,
            taught_spell_ids=_CLERIC_CANONICAL_TEACHING_IDS,
            enforce_circle=True,
        )


def _load_guard_npc_class():
    guard_module_path = Path(__file__).with_name("npcs") / "guard.py"
    spec = importlib.util.spec_from_file_location("typeclasses._guard_npc_impl", guard_module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load guard NPC typeclass from {guard_module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.GuardNPC.__module__ = __name__
    return module.GuardNPC


GuardNPC = _load_guard_npc_class()