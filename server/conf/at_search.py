"""Search hook customizations for hidden-target filtering."""

from evennia.utils.utils import at_search_result as default_at_search_result


def _should_filter_for_caller(caller):
    if not caller:
        return False
    if not hasattr(caller, "can_perceive"):
        return False
    if not hasattr(caller, "location"):
        return False
    return True


def _is_perceivable_match(match, caller):
    if not caller or not hasattr(caller, "can_perceive"):
        return True
    if not hasattr(match, "is_hidden"):
        return True
    if not hasattr(match, "location"):
        return True
    return caller.can_perceive(match)


def at_search_result(matches, caller, query="", quiet=False, **kwargs):
    """Filter hidden targets from object searches, then delegate to Evennia's default handler."""
    filtered_matches = matches
    if _should_filter_for_caller(caller) and isinstance(matches, list):
        filtered_matches = [match for match in matches if _is_perceivable_match(match, caller)]

    return default_at_search_result(filtered_matches, caller, query=query, quiet=quiet, **kwargs)
