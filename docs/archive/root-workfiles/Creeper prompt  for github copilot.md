Specialty Task — Creeper Command + Implementation Log
Goal

Create an admin command called creeper that logs player-entered commands to a markdown file named:

creeperlog.md

Also create a second markdown file named:

creeperImplementation.md

That file must document, step by step:

every file created
every file modified
the folder path for each file
the exact code added or changed
any Evennia hook or commandset registration needed
how to test it
how to adapt it for another Evennia instance

This documentation is intended to help another Evennia user from the Discord support channel reproduce the feature.

Functional Requirements
1. Command name and usage

Implement an admin-only command:

creeper <playername>
creeper all
creeper stop <playername>
creeper stop all

Examples:

creeper jekar
creeper aiden
creeper all
creeper stop jekar
creeper stop all
2. Behavior
creeper <playername>

Start logging every command entered by that specific player.

creeper all

Start logging commands entered by all players.

creeper stop <playername>

Stop logging commands for that one player only.

creeper stop all

Stop all logging entirely.

3. Additive behavior

This must be additive.

Example:

creeper jekar

Later:

creeper aiden

Result:

both Jekar and Aiden are being logged

Stopping one should not stop the other.

Example:

creeper stop jekar

Result:

Jekar stops being logged
Aiden continues being logged
4. Logging target

Write captured commands into:

creeperlog.md

The file should append, not overwrite.

Use a readable markdown format.

Recommended entry format:

## 2026-03-27 14:33:12
- Player: jekar
- Account: jekar@example or account name if available
- Session: 123
- Command: attack goblin

If easier, a compact format is acceptable, but it must include:

timestamp
player/account identity
raw command text
5. What should be logged

Log player-entered commands exactly as entered.

This means:

typed commands from players
not NPC commands
not internal system calls
not automated execute_cmd calls unless they originated from live player input

Do not log server-generated messages.

6. Scope control model

Implement a tracking structure that supports:

a global all-players logging mode
a set of individually watched players

Recommended internal model:

{
    "all": False,
    "players": set([...])
}

Or equivalent persistent storage.

7. Persistence decision

Make the watched-target configuration persist across reloads if practical.

If not practical in the first pass, document that limitation clearly in creeperImplementation.md.

Preferred behavior:

creeper targets survive reload
file logging continues after reload
8. Permissions

This must be admin-only.

Use the same permission standard you use for other admin commands in this codebase.

If the repo already uses a helper like _is_admin(), reuse that pattern.

Technical Implementation Guidance
Recommended approach

Hook into the place where Evennia receives player input before command execution.

Preferred target:

the player-input pipeline
session or command preprocessing layer
not each individual command

The goal is:

capture every typed command once
avoid modifying every command class

Good implementation targets may include:

session input hook
command pre-processing hook
a central input handler already used by the repo

Aiden should choose the cleanest central interception point for this codebase and document why.

Important constraint

Do not create a duplicate command-processing pipeline.

This should be an interception/logging layer attached to the existing input flow.

Logging exclusions

Do not log commands unless:

creeper all is active
or the specific player is on the watched list
Suggested Deliverables
1. Command implementation

Create the creeper admin command.

2. Central logging hook

Add the command-capture logic in the correct Evennia pipeline location.

3. Markdown log output

Append entries to:

creeperlog.md
4. Implementation walkthrough

Create:

creeperImplementation.md

This must be written as a tutorial-style build log.

Required Documentation Format for creeperImplementation.md

Aiden must document each step as he goes.

Use this structure:

Section 1 — Goal

Brief explanation of what the feature does.

Section 2 — Files created

For each new file:

full path
why it was created
Section 3 — Files modified

For each changed file:

full path
what was changed
why
Section 4 — Exact code added

Include the actual code blocks added or changed.

Section 5 — Hook point explanation

Explain where command interception happens and why that location was chosen.

Section 6 — Command behavior

Document:

creeper player
creeper all
creeper stop player
creeper stop all
Section 7 — Logging format

Show sample log entries.

Section 8 — Testing steps

Document exactly how to test:

single player logging
additive logging
stop one player
stop all
persistence across reload if implemented
Section 9 — Porting notes for another Evennia project

Explain what another Evennia user would need to change in their own codebase.

Acceptance Criteria

The task is complete only when all of the following are true:

creeper jekar starts logging Jekar’s typed commands
creeper aiden adds Aiden without removing Jekar
creeper all logs all players
creeper stop jekar removes only Jekar
creeper stop all disables all logging
output is appended to creeperlog.md
implementation is documented in creeperImplementation.md
command is admin-restricted
implementation uses a central input interception point
no duplicate command-processing subsystem is created
Notes for Aiden
Prefer additive data structures over overwrite behavior.
Prefer central interception over per-command instrumentation.
Reuse existing admin permission patterns from this repo.
Document everything as if teaching another Evennia developer from scratch.
If you hit an Evennia-specific limitation, document the limitation and the workaround in creeperImplementation.md