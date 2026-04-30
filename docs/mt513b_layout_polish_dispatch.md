# MT-513b - Zone Score header layout polish

## Background

MT-513 landed Zone Score functionality successfully - the scorer
works, all three sub-scores compute correctly, the bardic tier
labels render, the quest_hooks prewire works, the stale indicator
works, and steady-state performance is under 500ms after the YAML
loader fix.

The visual layout, however, has four discoverability and
proportionality issues that came out of real use:

1. The expanded breakdown panel pushes the entire map workspace
   and editor down the page when opened, displacing the work
   area.
2. The score header block is jammed against the right edge of
   the viewport with no breathing room.
3. The toggle chevron is too subtle - the "click to expand"
   affordance is hard to discover.
4. The score header occupies too much vertical space relative
   to the DireBuilder title and zone selector, which feel
   shoved aside.

This dispatch fixes those four issues. It is layout polish only.
No scoring logic changes. No new schema fields. No new endpoints.

## Architectural guardrails

**Frozen design decisions:**

1. The score header stays in the top-right region of the page
   header. It does not move to a sidebar, a modal, or a separate
   surface.
2. The composite, tier label, three sub-scores, tagline, and
   tooltip icon remain present and visible. None of them are
   removed.
3. The expanded breakdown panel becomes a dropdown overlay
   anchored to the score header. It floats above page content
   instead of pushing content down.
4. The breakdown content (Completeness / Depth / Engagement /
   Needs Attention sections) stays exactly as MT-513 rendered
   it. Only the container behavior changes.
5. The seven-tier ladder and all label strings remain unchanged.
6. The tagline "DireEngine ZoneScore - We build better zones by
   building better builders." remains unchanged.

**Frozen what-not-to-do list:**

- DO NOT modify zone_scorer.py.
- DO NOT modify the score endpoint or its payload shape.
- DO NOT modify any schema field.
- DO NOT modify the room editor, map workspace, or zone editor
  layouts.
- DO NOT modify any page surface other than the score header
  and its expanded panel.
- DO NOT introduce a new modal/overlay component class - reuse
  existing dropdown/popover patterns from the codebase if any
  exist (check the tooltip popover infrastructure from MT-511
  as a reference for overlay positioning).
- DO NOT change the breakdown panel's content or section order.
- DO NOT modify the legacy /builder/ route.

**Stop-and-report conditions:**

- If overlay positioning requires modifying the existing
  page-header layout in ways that affect the DireBuilder title
  or zone selector, stop and report.
- If the existing CSS variable system for accent colors and
  spacing doesn't support the polish needs, stop and report
  rather than introducing new variables.
- If the existing tooltip popover positioning logic isn't
  reusable for the breakdown overlay, stop and report rather
  than building a parallel positioning system.

## In scope

- Restructure the score header in direbuilder.html to be more
  compact horizontally
- Convert the expanded breakdown panel from in-flow drop-down
  to floating overlay (dropdown anchored to the score header)
- Improve the click affordance on the toggle (make the whole
  composite block clickable, not just the small chevron)
- Tighten vertical spacing between tagline and score numbers so
  they read as a unified widget
- Add right-edge padding to the score header so it doesn't jam
  against the viewport edge
- Cache-bust direbuilder.js and direbuilder.css

## Out of scope

- Scoring logic changes
- Schema changes
- New routes or endpoints
- Layout changes to anything other than the score header

## Phase A - Score header restructure

Current shape (from MT-513):

```text
DIREENGINE ZONESCORE - We build better zones...                  i
48 [tier label wrapping to two lines]
[COMPLETENESS 71] [DEPTH 25] [ENGAGEMENT 40]                     v
```

Target shape:

```text
DIREENGINE ZONESCORE - We build better zones...                 i
48 The townsfolk will throw rotten food at you                  v
COMPLETENESS 71  •  DEPTH 25  •  ENGAGEMENT 40
```

Changes:
- Composite number sits next to the tier label on the same line
- Tier label is allowed to wrap to a second line if needed but
  the wrap doesn't displace the sub-scores below
- Sub-scores collapse onto a single line with bullet separators
  ("•") between them, smaller font than current
- Toggle chevron moves to the right end of the composite/tier
  line, not below the sub-scores
- The entire composite-and-tier block becomes a clickable button
  (not just the chevron). Hover shows a subtle background
  highlight using existing accent variables.
- Right-edge padding equal to the existing header's left-edge
  padding so the block has breathing room

Use existing `direbuilder-zone-score-*` class names. Do not
rename them. Do not add new component classes for the layout
itself - only adjust CSS rules for the existing classes.

## Phase B - Convert breakdown panel to overlay

Currently the panel is a `<div hidden>` inside the score header
block that pushes content down when revealed. Convert it to a
floating overlay:

- The panel is positioned absolutely (or fixed, depending on
  scroll behavior - pick whichever works for the existing
  page scroll structure) below the score header.
- Width: matches the score header's width or slightly wider,
  capped at 480px.
- Background: existing dark parchment with subtle drop shadow
  matching the existing modal/dropdown shadow style.
- Z-index: above page content but below any global modals
  (use the same z-index tier as MT-511's tooltip popover).
- Click-outside dismissal: clicking anywhere outside the
  overlay closes it. Clicking inside the overlay doesn't close.
- Escape key dismissal: same as MT-511's tooltip popover.
- The toggle button's `aria-expanded` reflects open state.

The breakdown content inside the overlay stays unchanged from
MT-513 - the same four sections with the same text. Only the
container behavior changes.

If the overlay would extend past the viewport bottom on small
screens, allow vertical scrolling within the overlay (`overflow: auto`)
rather than pushing it offscreen.

## Phase C - Affordance improvement

Make the composite-score block (the "48" + tier label area)
into a clickable button:

- Cursor: pointer on hover
- Subtle background highlight on hover (5-10% accent color
  overlay, no harsh borders)
- Focus outline for keyboard navigation matching existing button
  focus styles
- ARIA: role="button", `aria-expanded` reflects panel state,
  `aria-haspopup="dialog"` or similar
- Click handler is the same as the existing chevron toggle -
  consolidate so both targets share one handler

The chevron remains visible as a visual cue but is no longer
the sole click target. Its size stays roughly the same; it's
just no longer load-bearing on its own.

## Phase D - Spacing tightening

Reduce vertical gap between:
- Tagline line and the composite-and-tier line: from current
  large gap to ~8-12px
- Composite-and-tier line and sub-scores line: ~6-8px
- Sub-scores line and the bottom edge of the score header
  block: ~8px

Goal: the entire score header reads as one unified widget
rather than three separate stacked elements.

## Phase E - Cache-bust and verify

Bump direbuilder.js and direbuilder.css versions. Restart server.

## Verification checklist

1. Page loads at `/direbuilder/?zone=new_landing`. Score header
   visible in top-right with proper right-edge padding.
2. Tagline, composite, tier, and sub-scores all read as a
   single visual unit. No floating disconnected lines.
3. Composite block is visibly clickable on hover (cursor and
   background change).
4. Click composite block -> breakdown overlay appears as a
   floating dropdown.
5. Map workspace and room editor do NOT shift down or change
   position when the overlay opens.
6. Click outside the overlay -> overlay closes.
7. Press Escape -> overlay closes.
8. Click composite block again -> overlay opens again.
9. Tier label "The townsfolk will throw rotten food at you"
   renders without truncation. If it wraps to two lines, the
   sub-scores below stay in their correct position.
10. Sub-scores render on a single line with bullet separators
    between them.
11. The DireBuilder title and zone selector on the left side
    of the page header are no longer visually shoved aside.
12. Tooltip i icon for the score still works.
13. Stale indicator still appears/clears correctly during edit
    and save.
14. Score still updates after save.
15. Per-room "needs attention" entries in the overlay still
    select rooms when clicked (same behavior as before).
16. Legacy `/builder/` route untouched.

## Stop conditions

- Edit only direbuilder.html, direbuilder.css, direbuilder.js.
- Do not edit views.py, scorer module, schemas, or any other
  file.
- Do not introduce new component classes - adjust existing CSS.
- Do not change scoring behavior or endpoint behavior.
- If overlay positioning requires page-header restructuring
  beyond the score block, stop and report.
- If existing tooltip popover infrastructure can't be reused
  for overlay positioning, stop and report.

## Required artifacts

1. Updated direbuilder.html (score header markup restructure)
2. Updated direbuilder.css (layout, overlay, spacing, click
   affordance styles)
3. Updated direbuilder.js (overlay open/close, click-outside,
   escape, consolidated toggle handler)
4. exports/mt513b_layout_polish_validation.md - short note:
   - Screenshots or DOM snapshots showing before/after
     layout
   - Verification that map workspace doesn't shift on overlay
     open
   - Verification that all MT-513 functionality still works
     (stale indicator, save refetch, room jump, tooltip)
