# Godot / Browser Client Debug Summary

Date: 2026-03-28
Workspace: `c:\Users\gary\dragonsire`
Actual target at this stage: browser-native Evennia webclient override, not a native Godot runtime.

## Current Problem

The browser client connects, accepts input, sends commands, and receives Evennia output, but the main Game Feed panel remains visually blank.

The clearest current symptom set is:

- top-right status shows connected
- command input box is visible and works
- footer updates to `Received text`
- debug panel logs live `TEXT` events from Evennia
- line counter in the feed header increases (`Live session • N lines`)
- the main feed panel still renders as an empty dark rectangle

This means the failure is no longer transport or command handling. It is a browser rendering / DOM target / stale asset / overlay issue.

## What Is Proven Working

### Server / transport

- Evennia websocket transport is working.
- Valid payload contract was verified earlier as JSON arrays:
  - client -> server: `["text", ["look"], {}]`
  - server -> client: `["text", ["<span>room text...</span>"], {"type": "look"}]`
- Direct websocket tests against `ws://127.0.0.1:4008` succeeded.

### Browser connection

- Browser is connecting to the Evennia websocket.
- Browser receives live `text` events.
- Browser can send commands such as `help`, `look`, `inventory`, `stats`, movement directions, etc.

### Browser console evidence

Latest browser console output from the active client session:

```text
mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) chrome/146.0.0.0 safari/537.36
chrome
evennia.js:451 {"0":"Trying websocket ..."}
evennia.js:451 {"0":"Evennia initialized."}
evennia.js:451 {"0":"Evennia reconnecting."}
```

What this proves:

- the active browser is Chrome on Windows
- the Evennia base library is loading
- `Evennia.init()` is executing in the live page
- websocket connection logic is being invoked from the current client
- the custom manual bootstrap path is active enough to reach Evennia core connection setup

What it does not prove:

- that the latest custom `dragonsire-browser.js` asset is definitely the one being used everywhere
- that the visible feed surface is the same DOM node our latest append target expects
- that the visible console panel is not being overlaid, clipped, or otherwise obscured

### Payload content

The debug panel shows rich HTML payloads arriving intact, including:

- room descriptions with color spans
- clickable exits via `Evennia.msg("text", ["__clickmove__ west"], {})`
- inventory output
- help pager output
- stats output

Example payload shape observed repeatedly:

```json
{
  "args": [
    "<span class=\"color-014\">Elmbrook Lane...</span><br>...<a ...>west</a>"
  ],
  "kwargs": {
    "type": "look"
  }
}
```

### Separate gameplay bug fixed

`stats` and `mindstate` were previously crashing because `Character.get_active_learning_entries()` did not exist. That was fixed.

Added in:

- `typeclasses/characters.py`

Current implementation:

```python
def get_active_learning_entries(self):
    entries = [entry for entry in self.get_skill_entries(include_zero=False) if entry.get("mindstate", 0) > 0]
    entries.sort(key=lambda entry: (-entry.get("mindstate", 0), entry.get("display", entry.get("skill", "")).lower()))
    return entries
```

## What We Changed

### 1. Replaced incorrect assumptions about transport

Initial work assumed a more app-like custom envelope. Live validation showed Evennia uses array messages `[cmdname, args, kwargs]`.

### 2. Pivoted from native Godot delivery to browser-native delivery

Player-facing implementation moved into:

- `web/templates/webclient/webclient.html`
- `web/static/webclient/css/dragonsire-browser.css`
- `web/static/webclient/js/dragonsire-browser.js`

### 3. Expanded structured client payload support

Structured browser/Godot-style payload support was added on the server side for:

- `map`
- `character`
- `combat`

Relevant files:

- `world/area_forge/utils/messages.py`
- `world/area_forge/map_api.py`
- `world/area_forge/character_api.py`
- `typeclasses/characters.py`

### 4. Added client sync hooks to `Character`

Browser state refreshes were wired off movement, resource updates, equipment changes, inventory changes, targeting changes, etc.

### 5. Rebuilt the browser shell UI

The custom browser template currently includes:

- title changed to `Dragons Ire`
- left character rail
- center feed/input/status area
- right map/inventory/equipment/debug rail

### 6. Removed the stock embedded Evennia GUI

At one point the old Evennia webclient was still being instantiated underneath the custom shell. That created a hidden working output pane below the new UI.

To remove that, the template now disables the stock GUI/plugin bundle:

```django
{% block guilib_import %}{% endblock %}
```

File:

- `web/templates/webclient/webclient.html`

### 7. Rebootstrapped Evennia manually in the custom client

Removing the stock GUI also removed the default bootstrapping that called `Evennia.init()`, registered listeners, and connected the socket.

To replace that, `dragonsire-browser.js` now explicitly:

- sets `window.browser`
- calls `Evennia.init()`
- registers emitter handlers for `text`, `prompt`, `logged_in`, `connection_open`, `connection_close`, and `default`
- calls `Evennia.connect()` when needed

Relevant function:

```javascript
function bootstrapEvennia() {
  if (!window.Evennia || typeof Evennia.init !== "function") {
    return false;
  }

  if (!window.browser) {
    window.browser = window.navigator.userAgent || "dragonsire-browser";
  }

  Evennia.init();

  Evennia.emitter.off("text");
  Evennia.emitter.off("prompt");
  Evennia.emitter.off("logged_in");
  Evennia.emitter.off("connection_open");
  Evennia.emitter.off("connection_close");
  Evennia.emitter.off("default");

  Evennia.emitter.on("text", handleText);
  Evennia.emitter.on("prompt", handlePrompt);
  Evennia.emitter.on("logged_in", () => { ... });
  Evennia.emitter.on("connection_open", () => { ... });
  Evennia.emitter.on("connection_close", () => { ... });
  Evennia.emitter.on("default", onUnknownCmd);

  if (!Evennia.isConnected() && typeof Evennia.connect === "function") {
    Evennia.connect();
  }

  return true;
}
```

File:

- `web/static/webclient/js/dragonsire-browser.js`

### 8. Changed visible feed rendering to use HTML from `args`

Output rendering now joins `args` and appends HTML instead of stripping it to plain text.

Relevant function:

```javascript
function handleText(args, kwargs) {
  const html = (Array.isArray(args) ? args : [args]).map((part) => String(part || "")).join("<br>");
  const cls = kwargs && kwargs.cls ? String(kwargs.cls) : "out";
  appendRichLine(primaryFeedId(), html, cls);
  byId("footer-status").textContent = "Received text";
  appendDebug("TEXT", { args, kwargs });
  return true;
}
```

### 9. Tried to force feed visibility with CSS and inline styling

We attempted to solve the blank panel by:

- making `#console-panel` / `#console-views` / `.feed-view.active` fully flex-driven
- forcing min heights
- forcing colors and typography
- forcing row-level inline styles directly in JS

### 10. Introduced a dedicated feed target to bypass `#messagewindow`

Because `#messagewindow` appeared to be a legacy Evennia hotspot, a new dedicated visible target was added:

Template:

```html
<div id="feed-world" class="feed-view active">
  <div id="feed-surface"></div>
  <div id="messagewindow"></div>
</div>
```

CSS:

```css
#feed-surface {
  flex: 1 1 auto;
  min-height: 320px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 10px 14px;
  font-family: Consolas, "Courier New", monospace;
  font-size: 14px;
  line-height: 1.35;
  color: #f2e6cf;
}

#messagewindow {
  display: none;
}
```

JS routing:

```javascript
function primaryFeedId() {
  return byId("feed-surface") ? "feed-surface" : "messagewindow";
}
```

## Relevant Files

### Browser client

- `web/templates/webclient/webclient.html`
- `web/static/webclient/css/dragonsire-browser.css`
- `web/static/webclient/js/dragonsire-browser.js`

### Server support / structured state

- `world/area_forge/utils/messages.py`
- `world/area_forge/map_api.py`
- `world/area_forge/character_api.py`
- `typeclasses/characters.py`

### Separate command fix

- `commands/cmd_stats.py`
- `commands/cmd_mindstate.py`

## Current Observations That Matter Most

### Observation 1: feed append is happening

The feed header counter increases.

Example reported state:

- `Live session • 19 lines`
- `Live session • 25 lines`
- `Live session • 27 lines`

This strongly suggests `appendRichLine(...)` is executing and rows are being appended.

### Observation 2: debug panel proves live output

The debug panel shows incoming `TEXT` payloads in real time.

So the failure is not:

- websocket transport
- command send
- Evennia output generation
- emitter callback registration

### Observation 3: visible feed remains blank even after direct style forcing

We forced:

- container display
- container visibility
- container opacity
- row display
- row visibility
- row opacity
- row color
- row padding
- row border and background

and the main feed panel still appears blank.

This is the strongest sign that another layer or stale asset is involved.

## Important Inconsistency

There is one especially important inconsistency in the current code vs observed UI state.

Current JS only updates the visible line counter when `appendRichLine()` is called with `targetId === "messagewindow"`:

```javascript
const roomContext = byId("room-context");
if (roomContext && targetId === "messagewindow") {
  roomContext.textContent = `Live session • ${target.children.length} lines`;
}
```

But current routing code is supposed to send visible output to `feed-surface`, not `messagewindow`:

```javascript
function primaryFeedId() {
  return byId("feed-surface") ? "feed-surface" : "messagewindow";
}
```

The latest screenshots still showed the line counter increasing.

That suggests at least one of these is true:

1. stale cached JS is still running in the browser
2. stale cached HTML is still loaded and `feed-surface` is not present in the active DOM
3. the browser is not actually using the latest `dragonsire-browser.js`
4. a separate script path is still writing to `messagewindow`

This inconsistency is one of the most valuable clues currently available.

## Best Current Suspicions

### Most likely

1. Browser cache / stale asset mismatch
   - The UI behavior does not perfectly match the latest code.
   - The line-counter inconsistency strongly supports this.
  - The latest console logs confirm Evennia core bootstrap is live, but they do not eliminate stale custom asset loading.

2. Another element is overlaying the visible feed area
   - Rows may exist but be physically covered by another panel/layer.
   - This would explain why debug and counts work while the panel remains visually empty.

3. The browser is still bound to the legacy `messagewindow` path in practice
   - If the new `feed-surface` has not actually loaded, all feed writes may still be going to the old problematic target.

### Less likely

4. The appended nodes are being painted offscreen or clipped by a parent with unusual layout rules.

5. A browser extension or rendering quirk is affecting the panel.
   - This is less likely because the problem is highly localized, but not impossible.

## Recommended Next Troubleshooting Steps

### Highest value next step

Open browser devtools and verify the live DOM directly:

1. Check whether `#feed-surface` exists.
2. Check whether it contains child nodes after a `look` command.
3. Inspect computed styles for `#feed-surface` and one appended `.feed-line`.
4. Check whether another element overlays the console panel in the Elements inspector.
5. Confirm the loaded source of `dragonsire-browser.js` contains `primaryFeedId()` and `#feed-surface` routing.

### Very likely needed if caching is involved

Force a true cache-busting reload or temporarily rename the assets.

Examples:

- rename `dragonsire-browser.js` to a new filename and update the template
- rename `dragonsire-browser.css` to a new filename and update the template

This would eliminate stale asset ambiguity.

### Good fallback diagnostic

Insert a temporary absolute-position overlay inside `#console-panel`, not inside `#messagewindow`, and write incoming text there. If that overlay appears, the base feed area is being obscured or clipped.

## Most Relevant Code Anchors

### Template

- `web/templates/webclient/webclient.html`
  - disables stock GUI import via `{% block guilib_import %}{% endblock %}`
  - defines `#feed-surface`, `#messagewindow`, `#inputfield`, `#inputsend`

### Client JS

- `web/static/webclient/js/dragonsire-browser.js`
  - `primaryFeedId()`
  - `appendRichLine()`
  - `handleText()`
  - `bootstrapEvennia()`
  - startup probe sends `help`, `look`, `inventory`

### Client CSS

- `web/static/webclient/css/dragonsire-browser.css`
  - layout rules for `#console-panel`, `#console-views`, `.feed-view.active`
  - visible target `#feed-surface`
  - legacy target `#messagewindow { display: none; }`

### Character fix

- `typeclasses/characters.py`
  - `get_active_learning_entries()` added to fix `stats` and `mindstate`

## Short Diagnosis

The client is no longer blocked by transport, session, command dispatch, or Evennia output formatting.

The current bug is almost certainly one of:

- stale browser assets
- DOM mismatch between loaded HTML and current source
- overlay/clipping over the visual feed area
- residual coupling to legacy `messagewindow`

It is not a server output problem.
