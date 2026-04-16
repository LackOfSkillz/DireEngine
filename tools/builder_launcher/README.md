# Builder Launcher

This is a local-only bridge that lets the browser webclient open the Godot Builder client on the same machine.

It is intentionally separate from the Evennia runtime and binds only to `127.0.0.1:7777`.

## What It Does

- exposes a local health check at `GET /health`
- exposes a local launch endpoint at `POST /launch-builder`
- starts the Godot project without blocking the HTTP response
- accepts optional launch context such as `area_id`, `room_id`, and `character_name`

## Run It

From the repo root in Windows PowerShell:

```powershell
c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m pip install -r tools/builder_launcher/requirements.txt
c:/Users/gary/dragonsire/.venv/Scripts/python.exe tools/builder_launcher/launcher.py
```

The launcher listens on:

```text
http://127.0.0.1:7777
```

## Test Health

```powershell
Invoke-RestMethod -Method Get http://127.0.0.1:7777/health
```

Expected response:

```json
{"ok": true, "service": "builder_launcher"}
```

## Test Launch

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:7777/launch-builder -ContentType 'application/json' -Body '{"target":"builder","area_id":"new_landing","room_id":"room_1","character_name":"Wufgar"}'
```

Expected success response:

```json
{"ok": true, "status": "launched"}
```

## Known Limits

- localhost only
- no auth beyond localhost restriction and origin checks
- no process reuse detection yet
- no single-instance behavior yet
- no focus or window-raise guarantee yet
- browser launch requires this launcher service to be running first