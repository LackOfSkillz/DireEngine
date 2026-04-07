from .flow import APPEARANCE_FIELDS, CHARGEN_STEPS, format_chargen_summary, render_step_prompt
from .state import ChargenState
from .validators import (
    apply_stat_allocation,
    build_description_from_appearance,
    build_final_stats,
    format_stat_assignment_summary,
    release_name,
    reserve_name,
    reset_stat_allocation,
    validate_appearance_complete,
    validate_appearance_value,
    validate_step_input,
)


class ChargenController:
    def __init__(self, state=None, account=None):
        self.state = state or ChargenState()
        self.account = account

    def start(self, reset=False):
        if reset:
            if self.state.reserved_name:
                release_name(self.state.reserved_name)
            self.state = ChargenState()
        self.state.last_validation_error = None
        return self.status(include_summary=False)

    def status(self, include_summary=True):
        payload = {
            "ok": True,
            "step": self.state.current_step,
            "prompt": render_step_prompt(self.state),
            "blueprint": self.state.blueprint.to_dict(),
            "appearance": dict(self.state.appearance or {}),
            "points_remaining": self.state.points_remaining,
        }
        if include_summary:
            payload["summary"] = format_chargen_summary(self.state)
        return payload

    def handle_input(self, command, args=None):
        action = str(command or "").strip().lower()
        if action in {"charcreate", "chargen"}:
            return self.start(reset=action == "charcreate" and str(args or "").strip().lower() == "reset")
        if action in {"cancel", "chargencancel"}:
            return self.cancel()
        if action == "back":
            return self.go_back()
        if action == "next":
            return self.advance_step()
        if action == "resetstats":
            return self.reset_stats(args)
        if action == "stat":
            return self.apply_stat_command(args)
        if action in APPEARANCE_FIELDS:
            return self.apply_appearance(action, args)
        if self.state.current_step == "confirm" and action == "confirm":
            return self.confirm()
        return self.submit(args if args is not None else command, action=action)

    def submit(self, value, action=None):
        ok, error = validate_step_input(self.state.current_step, value, state=self.state)
        if not ok:
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}

        if self.state.current_step == "name":
            if self.state.reserved_name:
                release_name(self.state.reserved_name)
            ok, error = reserve_name(value)
            if not ok:
                self.state.last_validation_error = error
                return {"ok": False, "error": error, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}
            self.state.reserved_name = str(value).strip()
            self.state.blueprint.name = self.state.reserved_name
        elif self.state.current_step == "race":
            self.state.blueprint.race = str(value).strip()
            self.state.blueprint.stats = build_final_stats(self.state)
        elif self.state.current_step == "gender":
            self.state.blueprint.gender = str(value).strip().lower()
        self.state.last_validation_error = None

        self.advance()
        return {
            "ok": True,
            "step": self.state.current_step,
            "blueprint": self.state.blueprint.to_dict(),
            "preview_stats": build_final_stats(self.state),
            "prompt": render_step_prompt(self.state),
        }

    def advance(self):
        current_index = CHARGEN_STEPS.index(self.state.current_step)
        if current_index < len(CHARGEN_STEPS) - 1:
            self.state.current_step = CHARGEN_STEPS[current_index + 1]
        return self.state.current_step

    def advance_step(self):
        if self.state.current_step == "stats":
            if self.state.points_remaining > 0:
                error = "You must assign all remaining stat points before continuing."
                self.state.last_validation_error = error
                return {"ok": False, "error": error, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}
            self.state.blueprint.stats = build_final_stats(self.state)
            self.advance()
            return {"ok": True, "step": self.state.current_step, "prompt": render_step_prompt(self.state), "blueprint": self.state.blueprint.to_dict()}
        if self.state.current_step == "description":
            ok, error = validate_appearance_complete(self.state)
            if not ok:
                self.state.last_validation_error = error
                return {"ok": False, "error": error, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}
            self.state.blueprint.appearance = dict(self.state.appearance or {})
            self.state.blueprint.description = build_description_from_appearance(self.state)
            self.advance()
            return {"ok": True, "step": self.state.current_step, "prompt": render_step_prompt(self.state), "blueprint": self.state.blueprint.to_dict()}
        error = "Use the step command for this stage of character creation."
        self.state.last_validation_error = error
        return {"ok": False, "error": error, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}

    def go_back(self):
        current_index = CHARGEN_STEPS.index(self.state.current_step)
        if current_index > 0:
            self.state.current_step = CHARGEN_STEPS[current_index - 1]
        self.state.last_validation_error = None
        return {"ok": True, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}

    def cancel(self):
        if self.state.reserved_name:
            release_name(self.state.reserved_name)
        self.state = ChargenState()
        return {"ok": True, "step": "cancelled", "message": "Character creation cancelled."}

    def apply_stat_command(self, args):
        if self.state.current_step != "stats":
            error = "You can only assign stats during the stats step."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        if int(getattr(self.state, "points_remaining", 0) or 0) <= 0:
            error = "Starting stats are fixed by race in this version."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        raw_args = str(args or "").strip().split()
        if len(raw_args) != 2:
            error = "Usage: stat <name> <amount>"
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        stat_name, amount = raw_args
        try:
            apply_stat_allocation(self.state, stat_name, int(amount))
        except ValueError as exc:
            self.state.last_validation_error = str(exc)
            return {"ok": False, "error": str(exc), "step": self.state.current_step}
        self.state.blueprint.stats = build_final_stats(self.state)
        self.state.last_validation_error = None
        return {
            "ok": True,
            "step": self.state.current_step,
            "preview_stats": build_final_stats(self.state),
            "summary": format_stat_assignment_summary(self.state),
            "prompt": render_step_prompt(self.state),
        }

    def reset_stats(self, args):
        if self.state.current_step != "stats":
            error = "You can only reset stats during the stats step."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        if int(getattr(self.state, "points_remaining", 0) or 0) <= 0:
            error = "Starting stats are fixed by race in this version."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        if str(args or "").strip().lower() != "confirm":
            error = "Use 'resetstats confirm' to reset your stat allocation."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        reset_stat_allocation(self.state)
        self.state.blueprint.stats = build_final_stats(self.state)
        self.state.last_validation_error = None
        return {
            "ok": True,
            "step": self.state.current_step,
            "summary": format_stat_assignment_summary(self.state),
            "prompt": render_step_prompt(self.state),
        }

    def apply_appearance(self, field, args):
        if self.state.current_step != "description":
            error = "You can only set appearance during the appearance step."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        ok, error = validate_appearance_value(field, args)
        if not ok:
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step, "prompt": render_step_prompt(self.state)}
        self.state.appearance[str(field).strip().lower()] = str(args or "").strip().lower()
        self.state.blueprint.appearance = dict(self.state.appearance or {})
        if all(self.state.appearance.get(part) for part in APPEARANCE_FIELDS):
            self.state.blueprint.description = build_description_from_appearance(self.state)
        self.state.last_validation_error = None
        return {
            "ok": True,
            "step": self.state.current_step,
            "appearance": dict(self.state.appearance or {}),
            "prompt": render_step_prompt(self.state),
        }

    def confirm(self):
        if self.state.current_step != "confirm":
            error = "You can only confirm character creation at the final step."
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        if not self.account:
            return {"ok": True, "step": self.state.current_step, "blueprint": self.state.blueprint.to_dict()}
        from systems.character.creation import create_character_from_blueprint
        from systems.character.creation import CharacterCreationError

        try:
            character, errors = create_character_from_blueprint(
                self.account,
                self.state.blueprint,
                allow_reserved_name=bool(self.state.reserved_name),
            )
        except CharacterCreationError as exc:
            error = str(exc)
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        if errors:
            error = "; ".join(str(error) for error in errors)
            self.state.last_validation_error = error
            return {"ok": False, "error": error, "step": self.state.current_step}
        if self.state.reserved_name:
            release_name(self.state.reserved_name)
            self.state.reserved_name = None
        self.state.last_validation_error = None
        return {"ok": True, "character": character, "step": "complete"}
