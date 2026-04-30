# MT-507t 2b.2 Triage Questions and 2b.3 Prep

This note captures the agreed diagnostic questions for Phase 2b.2 and the follow-up framing for Phase 2b.3.

## 2b.2 Triage Questions

1. Did the YAML write path discover any read-shape information that the existing read path silently dropped?

   This is the round-tripping question in disguise. If 2b.2 reports that the read payload does not preserve enough shape information for population dual-path write-back, that is an architectural problem to solve before later phases.

2. Did the in-flight UI lock require any unexpected reach into existing UI components?

   Pills, accordions, exit dropdowns, and pill toggles all need to disable cleanly. If the implementation needs a shared helper or global editable-control registry, that is a signal the page is nearing the point where a more formal state-management pass may be warranted in Phase 3.

3. Did the canonical-zone-on-success response cause any JSON shape mismatches with what the page expects on initial load?

   If backend canonical output differs materially from the embedded JSON shape used on page load, the frontend may need a thin normalization layer so save success and first load remain shape-compatible.

## 2b.3 Prep

2b.3 is discard-from-disk wiring. The working expectation is:

- Clicking `Discard Changes` fetches the current zone fresh from disk.
- Both `originalZone` and `workingZone` are replaced with that fresh baseline.
- The right-column room editor and left-column zone editor rerender from the fresh data.
- Dirty state clears.
- The overflow modal closes.

Current design questions to answer after 2b.2 lands:

1. Can discard reuse the existing zone-load path, or does it need a dedicated additive API endpoint?
2. Does discard remain blocked during in-flight save? The default assumption is yes.
3. Does discard correctly restore the original population storage shape from disk after local edits?

This note is intentionally provisional. The 2b.2 implementation diagnostics may force adjustments before the 2b.3 dispatch and checklist are written.