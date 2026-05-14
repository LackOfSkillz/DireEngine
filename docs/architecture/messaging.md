# Messaging

DRG-MSG-001 defines the current messaging discipline for public gameplay actions.

The core rule is simple: when an action is socially visible, the code should
decide what the actor sees, what the direct target sees, and what nearby
observers see as separate outputs.

## Three-Audience Contract

Public action surfaces should treat messaging as three intentional channels:

- actor: what the initiating player sees
- target: what the directly affected player or NPC sees
- room: what observers in the shared location see

These channels are not interchangeable.

Examples:

- a parry should not read like a dodge
- an observer line should usually name both participants
- a target line can carry direct second-person phrasing that would be awkward in room text

## Ownership Rules

- commands and presenters own message delivery
- services may return message metadata such as `message`, `target_message`, and `room_message`
- services do not directly call `msg()` or `msg_contents()`

This follows the engine contract: commands translate intent and presentation,
while services remain logic-first and mutation-focused.

## Shared Helper

The shared action helper lives in `engine/services/messaging.py`.

Current entrypoints:

- `send_action_messages(...)`
- `send_untargeted_action(...)`

Use `send_action_messages(...)` when the action has a direct target or when the
room line needs explicit actor/target exclusion control.

Use `send_untargeted_action(...)` when the action is visible to the room but has
no direct target audience.

## When Actor-Only Is Still Correct

Not every output should be broadcast.

Actor-only messaging remains correct for:

- private progression details such as TDP totals
- internal validation failures that reveal no useful public state
- admin-only diagnostics that should not leak implementation detail into play

The discipline is not "broadcast everything". The discipline is to make public
actions intentionally public and keep private state intentionally private.

## Current Remediated Surfaces

DRG-MSG-001 applied this pattern to the current high-value gaps:

- trainer consult and commit flows
- guildleader circle preview and commit flows
- `target` person and body-part focus surfaces
- `disengage`
- `combatreset`
- combat presenter miss, mitigation, and impact narration

## Implementation Notes

- prefer a service-returned `room_message` over reconstructing observer text in
  multiple commands when the same service result feeds more than one verb
- prefer presenter-level wording splits for combat outcomes, since presenters
  already own the player-facing semantic difference between parry, evade,
  shield, hit quality, and mitigation
- avoid duplicating a direct `target.msg(...)` before calling the helper, or the
  target will receive two lines for the same action