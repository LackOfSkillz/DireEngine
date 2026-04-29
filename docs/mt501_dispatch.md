# MT-501 Dispatch

Goal: test whether room-description generation can emit well-formed Evennia `$state(name, content)` fragments without changing downstream engine behavior.

Scope:
- Update prompt assembly to expose state vocabulary and room-specific `applicable_states`.
- Generate descriptions for exactly three rooms:
  - `crossingV2_192_132`
  - `crossingV2_178_132`
  - `CRO_500_100`
- Save raw outputs to `exports/mt501_stateful_test.txt`.
- Save findings to `exports/mt501_findings.md`.

State vocabulary:
- Time: `morning`, `midday`, `evening`, `night`
- Season: `spring`, `summer`, `autumn`, `winter`
- Weather: `rain`, `snow`, `fog`
- Event: `invasion`
- Room-specific: `dark`, `flooded`, `burning`

Applicability targets:
- `crossingV2_192_132`: urban exterior
- `crossingV2_178_132`: urban interior hallway
- `CRO_500_100`: cave passage

Stop conditions:
- No prompt iteration.
- No extra rooms.
- Human reviewer decides any follow-up scope.

Follow-up note:
- MT-501 completed with zero emitted `$state(...)` fragments across all three rooms.
- MT-502 is the approved follow-up iteration: require at least one fragment per applicable state group, provide a complete worked example, and explicitly forbid meta-commentary about unchanged states.