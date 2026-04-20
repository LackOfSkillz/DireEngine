# Barbarian Choke Strings

## Summary

DireLore does not show a separate Barbarian skill page named `Choke`.
The Barbarian-relevant entry is `Choke command`, described as:

> For roleplaying and also a Barbarian-only brawling attack.

The separate `Ambush Choke` entry is a Thief ability, not Barbarian.

## Confirmed Strings From DireLore

### Generic choke

- Actor/self: `You gag, desperate for air!`
- Room/others: `<Name> gags horribly and gasps for air!`

### Choke while grappled

- Actor/self: `<Target> struggles helplessly in your strong grasp.`

### Neck-break kill text shown on the page

- Actor/self: `With a loud CRACK! you snap the arthelun cabalist's neck and toss it aside.`
- Additional observed aftermath text on the same page:
  - `An arthelun cabalist's eyes flare one last time before snuffing out forever.`
  - `The flames reluctantly withdraw from their host forming an ephemeral wisp that rapidly flees.`
  - `The shimmering ethereal shield fades from around a charred husk.`

## Not Found

- No separate target-facing string for Barbarian choke was found in DireLore.
- No separate room-facing string for the grapple or neck-break action was found in DireLore.
- No Barbarian-specific `skill choke` page distinct from `Choke command` was found.

## Grapple Follow-up Search

A second DireLore pass searched for pages containing both `grapple` and `choke`.

- No additional grapple-specific choke messaging was found beyond the existing `Choke command` line:
  - `<Target> struggles helplessly in your strong grasp.`
- The most relevant corroborating mechanics note came from `Brawling skill`, which says:
  - `Some maneuvers can only be executed while grappling`
- The `Brawling skill` page also includes a Barbarian note under special attacks:
  - `As of 03/05/19 choke kills just fine.`

This follow-up search did not produce any extra actor, target, or room strings for a grapple choke state.

## Source Notes

- Primary source: `raw_pages` entry for `https://elanthipedia.play.net/Choke_command`
- Corroborating source: `raw_pages` entry for `https://elanthipedia.play.net/Ambush_Choke`
- `Ambush Choke` explicitly identifies itself as a Thief ambush and says `Messaging: Unknown`.
- Additional corroborating mechanics source: `raw_pages` and `sections` entries for `https://elanthipedia.play.net/Brawling_skill`