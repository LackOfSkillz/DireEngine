DireSim Kernel v1 — Locked Specification (Updated with Aedan Constraints)

This is the final, enforceable blueprint.
It is no longer just architecture—it is an engineering contract.

🧠 Core Principle (Unchanged, Locked)

NPC state stays on the NPC.
NPC time belongs to the simulation kernel.

🔒 Non-Negotiable System Rules

These are hard constraints, not guidelines.

Rule 1 — No Per-NPC Execution Surfaces
❌ No per-NPC repeating scripts
❌ No NPC self-scheduling
✅ All execution flows through Zone Services
Rule 2 — Bounded Work Per Cycle

Every service MUST enforce:

max NPCs processed
max milliseconds spent

Processing MUST stop when either limit is hit.

Rule 3 — Read → Decide → Commit (MANDATORY)

Every NPC update MUST follow this structure:

# READ (no mutation allowed)
facts = read_cached_facts(npc)
state = npc.sim

# DECIDE (no mutation allowed)
decision = resolver.decide(state, facts)

# COMMIT (mutation allowed)
apply_decision(npc, decision)
state.apply_changes(decision)
🚫 Forbidden:
Writing to .db or handler state during READ or DECIDE phases
Rule 4 — Event-First, Not Poll-First
❌ No repeated scanning of room.contents per NPC tick
✅ World changes emit events
✅ Services consume events and update state
Rule 5 — Event Fan-Out Control (NEW)

A single event MUST NOT wake unlimited NPCs.

Required:
MAX_EVENT_WAKE_NPCS = 10
Only enqueue NPCs that are:
in same room
adjacent rooms
same patrol cluster
already HOT/WARM
Rule 6 — Fact Cache Authority (NEW)

Every cached field has a single authoritative source:

Field	Authority
player_count	room enter/leave hooks
guard_count	NPC movement hooks
crime_flag	crime system
hot_until	zone service only
active_targets	enforcement transitions
🚫 Forbidden:
Recomputing from room.contents unless cache missing AND logged
Rule 7 — Significance Tier is NOT Persistent (UPDATED)
❌ Do NOT store tier in .db
✅ Derive from:
player proximity
zone heat
active events
Rule 8 — Budget Overrun Behavior (NEW)

If a service repeatedly hits budget:

MUST:
Drop COLD NPC processing
Reduce WARM cadence
Throttle messages
Log warning
Optionally degrade decision fidelity
Rule 9 — Message Throttling (NEW, FIRST-CLASS)

System-wide limits required:

MAX_MESSAGES_PER_ROOM_PER_SEC = 3
MAX_MESSAGES_PER_NPC_PER_SEC = 1
Rule 10 — Awareness ≠ Movement (NEW)

Separate cadence:

System	Cadence
Awareness	fast
Movement	slower
Rule 11 — Legacy Adapter Contract (NEW)

Legacy logic MUST be wrapped.

Allowed:
decision = resolve_guard_action(state, facts)
Forbidden:
scanning world directly
scheduling itself
looping other NPCs
🧩 System Architecture
Layers
A. Evennia Core
rooms, objects, persistence, commands
B. DireSim Kernel
scheduling, batching, budgets, rings
C. Zone Services
per-zone execution control
D. Handlers
NPC state + memory
E. Fact Cache
room/zone derived data
📁 Repo Structure
world/simulation/
  kernel.py
  service.py
  budgets.py
  events.py
  significance.py
  registry.py
  metrics.py

  zones/
    guard_zone_service.py

  cache/
    room_facts.py
    zone_facts.py

  handlers/
    guard_state.py

  resolvers/
    guard_resolver.py
⚙️ Core Components
SimulationKernel

Responsibilities:

drive update rings
enforce global constraints
dispatch zone services
ZoneSimulationService

Responsibilities:

manage NPC queues
consume events
enforce budgets
process NPCs in slices
GuardZoneService

Replaces:

per-guard scripts

Handles:

patrol
suspicion
enforcement
clustering
GuardStateHandler

Owns:

memory
cooldowns
targets
patrol state
RoomFacts / ZoneFacts

Provide:

cached world state
zero-scan reads
🧠 Significance System
HOT
player present / combat / crime
WARM
nearby player activity
COLD
inactive but relevant
DORMANT
no activity
🔁 Update Rings
Fast (0.25–0.5s)
events
hot reactions
enforcement
Normal (1s)
HOT NPCs
warnings
targeting
Slow (3s)
WARM NPCs
patrol
Deep (10–20s)
COLD NPCs
maintenance
📊 Budget Model

Example:

FAST_RING_MAX_NPCS = 4
FAST_RING_MAX_MS = 3

NORMAL_RING_MAX_NPCS = 6
NORMAL_RING_MAX_MS = 5

Stop processing when limit hit.

⚡ Event System
Events
PLAYER_ENTER_ROOM
PLAYER_LEAVE_ROOM
CRIME_COMMITTED
NPC_MOVED
TARGET_LOST
COMBAT_STARTED
COMBAT_ENDED
Flow
event → update cache → enqueue relevant NPCs → process in budgeted cycle
🧠 Guard Decision Pipeline
Eligibility check (cheap)
Read cached facts
Decide mode
Resolve ONE action
Commit mutation
Record metrics
🧾 Persistence Rules
Persistent
patrol index
suspicion
targets
warning count
Transient
metrics
cached data
temp decisions
🚀 Rollout Plan (Locked)
Phase 0 — Baseline
guards off
instrumentation on
Phase 1 — Hotspot Isolation
identify expensive slice
fix worst offender
Phase 2 — Kernel Shell
introduce SimulationKernel
introduce GuardZoneService
wrap existing logic
Phase 3 — Fact Cache
implement RoomFacts
remove repeated scans
Phase 4 — Handler Migration
move guard state to handler
Phase 5 — Significance System
tier-based processing
Phase 6 — Event Model
replace polling
Phase 7 — Catch-up Simulation
dormant NPC handling
📊 Metrics (REQUIRED)

Track:

NPCs processed
ms per cycle
budget hits
queue depth
event count
✅ Acceptance Criteria
Runtime
no web lag with 15 guards
smooth movement
clean shutdown
Scheduling
no per-NPC scripts
bounded execution
State
handler-owned
clean separation
Scaling
more NPCs → degrade gracefully
no runtime collapse
🧠 Final Summary
Old System

1 NPC = 1 brain = 1 loop = 1 problem

DireSim

1 Zone = 1 scheduler = many controlled brains

🔒 FINAL LOCK

This spec is now:

architecturally complete
constraint-hardened
failure-resistant
ready for implementation