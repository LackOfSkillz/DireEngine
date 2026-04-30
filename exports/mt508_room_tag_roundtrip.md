# MT-508 Room Tag Vocab Parity

## Outcome

- Added server-side room tag vocab payload injection for DireBuilder room tag editors.
- Converted schema-constrained room tag fields from freeform add/remove inputs to vocab-backed pill pickers.
- Preserved `tags.custom` as the only freeform room tag field.
- Reused the existing MT-507z chip editor pattern rather than introducing a second picker implementation.

## Fields Covered

- Scalar room tags: `structure`, `specific_function`, `named_feature`, `condition`
- Atmosphere multi-value tags: `materials`, `social_character`, `surroundings`, `sensory`
- Atmosphere single-value tag: `upkeep`
- Freeform retained: `custom`

## Validation

- Verified the live DireBuilder page serves the new room tag vocab payload and updated `direbuilder.js` asset.
- Confirmed room tag accordions render vocab pills for controlled fields and a freeform add/remove editor for `custom`.
- Performed a live save on `builder2` room `CRO_450_300` using:
  - `structure = plaza`
  - `custom += mt508-custom`
  - `atmosphere.social_character += affluent`
  - `atmosphere.upkeep = shabby`
- Captured the outgoing save payload and verified `atmosphere.materials` and `atmosphere.social_character` were serialized as arrays, including the single-selected `social_character` value.
- Reloaded the page and confirmed all edited room tag summaries persisted through refresh.
- Restored the validation room back to its prior tag state and confirmed the page returned to clean state with no save-error banner.

## Files Changed

- `web/views.py`
- `web/templates/webclient/direbuilder.html`
- `web/static/webclient/js/direbuilder.js`