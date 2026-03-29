## Report — Microtasks 221-240

### MT221 - Create WearableContainer typeclass
- Added `WearableContainer` in `typeclasses/wearable_containers.py`.
- The new base typeclass initializes container-specific state for wearable storage items:
	- `self.db.is_container = True`
	- `self.db.capacity = 1`
	- `self.db.allowed_types = []`
- Result: PASS

### MT222 - Add container ownership rule
- Added `is_worn()` to `typeclasses/wearable_containers.py`.
- Container use now resolves from actual equipped ownership through `self.db.worn_by`.
- Result: PASS

### MT223 - Add can_hold_item validation
- Added `can_hold_item(item)` to `typeclasses/wearable_containers.py`.
- Validation now blocks when:
	- the container is not being worn
	- the item is not currently carried by the wearer
	- the item is already being worn
	- the container is full
	- the item type is not allowed
- Result: PASS

### MT224 - Add store_item method
- Added `store_item(item)` to `typeclasses/wearable_containers.py`.
- Successful stow now:
	- moves the item into the wearable container object
	- records `item.db.stored_in`
	- returns tactile stow messaging
- Result: PASS

### MT225 - Add retrieve_item method
- Added `retrieve_item(item_name)` to `typeclasses/wearable_containers.py`.
- Retrieval now:
	- searches stored contents by key/alias match
	- moves the item back to the wearer
	- clears `item.db.stored_in`
	- returns draw messaging
- Result: PASS

### MT226 - Create stow command
- Reworked `commands/cmd_stow.py` around worn containers instead of the earlier sheath-only path.
- `stow <item>` now:
	- searches worn containers
	- uses an explicitly named container when provided with `in <container>`
	- fails cleanly if no worn container is available
	- fails cleanly if more than one container is worn and no target is specified
- Result: PASS

### MT227 - Create draw command
- Reworked `commands/cmd_draw.py` around worn containers instead of the earlier sheath-only path.
- `draw <item>` now:
	- searches worn containers
	- supports `from <container>` targeting
	- returns the item to inventory
	- auto-wields retrieved weapons
- Result: PASS

### MT228 - Create test scabbard
- Updated `commands/cmd_spawnsheath.py` so test sheaths/scabbards spawn directly into the caller's inventory.
- The back scabbard remains a wearable back-slot container with weapon-only storage.
- Result: PASS

### MT229 - Tag weapons with item_type
- Added `self.db.item_type = "weapon"` to `Weapon.at_object_creation()` in `typeclasses/weapons.py`.
- This now drives wearable-container type filtering.
- Result: PASS

### MT230 - Prevent storing equipped weapon
- Added active-item guardrails to the new container path so worn items cannot be stowed directly.
- For wielded weapons, the implementation follows the optional safer behavior from MT231 by clearing the equipped weapon state during stow instead of leaving stale wield references behind.
- Result: PASS

### MT231 - Auto-unwield on stow
- Added auto-unwield handling in `WearableContainer.store_item()`.
- When the stowed item is the currently equipped weapon, the equipped-weapon reference is cleared before the move.
- Result: PASS

### MT232 - Show container contents in appearance
- Added owner-visible contents rendering in `WearableContainer.return_appearance()`.
- Owners now see:
	- `It currently holds:` followed by stored items
	- or `It currently holds: empty.`
- Result: PASS

### MT233 - Hide container contents from room view
- Restricted container contents display in `return_appearance()` so only the wearer sees stored items.
- Observers can still see the container object, but not its contents.
- Result: PASS

### MT234 - Prevent stowing items not carried
- Added carried-item validation in `can_hold_item()`.
- Stowing now fails with `You must be holding that.` when the item is not in the wearer's inventory.
- Result: PASS

### MT235 - Validate capacity
- Live-tested a one-capacity scabbard with two weapons.
- Confirmed the second stow fails with:
	- `It cannot hold anything more.`
- Result: PASS

### MT236 - Validate wrong type
- Live-tested stowing a non-weapon wearable into a weapon-only scabbard.
- Confirmed the stow fails with:
	- `That does not fit.`
- Result: PASS

### MT237 - Validate worn requirement
- Live-tested attempting to stow into an unworn scabbard.
- Confirmed the action fails with:
	- `You must be wearing it to use it.`
- Result: PASS

### MT238 - Full stow/draw loop
- Live-tested the full loop with a disposable character:
	- wear scabbard
	- stow weapon
	- draw weapon
	- stow weapon again
- Confirmed:
	- clean movement between inventory and container
	- no duplication
	- clean equipped-weapon state when stowing
- Result: PASS

### MT239 - Validate persistence
- Performed a reload with a disposable weapon stored inside a worn scabbard.
- Verified after reload by dbref comparison that:
	- the weapon still had the scabbard as its location
	- `item.db.stored_in` still pointed at the scabbard
- Result: PASS

### MT240 - Full system validation
- Reloaded Evennia successfully after implementation.
- Validated:
	- worn-only container use
	- type filtering
	- capacity enforcement
	- auto-unwield on stow
	- owner-only contents visibility
	- reload persistence
	- no ghost items or duplication during the disposable tests
- Result: PASS

## Batch Outcome

- Sheaths and scabbards now operate as real wearable containers instead of ad hoc storage helpers.
- Storage is now tied directly to equipped ownership.
- Draw and stow flows now move actual objects cleanly between inventory and worn containers.
- The equipment foundation is now ready for broader pouch/quiver/container work.

## Validation Summary

- Reloaded Evennia successfully after the implementation pass.
- Live-validated with disposable test objects:
	- unworn container rejection
	- wrong-type rejection
	- one-item capacity enforcement
	- clean stow/draw loop behavior
	- auto-unwield on stow
	- owner-only container contents visibility
- Performed a second reload with a stored test weapon left in place and confirmed persistence by stable dbref comparison.
- Deleted all disposable test objects after validation.

## Implementation Note

- The original sheath code path was replaced with a generalized wearable-container layer so the same storage rules can support future scabbards, pouches, and quivers.
- During validation, object-identity comparison in Evennia shell gave a misleading false negative for persistence checks; the final persistence verification was performed by comparing dbrefs instead, which confirmed the stored state survived reload correctly.