"""
Changing the default command parser

The cmdparser is responsible for parsing the raw text inserted by the
user, identifying which command/commands match and return one or more
matching command objects. It is called by Evennia's cmdhandler and
must accept input and return results on the same form. The default
handler is very generic so you usually don't need to overload this
unless you have very exotic parsing needs; advanced parsing is best
done at the Command.parse level.

The default cmdparser understands the following command combinations
(where [] marks optional parts.)

[cmdname[ cmdname2 cmdname3 ...] [the rest]

A command may consist of any number of space-separated words of any
length, and contain any character. It may also be empty.

The parser makes use of the cmdset to find command candidates. The
parser return a list of matches. Each match is a tuple with its first
three elements being the parsed cmdname (lower case), the remaining
arguments, and the matched cmdobject from the cmdset.


This module is not accessed by default. To tell Evennia to use it
instead of the default command parser, add the following line to
your settings file:

    COMMAND_PARSER = "server.conf.cmdparser.cmdparser"

"""


from evennia.commands import cmdparser as default_cmdparser


def _build_prefix_matches(raw_string, cmdset):
    """Build fallback matches by treating the first token as a command prefix."""
    if not raw_string:
        return []

    command_token = raw_string.split(None, 1)[0].lower()
    if not command_token:
        return []

    matches = []
    for cmd in cmdset:
        match_names = sorted(
            {str(name).lower() for name in getattr(cmd, "_matchset", set()) if name},
            key=lambda name: (-len(name), name),
        )
        for name in match_names:
            if name.startswith(command_token):
                matches.append(default_cmdparser.create_match(command_token, raw_string, cmd, name))
                break

    return matches


def cmdparser(raw_string, cmdset, caller, match_index=None):
    """
    This function is called by the cmdhandler once it has
    gathered and merged all valid cmdsets valid for this particular parsing.

    raw_string - the unparsed text entered by the caller.
    cmdset - the merged, currently valid cmdset
    caller - the caller triggering this parsing
    match_index - an optional integer index to pick a given match in a
                  list of same-named command matches.

    Returns:
     list of tuples: [(cmdname, args, cmdobj, cmdlen, mratio), ...]
            where cmdname is the matching command name and args is
            everything not included in the cmdname. Cmdobj is the actual
            command instance taken from the cmdset, cmdlen is the length
            of the command name and the mratio is some quality value to
            (possibly) separate multiple matches.

    """
    matches = default_cmdparser.cmdparser(raw_string, cmdset, caller, match_index=match_index)
    if matches:
        return matches

    matches = _build_prefix_matches(raw_string, cmdset)
    matches = [match for match in matches if match[2].access(caller, "cmd")]

    if len(matches) > 1:
        return [matches[0]]
    return matches
