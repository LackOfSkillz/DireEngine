# Dispatch Template Notes

This file captures recurring dispatch patterns that should be specified
explicitly when the work touches shared architecture.

## Messaging Triple Spec Pattern

When a dispatch changes a public action surface, include a messaging section that
states whether the action has distinct outputs for:

- actor
- target
- room observers

Recommended wording:

```text
Messaging Triple:
- Actor: <what the initiating player should see>
- Target: <what the directly affected target should see, or "none">
- Room: <what observers should see, or "none">
```

If a surface is intentionally actor-only, say so directly and explain why.

Example:

```text
Messaging Triple:
- Actor: full confirmation text, including private requirement detail
- Target: none
- Room: a lightweight observer line showing that the interaction happened
```

## Architecture Reminder

- commands and presenters deliver messages
- services may return text-bearing result metadata
- services should not broadcast directly unless the dispatch explicitly changes
  that contract

## Validation Reminder

For messaging work, include at least one validation step that checks audience
splitting rather than only command success.