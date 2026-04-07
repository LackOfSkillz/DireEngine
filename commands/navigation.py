def _normalized_names_for_exit(exit_obj):
    names = {str(getattr(exit_obj, "key", "") or "").strip().lower()}
    aliases = getattr(getattr(exit_obj, "aliases", None), "all", lambda: [])()
    names.update(str(alias or "").strip().lower() for alias in aliases)
    return {name for name in names if name}


def find_named_exit(room, name):
    if not room:
        return None
    normalized = str(name or "").strip().lower()
    if not normalized:
        return None

    exits = list(getattr(room, "exits", []) or [])
    for exit_obj in exits:
        if normalized == str(getattr(exit_obj, "key", "") or "").strip().lower():
            return exit_obj
    for exit_obj in exits:
        if normalized in _normalized_names_for_exit(exit_obj):
            return exit_obj
    return None


def traverse_named_exit(caller, name):
    room = getattr(caller, "location", None)
    exit_obj = find_named_exit(room, name)
    if not exit_obj:
        return False
    if hasattr(exit_obj, "access") and not exit_obj.access(caller, "traverse"):
        if hasattr(exit_obj, "access"):
            exit_obj.access(caller, "traverse")
        return True
    target = getattr(exit_obj, "destination", None)
    if not target:
        return False
    exit_obj.at_traverse(caller, target)
    return True