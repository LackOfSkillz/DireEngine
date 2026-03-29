# Welcome to Evennia!

This is your game directory, set up to let you start with
your new game right away. An overview of this directory is found here:
https://github.com/evennia/evennia/wiki/Directory-Overview#the-game-directory

You can delete this readme file when you've read it and you can
re-arrange things in this game-directory to suit your own sense of
organisation (the only exception is the directory structure of the
`server/` directory, which Evennia expects). If you change the structure
you must however also edit/add to your settings file to tell Evennia
where to look for things.

Your game's main configuration file is found in
`server/conf/settings.py` (but you don't need to change it to get
started). If you just created this directory (which means you'll already
have a `virtualenv` running if you followed the default instructions),
`cd` to this directory then initialize a new database using

    evennia migrate

To start the server, stand in this directory and run

    evennia start

This will start the server, logging output to the console. Make
sure to create a superuser when asked. By default you can now connect
to your new game using a MUD client on `localhost`, port `4000`.  You can
also log into the web client by pointing a browser to
`http://localhost:4001`.

# Quick testing

After login, Limbo includes a persistent `training dummy` NPC for combat testing.

- use `attack training dummy` to exercise retaliation/combat timing
- use `att training dummy` as the short alias during live combat testing
- use `health` or `hp` as aliases for `stats` when checking your current condition
- as an admin/developer, use `renew`, `renew <target>`, `renew room`, or `renew all` to fully restore test characters and NPCs
- use `spawnwearable`, `wear`, `remove`, `inv`, and `slots` to validate the slot-based equipment foundation
- use `spawnsheath belt` or `spawnsheath back`, `get <sheath>`, `wear <sheath>`, and `stow <weapon>` to test sheath storage; after the first stow, that worn sheath becomes the remembered default home for later `stow <weapon>` use
- use `draw <weapon>` as the explicit verb for pulling a weapon back out of a worn sheath

# Getting started

From here on you might want to look at one of the beginner tutorials:
http://github.com/evennia/evennia/wiki/Tutorials.

Evennia's documentation is here:
https://github.com/evennia/evennia/wiki.

Enjoy!
