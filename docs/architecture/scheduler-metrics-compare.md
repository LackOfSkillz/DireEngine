# Scheduler Metrics Compare

Phase 2 metrics comparison confirms the scheduler remains bounded under load and under backpressure.

## Scenarios

### Stress

- Artifact: `artifacts/interest-scheduler-stress_direct_564416400/metrics.json`
- Executed jobs: `24`
- Scheduled total: `24`
- Queue peak: `24`
- Queue current after flush: `0`
- Flush executed total: `24`

Interpretation: burst scheduling executes fully and drains cleanly without residual queue growth.

### Queue Stability

- Artifact: `artifacts/interest-scheduler-queue-stability_direct_591038100/metrics.json`
- Executed jobs: `36`
- Scheduled total: `36`
- Queue peak: `3`
- Queue current after final flush: `0`

Interpretation: repeated schedule/flush cycles stay bounded to the per-cycle workload and do not leak queue depth over time.

### Quota and Backpressure

- Artifact: `artifacts/interest-scheduler-quota-violation_direct_74001200/metrics.json`
- Queue peak: `2`
- Queue current after final flush: `0`
- Scheduled total: `9`
- Owner quota rejections: `1`
- Owner quota replacements: `1`
- Owner quota delays: `1`
- System quota rejections: `1`
- Global quota rejections: `1`

Interpretation: overflow is explicit and bounded. Reject, replace, and delay all keep queue depth finite and return the queue to zero.

## Conclusion

The comparison across burst load, steady repeated load, and quota overflow shows:

- queue depth returns to zero after work completes
- peak depth remains proportional to admitted workload
- overflow is handled by explicit backpressure instead of silent growth
- no scenario showed runaway queue accumulation