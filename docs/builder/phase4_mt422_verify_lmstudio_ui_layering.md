# MT-422 Verify LM Studio UI Prompt Layering

## Background

The MT-421 rerun produced different output even though the codebase prompt and Qwen model configuration were unchanged.
Whether the LM Studio UI system prompt actually layered onto the API request path is unclear.

The live Dragonsire client path posts to `/v1/chat/completions` with a single `user` message and no API-provided `system` message.

## Phase A: Capture the actual API request payload

Run a one-shot Python diagnostic that:
1. Loads `crossingV2_178_132` through the same runtime loader used by the sample generator.
2. Builds the same prompt text the codebase would send for MT-421.
3. Posts the exact payload shape used by `LocalLLMClient.generate()`.
4. Saves the exact request payload and response body.

Save the capture as `tmp/mt422_layering_check.txt`.

## Phase B: Check for evidence of UI prompt influence

Read the response and look for:
- hearth, beams, ale, roasting meat
- stub openings such as `A narrow passage`
- phrases that the LM Studio UI prompt explicitly bans

Interpretation:
- If the response includes fabricated tavern/interior content explicitly forbidden by the UI prompt, the UI prompt is not taking effect on the API path.
- If the response stays clean and grounded, the UI prompt may be influencing the API path.

## Deliverables

- `tmp/mt422_layering_check.txt`
- `tmp/mt422_layering_verdict.md`

## Constraints

- Diagnostic only.
- Do not change prompt or runtime code.
- Use the same model endpoint and request shape as the MT-421 rerun path.