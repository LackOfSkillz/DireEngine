# MT-502 Dispatch

Goal: tighten the stateful fragment prompt so room-description generation emits required `$state(name, content)` fragments when state groups are applicable.

Background:
- MT-501 produced grounded prose but zero `$state(...)` fragments.
- `CRO_500_100` responded with meta-commentary about seasons staying unchanged instead of using fragments.

Scope:
- Update the system prompt's stateful fragment guidance.
- Require at least one fragment per applicable state group.
- Add a complete worked example showing integrated fragments.
- Explicitly forbid meta-commentary about unchanged state variation.
- Re-run the same three rooms:
  - `crossingV2_192_132`
  - `crossingV2_178_132`
  - `CRO_500_100`
- Save raw outputs to `exports/mt502_stateful_test.txt`.
- Save findings to `exports/mt502_findings.md`.

Evaluation:
- Did the model produce `$state(...)` fragments?
- Did each applicable state group get at least one fragment?
- Are fragments syntactically correct?
- Does whitespace remain correct?
- Does prose remain grammatical with fragments removed?
- Does a combined active-state render remain grammatical?
- Did the model avoid meta-commentary about state variability?

Stop conditions:
- Single test run only.
- No additional rooms.
- No prompt iteration beyond this change.