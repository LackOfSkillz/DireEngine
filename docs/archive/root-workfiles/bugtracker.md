# Bug Tracker

This file tracks significant confirmed bugs and their fixes so recurring issues can be identified quickly.

## Project Rule - Never Again

- Never add a global per-second sweep that performs meaningful work for all characters or NPCs.
- Prefer event-driven behavior where possible.
- If periodic work is required, keep it state-gated so idle actors are skipped.
- Separate high-frequency combat/status work from slower systems like learning or maintenance.
- If a periodic loop must touch many objects, add slow-path timing warnings before it ships.

## Bug 001 - Global ticker caused severe command lag

- Status: Fixed
- First documented: 2026-03-25
- Severity: High

### Symptoms

- `connect` delayed by roughly `3s` to `10s`
- simple commands like `look`, `north`, and `south` delayed by roughly `5s` to `8s`
- command logic itself executed quickly once processing actually started

### Confirmed non-causes

- `return_appearance()` rendering was not the active root cause
- command/combat code execution time was not the active root cause
- MCCP compression was disabled and verified absent from the telnet handshake, but the lag still reproduced

### Root cause

- The original 1-second global ticker in `server/conf/at_server_startstop.py` iterated all Character/NPC objects every second.
- During diagnosis, that sweep covered about `185` objects.
- For each object it could call multiple maintenance behaviors:
  - balance recovery
  - fatigue recovery
  - bleed processing
  - bleed-state updates
  - learning pulse processing
  - NPC combat actions
- Those calls repeatedly touched default-normalization paths and sometimes emitted messages or executed commands, which blocked the Evennia reactor and stalled unrelated live commands.

### Isolation proof

- Temporarily disabling the global ticker dropped movement latency from multi-second delays to about `0.04s` to `0.06s`.
- That established the ticker loop as the decisive cause of the lag.

### Permanent fix

- Kept MCCP hard-disabled in the custom telnet protocol:
  - `server/conf/settings.py`
  - `server/conf/telnet.py`
  - `server/conf/mssp.py`
- Replaced the old monolithic global sweep in `server/conf/at_server_startstop.py` with:
  - a lightweight `1s` status tick
  - a separate `10s` learning tick
- Skipped idle characters entirely.
- Only processed balance/fatigue/bleed/NPC combat when needed.
- Removed per-pulse debug spam from `typeclasses/characters.py`.

### Verified post-fix behavior

- `connect`: about `0.78s`
- `look`: about `0.02s`
- `look jekar`: about `0.10s`
- room movement returned to sub-second response time

### Fast recognition rule

If `connect`, `look`, and simple movement all become uniformly slow by several seconds, inspect periodic global loops before touching rendering code.

Check first:

- `server/conf/at_server_startstop.py`
- any ticker that walks all Character/NPC objects every second
- any loop that repeatedly triggers default-normalization or command execution across the full object set

## Bug 002 - Twisted file log observer disabled after closed-file write

- Status: Open
- First documented: 2026-03-25
- Severity: Medium

### Symptoms

- server log output showed repeated Twisted observer failures during or after restart/log rotation activity
- file logging could be partially disabled, which risks hiding later runtime errors

### Observed error signature

- `ValueError: I/O operation on closed file.`
- `Temporarily disabling observer <twisted.logger._file.FileLogObserver ...> due to exception`

### Known impact

- debugging becomes less reliable because later exceptions may not be written to the normal log sink
- this did not appear to be the root cause of Bug 001, but it is dangerous because it can mask future faults

### Current status

- documented for follow-up
- not yet root-caused or fixed
- reproduced again during restart verification on 2026-03-25

### Latest verification notes

- a clean stop/start verification was completed after the tick instrumentation was added
- no `process_status_tick slow` or `process_learning_tick slow` warnings appeared in the logs during normal restart/load
- the closed-file observer failure still reproduced in `server/logs/server.log`
- `server/logs/portal.log` also showed an AMP-side error during one restart cycle:
  - `Unhandled Command: b'AdminPortal2Server'`
- that AMP error may be related to restart sequencing or the same broader logging/observer lifecycle problem, but it is not root-caused yet

### Next investigation points

- check Evennia/Twisted logfile lifecycle during restart and shutdown
- verify whether log rotation or repeated stop/start cycles are leaving a closed file handle attached to an active observer
- confirm whether the issue is local project behavior or an upstream Evennia/Twisted integration edge case