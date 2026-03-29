# commands/

This folder holds modules for implementing one's own commands and
command sets. All the modules' classes are essentially empty and just
imports the default implementations from Evennia; so adding anything
to them will start overloading the defaults. 

You can change the organisation of this directory as you see fit, just
remember that if you change any of the default command set classes'
locations, you need to add the appropriate paths to
`server/conf/settings.py` so that Evennia knows where to find them.
Also remember that if you create new sub directories you must put
(optionally empty) `__init__.py` files in there so that Python can
find your modules.

## Custom command notes

- `attack` has alias `att`
- `draw` has alias `dra` and draws a stowed weapon from a worn sheath
- `disengage` has alias `dis`
- `drop` overrides the default drop flow so worn items are automatically removed before dropping
- `inventory` overrides the default inventory flow and excludes worn items from carried-item output
- `stats` has aliases `health`, `hp`, and `sta`
- `injuries` has aliases `bleeding`, `wounds`, and `inj`
- `mindstate` has aliases `learn`, `learning`, and `mnd`
- `remove` has alias `rem` and removes worn equipment back into inventory
- `skills` has alias `ski`
- `slots` has alias `slt` and shows current slot occupancy for debugging
- `tend` has alias `ten`
- `wield` has alias `wie`
- `spawnnpc` has alias `spn`
- `spawnsheath` has alias `sps` and supports `belt`, `back`, or `generic`
- `spawnwearable` has alias `spwa` and creates a torso-slot test wearable in inventory
- `spawnweapon` has alias `spw`
- `renew` has alias `ren` and supports `renew`, `renew <target>`, `renew room`, and `renew all` for admin/developer accounts
- `wear` has alias `wea` and equips wearable items into slot-backed equipment state
- `stow` has alias `sto` and stores a carried weapon in your worn sheath; `stow <weapon> in <sheath>` explicitly targets one worn sheath
- `unwield` has alias `unw` and clears your currently wielded weapon
