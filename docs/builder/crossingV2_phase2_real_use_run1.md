## crossingV2 Phase 2 Real-Use Run 1

Purpose: stage one 20-room live-use batch for manual builder review without changing prompts or architecture.

### Selected Rooms

| Room ID | Name | Bucket | Tagged |
| --- | --- | --- | --- |
| crossingV2_204_360 | crossingV2_204_360 | main thoroughfare | yes |
| crossingV2_246_360 | crossingV2_246_360 | main thoroughfare | no |
| crossingV2_350_362 | crossingV2_350_362 | main thoroughfare | no |
| crossingV2_470_388 | crossingV2_470_388 | main thoroughfare | no |
| crossingV2_640_546 | crossingV2_640_546 | main thoroughfare | yes |
| crossingV2_488_634 | crossingV2_488_634 | main thoroughfare | no |
| crossingV2_462_714 | crossingV2_462_714 | generic intersection | no |
| crossingV2_92_360 | crossingV2_92_360 | side alley | no |
| crossingV2_318_362 | crossingV2_318_362 | side alley | yes |
| crossingV2_424_266 | crossingV2_424_266 | side alley | yes |
| crossingV2_750_328 | crossingV2_750_328 | side alley | no |
| crossingV2_318_564 | Society tn | named-feature room | yes |
| crossingV2_120_702 | He Shrine Riverpine | named-feature room | yes |
| crossingV2_96_918 | Te" ravern | named-feature room | yes |
| crossingV2_552_238 | 'wale | hard case | yes |
| crossingV2_352_326 | crossingV2_352_326 | generic intersection | no |
| crossingV2_414_426 | crossingV2_414_426 | generic intersection | no |
| crossingV2_520_642 | crossingV2_520_642 | generic intersection | no |
| crossingV2_684_642 | East wt | hard case | yes |
| crossingV2_778_264 | crossingV2_778_264 | hard case | yes |

### Tagging Plan

| Room ID | structure | specific_function | named_feature | condition | custom |
| --- | --- | --- | --- | --- | --- |
| crossingV2_204_360 | intersection |  | signpost | worn | |
| crossingV2_640_546 | intersection |  |  | worn | |
| crossingV2_318_362 | alley |  |  | worn | service-lane |
| crossingV2_424_266 | dock | warehouse |  | worn | loading-lane |
| crossingV2_318_564 | building-interior | guild-hall |  | worn | meeting-hall |
| crossingV2_120_702 | building-interior | temple | shrine | well-maintained | riverpine |
| crossingV2_96_918 | building-interior | tavern | hearth | worn | taproom, riverfront |
| crossingV2_552_238 | dock |  | workbench | crumbling | slipway |
| crossingV2_684_642 | entrance |  | signpost | worn | eastward-road |
| crossingV2_778_264 | threshold |  |  | abandoned | edge-lot |

Target export: `exports/sample_descriptions_phase2_real_use_run1.txt`