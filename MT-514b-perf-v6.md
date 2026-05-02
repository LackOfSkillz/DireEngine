# MT-514b-perf-v6 — Cold-start cache priming

## Background

v5 closed the steady-state perf problem (warm cycle 0.282s).
But the first natural tick after server boot still pays cold-cache
cost: 7.203s observed. Not a player-facing freeze (happens once
at boot, on a 3.75-minute timer after that), but worth eliminating
for clean operational behavior.

## Scope

In `WeatherScript.at_start()`, warm the caches that v5 added so
the first natural tick has populated state.

## Implementation

After existing at_start() invalidation logic, call the cache-
warming helpers for all known zones:

```python
def at_start(self):
    # ... existing invalidation ...
    
    # Warm caches so first natural tick after server boot is fast
    for payload in _iter_zone_payloads():
        zone_id = str(payload.get('zone_id') or '').strip()
        if zone_id:
            _eligible_rooms_for_zone(zone_id)
            # any other warm-up calls
```

## Verification

Restart server. Time first `at_repeat()` call. Should be under
2 seconds. Done.

## Acceptance gate

First post-restart tick under 2 seconds.

## Stop conditions

- Cache warming requires DB access during script start in a way
  that conflicts with Evennia's startup ordering: stop and report.
- First post-restart tick still over 2 seconds: stop and report.
- Anything unexpected during warm-up: stop and report.
