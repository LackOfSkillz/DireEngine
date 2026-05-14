"""Three-audience messaging helpers for player-visible actions.

DragonRealms canon treats public actions as separate views for the actor,
the target when one exists, and room observers. These helpers package the
standard Evennia sends into one call so new actions do not silently omit
one of those audiences.
"""

from typing import Optional


def send_action_messages(
    actor,
    target=None,
    room=None,
    actor_message: Optional[str] = None,
    target_message: Optional[str] = None,
    room_message: Optional[str] = None,
    room_exclude_actor: bool = True,
    room_exclude_target: bool = True,
) -> None:
    """Send actor, target, and room messages for a single action."""
    if actor and actor_message:
        actor.msg(actor_message)

    if target and target_message:
        target.msg(target_message)
    elif target and room_message and not target_message:
        target.msg(room_message)

    if not room_message:
        return

    location = room or getattr(actor, "location", None)
    if not location:
        return

    exclude = []
    if actor and room_exclude_actor:
        exclude.append(actor)
    if target and room_exclude_target:
        exclude.append(target)
    location.msg_contents(room_message, exclude=exclude or None)


def send_untargeted_action(
    actor,
    room=None,
    actor_message: Optional[str] = None,
    room_message: Optional[str] = None,
) -> None:
    """Convenience wrapper for public actions without a direct target."""
    send_action_messages(
        actor=actor,
        target=None,
        room=room,
        actor_message=actor_message,
        room_message=room_message,
    )