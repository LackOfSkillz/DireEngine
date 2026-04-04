# Scheduler Quotas

Phase 2 hardens the scheduler by enforcing bounded queue growth at the scheduler layer, not in gameplay systems.

## Policy

- Max jobs per owner: `5`
- Max jobs per system: `100`
- Max total queued jobs: `1000`

## Enforcement Behavior

- Owner quota behavior: `reject` by default, optional `replace_oldest` or `delay`
- System quota behavior: `reject`
- Global quota behavior: `reject`

This behavior is explicit and predictable.

When a quota is exceeded, the scheduler:

- rejects the new job
- records a scheduler rejection metric
- logs the rejection with the reason and metadata

When owner quota replacement is enabled, the scheduler:

- evicts the oldest queued job for that owner
- records a scheduler replacement metric
- logs the replacement with both the evicted key and the incoming key

When owner quota delay is enabled, the scheduler:

- parks the overflow job in a delayed retry queue
- retries it after a bounded delay when capacity may be available
- records both delay and delayed-retry execution metrics

It does not silently accept overflow and does not silently drop an accepted job later.

## Rationale

- Owner quota prevents a single object from flooding the queue
- System quota prevents one subsystem from dominating the scheduler
- Global quota prevents unbounded queue growth under aggregate load

## Current Reasons

- `owner-quota`
- `system-quota`
- `global-quota`
- `duplicate-key`

## Notes

- Key conflicts are handled separately from quota checks
- The default quota strategy remains `reject`; owner `replace_oldest` is available when explicit backpressure replacement is preferred
- Owner `delay` is available for bounded retry-style backpressure
- Queue depth and rejection visibility remain scheduler responsibilities only