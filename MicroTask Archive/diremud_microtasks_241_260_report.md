## Report — Microtasks 241-260

### MT241 - Add slot-grouped worn display (self)
- Updated `typeclasses/characters.py` so self-look now groups worn gear by slot instead of rendering a flat item list.
- Added a shared appearance slot order covering:
	- `head`
	- `face`
	- `neck`
	- `shoulders`
	- `torso`
	- `back`
	- `arms`
	- `hands`
	- `waist`
	- `legs`
	- `feet`
	- `fingers`
- Multi-slot entries such as rings now render under their slot group.
- Result: PASS

### MT242 - Add slot-grouped worn display (others)
- Updated observer-facing appearance in `typeclasses/characters.py`.
- Observers now see a clean worn-items list without internal slot labels.
- Result: PASS

### MT243 - Improve condition descriptions
- Added `get_condition_text()` to `typeclasses/characters.py`.
- Condition now resolves to smoother narrative states:
	- `in perfect health`
	- `in good shape`
	- `slightly wounded`
	- `badly wounded`
	- `on the brink of collapse`
	- `dead`
- Result: PASS

### MT244 - Integrate condition into appearance
- Updated `return_appearance()` to use `get_condition_text()` instead of the older blunt condition labels.
- Condition text now appears in both self and observer views.
- Result: PASS

### MT245 - Add bleeding description layer
- Added `get_bleed_text(looker=None)` to `typeclasses/characters.py`.
- Appearance now adds:
	- `You are bleeding.` for self-look
	- `They are bleeding.` for observer look
- Bleeding only appears when the character's bleed state is active.
- Result: PASS

### MT246 - Hide internal debug/state info from look
- Kept `return_appearance()` fully narrative.
- Look output now avoids numeric resource values and internal state/debug terms.
- Result: PASS

### MT247 - Add held/wielded item display
- Preserved and integrated wielded-weapon visibility in the new appearance layout.
- Characters still show wielded weapons separately from worn gear.
- Result: PASS

### MT248 - Add inventory visibility (others)
- Added a minimal observer-facing carry hint in `typeclasses/characters.py`.
- Observers now see:
	- `They are carrying some items.`
- No carried item list is leaked.
- Result: PASS

### MT249 - Add container visibility hint
- Worn containers remain visible as part of the grouped worn-gear output.
- Container contents are no longer shown inline in general appearance output.
- Result: PASS

### MT250 - Improve look formatting spacing
- Reworked section assembly in `return_appearance()` and `get_equipment_display_lines()` to keep spacing clean between:
	- description
	- wielded item display
	- worn gear
	- carry hint
	- flavor hooks
	- condition/bleed text
- Result: PASS

### MT251 - Add flavor descriptions hook
- Added `get_flavor_text()` to `typeclasses/characters.py`.
- The default implementation returns `None` for now.
- Hook is wired into `return_appearance()` for future descriptive systems.
- Result: PASS

### MT252 - Add equipment-based flavor hook
- Added `get_equipment_flavor()` to `typeclasses/characters.py`.
- The default implementation returns `None` for now.
- Hook is wired into `return_appearance()` for future armor/equipment flavor systems.
- Result: PASS

### MT253 - Add perception stub (future stealth)
- Added `can_perceive(target)` to `typeclasses/characters.py`.
- It currently always returns `True`.
- Result: PASS

### MT254 - Gate appearance through perception
- Updated `return_appearance()` so it first checks the looker's perception gate.
- If perception fails, appearance returns:
	- `You see nothing unusual.`
- Current behavior is unchanged because the perception stub always returns `True`.
- Result: PASS

### MT255 - Normalize all messaging tone
- Kept appearance output fully narrative and removed any system-facing resource terminology from the look layer.
- Result: PASS

### MT256 - Validate self look
- Live-validated self-look with a disposable test character.
- Confirmed self-look included:
	- description
	- grouped worn gear by slot
	- narrative condition text
	- narrative bleeding text
- Result: PASS

### MT257 - Validate look other player
- Live-validated observer-facing look.
- Confirmed observer view included:
	- condition
	- visible worn items
	- wielded-item visibility when applicable
	- no slot labels leaking to observers
- Result: PASS

### MT258 - Validate container secrecy
- Live-validated a worn scabbard containing a stored weapon.
- Confirmed observers could see the container but not the stored item.
- Result: PASS

### MT259 - Validate weapon visibility
- Preserved weapon visibility as a separate appearance line from worn gear.
- Confirmed wielded items still render distinctly in the appearance block.
- Result: PASS

### MT260 - Full system validation
- Reloaded Evennia successfully after implementation.
- Validated:
	- grouped slot display for self
	- clean item list display for observers
	- multi-slot grouping for rings
	- narrative condition text
	- bleeding visibility when active
	- carried-item hint without inventory leaks
	- hidden container contents from room observers
	- no crashes during reload or live shell validation
- Result: PASS

## Batch Outcome

- Character appearance now reads as a narrative presentation layer instead of a debug/status dump.
- Worn gear is structured and readable.
- Observer information is intentionally limited to what should be perceivable.
- The system now has the hooks needed for future stealth, flavor, and armor-driven appearance extensions.

## Validation Summary

- Reloaded Evennia successfully after the implementation pass.
- Live-validated with disposable test characters, worn items, rings, a scabbard, and a stored weapon.
- Confirmed:
	- self-look groups gear by slot
	- observer look shows gear cleanly without slot labels
	- condition and bleeding text render correctly
	- observer carry visibility is only a presence hint
	- container contents remain hidden from observers
	- inline container-content leaks were removed from appearance output
- Deleted all disposable validation objects after the test completed.