import time

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.scripts import Script


class OnboardingRoleplayScript(Script):
    def at_script_creation(self):
        self.key = "onboarding_roleplay"
        self.interval = 5
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def is_valid(self):
        obj = self.obj
        role = str(getattr(getattr(obj, "db", None), "onboarding_role", "") or "").lower()
        return bool(obj and role in {"mentor", "gremlin"})

    def at_repeat(self):
        def _run():
            obj = self.obj
            room = getattr(obj, "location", None)
            if not obj or not room:
                return
            from systems import onboarding

            last_prompt = dict(getattr(self.db, "last_prompt_by_character", {}) or {})
            now = time.time()
            for occupant in list(getattr(room, "contents", []) or []):
                if not getattr(occupant, "has_account", False):
                    continue
                if not onboarding.is_onboarding_character(occupant):
                    continue
                character_id = str(getattr(occupant, "id", "") or "")
                if onboarding.prompt_spacing_active(occupant, minimum_interval=2.5):
                    continue
                if now - float(last_prompt.get(character_id, 0.0) or 0.0) < 20.0:
                    continue
                state = onboarding.ensure_onboarding_state(occupant)
                delay = now - max(
                    float(state.get("last_progress_at", 0.0) or 0.0),
                    float(state.get("room_entered_at", 0.0) or 0.0),
                )
                room_key = str(getattr(getattr(occupant, "location", None), "key", "") or "")
                role = str(getattr(getattr(obj, "db", None), "onboarding_role", "") or "").lower()
                if onboarding.remind_objective_if_idle(occupant, idle_threshold=5.0, minimum_interval=12.0):
                    last_prompt[character_id] = now
                    break
                if role == "gremlin" and room_key == "Gear Rack Room" and delay > 10.0:
                    if onboarding.trigger_gear_delay_scene(occupant):
                        last_prompt[character_id] = now
                        break
                if role == "gremlin" and room_key == "Training Yard" and delay > 8.0:
                    if onboarding.trigger_almost_failure_scene(occupant):
                        last_prompt[character_id] = now
                        break
                line = onboarding.get_roleplay_nudge(obj, occupant)
                if not line:
                    continue
                onboarding.emit_npc_line(occupant, obj, line)
                last_prompt[character_id] = now
                break
            self.db.last_prompt_by_character = last_prompt

        self._track_repeat_timing("script:OnboardingRoleplayScript", _run)


class OnboardingGuidePromptScript(Script):
    def at_script_creation(self):
        self.key = "onboarding_guide_prompt"
        self.interval = 6
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def is_valid(self):
        obj = self.obj
        return bool(obj and obj.db.is_onboarding_guide)

    def at_repeat(self):
        def _run():
            obj = self.obj
            room = getattr(obj, "location", None)
            if not obj or not room:
                return
            from systems.chargen import mirror as chargen_mirror
            from systems import onboarding

            for occupant in list(getattr(room, "contents", []) or []):
                if not getattr(occupant, "has_account", False):
                    continue
                if chargen_mirror.is_chargen_active(occupant):
                    if chargen_mirror.maybe_nudge_if_idle(occupant, idle_threshold=5.0, minimum_interval=6.0):
                        break
                    continue
                if not onboarding.is_onboarding_character(occupant):
                    continue
                if onboarding.remind_objective_if_idle(occupant, idle_threshold=5.0, minimum_interval=5.0):
                    break

        self._track_repeat_timing("script:OnboardingGuidePromptScript", _run)


class OnboardingInvasionScript(Script):
    def at_script_creation(self):
        self.key = "onboarding_invasion"
        self.interval = 6
        self.start_delay = True
        self.repeats = 0
        self.persistent = True

    def is_valid(self):
        obj = self.obj
        return bool(obj and obj.db.is_tutorial)

    def _find_room(self, key):
        for room in ObjectDB.objects.filter(db_key__iexact=key):
            if room.db.is_tutorial:
                return room
        return None

    def _get_onboarding_characters(self):
        from systems import onboarding

        characters = []
        for room_name in [
            "Wake Room",
            "Intake Hall",
            "Lineup Platform",
            "Mirror Alcove",
            "Gear Rack Room",
            "Weapon Cage",
            "Training Yard",
            "Supply Shack",
            "Vendor Stall",
            "Breach Corridor",
            "Outer Gate",
            "Secret Tunnel",
        ]:
            room = self._find_room(room_name)
            if not room:
                continue
            for occupant in list(getattr(room, "contents", []) or []):
                if getattr(occupant, "has_account", False) and onboarding.is_onboarding_character(occupant):
                    characters.append(occupant)
        return characters

    def _active_breach_goblins(self):
        return [
            obj for obj in ObjectDB.objects.filter(db_location=self.obj)
            if bool(getattr(getattr(obj, "db", None), "is_npc", False))
            if str(getattr(getattr(obj, "db", None), "onboarding_enemy_role", "") or "").lower() == "breach"
            and int(getattr(getattr(obj, "db", None), "hp", 0) or 0) > 0
        ]

    def _spawn_breach_goblin(self):
        spawn_count = int(getattr(self.db, "spawn_count", 0) or 0)
        if spawn_count >= 2:
            return None
        goblin = create_object("typeclasses.npcs.NPC", key="breach goblin", location=self.obj, home=self.obj)
        goblin.aliases.add("goblin")
        goblin.db.desc = "A panicked goblin forces its way through the broken line, all quick slashes and uglier nerve."
        goblin.db.is_npc = True
        goblin.db.is_tutorial_enemy = True
        goblin.db.onboarding_enemy_role = "breach"
        goblin.db.hp = 28
        goblin.db.max_hp = 28
        goblin.db.balance = 70
        goblin.db.max_balance = 70
        self.db.spawn_count = spawn_count + 1
        return goblin

    def at_repeat(self):
        def _run():
            from systems import onboarding

            characters = self._get_onboarding_characters()
            if not characters:
                self.db.stage = "idle"
                self.db.announced_warning = False
                return

            ready = [char for char in characters if "economy" in set(onboarding.ensure_onboarding_state(char).get("completed_steps") or []) and "breach" not in set(onboarding.ensure_onboarding_state(char).get("completed_steps") or [])]
            if not ready:
                self.db.stage = "idle"
                self.db.announced_warning = False
                self.db.stabilized = False
                return

            stage = str(getattr(self.db, "stage", "idle") or "idle")
            if stage == "idle":
                self.db.stage = "warning"
                self.db.stage_started_at = time.time()
                if not bool(getattr(self.db, "announced_warning", False)):
                    self.obj.msg_contents('A horn sounds somewhere deeper in the compound, followed by the scrape of something forcing metal wide.')
                    for char in ready:
                        onboarding.note_breach_progress(char, "start")
                        onboarding.note_step_failure(char, "breach")
                    self.db.announced_warning = True
                return

            if stage == "warning":
                if time.time() - float(getattr(self.db, "stage_started_at", 0.0) or 0.0) < 6.0:
                    return
                self.obj.msg_contents("A training horn cracks across the compound, then cuts off mid-call as something slams into the outer braces.")
                self.db.stage = "first_contact"
                self.db.stage_started_at = time.time()
                return

            if stage == "first_contact":
                if time.time() - float(getattr(self.db, "stage_started_at", 0.0) or 0.0) < 6.0:
                    return
                self.obj.msg_contents("A barricade post jumps in its brackets, showering dust and splinters into the corridor.")
                self.db.stage = "breach"
                self.db.stage_started_at = time.time()
                return

            if stage == "breach" and not self._active_breach_goblins():
                self._spawn_breach_goblin()
                self.obj.msg_contents("A goblin squeezes through the breach with a ragged shriek as the outer door buckles inward.")
                self.db.stage = "active"
                self.db.stage_started_at = time.time()
                return

            if stage == "active":
                if self._active_breach_goblins():
                    return
                if int(getattr(self.db, "spawn_count", 0) or 0) < 2:
                    self.db.stage = "breach"
                    return
                if not bool(getattr(self.db, "stabilized", False)):
                    self.obj.msg_contents("The corridor steadies as the last shove against the gate fails and the broken barricade settles back into place.")
                    self.db.stabilized = True
                    self.db.stage = "stabilization"
                    self.db.stage_started_at = time.time()
                return

            if stage == "stabilization" and not bool(getattr(self.db, "stabilized_mentor_line", False)):
                self.obj.msg_contents('Marshal Vey shouts from down the corridor, "Hold it there. That was the push."')
                self.db.stabilized_mentor_line = True

        self._track_repeat_timing("script:OnboardingInvasionScript", _run)