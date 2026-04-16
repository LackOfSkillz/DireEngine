(function () {
  const state = {
    map: { rooms: [], edges: [], player_room_id: null },
    roomPositions: new Map(),
    hoveredRoomId: null,
    zoom: 1,
    lastEcho: { text: "", time: 0 },
    debugEnabled: false,
    selectedInventoryItem: null,
    hotbar: ["look", "inventory", "stats"],
    activeView: "world",
    character: null,
    inventoryLookup: new Map(),
    abilityLookup: new Map(),
    initialRefreshSent: false,
    commandHistory: [],
    commandHistoryIndex: -1,
    commandHistoryDraft: "",
  };

  const HOTBAR_STORAGE_KEY = "dragonsire.hotbar";
  const UI_PREFS_STORAGE_KEY = "dragonsire.browser.ui";

  function byId(id) {
    return document.getElementById(id);
  }

  function normalizeMessage(cmdname, args, kwargs) {
    return { cmd: cmdname, args: args || [], kwargs: kwargs || {} };
  }

  function primaryFeedId() {
    return byId("feed-surface") ? "feed-surface" : "messagewindow";
  }

  function appendDebug(label, payload) {
    const log = byId("debug-log");
    if (!log) return;
    const line = `[${new Date().toLocaleTimeString()}] ${label}\n${JSON.stringify(payload, null, 2)}\n\n`;
    log.textContent = (line + log.textContent).slice(0, 12000);
  }

  function appendRichLine(targetId, html, cssClass) {
    const target = byId(targetId);
    if (!target) return;
    target.style.display = "block";
    target.style.visibility = "visible";
    target.style.opacity = "1";
    target.style.color = "#f2e6cf";
    target.style.fontSize = "14px";
    target.style.lineHeight = "1.35";
    target.style.whiteSpace = "normal";
    target.style.padding = "8px 10px 14px";
    target.style.overflowY = "auto";
    target.style.minHeight = "320px";
    const row = document.createElement("div");
    row.className = `feed-line ${cssClass || "out"}`;
    row.innerHTML = html || "&nbsp;";
    row.style.display = "block";
    row.style.position = "relative";
    row.style.visibility = "visible";
    row.style.opacity = "1";
    row.style.color = "#f2e6cf";
    row.style.background = "rgba(255, 255, 255, 0.02)";
    row.style.borderLeft = "2px solid rgba(214, 176, 97, 0.35)";
    row.style.padding = "6px 8px";
    row.style.marginBottom = "6px";
    row.style.whiteSpace = "pre-wrap";
    row.style.minHeight = "1.2em";
    target.appendChild(row);
    target.scrollTop = target.scrollHeight;
    const roomContext = byId("room-context");
    if (roomContext && targetId === "messagewindow") {
      roomContext.textContent = `Live session • ${target.children.length} lines`;
    }
  }

  function rememberCommand(command) {
    const normalized = String(command || "").trim();
    if (!normalized) return;
    state.commandHistory.push(normalized);
    if (state.commandHistory.length > 100) {
      state.commandHistory = state.commandHistory.slice(-100);
    }
    state.commandHistoryIndex = -1;
    state.commandHistoryDraft = "";
  }

  function setInputValue(input, value) {
    input.value = value;
    const caret = input.value.length;
    if (typeof input.setSelectionRange === "function") {
      input.setSelectionRange(caret, caret);
    }
  }

  function navigateCommandHistory(input, direction) {
    if (!state.commandHistory.length) return false;

    if (direction < 0) {
      if (state.commandHistoryIndex === -1) {
        state.commandHistoryDraft = input.value || "";
        state.commandHistoryIndex = state.commandHistory.length - 1;
      } else if (state.commandHistoryIndex > 0) {
        state.commandHistoryIndex -= 1;
      }
      setInputValue(input, state.commandHistory[state.commandHistoryIndex] || "");
      return true;
    }

    if (state.commandHistoryIndex === -1) return false;
    if (state.commandHistoryIndex < state.commandHistory.length - 1) {
      state.commandHistoryIndex += 1;
      setInputValue(input, state.commandHistory[state.commandHistoryIndex] || "");
      return true;
    }

    state.commandHistoryIndex = -1;
    setInputValue(input, state.commandHistoryDraft || "");
    state.commandHistoryDraft = "";
    return true;
  }

  function handleText(args, kwargs) {
    const html = (Array.isArray(args) ? args : [args]).map((part) => String(part || "")).join("<br>");
    const cls = kwargs && kwargs.cls ? String(kwargs.cls) : "out";
    appendRichLine(primaryFeedId(), html, cls);
    byId("footer-status").textContent = "Received text";
    appendDebug("TEXT", { args, kwargs });
    return true;
  }

  function handlePrompt(args, kwargs) {
    const prompt = byId("prompt");
    if (!prompt) return true;
    const parser = new DOMParser();
    const html = String((args || [""])[0] || "");
    const parsed = parser.parseFromString(`<body>${html}</body>`, "text/html");
    prompt.className = `prompt ${kwargs && kwargs.cls ? kwargs.cls : "out"}`;
    prompt.textContent = (parsed.body.textContent || html || "").trim();
    byId("footer-status").textContent = "Received prompt";
    appendDebug("PROMPT", { args, kwargs });
    return true;
  }

  function requestInitialRefresh() {
    if (state.initialRefreshSent) return;
    state.initialRefreshSent = true;
    window.setTimeout(() => sendCommand("help"), 50);
    window.setTimeout(() => sendCommand("look"), 150);
    window.setTimeout(() => sendCommand("inventory"), 250);
  }

  function updateDebugSummary(message) {
    const cmdLabel = byId("debug-last-cmd");
    if (cmdLabel) cmdLabel.textContent = `Last cmd: ${message.cmd}`;
    if (message.cmd === "map") {
      const payload = message.args[0] || {};
      const roomCount = (payload.rooms || []).length;
      const edgeCount = (payload.edges || []).length;
      byId("debug-last-room-count").textContent = `Rooms: ${roomCount} / Exits: ${edgeCount}`;
    }
    if (message.cmd === "character") {
      const payload = message.args[0] || {};
      byId("debug-last-character").textContent = `Character: ${payload.name || "unknown"}`;
    }
  }

  function sendCommand(command) {
    const normalized = (command || "").trim();
    if (!normalized) return;
    echoCommand(normalized);
    byId("footer-status").textContent = `Sent ${normalized}`;
    if (window.Evennia && typeof Evennia.msg === "function") {
      Evennia.msg("text", [normalized], {});
    } else if (window.plugin_handler && typeof window.plugin_handler.onSend === "function") {
      window.plugin_handler.onSend(normalized);
    }
  }

  function echoCommand(command) {
    const normalized = (command || "").trim();
    if (!normalized) return;

    const now = Date.now();
    if (state.lastEcho.text === normalized && now - state.lastEcho.time < 250) {
      return;
    }
    state.lastEcho = { text: normalized, time: now };

    const msgWindow = byId(primaryFeedId());
    if (!msgWindow) return;

    const line = document.createElement("div");
    line.className = "cmd-echo";
    line.textContent = `> ${normalized}`;
    msgWindow.appendChild(line);
    msgWindow.scrollTop = msgWindow.scrollHeight;
  }

  function updateConnection(open) {
    const indicator = byId("connection-indicator");
    if (!indicator) return;
    indicator.textContent = open ? "Connected" : "Disconnected";
    indicator.classList.toggle("connection-open", open);
    indicator.classList.toggle("connection-closed", !open);
  }

  function toast(message) {
    const stack = byId("toast-stack");
    if (!stack) return;
    const node = document.createElement("div");
    node.className = "toast";
    node.textContent = message;
    stack.appendChild(node);
    setTimeout(() => node.remove(), 2600);
  }

  function saveHotbar() {
    try {
      window.localStorage.setItem(HOTBAR_STORAGE_KEY, JSON.stringify(state.hotbar));
    } catch (_) {}
  }

  function saveUiPrefs() {
    try {
      window.localStorage.setItem(
        UI_PREFS_STORAGE_KEY,
        JSON.stringify({
          activeView: state.activeView,
          zoom: state.zoom,
          debugEnabled: state.debugEnabled,
        })
      );
    } catch (_) {}
  }

  function loadUiPrefs() {
    try {
      const raw = window.localStorage.getItem(UI_PREFS_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        state.activeView = parsed.activeView || state.activeView;
        state.zoom = Number(parsed.zoom) || state.zoom;
        state.debugEnabled = Boolean(parsed.debugEnabled);
      }
    } catch (_) {}
  }

  function loadHotbar() {
    try {
      const raw = window.localStorage.getItem(HOTBAR_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length) {
        state.hotbar = parsed;
      }
    } catch (_) {}
  }

  function renderHotbar() {
    document.querySelectorAll(".hotbar-button").forEach((button, index) => {
      const command = state.hotbar[index] || "";
      const ability = state.abilityLookup.get(command);
      button.dataset.command = command;
      button.classList.toggle("has-ability", Boolean(ability));
      button.classList.toggle("on-cooldown", Boolean(ability && ability.cooldown > 0));
      button.textContent = ability && ability.cooldown > 0 ? `${command} ${ability.cooldown}s` : (command || `Slot ${index + 1}`);
      button.title = ability
        ? `${ability.key} • ${ability.category}${ability.roundtime ? ` • RT ${ability.roundtime}s` : ""}${ability.cooldown ? ` • CD ${ability.cooldown}s` : ""}`
        : command || "Empty hotbar slot";
    });
  }

  function normalizeInventoryEntry(entry) {
    if (!entry) return null;
    if (typeof entry === "string") {
      return {
        name: entry,
        type: "item",
        wearable: false,
        wieldable: false,
        is_wielded: false,
        actions: ["look", "drop"],
      };
    }
    return {
      name: entry.name || "item",
      type: entry.type || "item",
      slot: entry.slot || null,
      wearable: Boolean(entry.wearable),
      wieldable: Boolean(entry.wieldable),
      weapon_type: entry.weapon_type || null,
      is_wielded: Boolean(entry.is_wielded),
      actions: Array.isArray(entry.actions) && entry.actions.length ? entry.actions : ["look", "drop"],
    };
  }

  function selectedInventoryEntry() {
    return state.inventoryLookup.get(state.selectedInventoryItem) || null;
  }

  function updateInventoryActions(entry) {
    const buttons = Array.from(document.querySelectorAll("#inventory-actions button"));
    const fallback = ["look", "drop", "drop"];
    const actions = entry ? entry.actions.slice(0, 3) : fallback;
    buttons.forEach((button, index) => {
      const action = actions[index] || fallback[index];
      button.dataset.action = action;
      button.textContent = action.charAt(0).toUpperCase() + action.slice(1);
    });
    byId("inventory-mode").textContent = entry
      ? `${entry.type}${entry.slot ? ` • ${entry.slot}` : ""}`
      : "Click to inspect";
  }

  function renderAbilities(payload) {
    state.abilityLookup = new Map((payload.abilities || []).map((ability) => [ability.key, ability]));
    const abilityList = byId("ability-list");
    if (!abilityList) return;
    abilityList.innerHTML = "";

    (payload.abilities || []).forEach((ability) => {
      const row = document.createElement("button");
      row.className = "ability-item";
      row.type = "button";
      row.title = `${ability.category}${ability.required_skill ? ` • ${ability.required_skill} ${ability.current_rank}/${ability.required_rank}` : ""}`;
      row.innerHTML = `<span class="ability-name">${ability.key}</span><span class="ability-meta">${ability.cooldown > 0 ? `CD ${ability.cooldown}s` : ability.category}</span>`;
      row.addEventListener("click", () => {
        if (ability.cooldown > 0) {
          toast(`${ability.key} is on cooldown for ${ability.cooldown}s`);
          return;
        }
        sendCommand(ability.key);
      });
      abilityList.appendChild(row);
    });

    if (!abilityList.children.length) {
      const empty = document.createElement("div");
      empty.className = "status-tag";
      empty.textContent = "No abilities exposed yet";
      abilityList.appendChild(empty);
    }
  }

  function updateCharacter(payload) {
    state.character = payload;
    state.inventoryLookup = new Map();
    byId("character-name").textContent = payload.name || "Adventurer";
    const crest = document.querySelector(".crest-banner");
    if (crest) {
      crest.textContent = payload.guild
        ? `${String(payload.guild).replace(/_/g, " ").toUpperCase()} INTERFACE`
        : "Wayfarer Interface";
    }

    const hp = payload.hp || 0;
    const maxHp = payload.max_hp || 100;
    const stamina = payload.stamina || 0;
    const maxStamina = payload.max_stamina || 100;

    byId("character-hp-label").textContent = `Health ${hp} / ${maxHp}`;
    byId("character-stamina-label").textContent = `Stamina ${stamina} / ${maxStamina}`;
    byId("hp-fill").style.width = `${Math.max(0, Math.min(100, (hp / maxHp) * 100))}%`;
    byId("stamina-fill").style.width = `${Math.max(0, Math.min(100, (stamina / maxStamina) * 100))}%`;
    byId("hp-fill-footer").style.width = `${Math.max(0, Math.min(100, (hp / maxHp) * 100))}%`;
    byId("stamina-fill-footer").style.width = `${Math.max(0, Math.min(100, (stamina / maxStamina) * 100))}%`;

    const inventoryList = byId("inventory-list");
    inventoryList.innerHTML = "";
    (payload.inventory || []).map(normalizeInventoryEntry).filter(Boolean).forEach((item) => {
      state.inventoryLookup.set(item.name, item);
      const row = document.createElement("button");
      row.className = "inventory-item";
      row.draggable = true;
      row.title = `${item.type}${item.slot ? ` • ${item.slot}` : ""}`;
      if (state.selectedInventoryItem === item.name) {
        row.classList.add("is-selected");
      }
      row.textContent = item.is_wielded ? `${item.name} (wielded)` : item.name;
      row.addEventListener("click", () => {
        state.selectedInventoryItem = item.name;
        updateCharacter(payload);
      });
      row.addEventListener("dblclick", () => sendCommand(`look ${item.name}`));
      row.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", item.name);
        event.dataTransfer.setData("application/x-dragonsire-item", JSON.stringify(item));
        event.dataTransfer.effectAllowed = "copy";
      });
      inventoryList.appendChild(row);
    });

    if (state.selectedInventoryItem && !state.inventoryLookup.has(state.selectedInventoryItem)) {
      state.selectedInventoryItem = null;
    }
    updateInventoryActions(selectedInventoryEntry());

    const equipmentList = byId("equipment-list");
    equipmentList.innerHTML = "";
    if (payload.equipped_weapon) {
      const weaponRow = document.createElement("div");
      weaponRow.className = "equipment-item";
      weaponRow.textContent = `weapon: ${payload.equipped_weapon}`;
      equipmentList.appendChild(weaponRow);
    }
    Object.entries(payload.equipment || {}).forEach(([slot, value]) => {
      if (!value || (Array.isArray(value) && !value.length)) {
        return;
      }
      const row = document.createElement("div");
      row.className = "equipment-item";
      row.textContent = `${slot}: ${Array.isArray(value) ? value.join(", ") : value}`;
      equipmentList.appendChild(row);
    });

    const statusList = byId("status-list");
    statusList.innerHTML = "";
    (payload.status || []).forEach((status) => {
      const row = document.createElement("div");
      row.className = "status-tag";
      row.textContent = status;
      statusList.appendChild(row);
    });

    if (!statusList.children.length) {
      const row = document.createElement("div");
      row.className = "status-tag";
      row.textContent = "Ready";
      statusList.appendChild(row);
    }

    byId("footer-status").textContent = payload.in_combat
      ? `Target ${payload.target || "unknown"}`
      : (payload.status && payload.status[0]) || "Standing by";

    renderAbilities(payload);
    renderHotbar();
  }

  function roomById(roomId) {
    return state.map.rooms.find((room) => room.id === roomId);
  }

  function isPlayerRoom(room) {
    return Boolean(room && (room.is_player || room.current || room.id === state.map.player_room_id));
  }

  function roomColor(room) {
    if (room.map_color) return room.map_color;
    if (isPlayerRoom(room)) return "#df564a";
    if (room.has_guild_entrance) return "#f0d45f";
    if (room.has_poi) return "#69b8ff";
    if (room.type === "guild_entrance") return "#f0d45f";
    if (room.type === "poi") return "#69b8ff";
    if (room.type === "guild") return "#bc7eff";
    if (room.type === "shop") return "#69b8ff";
    return "#5f8f57";
  }

  function worldPosition(room, canvas) {
    const spacing = 34 * state.zoom;
    return {
      x: canvas.width / 2 + room.x * spacing,
      y: canvas.height / 2 + room.y * spacing,
    };
  }

  function renderMap() {
    const canvas = byId("map-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    state.roomPositions.clear();

    state.map.rooms.forEach((room) => {
      state.roomPositions.set(room.id, worldPosition(room, canvas));
    });

    state.map.edges.forEach((edge) => {
      const from = state.roomPositions.get(edge.from);
      const to = state.roomPositions.get(edge.to);
      if (!from || !to) return;
      ctx.strokeStyle = "rgba(195, 164, 104, 0.35)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    state.map.rooms.forEach((room) => {
      const pos = state.roomPositions.get(room.id);
      const playerRoom = isPlayerRoom(room);
      const radius = playerRoom ? 9 : 6;
      if (room.id === state.hoveredRoomId) {
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = roomColor(room);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fill();
    });

    const currentRoom = roomById(state.map.player_room_id);
    if (currentRoom) {
      byId("map-room-name").textContent = currentRoom.name;
      byId("room-context").textContent = currentRoom.name;
    }
    byId("map-meta-rooms").textContent = `Rooms ${state.map.rooms.length}`;
    byId("map-meta-exits").textContent = `Exits ${state.map.edges.length}`;
    byId("map-meta-zoom").textContent = `Zoom ${state.zoom.toFixed(1)}x`;
    renderExitStrip();
    updateCompassFromMap();
  }

  function renderExitStrip() {
    const strip = byId("exit-strip");
    if (!strip) return;
    strip.innerHTML = "";
    state.map.edges
      .filter((edge) => edge.from === state.map.player_room_id)
      .forEach((edge) => {
        const chip = document.createElement("button");
        chip.className = "exit-chip";
        chip.textContent = edge.dir;
        chip.addEventListener("click", () => sendCommand(edge.dir));
        strip.appendChild(chip);
      });
  }

  function updateCompassFromMap() {
    const available = new Set(
      state.map.edges
        .filter((edge) => edge.from === state.map.player_room_id)
        .map((edge) => (edge.dir || "").toLowerCase())
    );

    document.querySelectorAll("#compass button").forEach((button) => {
      const dir = (button.dataset.dir || "").toLowerCase();
      const enabled = dir === "look" || available.has(dir);
      button.disabled = !enabled;
      button.classList.toggle("disabled", !enabled);
    });
  }

  function updateMap(payload) {
    state.map = {
      rooms: payload.rooms || [],
      edges: payload.edges || [],
      player_room_id: payload.player_room_id,
    };
    renderMap();
    saveUiPrefs();
  }

  function switchView(viewName) {
    state.activeView = viewName;
    document.querySelectorAll("#topbar-tabs .chrome-tab").forEach((button) => {
      button.classList.toggle("active", button.dataset.view === viewName);
    });
    document.querySelectorAll(".feed-view").forEach((panel) => {
      panel.classList.toggle("active", panel.id === `feed-${viewName}`);
    });
    if (viewName === "map") {
      document.getElementById("map-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (viewName === "inventory") {
      document.getElementById("inventory-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    saveUiPrefs();
  }

  function appendChatLine(text) {
    const chatWindow = byId("chatwindow");
    if (!chatWindow) return;
    const row = document.createElement("div");
    row.textContent = text;
    chatWindow.appendChild(row);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function updateTooltip(clientX, clientY, room) {
    const tooltip = byId("map-tooltip");
    if (!room) {
      tooltip.style.display = "none";
      state.hoveredRoomId = null;
      renderMap();
      return;
    }
    tooltip.textContent = room.name;
    tooltip.style.display = "block";
    tooltip.style.left = `${clientX}px`;
    tooltip.style.top = `${clientY}px`;
    state.hoveredRoomId = room.id;
    renderMap();
  }

  function roomAtCanvasPosition(x, y) {
    for (const room of state.map.rooms) {
      const pos = state.roomPositions.get(room.id);
      if (!pos) continue;
      const dx = pos.x - x;
      const dy = pos.y - y;
      if (Math.sqrt(dx * dx + dy * dy) <= 12) {
        return room;
      }
    }
    return null;
  }

  function setupMapInteractions() {
    const canvas = byId("map-canvas");
    canvas.addEventListener("mousemove", (event) => {
      const rect = canvas.getBoundingClientRect();
      const room = roomAtCanvasPosition(
        ((event.clientX - rect.left) / rect.width) * canvas.width,
        ((event.clientY - rect.top) / rect.height) * canvas.height
      );
      updateTooltip(event.clientX, event.clientY, room);
    });

    canvas.addEventListener("mouseleave", () => updateTooltip(0, 0, null));

    canvas.addEventListener("click", (event) => {
      const rect = canvas.getBoundingClientRect();
      const room = roomAtCanvasPosition(
        ((event.clientX - rect.left) / rect.width) * canvas.width,
        ((event.clientY - rect.top) / rect.height) * canvas.height
      );
      if (!room || room.id === state.map.player_room_id) return;
      const edge = state.map.edges.find((entry) => entry.from === state.map.player_room_id && entry.to === room.id);
      if (edge && edge.dir) {
        sendCommand(edge.dir);
      }
    });

    canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      state.zoom = Math.max(0.5, Math.min(2.5, state.zoom + (event.deltaY < 0 ? 0.1 : -0.1)));
      renderMap();
      saveUiPrefs();
    });
  }

  function attachDropTarget(node, onDrop) {
    if (!node) return;
    node.addEventListener("dragover", (event) => {
      event.preventDefault();
      node.classList.add("drop-target-active");
    });
    node.addEventListener("dragleave", () => node.classList.remove("drop-target-active"));
    node.addEventListener("drop", (event) => {
      event.preventDefault();
      node.classList.remove("drop-target-active");
      const item = event.dataTransfer.getData("text/plain");
      if (item) {
        onDrop(item, event);
      }
    });
  }

  function bindInputControls() {
    const input = byId("inputfield");
    const sendButton = byId("inputsend");
    if (!input || !sendButton) return;

    const submitInput = () => {
      const value = input.value || "";
      if (!value.trim()) return;
      rememberCommand(value);
      sendCommand(value);
      input.value = "";
      input.focus();
    };

    sendButton.addEventListener("click", (event) => {
      event.preventDefault();
      submitInput();
    });

    input.addEventListener("keydown", (event) => {
      if (!event.shiftKey && !event.ctrlKey && !event.altKey && !event.metaKey) {
        if (event.key === "ArrowUp" && navigateCommandHistory(input, -1)) {
          event.preventDefault();
          return;
        }
        if (event.key === "ArrowDown" && navigateCommandHistory(input, 1)) {
          event.preventDefault();
          return;
        }
      }
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        submitInput();
      }
    });

    input.addEventListener("input", () => {
      if (state.commandHistoryIndex === -1) {
        state.commandHistoryDraft = input.value || "";
      }
    });
  }

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
    Evennia.emitter.on("logged_in", () => {
      updateConnection(true);
      byId("footer-status").textContent = "Logged in";
      requestInitialRefresh();
    });
    Evennia.emitter.on("connection_open", () => {
      updateConnection(true);
      byId("footer-status").textContent = "Connection open";
      requestInitialRefresh();
    });
    Evennia.emitter.on("connection_close", () => {
      updateConnection(false);
      byId("footer-status").textContent = "Connection closed";
    });
    Evennia.emitter.on("default", onUnknownCmd);

    if (!Evennia.isConnected() && typeof Evennia.connect === "function") {
      Evennia.connect();
    }

    return true;
  }

  function handleCombat(payload) {
    const line = `You hit ${payload.target || "target"} for ${payload.damage || 0} damage.`;
    const msgWindow = byId(primaryFeedId());
    const row = document.createElement("div");
    row.textContent = line;
    msgWindow.appendChild(row);
    msgWindow.scrollTop = msgWindow.scrollHeight;
    byId("footer-status").textContent = `Combat: ${payload.target || "target"}`;
    byId("character-card").classList.remove("combat-flash");
    void byId("character-card").offsetWidth;
    byId("character-card").classList.add("combat-flash");
    toast(line);
  }

  function onUnknownCmd(cmdname, args, kwargs) {
    const message = normalizeMessage(cmdname, args, kwargs);
    appendDebug(`IN ${message.cmd}`, message);
    updateDebugSummary(message);
    switch (message.cmd) {
      case "map":
        updateMap(message.args[0] || {});
        return true;
      case "character":
        updateCharacter(message.args[0] || {});
        return true;
      case "combat":
        handleCombat(message.args[0] || {});
        return true;
      case "chat":
        appendChatLine(String((message.args[0] || {}).text || ""));
        return true;
      default:
        return false;
    }
  }

  function init() {
    loadHotbar();
    loadUiPrefs();
    bootstrapEvennia();
    renderHotbar();
    setupMapInteractions();
    bindInputControls();
    const debugToggle = byId("debug-toggle");
    if (debugToggle) {
      byId("debug-panel").classList.toggle("collapsed", !state.debugEnabled);
      debugToggle.textContent = state.debugEnabled ? "Hide" : "Show";
      debugToggle.addEventListener("click", () => {
        state.debugEnabled = !state.debugEnabled;
        byId("debug-panel").classList.toggle("collapsed", !state.debugEnabled);
        debugToggle.textContent = state.debugEnabled ? "Hide" : "Show";
        saveUiPrefs();
      });
    }

    document.querySelectorAll("#topbar-tabs .chrome-tab").forEach((button) => {
      button.addEventListener("click", () => switchView(button.dataset.view));
    });
    switchView(state.activeView);

    appendRichLine(primaryFeedId(), "<strong>Client feed online.</strong>", "sys");

    document.querySelectorAll("#compass button").forEach((button) => {
      button.addEventListener("click", () => {
        if (!button.disabled) {
          sendCommand(button.dataset.dir);
        }
      });
    });
    document.querySelectorAll(".hotbar-button").forEach((button) => {
      button.addEventListener("click", () => {
        const command = button.dataset.command;
        const ability = state.abilityLookup.get(command);
        if (ability && ability.cooldown > 0) {
          toast(`${ability.key} is on cooldown for ${ability.cooldown}s`);
          return;
        }
        sendCommand(command);
      });
      button.addEventListener("contextmenu", (event) => {
        event.preventDefault();
        const index = Number(button.dataset.index);
        const current = state.hotbar[index] || "";
        const next = window.prompt("Set hotbar command", current);
        if (next === null) return;
        state.hotbar[index] = next.trim();
        saveHotbar();
        renderHotbar();
        toast(`Hotbar slot ${index + 1} updated`);
      });
      attachDropTarget(button, (item) => {
        const index = Number(button.dataset.index);
        state.hotbar[index] = item;
        saveHotbar();
        renderHotbar();
        toast(`${item} assigned to hotbar slot ${index + 1}`);
      });
    });

    attachDropTarget(byId("equipment-panel"), (item) => {
      const entry = state.inventoryLookup.get(item);
      const action = entry?.wearable ? "wear" : entry?.wieldable ? "wield" : "look";
      sendCommand(`${action} ${item}`);
      toast(`${action} ${item}`);
    });

    document.querySelectorAll("#inventory-actions button").forEach((button) => {
      button.addEventListener("click", () => {
        const entry = selectedInventoryEntry();
        if (!entry) {
          byId("footer-status").textContent = "Select an inventory item first";
          return;
        }
        const action = button.dataset.action;
        byId("footer-status").textContent = `${action} ${entry.name}`;
        sendCommand(`${action} ${entry.name}`);
        toast(`${action} ${entry.name}`);
      });
    });

    updateConnection(window.Evennia && typeof Evennia.isConnected === "function" ? Evennia.isConnected() : false);
    window.setTimeout(() => {
      bootstrapEvennia();
      const input = byId("inputfield");
      if (input) {
        input.focus();
      }
      requestInitialRefresh();
    }, 800);
  }

  if (window.plugin_handler && typeof plugin_handler.add === "function") {
    plugin_handler.add("dragonsire_browser", {
      init: init,
      onText: handleText,
      onPrompt: handlePrompt,
      onUnknownCmd: onUnknownCmd,
      onConnectionClose: () => updateConnection(false),
    });
  } else {
    window.addEventListener("load", init);
  }
})();