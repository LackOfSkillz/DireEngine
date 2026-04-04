Perfect — here is Δ61–70: Roundtime Retrofit Layer, written in the same strict, Aedan-ready format you’ve been using.

This batch:

installs roundtime as a core system
integrates it into attack / disengage / tend
avoids duplication
enforces clean validation + messaging
Δ61–70 — Roundtime Retrofit Layer
Microtask Δ61 — Add roundtime attribute

File:

typeclasses/characters.py

Task:
Inside Character.at_object_creation(), add:

self.db.roundtime_end = 0

Validation:

Run: evennia reload
Create/login character
No errors

Result:

Character now tracks roundtime
Microtask Δ62 — Add is_in_roundtime()

File:

typeclasses/characters.py

Task:
Add method:

import time

def is_in_roundtime(self):
    return time.time() < (self.db.roundtime_end or 0)

Validation:

Reload succeeds
No runtime errors

Result:

Can detect active roundtime
Microtask Δ63 — Add get_remaining_roundtime()

File:

typeclasses/characters.py

Task:
Add:

def get_remaining_roundtime(self):
    import time
    remaining = (self.db.roundtime_end or 0) - time.time()
    return max(0, int(remaining))

Validation:

Reload succeeds
No errors

Result:

Can query remaining RT cleanly
Microtask Δ64 — Add set_roundtime(seconds)

File:

typeclasses/characters.py

Task:
Add:

def set_roundtime(self, seconds):
    import time
    self.db.roundtime_end = time.time() + seconds

Validation:

Reload succeeds
No errors

Result:

Character can receive roundtime
Microtask Δ65 — Standard roundtime block message

File:

typeclasses/characters.py

Task:
Add helper:

def msg_roundtime_block(self):
    remaining = self.get_remaining_roundtime()
    self.msg(f"You must wait {remaining} seconds before acting.")

Validation:

Reload succeeds

Result:

Unified messaging for all commands
Microtask Δ66 — Apply roundtime gate to attack

File:

commands/cmd_attack.py

Task:
At the VERY TOP of func() (before any validation):

if self.caller.is_in_roundtime():
    self.caller.msg_roundtime_block()
    return

Validation:

Reload
Spam attack target
Output shows:
You must wait X seconds before acting.

Result:

Attack is properly gated
Microtask Δ67 — Apply roundtime on successful attack

File:

commands/cmd_attack.py

Task:
AFTER successful attack execution (after damage/messaging):

self.caller.set_roundtime(3)

Validation:

Run attack target
Immediately run again → blocked
Wait ~3 seconds → works again

Result:

Attack now applies roundtime
Microtask Δ68 — Apply roundtime gate + cost to disengage

File:

commands/cmd_disengage.py

Task:

Add gate at top:
if self.caller.is_in_roundtime():
    self.caller.msg_roundtime_block()
    return
After successful disengage:
self.caller.set_roundtime(2)

Validation:

attack target
disengage
Immediately disengage again → blocked
Wait → allowed

Result:

Disengage respects roundtime
Microtask Δ69 — Apply roundtime gate + cost to tend

File:

commands/cmd_tend.py

Task:

Add gate at top:
if self.caller.is_in_roundtime():
    self.caller.msg_roundtime_block()
    return
After successful tend:
self.caller.set_roundtime(2)

Validation:

tend chest
Immediately repeat → blocked
Wait → allowed

Result:

Healing is now time-bound
Microtask Δ70 — Full system validation (roundtime across commands)

No code changes

Scenario:

attack target
Immediately attack target → blocked
Wait → attack works
disengage
Immediately tend chest → blocked (RT applies globally)
Wait → tend chest works

Expected outputs include:

You must wait X seconds before acting.
All commands respect the same RT system

Final checks:

No command bypasses roundtime
No crashes
No duplicate messaging spam

Result:

Roundtime system is globally enforced and stable
🔒 Design Locked In

After Δ61–70, your system now has:

✅ Centralized roundtime
✅ Shared gating across all actions
✅ Clean messaging (no spam loops)
✅ Compatible with:
combat
bleeding
healing
future skill system