import random

from evennia import Command


class CmdTend(Command):
    """
    Try to stop bleeding on one of your injured body parts.

    Examples:
      tend head
      tend left arm
      ten chest
    """

    key = "tend"
    aliases = ["ten"]
    help_category = "Combat"

    def resolve_tend_target(self):
        query = (self.args or "").strip()
        if not query:
            return None

        if query.lower() in {"self", "me", "myself"}:
            return self.caller

        target = self.caller.search(query)
        if not target:
            return None

        if not hasattr(target, "get_first_bleeding_part") or not hasattr(target, "get_body_part"):
            self.caller.msg("You can only tend living targets with injuries.")
            return None

        if hasattr(target, "is_alive") and not target.is_alive():
            self.caller.msg(f"{target.key} is beyond your aid.")
            return None

        return target

    def func(self):
        if not self.caller.is_alive():
            self.caller.msg("You cannot tend wounds while defeated.")
            return

        if self.caller.is_in_roundtime():
            self.caller.msg_roundtime_block()
            return

        if not self.args:
            self.caller.msg("Which body part are you trying to tend?")
            return

        patient = self.caller
        part_key = self.caller.normalize_body_part_name(self.args)
        bp = patient.get_body_part(part_key)

        if not bp:
            patient = self.resolve_tend_target()
            if not patient:
                return
            part_key = patient.get_first_bleeding_part()
            if not part_key:
                fallback_part = patient.get_first_bleeding_part(include_tended=True)
                if fallback_part and patient.is_tended(fallback_part):
                    fallback_display = patient.format_body_part_name(fallback_part)
                    if patient == self.caller:
                        self.caller.msg(f"Your {fallback_display} is already tended.")
                    else:
                        self.caller.msg(f"{patient.key}'s {fallback_display} is already tended.")
                elif patient == self.caller:
                    self.caller.msg("You are not bleeding anywhere that needs tending.")
                else:
                    self.caller.msg(f"{patient.key} is not bleeding anywhere that needs tending.")
                return
            bp = patient.get_body_part(part_key)

        part_display = patient.format_body_part_name(part_key)

        trauma = patient.get_part_trauma(bp)
        if trauma <= 0 and bp.get("bleed", 0) <= 0:
            if patient == self.caller:
                self.caller.msg(f"Your {part_display} does not need tending.")
            else:
                self.caller.msg(f"{patient.key}'s {part_display} does not need tending.")
            return

        if bp["bleed"] <= 0:
            if patient == self.caller:
                self.caller.msg(f"Your {part_display} is not bleeding.")
            else:
                self.caller.msg(f"{patient.key}'s {part_display} is not bleeding.")
            return

        if hasattr(patient, "is_alive") and not patient.is_alive():
            if patient == self.caller:
                self.caller.msg("You cannot tend wounds while defeated.")
            else:
                self.caller.msg(f"{patient.key} is beyond your aid.")
            return

        if patient.is_tended(part_key):
            if patient == self.caller:
                self.caller.msg(f"Your {part_display} is already tended.")
            else:
                self.caller.msg(f"{patient.key}'s {part_display} is already tended.")
            return

        bleed = bp["bleed"]
        severity_penalty = bleed * 12
        wound_penalty = trauma // 5
        skill_name = "first_aid"
        skill_rank = self.caller.get_skill_rank(skill_name)
        aptitude = (
            self.caller.get_stat("wisdom")
            + self.caller.get_stat("intelligence")
            + self.caller.get_stat("discipline")
        ) // 3
        success_chance = max(15, min(95, 35 + (skill_rank * 5) + aptitude - severity_penalty - wound_penalty))
        difficulty = max(10, (bleed * 10) + wound_penalty)
        self.caller.use_skill(
            skill_name,
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
            learning_multiplier=4,
        )
        self.caller.set_roundtime(3)
        if random.randint(1, 100) <= success_chance:
            patient.apply_tend(part_key, tender=self.caller)
            patient.heal_body_part(part_key, 5 + max(0, skill_rank // 5))
            if patient == self.caller:
                message = f"You tend your {part_display}."
            else:
                message = f"You tend {patient.key}'s {part_display}."
                self.caller.msg(message)
                patient.msg(f"{self.caller.key} tends your {part_display}.")
            if patient == self.caller:
                self.caller.msg(message)
            if self.caller.location:
                action = (
                    f"{self.caller.key} tends to their {part_display}."
                    if patient == self.caller
                    else f"{self.caller.key} tends to {patient.key}'s {part_display}."
                )
                self.caller.location.msg_contents(
                    action,
                    exclude=[self.caller, patient] if patient != self.caller else self.caller,
                )
            try:
                from systems import onboarding

                completed, awarded = onboarding.note_healing_action(self.caller, patient=patient, part=part_key)
                if completed and awarded:
                    self.caller.msg(onboarding.format_token_feedback(onboarding.ensure_onboarding_state(self.caller)))
            except Exception:
                pass
            return

        if patient == self.caller:
            self.caller.msg(f"You fail to stop the bleeding on your {part_display}.")
        else:
            self.caller.msg(f"You fail to stop the bleeding on {patient.key}'s {part_display}.")
            patient.msg(f"{self.caller.key} fails to stop the bleeding on your {part_display}.")
        if self.caller.location:
            action = (
                f"{self.caller.key} tends to their {part_display}, but fails to stop the bleeding."
                if patient == self.caller
                else f"{self.caller.key} tends to {patient.key}'s {part_display}, but fails to stop the bleeding."
            )
            self.caller.location.msg_contents(
                action,
                exclude=[self.caller, patient] if patient != self.caller else self.caller,
            )
        try:
            from systems import onboarding

            onboarding.note_step_failure(self.caller, "healing")
        except Exception:
            pass