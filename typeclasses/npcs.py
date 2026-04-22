import random
import time
from collections.abc import Mapping
import importlib.util
from pathlib import Path

from django.utils.text import slugify

from server.systems.loot.loot_runtime import on_npc_defeated

from typeclasses.characters import Character


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


class HealerNPC(NPC):
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


class RangerGuildmaster(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.key = "Elarion"
        for alias in ["guildmaster", "ranger guildmaster", "elarion"]:
            self.aliases.add(alias)
        self.db.is_trainer = True
        self.db.trains_profession = "ranger"
        self.db.guild_role = "guildmaster"
        self.db.desc = (
            "A weathered ranger stands with the unhurried stillness of someone who has spent more time reading wind and brush than walls. "
            "Nothing about Elarion is ornate, but every tool and motion looks deliberate."
        )
        self.db.default_inquiry_response = "The wild answers patience better than hurry. Ask plainly if you want useful counsel."

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if not normalized:
            return super().handle_inquiry(actor, topic)

        if normalized in {"join", "joining", "guild", "ranger", "oath"}:
            if hasattr(actor, "is_profession") and actor.is_profession("ranger"):
                return "You already wear the path. Keep your eyes open, your hands useful, and your word clean."
            return (
                "If you're going to stand with us, do it clean.\n"
                "Elarion gives you a brief, measuring look.\n"
                "You're close enough. Say it, and mean it."
            )

        if normalized in {"training", "train", "practice"}:
            return "Start with the land itself. Forage, scout, learn to notice what others miss, and keep a weapon close enough to finish what you find."

        if normalized in {"advancement", "advance", "circle", "promotion"}:
            if not hasattr(actor, "can_advance_ranger"):
                return "Join us first. Advancement means nothing to someone still outside the path."
            can_advance, reason = actor.can_advance_ranger()
            if not can_advance:
                if isinstance(reason, list):
                    return "\n".join(str(entry) for entry in reason if str(entry).strip())
                return reason or "You are not ready to advance."
            if hasattr(actor, "set_ranger_circle"):
                actor.set_ranger_circle(max(2, int(getattr(actor.db, "ranger_circle", 1) or 1)))
            else:
                actor.db.circle = 2
                actor.db.ranger_circle = 2
                if hasattr(actor, "sync_client_state"):
                    actor.sync_client_state()
            return (
                "Elarion studies you for a long moment.\n"
                "\"You have taken your first true step into the wilds.\"\n"
                "You feel your understanding deepen."
            )

        return super().handle_inquiry(actor, topic)


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


class RangerMentor(NPC):
    domain = None
    inquiry_topics = ()
    mentor_aliases = ()
    mentor_desc = ""
    mentor_default_inquiry = "Ask about training if you want field-ready counsel."

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_trainer = True
        self.db.trains_profession = "ranger"
        self.db.guild_role = "mentor"
        self.db.mentor_domain = self.domain
        if self.mentor_desc:
            self.db.desc = self.mentor_desc
        if self.mentor_default_inquiry:
            self.db.default_inquiry_response = self.mentor_default_inquiry
        for alias in list(self.mentor_aliases or []):
            self.aliases.add(alias)

    def get_inquiry_topics(self):
        topics = {str(self.domain or "").strip().lower()}
        for topic in list(self.inquiry_topics or []):
            normalized = str(topic or "").strip().lower()
            if normalized:
                topics.add(normalized)
        return {topic for topic in topics if topic}

    def handle_inquiry(self, actor, topic):
        normalized = str(topic or "").strip().lower()
        if not normalized:
            return super().handle_inquiry(actor, topic)

        if normalized in {"training", "train", "practice"} | self.get_inquiry_topics():
            return self.training_response(actor)

        return super().handle_inquiry(actor, topic)

    def training_response(self, speaker):
        return "You should not see this."


class BramThornhand(RangerMentor):
    domain = "survival"
    inquiry_topics = ("forage", "foraging", "skin", "skinning")
    mentor_aliases = ("bram", "thornhand")
    mentor_desc = "A broad-shouldered ranger with scarred hands and an easy stance watches the guild court like a man who has spent years learning what land will give and what it will take."
    mentor_default_inquiry = "If you want survival counsel, ask plain and expect work instead of shortcuts."

    def training_response(self, speaker):
        return "The wild provides, if you know how to listen. Start with forage. Learn what grows beneath your feet, and do not waste the hide of anything you bring down."


class SerikVale(RangerMentor):
    domain = "hunting"
    inquiry_topics = ("hunt", "bow", "bows", "aim", "ranged")
    mentor_aliases = ("serik", "vale")
    mentor_desc = "A lean ranger keeps his bow close and his words spare, every motion measured like a shot he has already decided to take."
    mentor_default_inquiry = "If you want hunting advice, ask before you loose something you cannot call back."

    def training_response(self, speaker):
        return "A clean shot ends suffering quickly. Practice your aim, learn your distance, and respect your prey enough to finish the work cleanly."


class LysaWindstep(RangerMentor):
    domain = "scouting"
    inquiry_topics = ("scout", "stealth", "hidden", "movement")
    mentor_aliases = ("lysa", "windstep")
    mentor_desc = "A wiry ranger studies the lanes beyond the guild with patient attention, as if she is tracking movement no one else has noticed yet."
    mentor_default_inquiry = "If you want scouting counsel, ask before you blunder loud enough to warn the whole street."

    def training_response(self, speaker):
        return "You are loud. The forest hears you coming, and so does any quarry worth catching. Learn to scout, move without being noticed, and trust what your eyes tell you before your pride does."

    def get_vendor_interaction_lines(self, actor, action="shop"):
        if str(action or "shop").strip().lower() == "shop":
            return [
                "Lysa unrolls a compact spread of field-tuned gear and taps the pieces built for real climbs.",
                "Nothing here is ornamental. Every piece looks worn into usefulness.",
            ]
        return super().get_vendor_interaction_lines(actor, action=action)

    def get_vendor_purchase_message(self, actor, item_name, price):
        return f"Lysa passes you {item_name} and says, 'If you trust it, use it hard.'"


class OrrenMossbinder(RangerMentor):
    domain = "lore"
    inquiry_topics = ("magic", "spells", "nature", "ritual")
    mentor_aliases = ("orren", "mossbinder")
    mentor_desc = "A quiet ranger tends bundled herbs and field notes with the care of someone who treats old knowledge as a tool instead of a trophy."
    mentor_default_inquiry = "If you want lore, ask with intention. The old ways do not answer idle mouths."

    def training_response(self, speaker):
        return "There is power in the old ways, but power without understanding just leaves wreckage. Learn the names of things first. Control comes after."


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