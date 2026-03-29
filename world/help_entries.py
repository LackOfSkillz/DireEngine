"""
File-based help entries. These complements command-based help and help entries
added in the database using the `sethelp` command in-game.

Control where Evennia reads these entries with `settings.FILE_HELP_ENTRY_MODULES`,
which is a list of python-paths to modules to read.

A module like this should hold a global `HELP_ENTRY_DICTS` list, containing
dicts that each represent a help entry. If no `HELP_ENTRY_DICTS` variable is
given, all top-level variables that are dicts in the module are read as help
entries.

Each dict is on the form
::

    {'key': <str>,
     'text': <str>}``     # the actual help text. Can contain # subtopic sections
     'category': <str>,   # optional, otherwise settings.DEFAULT_HELP_CATEGORY
     'aliases': <list>,   # optional
     'locks': <str>       # optional, 'view' controls seeing in help index, 'read'
                          #           if the entry can be read. If 'view' is unset,
                          #           'read' is used for the index. If unset, everyone
                          #           can read/view the entry.

"""

HELP_ENTRY_DICTS = [
    {
        "key": "evennia",
        "aliases": ["ev"],
        "category": "General",
        "locks": "read:perm(Developer)",
        "text": """
            Evennia is a MU-game server and framework written in Python. You can read more
            on https://www.evennia.com.

            # subtopics

            ## Installation

            You'll find installation instructions on https://www.evennia.com.

            ## Community

            There are many ways to get help and communicate with other devs!

            ### Discussions

            The Discussions forum is found at https://github.com/evennia/evennia/discussions.

            ### Discord

            There is also a discord channel for chatting - connect using the
            following link: https://discord.gg/AJJpcRUhtF

        """,
    },
    {
        "key": "getting started",
        "aliases": ["start", "basics"],
        "category": "General",
        "text": """
Start with the core player commands on the first help page, then branch into the
system guides that fit what you want to do.

- `stats`, `injuries`, `skills`, and `mindstate` show your current condition.
- `inventory`, `wear`, `remove`, `wield`, `unwield`, `draw`, and `stow` handle gear.
- `attack`, `target`, `stance`, `disengage`, and `tend` cover combat.
- `observe`, `search`, `hide`, `sneak`, `forage`, `inspect`, and `pick` cover fieldcraft.

Examples:

- `stats`
- `inventory`
- `wear cloak`
- `wield sword`
- `attack goblin`
- `inspect practice box`
- `tend left arm`

Useful follow-up topics:

- `help combat`
- `help equipment`
- `help character`
- `help fieldcraft`

Use `help <command>` for details on a specific command.
        """,
    },
    {
        "key": "combat",
        "aliases": ["fighting"],
        "category": "Combat",
        "text": """
Combat commands are meant to be short and direct.

- `attack <target>` starts or continues an attack.
- `target <part>` focuses your attacks on `head`, `chest`, `arm`, or `leg`.
- `stance <0-100>` shifts you toward offense or defense.
- `disengage` steps out of the fight.
- `tend <body part>` tries to stop bleeding.

Examples:

- `attack corl`
- `target head`
- `stance 70`
- `disengage`
- `tend chest`
        """,
    },
    {
        "key": "equipment",
        "aliases": ["gear"],
        "category": "Equipment",
        "text": """
Equipment commands help you manage what you carry, wear, and ready for combat.

- `inventory` lists carried items.
- `wear <item>` puts on gear you are carrying.
- `remove <item>` takes off worn gear.
- `wield <item>` readies an item for fighting.
- `unwield` lowers your current weapon.
- `draw <item>` and `stow <item>` move gear in and out of worn containers.
- `drop <item>` puts something on the ground.
- `slots` shows which worn slots are filled.

Examples:

- `wear belt sheath`
- `draw sword`
- `stow dagger in belt sheath`
- `drop cloak`
        """,
    },
    {
        "key": "character",
        "aliases": ["status"],
        "category": "Character",
        "text": """
Character commands help you read your current state.

- `stats` shows condition, attributes, and active learning.
- `injuries` shows wounds and bleeding.
- `skills` shows all known skills.
- `mindstate` shows only skills that are learning right now.
- `use <skill>` tries a skill directly when that makes sense.

Examples:

- `stats`
- `injuries`
- `skills`
- `mindstate`
- `use disengage`
        """,
    },
    {
        "key": "fieldcraft",
        "aliases": ["exploration", "survival", "stealth", "perception"],
        "category": "Survival",
        "text": """
    Fieldcraft covers awareness, stealth, environmental actions, and trap or loot work.

    - `observe` and `search` reveal hidden details.
    - `hide`, `unhide`, `sneak`, `stalk`, and `ambush` handle stealth.
    - `forage`, `climb`, and `swim` handle common wilderness actions.
    - `inspect`, `disarm`, `pick`, and `open` handle boxes, traps, and locks.
    - `analyze`, `harvest`, and `skin` handle creature resource gathering.

    Examples:

    - `search`
    - `hide`
    - `forage`
    - `inspect iron lockbox`
    - `pick iron lockbox with crude`
    - `harvest carcass`
        """,
        },
        {
        "key": "training gear",
        "aliases": ["practice gear", "builder tools"],
        "category": "Builder",
        "text": """
These utility commands create practice gear and test targets.

- `spawnnpc` creates a practice NPC in the room.
- `spawnweapon` creates a practice weapon.
- `spawnwearable` creates practice wearable gear.
- `spawnsheath` creates a practice sheath or scabbard.

Examples:

- `spawnnpc`
- `spawnweapon dagger`
- `spawnwearable armor`
- `spawnsheath back`
        """,
    },
]
