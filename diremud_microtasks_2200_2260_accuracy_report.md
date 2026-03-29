# DireMUD Microtasks 2200-2260 Accuracy Report

## Scope

This report compares the AreaForge-generated Landing map artifacts against the original source image at [maps/CrossingMap (1).png](c:/Users/gary/dragonsire/maps/CrossingMap%20(1).png), with emphasis on graph accuracy rather than UI polish.

Artifacts compared:
- [build/the_landing/areaspec.json](c:/Users/gary/dragonsire/build/the_landing/areaspec.json)
- [build/new_landing/areaspec.json](c:/Users/gary/dragonsire/build/new_landing/areaspec.json)
- [build/the_landing/review.txt](c:/Users/gary/dragonsire/build/the_landing/review.txt)
- [build/new_landing/review.txt](c:/Users/gary/dragonsire/build/new_landing/review.txt)
- [build/snapshots/the_landing.json](c:/Users/gary/dragonsire/build/snapshots/the_landing.json)

## Summary

Topological accuracy is currently strong.

- A fresh extraction from the original Crossing image matched the saved Landing build exactly.
- The rebuilt `new_landing` artifact also matches `the_landing` exactly at the node and edge level.
- The weak point is not graph structure. It is OCR-driven naming and review coverage.

In short:
- Graph accuracy: high
- Spatial fidelity to extracted walkable network: high
- Naming / label accuracy: mixed

## Structural Comparison

Comparison: fresh extraction from the original Crossing image vs [build/the_landing/areaspec.json](c:/Users/gary/dragonsire/build/the_landing/areaspec.json)

- Built nodes: 211
- Fresh nodes: 211
- Built-only nodes: 0
- Fresh-only nodes: 0
- Built edges: 470
- Fresh edges: 470
- Built-only edges: 0
- Fresh-only edges: 0

Result:
- The saved Landing graph is an exact structural match for a fresh extraction of the source map under the current extraction logic.

Comparison: [build/new_landing/areaspec.json](c:/Users/gary/dragonsire/build/new_landing/areaspec.json) vs [build/the_landing/areaspec.json](c:/Users/gary/dragonsire/build/the_landing/areaspec.json)

- `new_landing` nodes: 211
- `the_landing` nodes: 211
- Node symmetric difference: 0
- `new_landing` edges: 470
- `the_landing` edges: 470
- Edge symmetric difference: 0

Result:
- The rebuilt `new_landing` artifact does not drift structurally from the current Landing artifact.

## Visual Interpretation

Comparing the fullscreen rendered graph against the original map image suggests the browser map is an accurate abstraction of the walkable street network, not a literal re-render of the source cartography.

That distinction matters:

- The browser map correctly preserves the extracted graph shape, junction density, branching, and special-route topology.
- It intentionally omits non-graph art from the source image such as:
  - water bodies
  - printed labels
  - decorative framing
  - building boxes and legend text
- The result is visually sparse compared to the source image, but that sparsity is expected for a navigation graph.

So the apparent mismatch is mostly representational, not structural.

## Quality Signals

Node kind distribution in [build/the_landing/areaspec.json](c:/Users/gary/dragonsire/build/the_landing/areaspec.json):

- gray: 108
- green: 35
- cyan: 27
- red: 25
- poi_stub: 10
- yellow: 5
- magenta: 1

Node OCR confidence tiers:

- medium: 91
- none: 72
- low: 30
- high: 18

Nodes flagged `needs_label_review`:

- 96 of 211 nodes

Edge OCR confidence tiers:

- medium: 202
- low: 128
- none: 85
- high: 55

Interpretation:

- The extracted graph itself is stable.
- A large amount of semantic labeling still needs human review.
- Exit labeling is especially noisy in OCR-heavy regions.

## Review File Findings

The review artifacts show the main quality debt is concentrated in labels and exit names, not node placement.

Examples from [build/the_landing/review.txt](c:/Users/gary/dragonsire/build/the_landing/review.txt):

- `Low-confidence label: Residental Cloister arch to To`
- `Low-confidence label: J Commissary (Stamina`
- `Label needs review: Central Crossing [666,432]`
- `Uncertain exit label: North go Gate`

This means:

- OCR is still misreading landmarks and signage text in multiple places.
- Generated room naming is compensating for that noise, but many rooms remain flagged for manual review.
- Structural map extraction is ahead of semantic map cleanup.

## Accuracy Verdict

If the question is "Does the generated playable map match the extracted map graph from the source image?"

Answer:
- Yes, exactly under the current extraction pipeline.

If the question is "Does the generated map preserve the full informational richness of the source image?"

Answer:
- Not yet.
- The navigational topology is preserved, but OCR-derived names, special labels, and map semantics still need manual cleanup.

## Recommended Next Checks

Highest-value next steps for accuracy work:

1. Prioritize manual cleanup of the 96 `needs_label_review` nodes in [build/the_landing/review.txt](c:/Users/gary/dragonsire/build/the_landing/review.txt).
2. Audit uncertain special exits such as `gate`, `arch`, `bridge`, `stair`, and `ramp` labels against the source image.
3. Add an optional browser overlay mode that colors nodes by confidence tier so map-quality issues are visible in-client.
4. Compare generated room names against the original printed map labels for major landmarks and district anchors, not just graph structure.

## Conclusion

AreaForge is currently accurate as a graph extractor for this map.

The main remaining accuracy gap is semantic:
- OCR interpretation
- landmark naming
- exit-label cleanup

The playable navigation surface is faithful.
The cartographic naming layer still needs review.