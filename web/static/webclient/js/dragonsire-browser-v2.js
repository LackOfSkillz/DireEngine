(function () {
  console.log("DRAGONSIRE CLIENT v2 LOADED");
  window.DRAGONSIRE_CLIENT_VERSION = "v2";

  const state = {
    mode: getRequestedInitialMode(),
    map: { rooms: [], edges: [], exits: [], player_room_id: null, zone: null },
    builder: {
      enabled: false,
      areaId: "",
      busy: false,
      launcherBusy: false,
      lastExport: null,
      lastDiff: null,
      lastUndoDiff: null,
      history: [],
    },
    roomPositions: new Map(),
    hoveredRoomId: null,
    zoom: 1,
    mapScale: 1,
    mapOffset: { x: 24, y: 24 },
    mapAutoFit: true,
    mapRefitRequestId: 0,
    isDragging: false,
    suppressMapClick: false,
    lastMouse: { x: 0, y: 0 },
    isWalking: false,
    autoWalkEnabled: true,
    walkToken: 0,
    lastEcho: { text: "", time: 0 },
    debugEnabled: false,
    selectedInventoryItem: null,
    hotbar: ["look", "inv", "attack"],
    activeView: "world",
    character: null,
    subsystem: null,
    inventoryLookup: new Map(),
    abilityLookup: new Map(),
    initialRefreshSent: false,
    recentCharacters: [],
    audioEnabled: true,
    rightRailOrder: ["map", "inventory", "equipment", "debug"],
    reconnectTimer: null,
    reconnectCountdown: 0,
    reconnectAttempts: 0,
    commandHistory: [],
    commandHistoryIndex: -1,
    commandHistoryDraft: "",
  };

  const HOTBAR_STORAGE_KEY = "dragonsire.hotbar";
  const UI_PREFS_STORAGE_KEY = "dragonsire.browser.ui";
  const ROOM_IMAGE_LIBRARY = {
    city: "Nightwatch atop the city rooftops.png",
    market: "Twilight market antics.png",
    forest: "Ranger in twilight forest aiming at stag.png",
    lake: "Autumn warriors by the lake (1).png",
    spring: "Elven guardians of the spring city.png",
    graveyard: "Elothien defenders in a haunted graveyard.png",
    forge: "Warrior mage and runesmith in forge.png",
    tavern: "Healing through music and magic.png",
    guild: "Warriors of the fiery forge.png",
    stealth: "The rogue's secret heist.png",
    village: "Moonlit guardians of the hamlet.png",
    fallback: "hero.png",
  };

  function getRequestedInitialMode() {
    const requested = String(new URLSearchParams(window.location.search).get("mode") || "").trim().toLowerCase();
    if (["landing", "play", "build"].includes(requested)) {
      return requested;
    }
    return "play";
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function normalizeSceneToken(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function staticRoomImageUrl(fileName) {
    return `/static/website/images/${encodeURIComponent(fileName)}`;
  }

  function resolveRoomImage(currentRoom) {
    if (!currentRoom) {
      return {
        src: staticRoomImageUrl(ROOM_IMAGE_LIBRARY.fallback),
        caption: "Dragonsire",
      };
    }

    if (currentRoom.image_key) {
      return {
        src: String(currentRoom.image_key).startsWith("/")
          ? String(currentRoom.image_key)
          : staticRoomImageUrl(String(currentRoom.image_key)),
        caption: currentRoom.name || "Dragonsire",
      };
    }

    const zone = normalizeSceneToken(state.map.zone);
    const roomType = normalizeSceneToken(currentRoom.type);
    const roomName = normalizeSceneToken(currentRoom.name);
    const sceneText = [zone, roomType, roomName].filter(Boolean).join(" ");

    const keywordMap = [
      [["market", "bazaar", "merchant", "square"], ROOM_IMAGE_LIBRARY.market],
      [["alley", "street", "lane", "midway", "riverfront", "urban", "city", "landing", "reach"], ROOM_IMAGE_LIBRARY.city],
      [["forest", "wood", "grove", "trail", "path", "ranger"], ROOM_IMAGE_LIBRARY.forest],
      [["lake", "shore", "waterfront", "river", "dock"], ROOM_IMAGE_LIBRARY.lake],
      [["spring", "sanctuary", "garden"], ROOM_IMAGE_LIBRARY.spring],
      [["graveyard", "crypt", "haunted", "cemetery", "undead"], ROOM_IMAGE_LIBRARY.graveyard],
      [["forge", "smith", "anvil", "fire", "runesmith"], ROOM_IMAGE_LIBRARY.forge],
      [["tavern", "inn", "music", "hall"], ROOM_IMAGE_LIBRARY.tavern],
      [["guild", "temple", "cleric", "chapel"], ROOM_IMAGE_LIBRARY.guild],
      [["rogue", "thief", "stealth", "hideout"], ROOM_IMAGE_LIBRARY.stealth],
      [["hamlet", "village"], ROOM_IMAGE_LIBRARY.village],
    ];

    const matched = keywordMap.find(([keywords]) => keywords.some((keyword) => sceneText.includes(keyword)));
    return {
      src: staticRoomImageUrl(matched ? matched[1] : ROOM_IMAGE_LIBRARY.fallback),
      caption: currentRoom.name || String(state.map.zone || "Dragonsire"),
    };
  }

  function updateSceneImage(currentRoom) {
    const sceneImage = byId("scene-image");
    if (!sceneImage) return;
    const resolved = resolveRoomImage(currentRoom);
    sceneImage.style.backgroundImage = `linear-gradient(180deg, rgba(15, 11, 8, 0.08), rgba(15, 11, 8, 0.35)), url("${resolved.src}")`;
    sceneImage.dataset.caption = resolved.caption || "";
    sceneImage.setAttribute("aria-label", resolved.caption || "Room illustration");
    sceneImage.title = resolved.caption || "";
  }

  function railContainer() {
    return byId("right-sidebar") || byId("sidebar") || byId("right-rail");
  }

  function syncModeInUrl() {
    const url = new URL(window.location.href);
    url.searchParams.set("mode", state.mode);
    window.history.replaceState({}, "", url.toString());
  }

  function renderMode() {
    const landing = byId("mode-landing");
    const play = byId("mode-play");
    const build = byId("mode-build");
    if (landing) {
      landing.hidden = state.mode !== "landing";
    }
    if (play) {
      play.hidden = state.mode !== "play";
    }
    if (build) {
      build.hidden = state.mode !== "build";
    }
    document.body.dataset.mode = state.mode;
    const legacyBuilderPanel = byId("builder-panel");
    if (legacyBuilderPanel) {
      legacyBuilderPanel.hidden = state.mode !== "build" || !state.builder.enabled;
    }
  }

  function ensureBuildMode(contextLabel = "Builder action") {
    if (state.mode === "build") {
      return true;
    }
    toast(`${contextLabel} is only available in build mode.`);
    return false;
  }

  function setMode(mode) {
    const normalized = String(mode || "").trim().toLowerCase();
    if (!["landing", "play", "build"].includes(normalized)) {
      return;
    }
    state.mode = normalized;
    console.log("Mode:", state.mode);
    syncModeInUrl();
    renderMode();
    if ((state.mode === "play" || state.mode === "build") && !state.initialRefreshSent) {
      requestInitialRefresh();
    }
    if (state.mode === "play") {
      const input = byId("inputfield");
      if (input) {
        input.focus();
      }
    }
  }

  function ensureRailBrandPresent() {
    const rail = byId("left-rail-body");
    if (!rail) return;

    let brand = rail.querySelector(":scope > .left-rail-brand");
    if (!brand) {
      brand = document.createElement("div");
      brand.className = "left-rail-brand";

      const badge = document.createElement("div");
      badge.className = "engine-badge";
      badge.textContent = "DireEngine";

      const crest = document.createElement("div");
      crest.className = "crest-banner";
      crest.textContent = "Wayfarer Interface";

      brand.appendChild(badge);
      brand.appendChild(crest);
    }

    const staleBadge = rail.querySelector(":scope > .brand-mark-frame, :scope > .portrait-frame");
    if (staleBadge && staleBadge.parentNode === rail) {
      staleBadge.remove();
    }

    const staleCrest = Array.from(rail.querySelectorAll(":scope > .crest-banner")).find((node) => node.parentNode === rail && !node.closest(".left-rail-brand"));
    if (staleCrest) {
      staleCrest.remove();
    }

    if (brand.parentNode !== rail || rail.firstElementChild !== brand) {
      rail.insertBefore(brand, rail.firstChild);
    }
  }

  function resetLeftRailScroll() {
    const body = byId("left-rail-body");
    const rail = byId("left-rail");
    if (body) {
      body.scrollTop = 0;
      body.scrollLeft = 0;
    }
    if (rail) {
      rail.scrollTop = 0;
      rail.scrollLeft = 0;
    }
  }


  function stripHtmlToText(html) {
    const parser = new DOMParser();
    const parsed = parser.parseFromString(`<body>${String(html || "")}</body>`, "text/html");
    return (parsed.body.textContent || "").trim();
  }

  function setSessionStatus(text) {
    const node = byId("session-status");
    if (node) {
      node.textContent = text;
    }
  }

  function updateAudioToggleLabel() {
    const button = byId("audio-toggle");
    if (button) {
      button.textContent = state.audioEnabled ? "Audio On" : "Audio Off";
    }
  }

  function playTone(kind) {
    if (!state.audioEnabled) return;
    const AudioCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtor) return;

    playTone.ctx = playTone.ctx || new AudioCtor();
    const context = playTone.ctx;
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const profile = {
      combat: { frequency: 220, duration: 0.12, volume: 0.03 },
      chat: { frequency: 540, duration: 0.08, volume: 0.02 },
      reconnect: { frequency: 320, duration: 0.08, volume: 0.025 },
      ready: { frequency: 660, duration: 0.05, volume: 0.015 },
    }[kind] || { frequency: 440, duration: 0.06, volume: 0.02 };

    oscillator.type = kind === "combat" ? "sawtooth" : "sine";
    oscillator.frequency.value = profile.frequency;
    gain.gain.value = profile.volume;
    oscillator.connect(gain);
    gain.connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + profile.duration);
  }

  function renderRecentCharacters() {
    const list = byId("recent-characters");
    if (!list) return;
    list.innerHTML = "";
    state.recentCharacters.forEach((name) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "recent-character";
      button.textContent = name;
      button.addEventListener("click", () => {
        switchView("world");
        sendCommand(`connect ${name}`);
      });
      list.appendChild(button);
    });
    if (!list.children.length) {
      const empty = document.createElement("div");
      empty.className = "status-tag";
      empty.textContent = "No recent characters";
      list.appendChild(empty);
    }
  }

  function rememberCharacter(name) {
    const normalized = String(name || "").trim();
    if (!normalized) return;
    state.recentCharacters = [normalized, ...state.recentCharacters.filter((entry) => entry !== normalized)].slice(0, 5);
    renderRecentCharacters();
    saveUiPrefs();
  }

  function saveRailOrder() {
    const rail = railContainer();
    if (!rail) return;
    state.rightRailOrder = Array.from(rail.querySelectorAll(".rail-panel")).map((panel) => panel.dataset.panelKey).filter(Boolean);
    saveUiPrefs();
  }

  function applyRailOrder() {
    const rail = railContainer();
    if (!rail) return;
    state.rightRailOrder.forEach((key) => {
      const panel = rail.querySelector(`.rail-panel[data-panel-key="${key}"]`);
      if (panel) {
        rail.appendChild(panel);
      }
    });
  }

  function bindRailPanels() {
    const rail = railContainer();
    if (!rail) return;
    let draggedPanel = null;
    rail.querySelectorAll(".rail-panel").forEach((panel) => {
      panel.addEventListener("dragstart", () => {
        draggedPanel = panel;
        panel.classList.add("is-dragging");
      });
      panel.addEventListener("dragend", () => {
        panel.classList.remove("is-dragging");
        rail.querySelectorAll(".rail-panel").forEach((node) => node.classList.remove("drop-target-active"));
        draggedPanel = null;
        saveRailOrder();
      });
      panel.addEventListener("dragover", (event) => {
        event.preventDefault();
        if (!draggedPanel || draggedPanel === panel) return;
        panel.classList.add("drop-target-active");
      });
      panel.addEventListener("dragleave", () => panel.classList.remove("drop-target-active"));
      panel.addEventListener("drop", (event) => {
        event.preventDefault();
        panel.classList.remove("drop-target-active");
        if (!draggedPanel || draggedPanel === panel) return;
        const rect = panel.getBoundingClientRect();
        const insertAfter = event.clientY > rect.top + rect.height / 2;
        if (insertAfter) {
          rail.insertBefore(draggedPanel, panel.nextSibling);
        } else {
          rail.insertBefore(draggedPanel, panel);
        }
        saveRailOrder();
      });
    });
  }

  function scheduleReconnect() {
    if (state.reconnectTimer || (window.Evennia && typeof Evennia.isConnected === "function" && Evennia.isConnected())) {
      return;
    }
    state.reconnectAttempts += 1;
    state.reconnectCountdown = Math.min(10, 2 + state.reconnectAttempts);
    setSessionStatus(`Reconnecting in ${state.reconnectCountdown}s`);
    state.reconnectTimer = window.setInterval(() => {
      state.reconnectCountdown -= 1;
      if (state.reconnectCountdown > 0) {
        setSessionStatus(`Reconnecting in ${state.reconnectCountdown}s`);
        return;
      }
      window.clearInterval(state.reconnectTimer);
      state.reconnectTimer = null;
      setSessionStatus("Attempting reconnect");
      if (window.Evennia && typeof Evennia.connect === "function") {
        Evennia.connect();
        playTone("reconnect");
      }
    }, 1000);
  }

  function cancelReconnect() {
    if (state.reconnectTimer) {
      window.clearInterval(state.reconnectTimer);
      state.reconnectTimer = null;
    }
    state.reconnectCountdown = 0;
    state.reconnectAttempts = 0;
  }

  function isLikelyChatText(text, kwargs) {
    const lowered = String(text || "").toLowerCase();
    const typeValue = String((kwargs && kwargs.type) || "").toLowerCase();
    if (["say", "whisper", "tell", "pose", "chat"].includes(typeValue)) {
      return true;
    }
    return [
      " you say",
      " says,",
      " asks,",
      " whispers",
      " tells you",
      "[global]",
      "[trade]",
      "[chat]",
      "(ooc)",
    ].some((fragment) => lowered.includes(fragment));
  }

  function normalizeInputForView(command) {
    const raw = String(command || "").trim();
    if (!raw) return raw;
    if (state.activeView !== "chat") return raw;
    if (raw.startsWith("/")) return raw.slice(1).trim();
    if (/^(say|whisper|pose|emote|ooc|tell)\b/i.test(raw)) return raw;
    return `say ${raw}`;
  }

  function updateInputHint() {
    const input = byId("inputfield");
    if (!input) return;
    input.placeholder = state.activeView === "chat"
      ? "Chat mode: type to say, or prefix / for commands"
      : "Enter a command";
  }

  function primaryFeedId() {
    return byId("feed-surface") ? "feed-surface" : byId("messagewindow") ? "messagewindow" : "feed-overlay";
  }

  function appendDebug(label, payload) {
    const log = byId("debug-log");
    if (!log) return;
    const line = `[${new Date().toLocaleTimeString()}] ${label}\n${JSON.stringify(payload, null, 2)}\n\n`;
    log.textContent = (line + log.textContent).slice(0, 12000);
  }

  function scrollFeedToBottom(target) {
    if (!target) return;
    const containers = [
      target,
      target.closest("#feed-text"),
      target.closest("#feed-world"),
      target.closest("#feed-chat"),
    ].filter(Boolean);

    requestAnimationFrame(() => {
      containers.forEach((node) => {
        node.scrollTop = node.scrollHeight;
      });
    });
  }

  function appendRichLine(targetId, html, cssClass) {
    const target = byId(targetId);
    if (!target) return;
    target.style.display = "block";
    target.style.visibility = "visible";
    target.style.opacity = "1";
    const row = document.createElement("div");
    row.className = `feed-line ${cssClass || "out"}`;
    row.innerHTML = html || "&nbsp;";
    target.appendChild(row);
    scrollFeedToBottom(target);
    const roomContext = byId("room-context");
    if (roomContext && targetId === primaryFeedId()) {
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
    const plainText = stripHtmlToText(html);
    if (isLikelyChatText(plainText, kwargs)) {
      appendChatLine(plainText, cls);
      playTone("chat");
    }
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
      const edgeCount = (payload.edges || payload.exits || []).length;
      byId("debug-last-room-count").textContent = `Rooms: ${roomCount} / Exits: ${edgeCount}`;
    }
    if (message.cmd === "character") {
      const payload = message.args[0] || {};
      byId("debug-last-character").textContent = `Character: ${payload.name || "unknown"}`;
      const profession = payload.profession || "Unknown";
      const rank = payload.profession_rank || "Unknown";
      const node = byId("debug-last-profession");
      if (node) node.textContent = `Profession: ${profession}, Rank: ${rank}`;
    }
    if (message.cmd === "subsystem") {
      const payload = message.args[0] || {};
      const node = byId("debug-last-subsystem");
      if (node) node.textContent = `Subsystem: ${JSON.stringify(payload)}`;
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
    scrollFeedToBottom(msgWindow);
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
          builderAreaId: state.builder.areaId,
          zoom: state.zoom,
          debugEnabled: state.debugEnabled,
          audioEnabled: state.audioEnabled,
          recentCharacters: state.recentCharacters,
          rightRailOrder: state.rightRailOrder,
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
        state.builder.areaId = String(parsed.builderAreaId || state.builder.areaId || "").trim();
        state.zoom = Number(parsed.zoom) || state.zoom;
        state.debugEnabled = Boolean(parsed.debugEnabled);
        state.audioEnabled = parsed.audioEnabled !== undefined ? Boolean(parsed.audioEnabled) : state.audioEnabled;
        state.recentCharacters = Array.isArray(parsed.recentCharacters) ? parsed.recentCharacters.slice(0, 5) : state.recentCharacters;
        state.rightRailOrder = Array.isArray(parsed.rightRailOrder) && parsed.rightRailOrder.length
          ? parsed.rightRailOrder
          : state.rightRailOrder;
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
      row.className = `ability-item${ability.locked ? " is-locked" : ""}`;
      row.type = "button";
      row.title = `${ability.category}${ability.required_skill ? ` • ${ability.required_skill} ${ability.current_rank}/${ability.required_rank}` : ""}${ability.locked_reason ? ` • ${ability.locked_reason}` : ""}`;
      row.innerHTML = `<span class="ability-name">${ability.key}</span><span class="ability-meta">${ability.locked ? (ability.locked_reason || "locked") : (ability.cooldown > 0 ? `CD ${ability.cooldown}s` : ability.category)}</span>`;
      row.addEventListener("click", () => {
        if (ability.locked) {
          toast(ability.locked_reason || `${ability.key} is locked`);
          return;
        }
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

  function getCookie(name) {
    const prefix = `${name}=`;
    return document.cookie
      .split(";")
      .map((chunk) => chunk.trim())
      .find((chunk) => chunk.startsWith(prefix))
      ?.slice(prefix.length) || "";
  }

  function getCsrfToken() {
    return getCookie("csrftoken");
  }

  function setBuilderLastAction(text) {
    const node = byId("builder-availability");
    if (node) {
      node.textContent = text;
    }
  }

  function setBuilderStatus(text, stateKey = "idle") {
    const node = byId("builder-status");
    if (!node) return;
    node.textContent = text;
    node.dataset.state = stateKey;
  }

  function currentBuilderLaunchContext() {
    return {
      target: "builder",
      area_id: getBuilderAreaId() || String((state.map && state.map.zone) || "").trim(),
      room_id: String((state.map && state.map.player_room_id) || "").trim(),
      character_name: String((state.character && state.character.name) || "").trim(),
    };
  }

  function setBuilderOutput(value) {
    const node = byId("builder-output");
    if (!node) return;
    node.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function setBuilderAreaId(value, { overwrite = false } = {}) {
    const normalized = String(value || "").trim();
    const input = byId("builder-area-id");
    const current = input ? String(input.value || "").trim() : state.builder.areaId;
    if (!overwrite && current) {
      return current;
    }
    state.builder.areaId = normalized;
    if (input) {
      input.value = normalized;
    }
    saveUiPrefs();
    return normalized;
  }

  function getBuilderAreaId() {
    const input = byId("builder-area-id");
    const normalized = String((input && input.value) || state.builder.areaId || "").trim();
    state.builder.areaId = normalized;
    saveUiPrefs();
    return normalized;
  }

  function syncBuilderAreaFromMap() {
    const zone = String((state.map && state.map.zone) || "").trim();
    if (!zone) {
      return;
    }
    setBuilderAreaId(zone, { overwrite: false });
  }

  function renderBuilderHistory(entries) {
    const list = byId("builder-history");
    if (!list) return;
    list.innerHTML = "";
    (entries || []).forEach((entry) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "inventory-item builder-history-entry";
      const type = String(entry.type || "apply");
      const opCount = Array.isArray(entry.operation_ids)
        ? entry.operation_ids.length
        : Array.isArray((entry.diff || {}).operations)
          ? entry.diff.operations.length
          : 0;
      const timestamp = entry.timestamp
        ? new Date(Number(entry.timestamp) * 1000).toLocaleString()
        : "Unknown time";
      button.innerHTML = `<span><strong>${type}</strong><small>${timestamp}</small></span><span class="builder-history-meta">${opCount} ops</span>`;
      button.addEventListener("click", () => {
        const editor = byId("builder-diff-editor");
        const payload = entry.type === "undo" ? entry.undo_diff : entry.diff;
        if (editor && payload) {
          editor.value = JSON.stringify(payload, null, 2);
          setBuilderOutput(payload);
          setBuilderStatus(`Loaded ${type} entry into the diff editor.`, "ready");
          toast(`Loaded ${type} history entry`);
        }
      });
      list.appendChild(button);
    });

    if (!list.children.length) {
      const empty = document.createElement("div");
      empty.className = "status-tag";
      empty.textContent = "No Builder history loaded";
      list.appendChild(empty);
    }
  }

  function setBuilderEnabled(payload) {
    const enabled = Boolean(payload && (payload.is_builder || payload.builder_mode_available));
    state.builder.enabled = enabled;
    const panel = byId("builder-panel");
    const launchButton = byId("builder-launch-godot");
    if (panel) {
      panel.hidden = state.mode !== "build" || !enabled;
    }
    if (launchButton) {
      launchButton.hidden = !enabled;
    }
    if (!enabled) {
      setBuilderLastAction("Locked");
      setBuilderStatus("Builder mode unavailable", "idle");
      if (state.mode === "build") {
        setMode("play");
      }
      return;
    }
    syncBuilderAreaFromMap();
    setBuilderLastAction(payload.builder_session_id ? `Session ${payload.builder_session_id}` : "Ready");
    setBuilderStatus("Builder mode available in the browser client.", "ready");
  }

  async function builderRequest(url, options = {}) {
    const requestOptions = {
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
      ...options,
    };
    const method = String(requestOptions.method || "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") {
      requestOptions.headers["Content-Type"] = requestOptions.headers["Content-Type"] || "application/json";
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        requestOptions.headers["X-CSRFToken"] = csrfToken;
      }
    }
    const response = await window.fetch(url, requestOptions);
    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {
      payload = null;
    }
    if (!response.ok || (payload && payload.ok === false)) {
      const errorMessage = payload && payload.error ? payload.error : `HTTP ${response.status}`;
      const error = new Error(errorMessage);
      error.payload = payload;
      throw error;
    }
    return payload || { ok: response.ok };
  }

  async function builderLauncherRequest(path, options = {}) {
    const controller = new AbortController();
    const timeoutMs = options.timeoutMs || 4000;
    const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const requestOptions = {
        method: options.method || "GET",
        headers: {
          Accept: "application/json",
          ...(options.headers || {}),
        },
        signal: controller.signal,
        mode: "cors",
      };
      if (options.body !== undefined) {
        requestOptions.headers["Content-Type"] = "application/json";
        requestOptions.body = JSON.stringify(options.body);
      }
      const response = await window.fetch(`http://127.0.0.1:7777${path}`, requestOptions);
      let payload = null;
      try {
        payload = await response.json();
      } catch (_) {
        payload = null;
      }
      if (!response.ok || (payload && payload.ok === false)) {
        const error = new Error((payload && payload.error) || `HTTP ${response.status}`);
        error.payload = payload;
        throw error;
      }
      return payload || { ok: response.ok };
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("Launcher did not respond.");
      }
      if (error instanceof TypeError) {
        throw new Error("Local Builder Launcher is not running. Start tools/builder_launcher/launcher.py and try again.");
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  }

  async function checkBuilderLauncher() {
    return builderLauncherRequest("/health", { method: "GET", timeoutMs: 2500 });
  }

  async function launchGodotBuilder(payload = {}) {
    return builderLauncherRequest("/launch-builder", {
      method: "POST",
      body: payload,
      timeoutMs: 4000,
    });
  }

  function parseBuilderDiffEditor() {
    const editor = byId("builder-diff-editor");
    const raw = String((editor && editor.value) || "").trim();
    const parsed = raw ? JSON.parse(raw) : {};
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Diff payload must be a JSON object.");
    }
    const areaId = String(parsed.area_id || getBuilderAreaId() || "").trim();
    if (!areaId) {
      throw new Error("Area ID is required before running Builder actions.");
    }
    return {
      ...parsed,
      area_id: areaId,
      operations: Array.isArray(parsed.operations) ? parsed.operations : [],
    };
  }

  function setBuilderBusy(isBusy, label) {
    state.builder.busy = isBusy;
    document.querySelectorAll("#builder-panel button, #builder-panel input, #builder-panel textarea").forEach((node) => {
      node.disabled = isBusy;
    });
    if (label) {
      setBuilderStatus(label, isBusy ? "idle" : "ready");
    }
  }

  async function openGodotBuilder() {
    if (!ensureBuildMode("Builder launch")) {
      return;
    }
    if (state.builder.launcherBusy) {
      return;
    }
    state.builder.launcherBusy = true;
    const launchButton = byId("builder-launch-godot");
    if (launchButton) {
      launchButton.disabled = true;
      launchButton.textContent = "Launching...";
    }
    setBuilderStatus("Checking local launcher...", "idle");
    try {
      await checkBuilderLauncher();
      const response = await launchGodotBuilder(currentBuilderLaunchContext());
      setBuilderStatus("Launching Godot Builder...", "ready");
      setBuilderLastAction("Launched");
      setBuilderOutput(response);
      toast("Launching Godot Builder...");
    } catch (error) {
      setBuilderStatus(error.message, "error");
      toast(error.message);
    } finally {
      state.builder.launcherBusy = false;
      if (launchButton) {
        launchButton.disabled = false;
        launchButton.textContent = "Launch Builder";
      }
    }
  }

  async function exportBuilderMap() {
    if (!ensureBuildMode("Builder export")) {
      return;
    }
    const areaId = getBuilderAreaId();
    if (!areaId) {
      toast("Enter an area id first.");
      return;
    }
    setBuilderBusy(true, `Exporting ${areaId}...`);
    try {
      const response = await builderRequest(`/api/builder/map/export/${encodeURIComponent(areaId)}/`);
      const exported = (response.data && response.data.map) || response.map || null;
      state.builder.lastExport = exported;
      setBuilderOutput(exported || {});
      setBuilderStatus(`Exported ${areaId} with ${((exported && exported.rooms) || []).length} rooms.`, "ready");
      setBuilderLastAction("Exported");
      const editor = byId("builder-diff-editor");
      if (editor && !String(editor.value || "").trim()) {
        editor.value = JSON.stringify({ area_id: areaId, operations: [] }, null, 2);
      }
      toast(`Loaded Builder export for ${areaId}`);
    } catch (error) {
      setBuilderStatus(`Export failed: ${error.message}`, "error");
      setBuilderOutput(error.payload || error.message);
      toast(`Builder export failed: ${error.message}`);
    } finally {
      setBuilderBusy(false);
    }
  }

  async function loadBuilderHistory() {
    if (!ensureBuildMode("Builder history")) {
      return;
    }
    const areaId = getBuilderAreaId();
    if (!areaId) {
      toast("Enter an area id first.");
      return;
    }
    setBuilderBusy(true, `Loading history for ${areaId}...`);
    try {
      const response = await builderRequest(`/api/builder/map/history/?area_id=${encodeURIComponent(areaId)}&limit=8`);
      const history = Array.isArray(response.history)
        ? response.history
        : Array.isArray(response.data && response.data.history)
          ? response.data.history
          : [];
      state.builder.history = history;
      renderBuilderHistory(history);
      setBuilderStatus(`Loaded ${history.length} history entries for ${areaId}.`, "ready");
      setBuilderLastAction("History");
    } catch (error) {
      setBuilderStatus(`History failed: ${error.message}`, "error");
      toast(`Builder history failed: ${error.message}`);
    } finally {
      setBuilderBusy(false);
    }
  }

  async function runBuilderDiff(preview) {
    if (!ensureBuildMode(preview ? "Builder preview" : "Builder apply")) {
      return;
    }
    let diff = null;
    try {
      diff = parseBuilderDiffEditor();
    } catch (error) {
      setBuilderStatus(error.message, "error");
      toast(error.message);
      return;
    }
    setBuilderBusy(true, preview ? "Previewing diff..." : "Applying diff...");
    try {
      const response = await builderRequest("/api/builder/map/diff/", {
        method: "POST",
        body: JSON.stringify({ diff, preview }),
      });
      const result = (response.data && response.data.result) || response.result || response;
      setBuilderOutput(result);
      if (!preview) {
        state.builder.lastDiff = diff;
        state.builder.lastUndoDiff = result.undo_diff || null;
        await loadBuilderHistory();
        await exportBuilderMap();
      }
      setBuilderStatus(preview ? "Diff preview completed." : "Diff applied.", "ready");
      setBuilderLastAction(preview ? "Preview" : "Applied");
      toast(preview ? "Builder preview ready" : "Builder diff applied");
    } catch (error) {
      setBuilderStatus(`${preview ? "Preview" : "Apply"} failed: ${error.message}`, "error");
      setBuilderOutput(error.payload || error.message);
      toast(`Builder ${preview ? "preview" : "apply"} failed: ${error.message}`);
    } finally {
      setBuilderBusy(false);
    }
  }

  async function runBuilderUndo() {
    if (!ensureBuildMode("Builder undo")) {
      return;
    }
    if (!state.builder.lastUndoDiff) {
      toast("No undo diff is cached yet.");
      return;
    }
    setBuilderBusy(true, "Applying undo...");
    try {
      const response = await builderRequest("/api/builder/map/undo/", {
        method: "POST",
        body: JSON.stringify({ undo_diff: state.builder.lastUndoDiff }),
      });
      const result = response.result || (response.data && response.data.result) || response;
      setBuilderOutput(result);
      setBuilderStatus("Undo applied.", "ready");
      setBuilderLastAction("Undo");
      await loadBuilderHistory();
      await exportBuilderMap();
      toast("Builder undo applied");
    } catch (error) {
      setBuilderStatus(`Undo failed: ${error.message}`, "error");
      setBuilderOutput(error.payload || error.message);
      toast(`Builder undo failed: ${error.message}`);
    } finally {
      setBuilderBusy(false);
    }
  }

  async function runBuilderRedo() {
    if (!ensureBuildMode("Builder redo")) {
      return;
    }
    if (!state.builder.lastDiff) {
      toast("No applied diff is cached yet.");
      return;
    }
    setBuilderBusy(true, "Applying redo...");
    try {
      const response = await builderRequest("/api/builder/map/redo/", {
        method: "POST",
        body: JSON.stringify({ diff: state.builder.lastDiff }),
      });
      const result = response.result || (response.data && response.data.result) || response;
      setBuilderOutput(result);
      setBuilderStatus("Redo applied.", "ready");
      setBuilderLastAction("Redo");
      await loadBuilderHistory();
      await exportBuilderMap();
      toast("Builder redo applied");
    } catch (error) {
      setBuilderStatus(`Redo failed: ${error.message}`, "error");
      setBuilderOutput(error.payload || error.message);
      toast(`Builder redo failed: ${error.message}`);
    } finally {
      setBuilderBusy(false);
    }
  }

  function updateCharacterPanel(data) {
    if (!data) return;
    const professionNode = byId("char-profession");
    const rankNode = byId("char-rank");
    if (professionNode) {
      professionNode.textContent = data.profession
        ? String(data.profession).replace(/_/g, " ")
        : "Unknown";
    }
    if (rankNode) {
      rankNode.textContent = `Rank ${data.profession_rank || "Unknown"}`;
    }
    setBuilderEnabled(data);
  }

  function updateSubsystemUI(data) {
    if (!data) return;
    state.subsystem = data;
    const bar = byId("subsystem-bar");
    if (!bar) return;

    let value = 0;
    let max = 100;
    let label = data.type || data.label || "Unknown";

    if (data.fire !== undefined) {
      value = data.fire;
      max = data.max_fire || 100;
      label = "Inner Fire";
    }

    if (data.focus !== undefined) {
      value = data.focus;
      max = data.max_focus || 100;
      label = "Focus";
    }

    if (data.transfer_pool !== undefined) {
      value = data.transfer_pool;
      max = data.max_pool || 100;
      label = "Transfer";
    }

    if (data.attunement !== undefined) {
      value = data.attunement;
      max = data.max_attunement || 100;
      label = "Attunement";
    }

    bar.textContent = `${label}: ${value}/${max}`;
  }

  function updateCharacter(payload) {
    if (!payload) return;
    state.character = payload;
    rememberCharacter(payload.name || "");
    state.inventoryLookup = new Map();
    byId("character-name").textContent = payload.name || "Adventurer";
    updateCharacterPanel(payload);
    const crest = document.querySelector(".crest-banner");
    if (crest) {
      const identity = payload.profession || payload.guild;
      crest.textContent = identity
        ? `${String(identity).replace(/_/g, " ").toUpperCase()} INTERFACE`
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
    if (isPlayerRoom(room)) {
      const profession = state.character && state.character.profession;
      const professionColors = {
        thief: "#66ccff",
        empath: "#7ee0a1",
        barbarian: "#d97a43",
        moon_mage: "#a3a0ff",
      };
      return professionColors[profession] || "#df564a";
    }
    if (room.map_color) return room.map_color;
    if (room.has_guild_entrance) return "#f0d45f";
    if (room.has_poi) return "#69b8ff";
    if (room.type === "guild_entrance") return "#f0d45f";
    if (room.type === "poi") return "#69b8ff";
    if (room.type === "guild") return "#bc7eff";
    if (room.type === "shop") return "#69b8ff";
    return "#5f8f57";
  }

  function mapEdges() {
    return state.map.edges && state.map.edges.length ? state.map.edges : (state.map.exits || []);
  }

  function isCompactMap() {
    const rooms = state.map.rooms || [];
    return rooms.length > 0 && rooms.length <= 16;
  }

  function mapBounds() {
    const rooms = state.map.rooms || [];
    if (!rooms.length) {
      return { minX: 0, maxX: 0, minY: 0, maxY: 0, width: 1, height: 1 };
    }
    const xs = rooms.map((room) => Number(room.x) || 0);
    const ys = rooms.map((room) => Number(room.y) || 0);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    return {
      minX,
      maxX,
      minY,
      maxY,
      width: Math.max(1, maxX - minX),
      height: Math.max(1, maxY - minY),
    };
  }

  function mapRoomRadius(room, compactMap) {
    if (isPlayerRoom(room)) {
      return compactMap ? 9 : 6;
    }
    if (room.id === state.hoveredRoomId) {
      return compactMap ? 6 : 4;
    }
    return compactMap ? 5 : 3;
  }

  function renderedMapBounds(canvas, scale) {
    const rooms = state.map.rooms || [];
    if (!canvas || !rooms.length) {
      return { minX: 0, maxX: 1, minY: 0, maxY: 1, width: 1, height: 1 };
    }

    const compactMap = isCompactMap();
    const ctx = canvas.getContext("2d");
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (const room of rooms) {
      const roomX = (Number(room.x) || 0) * scale;
      const roomY = (Number(room.y) || 0) * scale;
      const radius = mapRoomRadius(room, compactMap);
      const outline = isPlayerRoom(room) ? 4 : 0;

      minX = Math.min(minX, roomX - radius - outline);
      maxX = Math.max(maxX, roomX + radius + outline);
      minY = Math.min(minY, roomY - radius - outline);
      maxY = Math.max(maxY, roomY + radius + outline);

      if (!compactMap) {
        continue;
      }

      const fontSize = isPlayerRoom(room) ? 12 : 11;
      ctx.save();
  ctx.font = isPlayerRoom(room) ? "600 12px Georgia" : "11px Georgia";
      const textWidth = ctx.measureText(room.name || "").width;
      ctx.restore();

      const textBottom = roomY - (radius + 8);
      const textTop = textBottom - fontSize;
      minX = Math.min(minX, roomX - textWidth / 2);
      maxX = Math.max(maxX, roomX + textWidth / 2);
      minY = Math.min(minY, textTop);
      maxY = Math.max(maxY, textBottom);
    }

    return {
      minX,
      maxX,
      minY,
      maxY,
      width: Math.max(1, maxX - minX),
      height: Math.max(1, maxY - minY),
    };
  }

  function resizeMapCanvas() {
    const canvas = byId("map-canvas");
    if (!canvas) return false;
    const rect = canvas.getBoundingClientRect();
    const nextWidth = Math.max(320, Math.round(rect.width || 320));
    const nextHeight = Math.max(320, Math.round(rect.height || 360));
    let resized = false;
    if (canvas.width !== nextWidth) {
      canvas.width = nextWidth;
      resized = true;
    }
    if (canvas.height !== nextHeight) {
      canvas.height = nextHeight;
      resized = true;
    }
    return resized;
  }

  function scheduleMapRefit(centerCurrent = false) {
    state.mapRefitRequestId += 1;
    const requestId = state.mapRefitRequestId;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        if (requestId !== state.mapRefitRequestId) {
          return;
        }
        resizeMapCanvas();
        if (centerCurrent) {
          centerOnCurrentRoom();
        } else {
          fitMapToCanvas();
        }
        renderMap();
      });
    });
  }

  function fitMapToCanvas() {
    const canvas = byId("map-canvas");
    if (!canvas || !state.map || !(state.map.rooms || []).length) return;
    const padding = 24;
    const usableWidth = Math.max(40, canvas.width - padding * 2);
    const usableHeight = Math.max(40, canvas.height - padding * 2);
    const rawBounds = mapBounds();
    let nextScale = Math.max(0.12, Math.min(usableWidth / rawBounds.width, usableHeight / rawBounds.height));

    for (let attempt = 0; attempt < 4; attempt += 1) {
      const bounds = renderedMapBounds(canvas, nextScale);
      const scaleFactor = Math.min(usableWidth / bounds.width, usableHeight / bounds.height);
      if (!Number.isFinite(scaleFactor) || scaleFactor <= 0) {
        break;
      }
      const adjustedScale = Math.max(0.12, nextScale * scaleFactor);
      if (Math.abs(adjustedScale - nextScale) < 0.01) {
        nextScale = adjustedScale;
        break;
      }
      nextScale = adjustedScale;
    }

    state.mapScale = nextScale;
    const bounds = renderedMapBounds(canvas, state.mapScale);
    state.mapOffset.x = padding + (usableWidth - bounds.width) / 2 - bounds.minX;
    state.mapOffset.y = padding + (usableHeight - bounds.height) / 2 - bounds.minY;
  }

  function getCurrentRoomId() {
    return state.map.player_room_id || ((state.map.rooms || []).find((room) => room.current) || {}).id || null;
  }

  function centerOnCurrentRoom() {
    const canvas = byId("map-canvas");
    const room = roomById(getCurrentRoomId());
    if (!canvas || !room) return;
    state.mapOffset.x = canvas.width / 2 - room.x * state.mapScale;
    state.mapOffset.y = canvas.height / 2 - room.y * state.mapScale;
  }

  function worldPosition(room, canvas) {
    return {
      x: room.x * state.mapScale + state.mapOffset.x,
      y: room.y * state.mapScale + state.mapOffset.y,
    };
  }

  function renderMap() {
    const canvas = byId("map-canvas");
    if (!canvas) return;
    resizeMapCanvas();
    fitMapToCanvas();
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    state.roomPositions.clear();

    if (!state.map || !Array.isArray(state.map.rooms)) {
      return;
    }

    state.map.rooms.forEach((room) => {
      state.roomPositions.set(room.id, worldPosition(room, canvas));
    });

    const compactMap = isCompactMap();

    mapEdges().forEach((edge) => {
      const from = state.roomPositions.get(edge.from);
      const to = state.roomPositions.get(edge.to);
      if (!from || !to) return;
      ctx.strokeStyle = compactMap ? "rgba(220, 188, 120, 0.82)" : "rgba(195, 164, 104, 0.6)";
      ctx.lineWidth = compactMap ? 2.4 : 1.5;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    });

    state.map.rooms.forEach((room) => {
      const pos = state.roomPositions.get(room.id);
      const radius = mapRoomRadius(room, compactMap);
      const playerRoom = isPlayerRoom(room);
      if (room.id === state.hoveredRoomId) {
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 5, 0, Math.PI * 2);
        ctx.fill();
      }
      if (playerRoom) {
        ctx.strokeStyle = "rgba(255, 240, 200, 0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = roomColor(room);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fill();

      if (compactMap) {
        ctx.fillStyle = playerRoom ? "rgba(255, 245, 220, 0.96)" : "rgba(230, 219, 194, 0.88)";
        ctx.font = playerRoom ? "600 12px Georgia" : "11px Georgia";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(room.name, pos.x, pos.y - (radius + 8));
      }
    });

    const currentRoom = roomById(state.map.player_room_id);
    if (currentRoom) {
      byId("map-room-name").textContent = currentRoom.name;
      byId("room-context").textContent = currentRoom.name;
    }
    updateSceneImage(currentRoom);
    byId("map-meta-rooms").textContent = `Rooms ${state.map.rooms.length}`;
    byId("map-meta-exits").textContent = `Exits ${mapEdges().length}`;
    byId("map-meta-zoom").textContent = state.map.zone ? `Zone ${String(state.map.zone).replace(/_/g, " ")}` : "Zone local";
    renderExitStrip();
    updateCompassFromMap();
  }

  function renderExitStrip() {
    const strip = byId("exit-strip");
    if (!strip) return;
    strip.innerHTML = "";
    mapEdges()
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
      mapEdges()
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
    console.log("MAP DATA:", payload);
    const nextRoomId = payload.player_room_id;
    state.map = {
      rooms: payload.rooms || [],
      edges: payload.edges || payload.exits || [],
      exits: payload.exits || payload.edges || [],
      player_room_id: nextRoomId,
      zone: payload.zone || null,
    };
    state.mapAutoFit = true;
    state.isDragging = false;
    syncBuilderAreaFromMap();
    scheduleMapRefit(false);
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
    byId("map-panel")?.classList.toggle("is-highlighted", viewName === "map");
    byId("inventory-panel")?.classList.toggle("is-highlighted", viewName === "inventory");
    updateInputHint();
    saveUiPrefs();
  }

  function appendChatLine(text, cssClass = "out") {
    const chatWindow = byId("chatwindow");
    if (!chatWindow) return;
    const row = document.createElement("div");
    row.className = `chat-line ${cssClass}`;
    row.textContent = text;
    chatWindow.appendChild(row);
    scrollFeedToBottom(chatWindow);
  }

  function findPath(startId, targetId, edges) {
    const queue = [[startId]];
    const visited = new Set();

    while (queue.length) {
      const path = queue.shift();
      const roomId = path[path.length - 1];

      if (roomId === targetId) {
        return path;
      }
      if (visited.has(roomId)) {
        continue;
      }
      visited.add(roomId);

      edges
        .filter((edge) => edge.from === roomId)
        .forEach((edge) => {
          if (!visited.has(edge.to)) {
            queue.push([...path, edge.to]);
          }
        });
    }

    return null;
  }

  function pathToDirections(path, edges) {
    const directions = [];
    for (let index = 0; index < path.length - 1; index += 1) {
      const step = edges.find((edge) => edge.from === path[index] && edge.to === path[index + 1]);
      if (step && step.dir) {
        directions.push(step.dir);
      }
    }
    return directions;
  }

  function stopAutoWalk(reason = "Auto-walk stopped") {
    const wasWalking = state.isWalking;
    state.isWalking = false;
    state.walkToken += 1;
    if (wasWalking) {
      console.log(reason);
    }
  }

  async function walkDirections(directions) {
    if (!state.autoWalkEnabled || !directions || !directions.length) {
      return;
    }

    const token = state.walkToken + 1;
    state.walkToken = token;
    state.isWalking = true;

    for (const dir of directions) {
      if (!state.isWalking || token !== state.walkToken) {
        break;
      }
      sendCommand(dir);
      await new Promise((resolve) => window.setTimeout(resolve, 320));
    }

    if (token === state.walkToken) {
      state.isWalking = false;
    }
  }

  function handleMapClick(roomId) {
    stopAutoWalk();
    const start = getCurrentRoomId();
    if (!start || roomId === start) {
      return;
    }

    const path = findPath(start, roomId, mapEdges());
    if (!path) {
      console.log("No path found");
      toast("No route found.");
      return;
    }

    const directions = pathToDirections(path, mapEdges());
    console.log("Walking to:", roomId);
    console.log("PATH:", path);
    console.log("DIRS:", directions);
    if (!directions.length) {
      return;
    }
    const targetRoom = roomById(roomId);
    toast(`Walking to ${targetRoom ? targetRoom.name : roomId}`);
    walkDirections(directions);
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
    if (!canvas) return;

    canvas.addEventListener("mousedown", (event) => {
      state.suppressMapClick = false;
    });

    window.addEventListener("mousemove", (event) => {
      void event;
    });

    window.addEventListener("mouseup", () => {
      state.isDragging = false;
      canvas.classList.remove("is-dragging");
    });

    canvas.addEventListener("mousemove", (event) => {
      const rect = canvas.getBoundingClientRect();
      const room = roomAtCanvasPosition(
        ((event.clientX - rect.left) / rect.width) * canvas.width,
        ((event.clientY - rect.top) / rect.height) * canvas.height
      );
      canvas.style.cursor = room ? "pointer" : "default";
      updateTooltip(event.clientX, event.clientY, room);
    });

    canvas.addEventListener("mouseleave", () => {
      canvas.style.cursor = "default";
      updateTooltip(0, 0, null);
    });

    canvas.addEventListener("click", (event) => {
      if (state.suppressMapClick) {
        state.suppressMapClick = false;
        return;
      }
      const rect = canvas.getBoundingClientRect();
      const room = roomAtCanvasPosition(
        ((event.clientX - rect.left) / rect.width) * canvas.width,
        ((event.clientY - rect.top) / rect.height) * canvas.height
      );
      if (!room) return;
      handleMapClick(room.id);
    });

    window.addEventListener("resize", () => {
      scheduleMapRefit(false);
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
      const rawValue = input.value || "";
      if (!rawValue.trim()) return;
      const normalized = normalizeInputForView(rawValue);
      if (!normalized) return;
      rememberCommand(rawValue);
      if (state.activeView === "chat") {
        appendChatLine(`> ${rawValue.trim()}`, "inp");
      }
      sendCommand(normalized);
      input.value = "";
      input.focus();
    };

    sendButton.addEventListener("click", (event) => {
      event.preventDefault();
      submitInput();
    });

    input.addEventListener("keydown", (event) => {
      stopAutoWalk();
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
    Evennia.emitter.off("map");
    Evennia.emitter.off("character");
    Evennia.emitter.off("combat");
    Evennia.emitter.off("chat");
    Evennia.emitter.off("subsystem");
    Evennia.emitter.off("logged_in");
    Evennia.emitter.off("connection_open");
    Evennia.emitter.off("connection_close");
    Evennia.emitter.off("default");

    Evennia.emitter.on("text", handleText);
    Evennia.emitter.on("prompt", handlePrompt);
    Evennia.emitter.on("map", (args, kwargs) => {
      const payload = (Array.isArray(args) && args.length ? args[0] : null) || kwargs || {};
      appendDebug("MAP", payload);
      updateDebugSummary({ cmd: "map", args: [payload], kwargs: kwargs || {} });
      updateMap(payload);
      return true;
    });
    Evennia.emitter.on("character", (args, kwargs) => {
      const payload = (Array.isArray(args) && args.length ? args[0] : null) || kwargs || {};
      appendDebug("CHARACTER", payload);
      updateDebugSummary({ cmd: "character", args: [payload], kwargs: kwargs || {} });
      updateCharacterPanel(payload);
      updateCharacter(payload);
      return true;
    });
    Evennia.emitter.on("combat", (args, kwargs) => {
      const payload = (Array.isArray(args) && args.length ? args[0] : null) || kwargs || {};
      appendDebug("COMBAT", payload);
      handleCombat(payload);
      return true;
    });
    Evennia.emitter.on("chat", (args, kwargs) => {
      const payload = (Array.isArray(args) && args.length ? args[0] : null) || kwargs || {};
      const text = String(payload.text || "");
      appendDebug("CHAT", payload);
      appendChatLine(text);
      toast(text || "New chat message");
      playTone("chat");
      return true;
    });
    Evennia.emitter.on("subsystem", (args, data) => {
      const payload = (Array.isArray(args) && args.length ? args[0] : null) || data || {};
      console.log("SUBSYSTEM:", payload);
      appendDebug("SUBSYSTEM", payload);
      updateDebugSummary({ cmd: "subsystem", args: [payload], kwargs: {} });
      updateSubsystemUI(payload);
      return true;
    });
    Evennia.emitter.on("logged_in", () => {
      cancelReconnect();
      updateConnection(true);
      byId("footer-status").textContent = "Logged in";
      setSessionStatus("Connected");
      playTone("ready");
      requestInitialRefresh();
    });
    Evennia.emitter.on("connection_open", () => {
      cancelReconnect();
      updateConnection(true);
      byId("footer-status").textContent = "Connection open";
      setSessionStatus("Connected");
      requestInitialRefresh();
    });
    Evennia.emitter.on("connection_close", () => {
      updateConnection(false);
      byId("footer-status").textContent = "Connection closed";
      setSessionStatus("Disconnected");
      toast("Connection closed. Reconnect scheduled.");
      scheduleReconnect();
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
    playTone("combat");
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
        toast(String((message.args[0] || {}).text || "New chat message"));
        playTone("chat");
        return true;
      default:
        return false;
    }
  }

  function init() {
    loadHotbar();
    loadUiPrefs();
    renderMode();
    resetLeftRailScroll();
    bootstrapEvennia();
    applyRailOrder();
    resetLeftRailScroll();
    renderHotbar();
    renderRecentCharacters();
    updateAudioToggleLabel();
    setupMapInteractions();
    bindRailPanels();
    bindInputControls();
    setSessionStatus("Ready");
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

    document.querySelectorAll("#topbar-tabs .chrome-tab[data-view]").forEach((button) => {
      button.addEventListener("click", () => switchView(button.dataset.view));
    });
    byId("mode-exit-button")?.addEventListener("click", () => {
      window.location.href = "/";
    });
    byId("mode-return-play")?.addEventListener("click", () => {
      setMode("play");
    });
    byId("mode-build-exit")?.addEventListener("click", () => {
      window.location.href = "/";
    });
    byId("reconnect-button")?.addEventListener("click", () => {
      cancelReconnect();
      setSessionStatus("Manual reconnect");
      if (window.Evennia && typeof Evennia.connect === "function") {
        Evennia.connect();
      }
    });
    byId("audio-toggle")?.addEventListener("click", () => {
      state.audioEnabled = !state.audioEnabled;
      updateAudioToggleLabel();
      saveUiPrefs();
      toast(`Audio ${state.audioEnabled ? "enabled" : "disabled"}`);
    });
    byId("map-fit-toggle")?.addEventListener("click", () => {
      state.mapAutoFit = true;
      scheduleMapRefit(false);
      toast("Map fit to viewport.");
    });
    byId("map-center-toggle")?.addEventListener("click", () => {
      state.mapAutoFit = true;
      scheduleMapRefit(false);
      toast("Map kept fit to the full viewport.");
    });
    byId("map-fullscreen-toggle")?.addEventListener("click", () => {
      const panel = byId("map-panel");
      panel?.classList.toggle("fullscreen");
      const button = byId("map-fullscreen-toggle");
      if (button && panel) {
        button.textContent = panel.classList.contains("fullscreen") ? "×" : "⛶";
      }
      state.mapAutoFit = true;
      scheduleMapRefit(false);
    });
    byId("builder-area-id")?.addEventListener("change", () => {
      getBuilderAreaId();
    });
    byId("builder-use-zone")?.addEventListener("click", () => {
      const zone = String((state.map && state.map.zone) || "").trim();
      if (!zone) {
        toast("No live zone id is available yet.");
        return;
      }
      setBuilderAreaId(zone, { overwrite: true });
      setBuilderStatus(`Builder area set from live zone: ${zone}`, "ready");
      toast(`Using zone ${zone}`);
    });
    byId("builder-export")?.addEventListener("click", () => {
      void exportBuilderMap();
    });
    byId("builder-history-refresh")?.addEventListener("click", () => {
      void loadBuilderHistory();
    });
    byId("builder-preview")?.addEventListener("click", () => {
      void runBuilderDiff(true);
    });
    byId("builder-apply")?.addEventListener("click", () => {
      void runBuilderDiff(false);
    });
    byId("builder-undo")?.addEventListener("click", () => {
      void runBuilderUndo();
    });
    byId("builder-redo")?.addEventListener("click", () => {
      void runBuilderRedo();
    });
    byId("builder-launch-godot")?.addEventListener("click", () => {
      if (!state.builder.enabled) {
        return;
      }
      setMode("build");
    });
    switchView(state.activeView);
    ensureRailBrandPresent();
    resetLeftRailScroll();

    if (state.builder.areaId) {
      setBuilderAreaId(state.builder.areaId, { overwrite: true });
    }
    renderBuilderHistory(state.builder.history);
    setBuilderOutput("Awaiting Builder action.");

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
      if (input && state.mode === "play") {
        input.focus();
      }
      if (state.mode !== "landing") {
        requestInitialRefresh();
      }
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
