
DIREBUILDER V2 — SCOPE & ENGINEERING BLUEPRINT
🎯 Core Vision

DireBuilder V2 is:

A spatial world editor with direct manipulation and structured data control

Where:

The map is the truth surface
The inspector edits state
The library supplies assets
The operation system guarantees integrity
🧠 DESIGN PRINCIPLES (LOCK THESE)
1. Spatial First
World is edited visually (map canvas)
Not through forms
2. Direct Manipulation
Drag → place
Drag → connect
Drag → assign

No hidden flows.

3. Clear Separation of Concerns
Area	Role
Left	Tools + navigation
Center	World
Right	Inspector
Bottom	System feedback
4. Single Source of Truth
Everything goes through operation journal
No direct mutation
5. Mode-Based Interaction
One active tool at a time
No mixed behaviors
6. Instance vs Template Separation
Type	Editable Where
Instance	Inspector
Template	Library tab
🧭 LAYOUT ARCHITECTURE
🔝 TopBar (Global Control Layer)

Purpose: System + session state

Contains:

Zone dropdown
Tool mode indicator
Undo / Redo
Save
Validation status
◀️ LeftDock (Navigation + Tools)
Section A — Tool Modes
Select
Create Room
Draw Exit
Move
Delete
Add NPC
Add Item
Section B — Content Tree
Zone
 ├ Rooms
 ├ NPCs
 ├ Items
Section C — Filters
Search field
Type filters
🟦 CenterCanvas (World Surface)

Primary editing surface

Supports:

Node placement
Edge creation
Drag/drop interactions
Hover previews
Zoom/pan
Entities Rendered:
Entity	Visual
Room	Node
NPC	Icon inside node
Item	Icon inside node
Exit	Line
▶️ RightDock (Inspector / Library Tabs)
Tabs:
[ Inspector ] [ NPC Library ] [ Item Library ]
Inspector (Context-Sensitive)
Room selected:
Name
Description
Type
Exits
Contents
NPC selected:
Stats
Inventory
Equipment
Behavior
Tags
Item selected:
Properties
Tags
Weight
Effects
Library Tabs
NPC Library
Search
Scroll list
Drag to canvas
Item Library
Same behavior
🔽 BottomDock (System Layer)
Logs
Operation journal
Validation output
Errors
🧱 CORE SYSTEMS
1. Operation Engine (Already Exists)

All actions must be:

BuilderOp
 → stage
 → apply
 → undoable
2. Entity Model
Room
{
  "id": "",
  "coords": [],
  "exits": [],
  "contents": {
    "npcs": [],
    "items": []
  }
}
NPC Instance
{
  "id": "",
  "template_id": "",
  "room_id": "",
  "stats": {},
  "inventory": [],
  "equipment": [],
  "vendor_stock": []
}
Item Instance
{
  "id": "",
  "template_id": "",
  "location": "room|npc|container",
  "parent_id": ""
}
3. Drag & Drop Engine
Drag Sources
NPC templates
Item templates
NPC instances
Item instances
Drop Targets
Target	Accepts
Room	NPC, Item
NPC	Item
Vendor NPC	Item
Canvas	Room (create)
Result → Operation
Action	Operation
Drop NPC on room	CREATE_NPC_INSTANCE
Drop item on room	ADD_ITEM_TO_ROOM
Drop item on NPC	ADD_ITEM_TO_NPC
Drop item on vendor	ADD_ITEM_TO_VENDOR
4. Selection System
Click = select entity
Inspector updates
Highlight active
5. Mode System

Only ONE active:

SELECT
CREATE_ROOM
DRAW_EXIT
MOVE
DELETE
ADD_NPC
ADD_ITEM
6. Visual Feedback System
Required:
Hover highlight
Drop target glow
Invalid drop state
Drag ghost preview
Selection outline
⚠️ CRITICAL UX RULES
1. Inspector NEVER changes role

It only edits selected object.

2. Library NEVER edits instances

It only supplies templates.

3. Canvas NEVER edits properties

Only placement + structure.

4. All edits are reversible

No silent state mutation.

🚫 WHAT WE REMOVE FROM V1
Mixed inspector/template panels
Hidden flows in scroll containers
Multiple contexts in one panel
Form-driven placement
Non-operation mutations
🧭 IMPLEMENTATION PHASES
Phase 1 — Shell Refactor
Layout (Top / Left / Center / Right / Bottom)
Dock containers
Remove legacy panel stacking
Phase 2 — Mode System
Tool selection
Cursor state
Interaction gating
Phase 3 — Selection + Inspector Stabilization
Single inspector context
Entity switching
Phase 4 — Library System
Load templates
Search
Render list
Phase 5 — Drag & Drop Core
Template → Room
Basic drop routing
Phase 6 — Instance Composition
Item → NPC
NPC → Room movement
Phase 7 — Visual Feedback
Highlighting
Drag preview
Error states
Phase 8 — Advanced Systems
Vendors
Equipment slots
Container nesting
🧠 FINAL TARGET STATE

User flow becomes:

Select tool → Click map → Create room
Drag NPC → Drop into room
Click NPC → Edit stats
Drag item → Drop onto NPC
Save

No friction.

🎯 NOW: TASK SYSTEM

We don’t jump into 100 tasks.

We start clean.

🧾 DBV2 TASK SET (FOUNDATION)
DBV2-01 — Layout Shell Refactor

Goal: Replace current UI with docked editor structure

Deliverables:

TopBar container
LeftDock container
CenterCanvas container
RightDock container
BottomDock container

Acceptance:

UI visually matches editor layout
No overlapping panels
DBV2-02 — Mode System Implementation

Goal: Enforce single active tool

Deliverables:

Tool enum
Active tool state
Tool switching UI
Input routing per mode

Acceptance:

Only one tool active
Behavior changes based on mode
DBV2-03 — Selection + Inspector Lock

Goal: Stabilize selection pipeline

Deliverables:

Select room/NPC/item
Inspector updates correctly
No mixed contexts

Acceptance:

Clicking entities updates inspector reliably
🚀 AFTER THAT

We move into:

DBV2-04 → Library system
DBV2-05 → Drag/drop core
DBV2-06 → Instance composition