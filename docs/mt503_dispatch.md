# MT-503 Dispatch

Goal: compare local Qwen and Claude Haiku 4.5 on the second-pass `$state(...)` markup-decoration task while keeping the base prose fixed.

Plan:
- Pass 1 uses the already-verified plain prose baseline from MT-502.
- Pass 2a asks local Qwen to decorate that prose with `$state(...)` markup.
- Pass 2b asks Claude Haiku 4.5 to decorate the same prose with `$state(...)` markup.
- Write the side-by-side comparison to `exports/mt503_qwen_vs_claude_markup.txt`.

Inputs:
- Reuse the three MT-502 rooms:
  - `crossingV2_192_132`
  - `crossingV2_178_132`
  - `CRO_500_100`
- Reuse the MT-502 plain-prose baselines as fixed Pass 1 inputs.

Requirements:
- Read `ANTHROPIC_API_KEY` from the environment.
- Use local Qwen through the LM Studio-compatible `/v1/chat/completions` endpoint.
- Compare Qwen markup decoration against Claude markup decoration on the exact same input prose.

Stop conditions:
- Single comparison pass only.
- No prompt iteration.
- No extra rooms.