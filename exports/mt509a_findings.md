# MT-509a Findings: Haiku 4.5 A/B Against MT-505 Sonnet Baseline

Single run only. No prompt iteration. All 40 planned Haiku calls completed successfully: 20 Pass 1 prose generations and 20 Pass 2 markup generations.

Run totals:
- Input tokens: 75,612
- Output tokens: 6,664
- Total API calls: 40
- Errors: 0
- Elapsed seconds: 95.94

Global A/B summary:
- Per-group coverage: Haiku hit 19/20 rooms; Sonnet hit 20/20.
- Syntactic correctness: Haiku malformed fragment count was 0; Sonnet malformed fragment count was 0.
- Whitespace handling: Haiku default renders were usually clean, but several active-state insertion points were more obviously broken than Sonnet's equivalent room outputs.
- Environment grounding: no Haiku output introduced a grounding violation that was not already absent or better-handled than Sonnet. Haiku was generally more conservative than Sonnet about adding props, NPCs, and scene dressing.
- Time coherence: no Haiku-only morning/midday/evening/night violation surfaced in the comparison set.
- Main Haiku failure mode: not wild invention, but thinner coverage plus several insertion-point sentences that render as visibly unfinished prose.

## Room-by-room comparison

1. `mt505_landing_low_river_alley` — Coverage complete, matching Sonnet on per-group coverage. Syntax clean. Default and active renders stay readable, though the evening warehouse-lantern line is still bolted on. No Haiku-only grounding or time issue. Haiku is more restrained than Sonnet. Shippable: yes.
2. `mt505_landing_low_dockside_street` — Coverage complete, matching Sonnet. Syntax clean. Renders are readable and slightly less cluttered than Sonnet's. No Haiku-only grounding or time issue. Haiku stays grounded and avoids Sonnet's more speculative warehouse/watch details. Shippable: yes.
3. `mt505_landing_merchant_market_square` — Coverage complete, matching Sonnet. Syntax clean. Renders are readable, though the `window boxes` spring detail is still a light embellishment rather than packet-grounded fact. No environment mismatch and no time issue. Haiku is slightly leaner than Sonnet. Shippable: yes.
4. `mt505_landing_merchant_shop_street` — Coverage complete, matching Sonnet. Syntax clean. Active renders are mechanically attached but still serviceable. No Haiku-only grounding or time issue. Haiku is more restrained than Sonnet and avoids Sonnet's baker/window-box specificity. Shippable: yes.
5. `mt505_landing_high_avenue` — Coverage complete, matching Sonnet. Syntax clean, but the midday render is visibly broken: `The avenue is quiet broken by ... broken only by ...`. No environment mismatch and no time-coherence failure. Haiku is more conservative than Sonnet, but this insertion defect is worse. Shippable: no.
6. `mt505_landing_high_lake_terrace` — Coverage complete, matching Sonnet. Syntax clean. The midday render breaks at `contemplation of the view crowded with well-dressed figures`, which reads unfinished. No Haiku-only grounding or time issue. Haiku is less florid than Sonnet, but the render integration is weaker here. Shippable: no.
7. `mt505_bramblefold_village_green` — Coverage complete, matching Sonnet. Syntax clean. Renders are readable and environmentally grounded. No Haiku-only grounding or time issue. Haiku is simpler than Sonnet and avoids Sonnet's more staged village-life details. Shippable: yes.
8. `mt505_bramblefold_road` — Coverage complete, matching Sonnet. Syntax clean. Renders read cleanly enough and stay grounded in hedgerow-road rural space. No Haiku-only grounding or time issue. Haiku is restrained relative to Sonnet. Shippable: yes.
9. `mt505_bramblefold_smithy_threshold` — Coverage complete, matching Sonnet. Syntax clean. Some time fragments are tacked on, but the room still reads coherently across the standard render set. No Haiku-only grounding or time issue. Haiku is slightly thinner but disciplined. Shippable: yes.
10. `mt505_forest_canopy_path` — Coverage complete, matching Sonnet. Syntax clean. Renders remain readable and properly wilderness-grounded. No Haiku-only grounding or time issue. Haiku is less atmospheric than Sonnet but still within quality bounds. Shippable: yes.
11. `mt505_plain_crossroads` — Coverage complete, matching Sonnet. Syntax clean. Renders are straightforward and coherent; Haiku stays inside the open-plain environment. No Haiku-only grounding or time issue. Haiku is plainer than Sonnet but stable. Shippable: yes.
12. `mt505_mountain_switchback` — Coverage complete, matching Sonnet. Syntax clean. Renders are coherent and terrain-appropriate, with no Haiku-only grounding or time issue. Haiku is somewhat less vivid than Sonnet, but not incorrectly so. Shippable: yes.
13. `mt505_castle_great_hall` — Coverage complete, matching Sonnet. Syntax clean. Several renders are visibly broken, especially `...well-maintained expanse the stone noticeably chill...` and `...expanse warm air rising gently from the flags.` No Haiku-only grounding or time issue. Haiku is much more grounded than Sonnet's feast-scene embellishment, but the insertion mechanics fail here. Shippable: no.
14. `mt505_castle_corridor` — Coverage complete, matching Sonnet. Syntax clean, but default rendering is broken because the markup attaches directly to `admitting`, yielding `admitting.` when no time state is active. No Haiku-only grounding or time issue. Haiku is otherwise restrained, but this default-render defect is disqualifying. Shippable: no.
15. `mt505_guild_workshop` — Coverage complete, matching Sonnet. Syntax clean. Active renders are somewhat bolted on, but still readable and grounded in the workshop packet. No Haiku-only grounding or time issue. Haiku is cleaner and less prop-heavy than Sonnet. Shippable: yes.
16. `mt505_guild_conference` — Coverage complete, matching Sonnet. Syntax clean. The lamplight and single-lamp additions are mild embellishments, but they fit the room. No Haiku-only grounding or time issue. Haiku is more restrained than Sonnet and preserves the conference-room identity. Shippable: yes.
17. `mt505_cave_entrance` — Coverage complete, matching Sonnet. Syntax clean. Renders stay coherent and properly threshold-grounded. No Haiku-only grounding or time issue. Haiku remains disciplined and less decorative than Sonnet. Shippable: yes.
18. `mt505_cave_passage_deep` — Coverage complete, matching Sonnet. Syntax clean. This is Haiku's most disciplined room: the deep cave stays fully cave-grounded, indirect, and grammatically stable. No Haiku-only grounding or time issue. Haiku matches or slightly improves on Sonnet's restraint here. Shippable: yes.
19. `mt505_temple_sanctuary` — Coverage incomplete. Haiku missed the required weather group entirely, while Sonnet covered all groups. Syntax clean, but several time renders are mechanically broken (`windows above bright and direct`, `windows above pale and silvered`) and the invasion render ends `space broken occasionally...`. No Haiku-only grounding or time issue; Haiku is actually better-grounded than Sonnet's ritual-detail inventions. Even so, the group miss plus insertion failures make this room non-shippable. Shippable: no.
20. `mt505_old_bridge_span` — Coverage complete, matching Sonnet. Syntax clean. Renders stay readable and bridge-grounded, with no Haiku-only grounding or time issue. Haiku is less embellished than Sonnet and avoids Sonnet's parapet-footstep oddity. Shippable: yes.

## Verdict

- Coverage parity: Haiku 19/20 vs Sonnet 20/20.
- Syntactic parity: Haiku malformed fragment count 0 vs Sonnet 0.
- Grounding gap: 0 rooms had Haiku grounding violations that did not appear in Sonnet's same-room output.
- Time-coherence gap: 0 rooms had Haiku time-coherence violations that did not appear in Sonnet's same-room output.
- Subjective shippability: Haiku 15/20 vs Sonnet 0/20 as judged against the project's current standard of environment preservation, readable rendered prose, and no broken grammar.
- Non-shippable Haiku rooms: `mt505_landing_high_avenue`, `mt505_landing_high_lake_terrace`, `mt505_castle_great_hall`, `mt505_castle_corridor`, `mt505_temple_sanctuary`.
- Bottom-line judgment: Haiku is close enough to Sonnet on grounding and syntax to be a serious candidate at roughly one-third the cost, but it does not reach full parity because the prompt tightening did not fully eliminate coverage loss and insertion-point failures in a handful of rooms.