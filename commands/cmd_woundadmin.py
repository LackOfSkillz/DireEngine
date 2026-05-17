from collections.abc import Mapping

from commands.command import Command
from engine.services.messaging import send_action_messages, send_untargeted_action


def _clamp_percent(value):
    return max(0, min(100, int(value or 0)))


def _format_part_name(target, part_name):
    if hasattr(target, "format_body_part_name"):
        return target.format_body_part_name(part_name, title=True)
    return str(part_name or "").replace("_", " ").replace("-", " ").title()


def _recalculate_summary_wounds(target):
    injuries = getattr(getattr(target, "db", None), "injuries", None) or {}
    vitality = 0
    bleeding = 0
    for body_part in dict(injuries).values():
        if not isinstance(body_part, Mapping):
            continue
        vitality += max(0, int(body_part.get("external", 0) or 0))
        vitality += max(0, int(body_part.get("internal", 0) or 0))
        bleeding += max(0, int(body_part.get("bleed", 0) or 0))
    target.set_empath_wound("vitality", _clamp_percent(vitality))
    target.set_empath_wound("bleeding", _clamp_percent(bleeding))
    return {
        "vitality": _clamp_percent(vitality),
        "bleeding": _clamp_percent(bleeding),
    }


class CmdWoundAdmin(Command):
    """
    Apply a controlled wound profile to a target body part.

    Examples:
        @wound SmokeEmpathLive chest 10 0 2
        @wound SmokeEmpathLive left_arm 4 0 1
    """

    key = "@wound"
    aliases = ["woundtest", "testwound"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        raw_args = str(self.args or "").strip()
        parts = raw_args.split()
        if len(parts) < 5:
            caller.msg("Usage: @wound <target> <part> <external> <internal> <bleed>")
            return

        target_query = " ".join(parts[:-4]).strip()
        part_name = parts[-4]
        try:
            external = _clamp_percent(parts[-3])
            internal = _clamp_percent(parts[-2])
            bleed = _clamp_percent(parts[-1])
        except (TypeError, ValueError):
            caller.msg("External, internal, and bleed values must be integers.")
            return

        target = caller.search(target_query, global_search=True)
        if not target:
            return
        if not all(hasattr(target, attr) for attr in ("get_body_part", "normalize_body_part_name", "set_empath_wound")):
            caller.msg(f"You cannot apply a test wound to {target.key}.")
            return

        target.ensure_core_defaults()
        normalized_part = target.normalize_body_part_name(part_name)
        injuries = dict(getattr(target.db, "injuries", None) or {})
        if normalized_part not in injuries:
            caller.msg(f"{_format_part_name(target, part_name)} is not a valid wound location on {target.key}.")
            return

        body_part = dict(target.get_body_part(normalized_part) or {})
        body_part["external"] = external
        body_part["internal"] = internal
        body_part["bleed"] = bleed
        body_part["tended"] = False
        body_part["tend"] = {
            "strength": 0,
            "duration": 0,
            "last_applied": 0.0,
            "min_until": 0.0,
        }
        injuries[normalized_part] = body_part
        target.db.injuries = injuries

        summary = _recalculate_summary_wounds(target)
        if hasattr(target, "update_bleed_state"):
            target.update_bleed_state()
        if hasattr(target, "sync_client_state"):
            target.sync_client_state()

        part_display = _format_part_name(target, normalized_part)
        actor_message = (
            f"You set {target.key}'s {part_display} wounds to external {external}, internal {internal}, bleed {bleed} "
            f"(summary vitality {summary['vitality']}, bleeding {summary['bleeding']})."
        )
        target_message = (
            f"A testing force sets your {part_display.lower()} wounds to external {external}, internal {internal}, bleed {bleed}."
        )
        room_message = f"{target.key} suddenly winces as a test wound profile settles in."

        if target != caller:
            send_action_messages(
                actor=caller,
                target=target,
                room=getattr(target, "location", None) or getattr(caller, "location", None),
                actor_message=actor_message,
                target_message=target_message,
                room_message=room_message,
            )
            return

        send_untargeted_action(
            caller,
            actor_message=actor_message,
            room_message=room_message,
        )