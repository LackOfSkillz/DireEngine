def _is_player_character(target):
    if not target or not hasattr(target, "is_typeclass"):
        return False
    if not target.is_typeclass("typeclasses.characters.Character", exact=False):
        return False
    return not bool(getattr(target.db, "is_npc", False))


def msg_actor(actor, text):
    actor.msg(text)


def msg_room(actor, text, exclude=None):
    if not actor.location:
        return
    actor.location.msg_contents(text, exclude=exclude or [])


def msg_detecting_observers(actor, text_func, observers):
    for observer in observers:
        observer.msg(text_func(observer))


def msg_target_player_only(target, text):
    if _is_player_character(target):
        target.msg(text)


def react_or_message_target(target, player_text=None, awareness=None):
    if _is_player_character(target):
        if player_text:
            target.msg(player_text)
    elif awareness and hasattr(target, "set_awareness"):
        target.set_awareness(awareness)