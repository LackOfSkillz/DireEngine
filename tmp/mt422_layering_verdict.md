# MT-422 Layering Verdict

UI prompt is not reliably taking effect on the API path.

## Request Shape

- Endpoint: `http://127.0.0.1:1234/v1/chat/completions`
- Message count: 1
- System messages sent by API client: 0
- Prompt trimmed: False

## Response Signals

- hearth: 1
- ale: 1
- patrons: 1
- flickering light: 1
- banned phrase: the air is thick with: 1

## Response Text

```text
The hallway serves as a bustling tavern passage, with a hearth set into the eastern wall casting flickering light across worn floorboards. The air is thick with the scent of roasting meats and spilled ale, mingling with the sounds of patrons laughing and clinking tankards. The space narrows slightly to the south before opening up again, connecting this tavern hub to other parts of the bustling city.
```

## Interpretation

If the LM Studio UI system prompt were strongly layering onto this API path, fabricated tavern/interior detail such as hearth, beams, ale, barrels, or roasting meat should have been suppressed for this diagnostic room. Their presence is evidence against reliable UI-prompt layering on the API path.
