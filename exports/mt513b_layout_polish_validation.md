# MT-513b Layout Polish Validation

## Scope
Validated the MT-513b Zone Score layout polish against:
- `docs/mt513b_layout_polish_dispatch.md`

Touched implementation files:
- `web/templates/webclient/direbuilder.html`
- `web/static/webclient/css/direbuilder.css`
- `web/static/webclient/js/direbuilder.js`

## Runtime Refresh
- Restarted the local Evennia web server after the MT-513b edits.
- Confirmed refreshed page served updated assets:
  - `direbuilder.css?v=18`
  - `direbuilder.js?v=21`

## Live DireBuilder Validation

### builder2 (`/direbuilder/?zone=builder2`)
- Confirmed the Zone Score header is now a single clickable button block.
- Confirmed the bardic tier label still renders correctly:
  - Composite: `57`
  - Tier: `It's a bit mid, don't you think?`
- Confirmed sub-scores now render as one compact inline sequence with bullet separators in the live DOM snapshot:
  - `Completeness 63 • Depth 6 • Engagement 100`
- Confirmed the right edge has breathing room:
  - measured right-gap from header promo to viewport edge: `55px`
- Confirmed tooltip icon still renders on the Zone Score tagline.
- Confirmed tooltip still opens and displays the `zone_score.header` content.

### Overlay behavior
- Confirmed the breakdown panel now renders as a floating overlay with `position: fixed`.
- Confirmed the panel no longer pushes the workspace down:
  - `.direbuilder-map-panel` top before open: `1178`
  - `.direbuilder-map-panel` top after open: `1178`
  - Result: `no vertical workspace shift`
- Confirmed click-outside dismissal works.
- Confirmed `Escape` dismissal works.
- Confirmed `aria-expanded` tracks open/close correctly.
- Confirmed the overlay remains interactive while open.

### Room jump behavior
- Opened the overlay and clicked the first `Needs Attention` room.
- Confirmed the clicked row selected the room in the editor:
  - target room id: `CRO_450_350`
  - editor heading after click: `CRO_450_350`

### Stale / save / refetch cycle
- Edited `Short Description` on `CRO_450_350`.
- Confirmed stale indicator appeared immediately.
- Saved the zone successfully.
- Confirmed stale indicator cleared after save.
- Confirmed the score payload refetched with a new timestamp:
  - before: `2026-04-30T20:02:00.698447Z`
  - after save: `2026-04-30T20:03:02.077107Z`
- Restored the edited field afterward.
- No save error occurred.

## Large-zone validation

### new_landing (`/direbuilder/?zone=new_landing`)
- Confirmed the long tier label renders in the compact header without truncation:
  - Composite: `48`
  - Tier: `The townsfolk will throw rotten food at you`
- Confirmed the overlay opens on the large zone without shifting the workspace:
  - Result: `no vertical workspace shift`
- Confirmed the breakdown overlay still shows all four MT-513 sections unchanged:
  - Completeness
  - Depth
  - Engagement
  - Needs Attention

## Legacy builder isolation
- Confirmed `/builder/` still loads.
- Confirmed no Zone Score UI is present there.
- Confirmed no `quest_hooks` references are present in the legacy builder UI.

## Notes
- The integrated browser viewport used for validation is narrow enough that the floating overlay may clamp left and narrow its width to stay onscreen. The key behavioral requirement still held: the panel stayed floating and did not displace the work area.
- MT-513 functionality remained intact after the layout polish:
  - scoring unchanged
  - stale/refetch unchanged
  - tooltip unchanged
  - room jump unchanged
  - legacy `/builder/` untouched

## Result
MT-513b layout polish is implemented and live-validated.
The breakdown panel now behaves as a floating overlay instead of pushing the workspace down, and the score header reads as a more compact single widget.