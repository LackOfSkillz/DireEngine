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
    sceneRotation: {
      timer: null,
      index: 0,
      key: "",
    },
  };

  const HOTBAR_STORAGE_KEY = "dragonsire.hotbar";
  const UI_PREFS_STORAGE_KEY = "dragonsire.browser.ui";
  const BUILDER_LAST_ROOM_STORAGE_KEY = "dragonsire.builder.lastRoomId";
  const BUILDER_LAST_ZONE_STORAGE_KEY = "dragonsire.builder.lastZoneId";
  const BUILDER_ROOM_LIST_SCROLL_STORAGE_KEY = "dragonsire.builder.roomListScrollTop";
  const BUILDER_ZONE_CAMERA_STORAGE_KEY = "dragonsire.builder.zoneCamera";
  const BUILDER_ZONE_MIN_ZOOM = 0.01;
  const BUILDER_ZONE_MAX_ZOOM = 2.5;
  const BUILDER_UNASSIGNED_ZONE_VALUE = "__unassigned__";
  const USE_REACT_FLOW_BUILDER = true;
  const DIR_ALIAS = {
    n: "north",
    s: "south",
    e: "east",
    w: "west",
    u: "up",
    d: "down",
    ne: "northeast",
    nw: "northwest",
    se: "southeast",
    sw: "southwest",
  };
  const DIR_VECTOR = {
    north: { x: 0, y: -1 },
    south: { x: 0, y: 1 },
    east: { x: 1, y: 0 },
    west: { x: -1, y: 0 },
    northeast: { x: 1, y: -1 },
    northwest: { x: -1, y: -1 },
    southeast: { x: 1, y: 1 },
    southwest: { x: -1, y: 1 },
    up: { x: 0, y: 0 },
    down: { x: 0, y: 0 },
  };
  const NON_SPATIAL_EXIT_DIRECTIONS = new Set([
    "gate",
    "arch",
    "bridge",
    "stair",
    "path",
    "walk",
    "guild",
    "out",
    "in",
    "ramp",
    "pier",
    "ferry",
    "dock",
    "enter",
    "leave",
    "entry",
    "veranda",
    "yard",
  ]);
  const MAP_BEARING_DIRECTIONS = new Set(Object.keys(DIR_VECTOR));
  const DIRECTIONS = [
    "north",
    "south",
    "east",
    "west",
    "up",
    "down",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "gate",
    "arch",
    "bridge",
    "stair",
    "path",
    "walk",
    "guild",
    "out",
    "in",
    "ramp",
    "pier",
    "ferry",
    "dock",
    "enter",
    "leave",
    "entry",
    "veranda",
    "yard",
  ];
  const BUILDER_SEASON_STATES = ["spring", "summer", "autumn", "winter"];
  const DEFAULT_EXIT_TYPECLASS = "typeclasses.exits.Exit";
  const DEFAULT_SLOW_EXIT_TYPECLASS = "typeclasses.exits_slow.SlowDireExit";
  const SLOW_EXIT_TYPECLASS = "evennia.contrib.grid.slow_exit.slow_exit.SlowExit";
  const SLOW_EXIT_SPEEDS = ["stroll", "walk", "run", "sprint"];
  const SCENE_IMAGE_ROTATION_MS = 120000;
  const DESKTOP_SHELL_FIT_WIDTH = 1460;
  const DESKTOP_SHELL_FIT_HEIGHT = 940;
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
  const builderState = {
    currentRoomId: null,
    selectedRoom: null,
    hoveredRoomId: null,
    currentZoneId: null,
    zones: [],
    rooms: [],
    currentRoom: null,
    zone: null,
    roomMap: {},
    roomLookup: new Map(),
    zoneGraph: null,
    zoneSurface: null,
    zoneMapBounds: null,
    zoneMapNeedsFit: true,
    zoneForceFitOnce: false,
    zoneZoomInitialized: false,
    zoneCanvasSize: { width: 0, height: 0 },
    zonePan: { x: 0, y: 0 },
    zoneZoom: 1,
    zoneDrag: null,
    reactFlowViewportRequest: { type: "fit", token: 0 },
    isDirty: false,
    connectMode: false,
    connectFrom: null,
    connectFromRoomId: null,
    previewTimer: null,
  };
  let hasInitialized = false;

  function isBuilderPage() {
    return Boolean(byId("builder-layout"));
  }

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

  function builderRoomKey(value) {
    return String(value ?? "").trim();
  }

  function normalizeBuilderYamlExits(exits) {
    if (Array.isArray(exits)) {
      return exits.reduce((accumulator, exit, index) => {
        const normalized = normalizeBuilderExit(exit, index);
        if (normalized.direction && normalized.target_id) {
          accumulator[normalized.direction] = {
            target: builderRoomKey(normalized.target_id),
            typeclass: normalized.typeclass,
            speed: normalized.speed,
            travel_time: normalized.travel_time,
          };
        }
        return accumulator;
      }, {});
    }
    return Object.entries(exits || {}).reduce((accumulator, [direction, targetValue]) => {
      const normalized = normalizeBuilderExit({ direction, ...(typeof targetValue === "object" && targetValue !== null ? targetValue : { target: targetValue }) });
      if (normalized.direction && normalized.target_id) {
        accumulator[normalized.direction] = {
          target: normalized.target_id,
          typeclass: normalized.typeclass,
          speed: normalized.speed,
          travel_time: normalized.travel_time,
        };
      }
      return accumulator;
    }, {});
  }

  function builderRoomExitsArray(room) {
    return Object.entries(room?.exits || room?.exitMap || {}).map(([direction, spec], index) => (
      normalizeBuilderExit({ direction, ...(typeof spec === "object" && spec !== null ? spec : { target: spec }) }, index)
    ));
  }

  function isSlowExitTypeclass(typeclass) {
    const normalized = String(typeclass || "").trim();
    return normalized === DEFAULT_SLOW_EXIT_TYPECLASS || normalized === SLOW_EXIT_TYPECLASS;
  }

  function normalizeExitTypeclass(typeclass) {
    const normalized = String(typeclass || "").trim();
    if (isSlowExitTypeclass(normalized)) {
      return DEFAULT_SLOW_EXIT_TYPECLASS;
    }
    return normalized || DEFAULT_EXIT_TYPECLASS;
  }

  function exitTravelPreview(exit) {
    const normalized = normalizeBuilderExit(exit || {});
    if (!isSlowExitTypeclass(normalized.typeclass)) {
      return "Instant travel";
    }
    if (normalized.travel_time > 0) {
      return `Travel time: ~${normalized.travel_time} seconds`;
    }
    const speed = normalized.speed || "walk";
    const bySpeed = { stroll: 6, walk: 4, run: 2, sprint: 1 };
    return `Travel time: ~${bySpeed[speed] || 4} seconds (${speed})`;
  }

  function normalizeBuilderStringMap(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      return {};
    }
    return Object.entries(value).reduce((accumulator, [key, text]) => {
      const normalizedKey = String(key || "").trim().toLowerCase();
      if (normalizedKey) {
        accumulator[normalizedKey] = String(text || "");
      }
      return accumulator;
    }, {});
  }

  function normalizeBuilderStringList(value) {
    if (!Array.isArray(value)) {
      return [];
    }
    return value
      .map((item) => String(item || "").trim().toLowerCase())
      .filter(Boolean)
      .filter((item, index, array) => array.indexOf(item) === index);
  }

  function normalizeBuilderAmbient(value) {
    const raw = value && typeof value === "object" && !Array.isArray(value) ? value : {};
    const rate = Number.parseInt(raw.rate ?? 0, 10);
    const messages = Array.isArray(raw.messages)
      ? raw.messages.map((message) => String(message || "")).filter((message) => message.trim())
      : [];
    return {
      rate: Number.isFinite(rate) && rate > 0 ? rate : 0,
      messages,
    };
  }

  function builderStateLabel(state) {
    return String(state || "")
      .split(/[_\s-]+/)
      .filter(Boolean)
      .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
      .join(" ");
  }

  function splitBuilderStatefulDescs(statefulDescs = {}) {
    const normalized = normalizeBuilderStringMap(statefulDescs);
    const seasonal = {};
    const custom = [];
    BUILDER_SEASON_STATES.forEach((state) => {
      seasonal[state] = normalized[state] || "";
    });
    Object.entries(normalized).forEach(([state, text]) => {
      if (!BUILDER_SEASON_STATES.includes(state)) {
        custom.push({ state, text: String(text || "") });
      }
    });
    custom.sort((left, right) => left.state.localeCompare(right.state));
    return { seasonal, custom };
  }

  function normalizeBuilderMapCoordinate(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  }

  function normalizeBuilderYamlRoom(room, index = 0, zoneId = "") {
    const roomId = builderRoomKey(room?.id || `room_${index + 1}`);
    const map = {
      x: normalizeBuilderMapCoordinate(room?.map?.x ?? room?.map_x ?? room?.x),
      y: normalizeBuilderMapCoordinate(room?.map?.y ?? room?.map_y ?? room?.y),
      layer: Number(room?.map?.layer ?? room?.map_layer ?? 0) || 0,
    };
    const statefulDescs = normalizeBuilderStringMap(room?.stateful_descs);
    const details = normalizeBuilderStringMap(room?.details);
    const roomStates = normalizeBuilderStringList(room?.room_states);
    const ambient = normalizeBuilderAmbient(room?.ambient);
    const exits = normalizeBuilderYamlExits(room?.exits || room?.exitMap || {});
    const exitMap = Object.entries(exits).reduce((accumulator, [direction, spec]) => {
      const target = builderRoomKey(spec?.target || spec?.target_id || "");
      if (target) {
        accumulator[direction] = target;
      }
      return accumulator;
    }, {});
    return {
      ...room,
      id: roomId,
      name: room?.name || roomId,
      typeclass: String(room?.typeclass || "typeclasses.rooms_extended.ExtendedDireRoom").trim() || "typeclasses.rooms_extended.ExtendedDireRoom",
      desc: room?.desc || "",
      short_desc: room?.short_desc ?? room?.shortDesc ?? null,
      stateful_descs: statefulDescs,
      details,
      room_states: roomStates,
      ambient,
      zone_id: builderRoomKey(room?.zone_id || zoneId),
      map,
      map_x: map.x,
      map_y: map.y,
      map_layer: map.layer,
      exits,
      exitMap,
      environment: String(room?.environment || "city").trim().toLowerCase() || "city",
    };
  }

  function normalizeBuilderZonePayload(payload, fallbackZoneId = "") {
    const zoneId = normalizeBuilderZoneId(payload?.zone_id || fallbackZoneId);
    const rooms = (payload?.rooms || []).map((room, index) => normalizeBuilderYamlRoom(room, index, zoneId));
    return {
      schema_version: payload?.schema_version || "v1",
      zone_id: zoneId,
      name: payload?.name || zoneId || "Untitled Zone",
      placements: payload?.placements || { npcs: [], items: [] },
      rooms,
    };
  }

  function rebuildBuilderRoomIndexes() {
    const roomMap = {};
    const roomLookup = new Map();
    const rooms = Array.isArray(builderState.zone?.rooms) ? builderState.zone.rooms : [];
    rooms.forEach((room, index) => {
      const normalizedRoom = normalizeBuilderYamlRoom(room, index, builderState.currentZoneId || builderState.zone?.zone_id || "");
      rooms[index] = normalizedRoom;
      roomMap[normalizedRoom.id] = normalizedRoom;
      roomLookup.set(normalizedRoom.id, normalizedRoom);
    });
    builderState.roomMap = roomMap;
    builderState.roomLookup = roomLookup;
    builderState.rooms = rooms;
    if (builderState.zone) {
      builderState.zone.rooms = rooms;
    }
    builderState.zoneGraph = builderState.zone;
  }

  function setBuilderDirty(isDirty = true) {
    builderState.isDirty = Boolean(isDirty);
    const saveButton = byId("save-zone");
    if (saveButton) {
      saveButton.textContent = builderState.isDirty ? "Save Zone*" : "Save Zone";
    }
  }

  function replaceBuilderZone(payload, options = {}) {
    const normalized = normalizeBuilderZonePayload(payload, options.fallbackZoneId || builderState.currentZoneId || "");
    builderState.currentZoneId = normalized.zone_id;
    builderState.zone = normalized;
    rebuildBuilderRoomIndexes();
    builderState.zoneZoomInitialized = false;
    builderState.zoneMapNeedsFit = true;
  }

  function updateBuilderZoneRoom(roomId, overrides = {}) {
    const normalizedRoomId = builderRoomKey(roomId);
    const room = builderState.roomMap[normalizedRoomId];
    if (!room || !builderState.zone) {
      throw new Error("Room not found.");
    }
    const exitMap = Object.prototype.hasOwnProperty.call(overrides, "exits") || Object.prototype.hasOwnProperty.call(overrides, "exitMap")
      ? normalizeBuilderYamlExits(overrides.exits ?? overrides.exitMap ?? room.exitMap)
      : room.exitMap;
    const map = {
      x: Number(overrides.map?.x ?? overrides.map_x ?? room.map?.x ?? room.map_x ?? 0) || 0,
      y: Number(overrides.map?.y ?? overrides.map_y ?? room.map?.y ?? room.map_y ?? 0) || 0,
      layer: Number(overrides.map?.layer ?? overrides.map_layer ?? room.map?.layer ?? room.map_layer ?? 0) || 0,
    };
    const nextRoom = normalizeBuilderYamlRoom(
      {
        ...room,
        ...overrides,
        id: normalizedRoomId,
        exits: exitMap,
        exitMap,
        map,
      },
      0,
      builderState.currentZoneId || builderState.zone?.zone_id || ""
    );
    builderState.zone.rooms = builderState.zone.rooms.map((candidate) => (
      builderRoomKey(candidate.id) === normalizedRoomId ? nextRoom : candidate
    ));
    rebuildBuilderRoomIndexes();
    if (builderRoomKey(builderState.currentRoomId) === normalizedRoomId) {
      builderState.currentRoom = nextRoom;
      builderState.selectedRoom = nextRoom.id;
    }
    setBuilderDirty(true);
    return nextRoom;
  }

  function applyBuilderDraftToState(options = {}) {
    if (!builderState.currentRoomId) {
      return null;
    }
    const draft = currentBuilderDraft();
    const updatedRoom = updateBuilderZoneRoom(draft.id, {
      name: draft.name,
      short_desc: draft.shortDesc || null,
      desc: draft.desc,
      stateful_descs: draft.stateful_descs,
      details: draft.details,
      room_states: draft.room_states,
      ambient: draft.ambient,
      environment: draft.environment,
      zone_id: draft.zone_id,
      exits: draft.exits,
      map_x: draft.map_x,
      map_y: draft.map_y,
      map_layer: draft.map_layer,
    });
    renderBuilderRoomList();
    renderBuilderPreview(updatedRoom, { flash: Boolean(options.flash) });
    renderZoneMap();
    return updatedRoom;
  }

  function uniqueBuilderRoomId(baseName) {
    const normalizedBase = String(baseName || "room")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "room";
    let candidate = normalizedBase;
    let suffix = 2;
    while (builderState.roomMap[candidate]) {
      candidate = `${normalizedBase}-${suffix}`;
      suffix += 1;
    }
    return candidate;
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

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function roomNameById(roomId) {
    const normalizedRoomId = builderRoomKey(roomId);
    const zoneRoom = builderState.roomMap[normalizedRoomId];
    if (zoneRoom) {
      return zoneRoom.name || `Room ${normalizedRoomId}`;
    }
    const match = builderState.rooms.find((room) => builderRoomKey(room.id) === normalizedRoomId);
    return match ? (match.name || match.db_key || `Room ${normalizedRoomId}`) : `Room ${normalizedRoomId}`;
  }

  function zoneCameraStorageKey(zoneId) {
    return `${BUILDER_ZONE_CAMERA_STORAGE_KEY}.${zoneId || "default"}`;
  }

  function saveZoneCamera() {
    if (!builderState.currentZoneId) {
      return;
    }
    window.localStorage.setItem(
      zoneCameraStorageKey(builderState.currentZoneId),
      JSON.stringify({ pan: builderState.zonePan, zoom: builderState.zoneZoom })
    );
  }

  function loadZoneCamera(zoneId) {
    if (!zoneId) {
      return null;
    }
    try {
      const raw = window.localStorage.getItem(zoneCameraStorageKey(zoneId));
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") {
        return null;
      }
      return {
        pan: {
          x: Number(parsed.pan?.x || 0),
          y: Number(parsed.pan?.y || 0),
        },
        zoom: Math.min(Math.max(Number(parsed.zoom || 1), 0.08), 2.5),
      };
    } catch (error) {
      return null;
    }
  }

  function setBuilderPageStatus(message) {
    const status = byId("builder-status");
    if (status) {
      status.textContent = message;
    }
  }

  function updateBuilderConnectToggle() {
    const button = byId("builder-connect-toggle");
    if (!button) {
      return;
    }
    button.classList.toggle("is-active", Boolean(builderState.connectMode));
    button.textContent = builderState.connectMode ? "Connecting..." : "Connect Rooms";
    button.setAttribute("aria-pressed", builderState.connectMode ? "true" : "false");
  }

  function clearBuilderConnectMode(options = {}) {
    builderState.connectMode = false;
    builderState.connectFrom = null;
    builderState.connectFromRoomId = null;
    if (options.clearHover) {
      builderState.hoveredRoomId = null;
    }
    updateBuilderConnectToggle();
    renderZoneMap();
  }

  function beginBuilderConnectMode() {
    builderState.connectMode = true;
    builderState.connectFrom = null;
    builderState.connectFromRoomId = null;
    updateBuilderConnectToggle();
    setBuilderPageStatus("Connect mode: click a source room.");
    renderZoneMap();
  }

  function normalizeBuilderZoneId(value) {
    const normalized = String(value || "").trim().toLowerCase();
    return normalized === BUILDER_UNASSIGNED_ZONE_VALUE ? "" : normalized;
  }

  function builderZoneSelectValue(zoneId) {
    return normalizeBuilderZoneId(zoneId) || BUILDER_UNASSIGNED_ZONE_VALUE;
  }

  function currentBuilderZoneMeta() {
    const currentZoneId = normalizeBuilderZoneId(builderState.currentZoneId);
    return builderState.zones.find((zone) => normalizeBuilderZoneId(zone.id) === currentZoneId) || null;
  }

  function currentBuilderZoneLabel() {
    const zone = currentBuilderZoneMeta();
    if (zone) {
      return zone.name || zone.id || "Unassigned";
    }
    return builderState.currentZoneId ? builderState.currentZoneId : "Unassigned";
  }

  function persistBuilderZoneSelection(zoneId) {
    window.localStorage.setItem(BUILDER_LAST_ZONE_STORAGE_KEY, builderZoneSelectValue(zoneId));
  }

  function builderAssignableZones() {
    return builderState.zones.filter((zone) => normalizeBuilderZoneId(zone.id));
  }

  function hasActiveBuilderZone() {
    return Boolean(normalizeBuilderZoneId(builderState.currentZoneId));
  }

  function requireActiveBuilderZone() {
    if (hasActiveBuilderZone()) {
      return true;
    }
    toast("No zone selected");
    return false;
  }

  function builderVisibleRooms() {
    const currentZoneId = normalizeBuilderZoneId(builderState.currentZoneId);
    const graphZoneId = normalizeBuilderZoneId(builderState.zone?.zone_id || "");
    if (!builderState.zone || graphZoneId !== currentZoneId) {
      return [];
    }
    return Array.isArray(builderState.zone.rooms) ? builderState.zone.rooms : [];
  }

  function defaultAssignableZoneId(fallbackZoneId = "") {
    const normalizedFallback = normalizeBuilderZoneId(fallbackZoneId);
    if (normalizedFallback) {
      return normalizedFallback;
    }
    return normalizeBuilderZoneId((builderAssignableZones()[0] || {}).id || "");
  }

  function builderZoneOptions(selectedZoneId) {
    return builderState.zones.map((zone) => {
      const zoneId = normalizeBuilderZoneId(zone.id);
      const selected = zoneId === normalizeBuilderZoneId(selectedZoneId) ? " selected" : "";
      const roomCount = Array.isArray(zone.rooms) ? zone.rooms.length : 0;
      const suffix = zoneId ? ` (${roomCount})` : ` (${roomCount} unassigned)`;
      const label = escapeHtml(`${zone.name || zoneId || "Unassigned"}${suffix}`);
      return `<option value="${escapeHtml(builderZoneSelectValue(zoneId))}"${selected}>${label}</option>`;
    }).join("");
  }

  function syncBuilderZoneMenus() {
    const currentZoneId = normalizeBuilderZoneId(builderState.currentZoneId);
      const roomZoneId = builderState.currentRoomId
        ? normalizeBuilderZoneId(byId("room-zone")?.value || builderState.currentRoom?.zone_id || currentZoneId)
      : defaultAssignableZoneId(currentZoneId);
    const dialogZoneId = normalizeBuilderZoneId(byId("builder-room-zone-input")?.value || defaultAssignableZoneId(currentZoneId));
    const assignableZoneOptions = builderAssignableZones().map((zone) => {
      const zoneId = normalizeBuilderZoneId(zone.id);
      const selected = zoneId === normalizeBuilderZoneId(roomZoneId) ? " selected" : "";
      const roomCount = Array.isArray(zone.rooms) ? zone.rooms.length : 0;
      const label = escapeHtml(`${zone.name || zoneId} (${roomCount})`);
      return `<option value="${escapeHtml(builderZoneSelectValue(zoneId))}"${selected}>${label}</option>`;
    }).join("");
    const createAssignableZoneOptions = builderAssignableZones().map((zone) => {
      const zoneId = normalizeBuilderZoneId(zone.id);
      const selected = zoneId === normalizeBuilderZoneId(dialogZoneId) ? " selected" : "";
      const roomCount = Array.isArray(zone.rooms) ? zone.rooms.length : 0;
      const label = escapeHtml(`${zone.name || zoneId} (${roomCount})`);
      return `<option value="${escapeHtml(builderZoneSelectValue(zoneId))}"${selected}>${label}</option>`;
    }).join("");

    ["builder-zone-select", "builder-zone-select-top"].forEach((controlId) => {
      const pageZone = byId(controlId);
      if (!pageZone) {
        return;
      }
      pageZone.innerHTML = builderZoneOptions(currentZoneId);
      pageZone.disabled = !builderState.zones.length;
      if (pageZone.options.length) {
        pageZone.value = builderZoneSelectValue(currentZoneId);
      }
    });

    const roomZone = byId("room-zone");
    if (roomZone) {
      roomZone.innerHTML = assignableZoneOptions;
      roomZone.disabled = !builderAssignableZones().length;
      if (roomZone.options.length) {
        roomZone.value = builderZoneSelectValue(defaultAssignableZoneId(roomZoneId));
      }
    }

    const createRoomZone = byId("builder-room-zone-input");
    if (createRoomZone) {
      createRoomZone.innerHTML = createAssignableZoneOptions;
      createRoomZone.disabled = !builderAssignableZones().length;
      if (createRoomZone.options.length) {
        createRoomZone.value = builderZoneSelectValue(defaultAssignableZoneId(dialogZoneId || currentZoneId));
      }
    }
  }

  function openBuilderDialog(id) {
    const dialog = byId(id);
    if (dialog && typeof dialog.showModal === "function") {
      dialog.showModal();
    }
  }

  function closeBuilderDialog(id) {
    const dialog = byId(id);
    if (dialog?.open) {
      dialog.close();
    }
  }

  function clearBuilderEditor(statusMessage, previewMessage) {
    builderState.currentRoomId = null;
    builderState.currentRoom = null;
    window.localStorage.removeItem(BUILDER_LAST_ROOM_STORAGE_KEY);
    if (byId("room-name")) {
      byId("room-name").value = "";
    }
    if (byId("room-short-desc")) {
      byId("room-short-desc").value = "";
    }
    if (byId("room-desc")) {
      byId("room-desc").value = "";
    }
    BUILDER_SEASON_STATES.forEach((state) => {
      const field = byId(`room-desc-${state}`);
      if (field) {
        field.value = "";
      }
    });
    if (byId("room-active-states")) {
      byId("room-active-states").value = "";
    }
    if (byId("room-ambient-rate")) {
      byId("room-ambient-rate").value = "0";
    }
    if (byId("room-ambient-messages")) {
      byId("room-ambient-messages").value = "";
    }
    if (byId("room-environment")) {
      byId("room-environment").value = "city";
    }
    if (byId("room-map-x")) {
      byId("room-map-x").value = "0";
    }
    if (byId("room-map-y")) {
      byId("room-map-y").value = "0";
    }
    if (byId("room-map-layer")) {
      byId("room-map-layer").value = "0";
    }
    syncBuilderZoneMenus();
    renderBuilderExitList([]);
    renderBuilderStatefulDescList({});
    renderBuilderDetailList({});
    syncBuilderPreviewStateOptions({ stateful_descs: {}, room_states: [] }, "");
    renderBuilderPreview({
      name: "No room selected",
      desc: previewMessage || "Choose a room from the list to inspect and edit it.",
      stateful_descs: {},
      details: {},
      room_states: [],
      ambient: { rate: 0, messages: [] },
      environment: "city",
      exits: [],
    });
    renderBuilderRoomList();
    renderZoneMap();
    setBuilderPageStatus(statusMessage || "Select a room to begin.");
  }

  function builderCreateRoomPosition() {
    const canvas = zoneMapCanvas();
    const zoom = Number(builderState.zoneZoom || 1);
    if (!canvas || !Number.isFinite(zoom) || zoom <= 0) {
      return { x: 0, y: 0 };
    }
    return {
      x: Math.round((canvas.width / 2 - builderState.zonePan.x) / zoom),
      y: Math.round((canvas.height / 2 - builderState.zonePan.y) / zoom),
    };
  }

  function showSavingState() {
    const saveButton = byId("save-room");
    if (!saveButton) {
      return;
    }
    saveButton.textContent = "Saving...";
    saveButton.disabled = true;
  }

  function showSavedState() {
    const saveButton = byId("save-room");
    if (!saveButton) {
      return;
    }
    saveButton.textContent = "Saved";
    window.setTimeout(() => {
      saveButton.textContent = "Save";
      saveButton.disabled = false;
    }, 1200);
  }

  function resetSaveState() {
    const saveButton = byId("save-room");
    if (!saveButton) {
      return;
    }
    saveButton.textContent = "Save";
    saveButton.disabled = false;
  }

  function currentBuilderDraft() {
    const shortDescValue = byId("room-short-desc")?.value || "";
    return {
      id: builderState.currentRoomId,
      name: byId("room-name")?.value || "",
      shortDesc: shortDescValue,
      desc: byId("room-desc")?.value || "",
      stateful_descs: collectBuilderStatefulDescs(),
      details: collectBuilderDetails(),
      room_states: collectBuilderRoomStates(),
      ambient: {
        rate: Number.parseInt(byId("room-ambient-rate")?.value || "0", 10) || 0,
        messages: collectBuilderAmbientMessages(),
      },
      environment: byId("room-environment")?.value || "city",
      exits: collectBuilderExits(),
      zone_id: normalizeBuilderZoneId(byId("room-zone")?.value || builderState.currentRoom?.zone_id || builderState.currentZoneId || ""),
      map_x: Number.parseInt(byId("room-map-x")?.value || `${builderState.currentRoom?.map?.x ?? builderState.currentRoom?.map_x ?? builderState.currentRoom?.x ?? 0}`, 10) || 0,
      map_y: Number.parseInt(byId("room-map-y")?.value || `${builderState.currentRoom?.map?.y ?? builderState.currentRoom?.map_y ?? builderState.currentRoom?.y ?? 0}`, 10) || 0,
      map_layer: Number.parseInt(byId("room-map-layer")?.value || `${builderState.currentRoom?.map?.layer ?? builderState.currentRoom?.map_layer ?? 0}`, 10) || 0,
    };
  }

  function renderBuilderStatefulDescList(statefulDescs = {}) {
    const split = splitBuilderStatefulDescs(statefulDescs);
    BUILDER_SEASON_STATES.forEach((state) => {
      const field = byId(`room-desc-${state}`);
      if (field) {
        field.value = split.seasonal[state] || "";
      }
    });
    const list = byId("builder-custom-stateful-desc-list");
    if (!list) {
      return;
    }
    list.innerHTML = split.custom.map(({ state, text }, index) => `
      <div class="builder-kv-row builder-state-row" data-index="${index}">
        <input class="builder-custom-state-key" type="text" value="${escapeHtml(state)}" placeholder="State name" autocomplete="off">
        <textarea class="builder-custom-state-text builder-compact-textarea" placeholder="Description">${escapeHtml(text)}</textarea>
        <button type="button" class="builder-kv-remove">Delete</button>
      </div>
    `).join("");
  }

  function renderBuilderDetailList(details = {}) {
    const list = byId("builder-detail-list");
    if (!list) {
      return;
    }
    const entries = Object.entries(normalizeBuilderStringMap(details)).sort(([left], [right]) => left.localeCompare(right));
    list.innerHTML = entries.map(([key, text], index) => `
      <div class="builder-kv-row builder-detail-row" data-index="${index}">
        <input class="builder-detail-key" type="text" value="${escapeHtml(key)}" placeholder="detail key" autocomplete="off">
        <textarea class="builder-detail-text builder-compact-textarea" placeholder="Detail description">${escapeHtml(text)}</textarea>
        <button type="button" class="builder-kv-remove">Delete</button>
      </div>
    `).join("");
  }

  function collectBuilderStatefulDescs() {
    const statefulDescs = {};
    BUILDER_SEASON_STATES.forEach((state) => {
      const value = String(byId(`room-desc-${state}`)?.value || "");
      if (value.trim()) {
        statefulDescs[state] = value;
      }
    });
    document.querySelectorAll("#builder-custom-stateful-desc-list .builder-state-row").forEach((row) => {
      const key = String(row.querySelector(".builder-custom-state-key")?.value || "").trim().toLowerCase();
      const text = String(row.querySelector(".builder-custom-state-text")?.value || "");
      if (key) {
        statefulDescs[key] = text;
      }
    });
    return statefulDescs;
  }

  function collectBuilderDetails() {
    const details = {};
    document.querySelectorAll("#builder-detail-list .builder-detail-row").forEach((row) => {
      const key = String(row.querySelector(".builder-detail-key")?.value || "").trim().toLowerCase();
      const text = String(row.querySelector(".builder-detail-text")?.value || "");
      if (key) {
        details[key] = text;
      }
    });
    return details;
  }

  function collectBuilderRoomStates() {
    return String(byId("room-active-states")?.value || "")
      .split(/[\n,]/)
      .map((state) => state.trim().toLowerCase())
      .filter(Boolean)
      .filter((state, index, array) => array.indexOf(state) === index);
  }

  function collectBuilderAmbientMessages() {
    return String(byId("room-ambient-messages")?.value || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  function syncBuilderPreviewStateOptions(room, preferredState = "") {
    const select = byId("builder-preview-state");
    if (!select) {
      return;
    }
    const normalizedRoom = normalizeBuilderYamlRoom(room || {}, 0, builderState.currentZoneId || "");
    const optionStates = Array.from(new Set([
      ...Object.keys(normalizedRoom.stateful_descs || {}),
      ...(normalizedRoom.room_states || []),
    ])).sort((left, right) => left.localeCompare(right));
    const preferred = String(preferredState || select.value || "").trim().toLowerCase();
    select.innerHTML = ['<option value="">Auto</option>', '<option value="default">Default</option>']
      .concat(optionStates.map((state) => `<option value="${escapeHtml(state)}">${escapeHtml(builderStateLabel(state))}</option>`))
      .join("");
    select.value = optionStates.includes(preferred) || preferred === "default" ? preferred : "";
  }

  function resolveBuilderPreviewDescription(room, selectedState = "") {
    const normalizedRoom = normalizeBuilderYamlRoom(room || {}, 0, builderState.currentZoneId || "");
    const statefulDescs = normalizedRoom.stateful_descs || {};
    const requestedState = String(selectedState || "").trim().toLowerCase();
    if (requestedState === "default") {
      return { state: "default", source: "default", desc: normalizedRoom.desc || "" };
    }
    if (requestedState && statefulDescs[requestedState]) {
      return { state: requestedState, source: requestedState, desc: statefulDescs[requestedState] };
    }
    const roomStates = normalizeBuilderStringList(normalizedRoom.room_states || []);
    const customStates = roomStates.filter((state) => !BUILDER_SEASON_STATES.includes(state)).sort((left, right) => left.localeCompare(right));
    for (const state of customStates) {
      if (statefulDescs[state]) {
        return { state, source: state, desc: statefulDescs[state] };
      }
    }
    for (const state of roomStates) {
      if (BUILDER_SEASON_STATES.includes(state) && statefulDescs[state]) {
        return { state, source: state, desc: statefulDescs[state] };
      }
    }
    return { state: "default", source: "default", desc: normalizedRoom.desc || "" };
  }

  function normalizeExitDirection(dir) {
    return String(dir || "").trim().toLowerCase();
  }

  function canonicalExitDirection(direction) {
    const value = normalizeExitDirection(direction);
    if (!value) {
      return "";
    }
    return DIR_ALIAS[value] || value;
  }

  function reverseDirection(direction) {
    switch (canonicalExitDirection(direction)) {
      case "north": return "south";
      case "south": return "north";
      case "east": return "west";
      case "west": return "east";
      case "northeast": return "southwest";
      case "northwest": return "southeast";
      case "southeast": return "northwest";
      case "southwest": return "northeast";
      case "up": return "down";
      case "down": return "up";
      default: return "";
    }
  }

  function builderRoomById(roomId) {
    return builderState.roomMap[builderRoomKey(roomId)] || null;
  }

  function getDirection(fromRoom, toRoom) {
    const dx = Number(toRoom?.map_x ?? toRoom?.x ?? 0) - Number(fromRoom?.map_x ?? fromRoom?.x ?? 0);
    const dy = Number(toRoom?.map_y ?? toRoom?.y ?? 0) - Number(fromRoom?.map_y ?? fromRoom?.y ?? 0);
    if (!dx && !dy) {
      return "";
    }
    if (Math.abs(dx) > Math.abs(dy)) {
      return dx > 0 ? "east" : "west";
    }
    return dy > 0 ? "south" : "north";
  }

  function mergeBuilderExit(exits, direction, targetId) {
    const normalizedDirection = canonicalExitDirection(direction);
    const normalizedTargetId = builderRoomKey(targetId);
    const nextExits = Array.isArray(exits)
      ? exits.map((exit, index) => normalizeBuilderExit(exit, index))
      : [];
    const existingIndex = nextExits.findIndex((exit) => canonicalExitDirection(exit.direction || "") === normalizedDirection);
    const nextExit = {
      direction: normalizedDirection,
      target_id: normalizedTargetId,
      target_name: roomNameById(normalizedTargetId),
      typeclass: existingIndex >= 0 ? nextExits[existingIndex].typeclass : DEFAULT_EXIT_TYPECLASS,
      speed: existingIndex >= 0 ? nextExits[existingIndex].speed : "",
      travel_time: existingIndex >= 0 ? nextExits[existingIndex].travel_time : 0,
    };
    if (existingIndex >= 0) {
      nextExits[existingIndex] = nextExit;
      return nextExits;
    }
    nextExits.push(nextExit);
    return nextExits;
  }

  function classifyBuilderExit(exit) {
    const rawDirection = normalizeExitDirection(exit?.direction || "");
    const direction = canonicalExitDirection(rawDirection);
    const targetId = builderRoomKey(exit?.target_id || exit?.targetId || "");
    const hasTarget = Boolean(targetId);
    const isSpecial = Boolean(direction) && !MAP_BEARING_DIRECTIONS.has(direction);
    const isRecognized = Boolean(direction);
    const isVertical = direction === "up" || direction === "down";
    const isDiagonal = ["northeast", "northwest", "southeast", "southwest"].includes(direction);
    const isSpatial = Boolean(direction) && MAP_BEARING_DIRECTIONS.has(direction) && hasTarget;
    return {
      rawDirection,
      direction,
      target_id: targetId,
      target_name: exit?.target_name || (targetId ? roomNameById(targetId) : ""),
      typeclass: normalizeExitTypeclass(exit?.typeclass),
      speed: String(exit?.speed || "").trim().toLowerCase(),
      travel_time: Math.max(0, Number.parseInt(exit?.travel_time ?? 0, 10) || 0),
      isRecognized,
      isSpecial,
      isVertical,
      isDiagonal,
      isSpatial,
      dropped: !isRecognized,
    };
  }

  function splitBuilderExits(exits = []) {
    const normalized = exits.map((exit) => classifyBuilderExit(exit));
    return {
      normalized,
      spatial: normalized.filter((exit) => exit.isSpatial),
      special: normalized.filter((exit) => exit.isSpecial),
      vertical: normalized.filter((exit) => exit.isVertical),
      dropped: normalized.filter((exit) => exit.dropped),
    };
  }

  function normalizeBuilderExit(exit, index = 0) {
    const fallbackDirection = DIRECTIONS[index % DIRECTIONS.length] || "north";
    const direction = canonicalExitDirection(exit?.direction || fallbackDirection);
    const targetId = builderRoomKey(exit?.target_id || exit?.targetId || exit?.target || "");
    return {
      id: builderRoomKey(exit?.id || ""),
      direction: direction || fallbackDirection,
      target_id: targetId,
      target_name: exit?.target_name || (targetId ? roomNameById(targetId) : ""),
      typeclass: normalizeExitTypeclass(exit?.typeclass),
      speed: String(exit?.speed || "").trim().toLowerCase(),
      travel_time: Math.max(0, Number.parseInt(exit?.travel_time ?? 0, 10) || 0),
    };
  }

  function createExitRow(exit, index) {
    const normalized = normalizeBuilderExit(exit, index);
    const exitTypeValue = isSlowExitTypeclass(normalized.typeclass) ? "slow" : "normal";
    const roomOptions = ['<option value="">Select room</option>']
      .concat(builderVisibleRooms().map((room) => (
        `<option value="${escapeHtml(room.id)}"${builderRoomKey(room.id) === builderRoomKey(normalized.target_id || "") ? " selected" : ""}>${escapeHtml(room.name || room.db_key || `Room ${room.id}`)}</option>`
      )))
      .join("");
    const speedOptions = ['<option value="">Default speed</option>']
      .concat(SLOW_EXIT_SPEEDS.map((speed) => `<option value="${speed}"${normalized.speed === speed ? " selected" : ""}>${escapeHtml(builderStateLabel(speed))}</option>`))
      .join("");
    return `
      <div class="builder-exit-row" data-index="${index}">
        <input class="builder-exit-direction" aria-label="Exit direction" list="builder-exit-direction-options" value="${escapeHtml(normalized.direction)}" autocomplete="off">
        <select class="builder-exit-target" aria-label="Exit target room">
          ${roomOptions}
        </select>
        <select class="builder-exit-type" aria-label="Exit type">
          <option value="normal"${exitTypeValue === "normal" ? " selected" : ""}>Normal</option>
          <option value="slow"${exitTypeValue === "slow" ? " selected" : ""}>Slow Exit</option>
        </select>
        <select class="builder-exit-speed" aria-label="Exit movement speed">
          ${speedOptions}
        </select>
        <input class="builder-exit-travel-time" aria-label="Exit travel time" type="number" min="0" step="1" value="${escapeHtml(String(normalized.travel_time || 0))}">
        <div class="builder-exit-preview">${escapeHtml(exitTravelPreview(normalized))}</div>
        <button type="button" class="builder-exit-remove">Delete</button>
      </div>
    `;
  }

  function renderBuilderExitList(exits = []) {
    const list = byId("exit-list");
    if (!list) {
      return;
    }
    const rows = (Array.isArray(exits) && exits.length ? exits : []).map((exit, index) => createExitRow(exit, index));
    list.innerHTML = rows.join("");
  }

  function collectBuilderExits() {
    return Array.from(document.querySelectorAll("#exit-list .builder-exit-row"))
      .map((row) => ({
        direction: canonicalExitDirection(row.querySelector(".builder-exit-direction")?.value || ""),
        target_id: builderRoomKey(row.querySelector(".builder-exit-target")?.value || ""),
        typeclass: row.querySelector(".builder-exit-type")?.value === "slow" ? DEFAULT_SLOW_EXIT_TYPECLASS : DEFAULT_EXIT_TYPECLASS,
        speed: String(row.querySelector(".builder-exit-speed")?.value || "").trim().toLowerCase(),
        travel_time: Math.max(0, Number.parseInt(row.querySelector(".builder-exit-travel-time")?.value || "0", 10) || 0),
      }))
      .filter((exit) => exit.direction || exit.target_id);
  }

  function validateBuilderExits(exits) {
    const zoneRooms = builderVisibleRooms();
    const seenDirections = new Set();
    for (const exit of exits) {
      const direction = canonicalExitDirection(exit.direction || "");
      const targetId = builderRoomKey(exit.target_id || "");
      if (!direction) {
        return `Invalid exit direction: ${direction || "blank"}.`;
      }
      if (seenDirections.has(direction)) {
        return `Duplicate exit direction: ${direction}.`;
      }
      if (!targetId || !zoneRooms.some((room) => builderRoomKey(room.id) === targetId)) {
        return `Exit target for ${direction} must be an existing room.`;
      }
      if (Number.parseInt(String(exit.travel_time ?? 0), 10) < 0) {
        return `Exit travel time for ${direction} cannot be negative.`;
      }
      seenDirections.add(direction);
    }
    return "";
  }

  function scrollSelectedBuilderRoomIntoView() {
    const selected = document.querySelector("#room-list .room-item.active");
    if (selected && typeof selected.scrollIntoView === "function") {
      selected.scrollIntoView({ block: "nearest" });
    }
  }

  function deriveBuilderShortDesc(data) {
    const explicit = String(data.shortDesc || "").trim();
    if (explicit) {
      return explicit;
    }
    const description = String(data.desc || "").trim();
    if (!description) {
      return String(data.name || "").trim();
    }
    const firstLine = description.split(/\r?\n/).find((line) => line.trim());
    const firstSentence = String(firstLine || description).split(/[.!?]/)[0].trim();
    return firstSentence || String(data.name || "").trim();
  }

  function triggerBuilderPreviewFlash() {
    const previewPanel = byId("room-preview");
    if (!previewPanel) {
      return;
    }
    previewPanel.classList.remove("preview-updated");
    void previewPanel.offsetWidth;
    previewPanel.classList.add("preview-updated");
  }

  function scheduleBuilderPreviewUpdate() {
    if (builderState.previewTimer) {
      window.clearTimeout(builderState.previewTimer);
    }
    builderState.previewTimer = window.setTimeout(() => {
      builderState.previewTimer = null;
      const updatedRoom = applyBuilderDraftToState({ flash: true });
      renderBuilderPreview(updatedRoom || currentBuilderDraft(), { flash: true });
    }, 150);
  }

  function highlightSelectedBuilderRoom() {
    document.querySelectorAll("#room-list .room-item").forEach((node) => {
      const roomId = builderRoomKey(node.dataset.id || "");
      node.classList.toggle("active", roomId === builderRoomKey(builderState.currentRoomId));
    });
    scrollSelectedBuilderRoomIntoView();
  }

  function renderBuilderRoomList() {
    const list = byId("room-list");
    if (!list) {
      return;
    }
    const rooms = builderVisibleRooms();
    if (!rooms.length) {
      list.innerHTML = '<div class="builder-room-empty">No rooms in this zone yet.</div>';
      return;
    }
    list.innerHTML = rooms
      .map(
        (room) => `<div class="room-item${builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId) ? " active" : ""}" data-id="${escapeHtml(room.id)}">${escapeHtml(room.name || room.db_key || `Room ${room.id}`)}</div>`
      )
      .join("");
  }

  function renderBuilderPreview(data, options = {}) {
    const normalized = normalizeBuilderYamlRoom(data || {}, 0, builderState.currentZoneId || "");
    const previewName = byId("builder-preview-room-name");
    const previewDesc = byId("builder-preview-room-desc");
    const previewState = byId("builder-preview-room-state");
    const previewDetails = byId("builder-preview-room-details");
    const previewExits = byId("builder-preview-room-exits");
    const previewContext = byId("room-context");
    const currentLabel = byId("builder-current-room");
    syncBuilderPreviewStateOptions(normalized, options.previewState);
    const selectedPreviewState = String(byId("builder-preview-state")?.value || "").trim().toLowerCase();
    const preview = resolveBuilderPreviewDescription(normalized, selectedPreviewState);
    const shortDesc = deriveBuilderShortDesc(normalized);
    const exits = builderRoomExitsArray(normalized);
    const exitGroups = splitBuilderExits(exits);
    const spatialLabels = exitGroups.spatial.map((exit) => exit.direction);
    const specialLabels = exitGroups.special.map((exit) => exit.direction);
    const slowExitLabels = exits.filter((exit) => isSlowExitTypeclass(exit.typeclass)).map((exit) => `${exit.direction}: ${exitTravelPreview(exit).replace('Travel time: ', '')}`);
    const detailKeys = Object.keys(normalized.details || {}).sort((left, right) => left.localeCompare(right));
    const ambientMessages = normalized.ambient?.messages || [];
    if (previewName) {
      previewName.textContent = shortDesc || normalized.name || "Untitled room";
    }
    if (previewDesc) {
      previewDesc.innerHTML = escapeHtml(preview.desc || "").replace(/\n/g, "<br>");
    }
    if (previewState) {
      const roomStates = normalized.room_states?.length ? normalized.room_states.join(", ") : "none";
      previewState.textContent = `State source: ${builderStateLabel(preview.source)} • Active: ${roomStates}`;
    }
    if (previewDetails) {
      const detailSummary = detailKeys.length ? detailKeys.join(", ") : "none";
      const ambientSummary = ambientMessages.length
        ? `${ambientMessages.length} messages @ ${normalized.ambient?.rate || 0}s`
        : "no ambient loop";
      previewDetails.textContent = `Details: ${detailSummary} • Ambient: ${ambientSummary}`;
    }
    if (previewExits) {
      const lines = [`Exits: ${spatialLabels.length ? spatialLabels.join(", ") : "none"}`];
      if (specialLabels.length) {
        lines.push(`Special: ${specialLabels.join(", ")}`);
      }
      if (slowExitLabels.length) {
        lines.push(`Slow: ${slowExitLabels.join("; ")}`);
      }
      if (state.debugEnabled) {
        lines.push(`Spatial exits: ${spatialLabels.length ? spatialLabels.join(", ") : "none"}`);
        lines.push(`Special exits: ${specialLabels.length ? specialLabels.join(", ") : "none"}`);
      }
      previewExits.innerHTML = lines.map((line) => escapeHtml(line)).join("<br>");
    }
    if (previewContext) {
      previewContext.textContent = `${String(normalized.environment || "city").toUpperCase()} preview`;
    }
    if (currentLabel) {
      currentLabel.textContent = normalized.name || "Untitled room";
    }
    if (options.flash) {
      triggerBuilderPreviewFlash();
    }
  }

  function builderMapPanel() {
    return byId("builder-map-panel");
  }

  function zoneMapCanvas() {
    return byId("builder-map-canvas");
  }

  function builderMapTooltip() {
    return byId("builder-map-tooltip");
  }

  function builderReactFlowRoot() {
    return byId("builder-reactflow-root");
  }

  function builderUsesReactFlow() {
    return Boolean(
      USE_REACT_FLOW_BUILDER
      && isBuilderPage()
      && builderReactFlowRoot()
      && window.DragonsireBuilderReactFlow?.mountBuilderReactFlow
    );
  }

  function setBuilderMapRenderMode(useReactFlow) {
    builderMapPanel()?.classList.toggle("uses-reactflow", Boolean(useReactFlow));
    builderReactFlowRoot()?.classList.toggle("builder-reactflow-root", Boolean(useReactFlow));
  }

  const REACT_FLOW_SCALE = 80;
  const REACT_FLOW_GRID_SIZE = 80;

  function snapToBuilderGrid(value) {
    return Math.round(Number(value || 0) / REACT_FLOW_GRID_SIZE) * REACT_FLOW_GRID_SIZE;
  }

  function buildFlowGraph(zone, selectedRoomId) {
    const nodes = [];
    const edges = [];
    for (const room of zone?.rooms || []) {
      const roomId = builderRoomKey(room?.id || "");
      const mapX = normalizeBuilderMapCoordinate(room?.map_x ?? room?.map?.x ?? room?.x);
      const mapY = normalizeBuilderMapCoordinate(room?.map_y ?? room?.map?.y ?? room?.y);
      if (!roomId || !Number.isFinite(mapX) || !Number.isFinite(mapY)) {
        continue;
      }
      nodes.push({
        id: roomId,
        type: "builderRoom",
        draggable: true,
        selectable: true,
        width: 14,
        height: 14,
        style: {
          width: 14,
          height: 14,
        },
        position: {
          x: mapX * REACT_FLOW_SCALE,
          y: -mapY * REACT_FLOW_SCALE,
        },
        data: {
          label: room.name || `Room ${roomId}`,
          roomId,
          selected: roomId === builderRoomKey(selectedRoomId),
        },
      });

      for (const [direction, spec] of Object.entries(room?.exits || {})) {
        const targetId = builderRoomKey(spec?.target || spec?.target_id || "");
        const normalizedDirection = canonicalExitDirection(direction);
        if (!targetId || !normalizedDirection) {
          continue;
        }
        edges.push({
          id: `${roomId}-${normalizedDirection}`,
          source: roomId,
          target: targetId,
          label: normalizedDirection,
          type: "straight",
          selectable: true,
          animated: false,
          data: {
            direction: normalizedDirection,
            roomId,
          },
          style: {
            stroke: "rgba(195, 164, 104, 0.72)",
            strokeWidth: 1.5,
          },
          labelStyle: {
            fill: "#e9dcc4",
            fontSize: 11,
          },
        });
      }
    }

    return { nodes, edges };
  }

  function queueBuilderReactFlowViewport(type) {
    builderState.reactFlowViewportRequest = {
      type,
      token: Number(builderState.reactFlowViewportRequest?.token || 0) + 1,
    };
    renderZoneMap();
  }

  async function saveBuilderRoomPayload(roomId, overrides = {}) {
    const normalizedRoomId = builderRoomKey(roomId);
    if (!normalizedRoomId) {
      throw new Error("Missing room id.");
    }
    const baseRoom = builderRoomById(normalizedRoomId);
    if (!baseRoom) {
      throw new Error("Room not found.");
    }
    const room = updateBuilderZoneRoom(normalizedRoomId, {
      name: overrides.name ?? baseRoom.name ?? `Room ${normalizedRoomId}`,
      desc: overrides.desc ?? baseRoom.desc ?? "",
      short_desc: overrides.short_desc ?? overrides.shortDesc ?? baseRoom.short_desc ?? null,
      stateful_descs: overrides.stateful_descs ?? baseRoom.stateful_descs ?? {},
      details: overrides.details ?? baseRoom.details ?? {},
      room_states: overrides.room_states ?? baseRoom.room_states ?? [],
      ambient: overrides.ambient ?? baseRoom.ambient ?? { rate: 0, messages: [] },
      environment: overrides.environment ?? baseRoom.environment ?? "city",
      exits: overrides.exits ?? overrides.exitMap ?? baseRoom.exitMap ?? {},
      zone_id: overrides.zone_id ?? baseRoom.zone_id ?? builderState.currentZoneId ?? "",
      map_x: overrides.map_x ?? Number(baseRoom.map?.x ?? baseRoom.map_x ?? baseRoom.x ?? 0),
      map_y: overrides.map_y ?? Number(baseRoom.map?.y ?? baseRoom.map_y ?? baseRoom.y ?? 0),
      map_layer: overrides.map_layer ?? Number(baseRoom.map?.layer ?? baseRoom.map_layer ?? 0),
    });
    return { room, zone_id: room.zone_id, exits: builderRoomExitsArray(room) };
  }

  async function persistBuilderRoomCoordinates(roomId, mapX, mapY) {
    const normalizedRoomId = builderRoomKey(roomId);
    if (!normalizedRoomId) {
      return;
    }
    const nextMapX = Number.isFinite(Number(mapX)) ? Math.round(Number(mapX)) : 0;
    const nextMapY = Number.isFinite(Number(mapY)) ? Math.round(Number(mapY)) : 0;
    setBuilderRoomCoordinates(normalizedRoomId, nextMapX, nextMapY);
    renderZoneMap();

    const response = await saveBuilderRoomPayload(normalizedRoomId, {
      map_x: nextMapX,
      map_y: nextMapY,
    });

    if (response.room) {
      builderState.currentRoom = response.room;
    }

    renderBuilderRoomList();
    renderZoneMap();
    setBuilderPageStatus(`Moved ${roomNameById(normalizedRoomId)} to (${nextMapX}, ${nextMapY}). Save zone to persist.`);
  }

  async function connectBuilderReactFlowRooms(sourceId, targetId) {
    const fromRoom = builderRoomById(sourceId);
    const toRoom = builderRoomById(targetId);
    if (!fromRoom || !toRoom) {
      throw new Error("Both rooms must exist in the loaded zone.");
    }

    const requestedDirection = window.prompt("Enter exit direction (north, south, etc):", getDirection(fromRoom, toRoom) || "");
    const direction = canonicalExitDirection(requestedDirection || "");
    if (!direction) {
      return;
    }

    const nextExits = builderRoomExitsArray(fromRoom).filter((exit) => canonicalExitDirection(exit.direction || "") !== direction);
    nextExits.push({
      direction,
      target_id: builderRoomKey(targetId),
      typeclass: DEFAULT_SLOW_EXIT_TYPECLASS,
      speed: "walk",
      travel_time: 5,
    });

    await saveBuilderRoomPayload(fromRoom.id, { exits: nextExits });
    renderBuilderRoomList();
    renderZoneMap();
    setBuilderPageStatus(`Connected ${roomNameById(fromRoom.id)} ${direction} to ${roomNameById(toRoom.id)}. Save zone to persist.`);
  }

  async function deleteBuilderReactFlowEdges(edges = []) {
    let deletedCount = 0;
    for (const edge of edges) {
      const roomId = builderRoomKey(edge?.data?.roomId || edge?.source || "");
      const direction = canonicalExitDirection(edge?.data?.direction || edge?.label || "");
      const room = builderRoomById(roomId);
      if (!room || !direction) {
        continue;
      }
      const nextExits = builderRoomExitsArray(room).filter((exit) => canonicalExitDirection(exit.direction || "") !== direction);
      if (nextExits.length === builderRoomExitsArray(room).length) {
        continue;
      }
      await saveBuilderRoomPayload(roomId, { exits: nextExits });
      deletedCount += 1;
    }
    if (deletedCount) {
      renderBuilderRoomList();
      renderZoneMap();
      setBuilderPageStatus(`Deleted ${deletedCount} exit${deletedCount === 1 ? "" : "s"}. Save zone to persist.`);
    }
  }

  async function createExitBetweenRooms(fromId, toId) {
    const fromRoom = builderRoomById(fromId);
    const toRoom = builderRoomById(toId);
    if (!fromRoom || !toRoom) {
      throw new Error("Both rooms must exist in the loaded zone.");
    }
    const direction = getDirection(fromRoom, toRoom);
    const reverse = reverseDirection(direction);
    if (!direction || !reverse) {
      throw new Error("Unable to determine exit direction from room positions.");
    }

    const nextFromExits = mergeBuilderExit(fromRoom.exits || fromRoom.exitMap || [], direction, toRoom.id);
    const nextToExits = mergeBuilderExit(toRoom.exits || toRoom.exitMap || [], reverse, fromRoom.id);

    await saveBuilderRoomPayload(fromRoom.id, { exits: nextFromExits });
    await saveBuilderRoomPayload(toRoom.id, { exits: nextToExits });
    renderBuilderRoomList();
    renderZoneMap();
    setBuilderPageStatus(`Connected ${roomNameById(fromRoom.id)} ${direction} to ${roomNameById(toRoom.id)}. Save zone to persist.`);
  }

  function renderBuilderReactFlowMap(zone) {
    const root = builderReactFlowRoot();
    if (!root || !window.DragonsireBuilderReactFlow?.mountBuilderReactFlow) {
      return false;
    }
    const { nodes, edges } = buildFlowGraph(zone, builderState.currentRoomId);
    const currentRoom = (zone?.rooms || []).find((room) => builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId));
    window.DragonsireBuilderReactFlow.mountBuilderReactFlow(root, {
      nodes,
      edges,
      selectedRoomId: builderRoomKey(builderState.currentRoomId),
      viewportRequest: builderState.reactFlowViewportRequest,
      onSelectRoom: (roomId) => {
        const normalizedRoomId = builderRoomKey(roomId);
        if (!normalizedRoomId || normalizedRoomId === builderRoomKey(builderState.currentRoomId)) {
          return;
        }
        void loadBuilderRoom(normalizedRoomId).catch((error) => {
          console.error(error);
          setBuilderPageStatus(error.message || "Unable to load room.");
        });
      },
      onMoveRoom: (payload) => {
        const snappedX = snapToBuilderGrid(payload.map_x);
        const snappedY = snapToBuilderGrid(payload.map_y);
        void persistBuilderRoomCoordinates(
          payload.roomId,
          Math.round(snappedX / REACT_FLOW_SCALE),
          Math.round(-snappedY / REACT_FLOW_SCALE)
        ).catch((error) => {
          console.error(error);
          setBuilderPageStatus(error.message || "Unable to save room position.");
          toast(error.message || "Unable to save room position.");
          renderZoneMap();
        });
      },
      onConnectRooms: ({ source, target }) => {
        void connectBuilderReactFlowRooms(source, target).catch((error) => {
          console.error(error);
          setBuilderPageStatus(error.message || "Unable to connect rooms.");
          toast(error.message || "Unable to connect rooms.");
          renderZoneMap();
        });
      },
      onDeleteEdges: (edgesToDelete) => {
        void deleteBuilderReactFlowEdges(edgesToDelete).catch((error) => {
          console.error(error);
          setBuilderPageStatus(error.message || "Unable to delete exit.");
          toast(error.message || "Unable to delete exit.");
          renderZoneMap();
        });
      },
    });
    updateBuilderMapMeta(nodes, edges);
    byId("builder-map-room-name").textContent = currentRoom ? currentRoom.name : "Awaiting room data";
    return true;
  }

  function updateBuilderMapMeta(rooms, edges) {
    const zoneLabel = builderState.zone?.zone_id || builderState.currentZoneId || "";
    byId("builder-map-meta-rooms").textContent = `Rooms ${rooms.length}`;
    byId("builder-map-meta-exits").textContent = `Exits ${edges.length}`;
    byId("builder-map-meta-zoom").textContent = zoneLabel
      ? `Zone ${String(zoneLabel).replace(/_/g, " ")}`
      : "Zone local";
  }

  function updateBuilderMapTooltip(panelX, panelY, room) {
    const tooltip = builderMapTooltip();
    if (!tooltip) {
      return;
    }
    if (!room) {
      tooltip.style.display = "none";
      return;
    }
    tooltip.textContent = room.name || `Room ${room.id}`;
    tooltip.style.display = "block";
    tooltip.style.left = `${panelX}px`;
    tooltip.style.top = `${panelY}px`;
  }

  function normalizeBuilderZoneRooms(rooms) {
    return (rooms || []).flatMap((room) => {
      const mapX = normalizeBuilderMapCoordinate(room?.map?.x ?? room?.map_x ?? room?.x);
      const mapY = normalizeBuilderMapCoordinate(room?.map?.y ?? room?.map_y ?? room?.y);
      if (!Number.isFinite(mapX) || !Number.isFinite(mapY)) {
        return [];
      }
      return [{
        ...room,
        map_x: mapX,
        map_y: mapY,
        x: mapX,
        y: mapY,
        map: {
          ...(room?.map || {}),
          x: mapX,
          y: mapY,
        },
        current: builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId),
        is_player: builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId),
      }];
    });
  }

  function builderZoneWorldPosition(roomId) {
    const room = builderRoomById(roomId);
    if (!room) {
      return null;
    }
    const mapX = Number(room.map_x);
    const mapY = Number(room.map_y);
    if (!Number.isFinite(mapX) || !Number.isFinite(mapY)) {
      console.warn("ROOM MISSING COORDS:", room.id, room.name, room.map_x, room.map_y);
      return null;
    }
    return {
      x: mapX,
      y: mapY,
    };
  }

  function builderZoneScreenPosition(roomId) {
    const world = builderZoneWorldPosition(roomId);
    if (!world) {
      return null;
    }
    return {
      x: world.x * builderState.zoneZoom + builderState.zonePan.x,
      y: world.y * builderState.zoneZoom + builderState.zonePan.y,
    };
  }

  function fitZoneMapToViewport() {
    const canvas = zoneMapCanvas();
    const rooms = builderState.zone?.rooms || [];
    if (!canvas || !rooms.length) {
      return;
    }
    const fitted = fitRoomsToCanvas(canvas, rooms, BUILDER_ZONE_MIN_ZOOM);
    builderState.zoneZoom = fitted.scale;
    builderState.zonePan = fitted.offset;
    builderState.zoneZoomInitialized = true;
    builderState.zoneMapNeedsFit = false;
    saveZoneCamera();
  }

  function isZoneCameraValid(camera, rooms, canvas) {
    if (!camera || !rooms || !rooms.length || !canvas) {
      return false;
    }
    const zoom = Number(camera.zoom || 0);
    if (!Number.isFinite(zoom) || zoom < BUILDER_ZONE_MIN_ZOOM || zoom > BUILDER_ZONE_MAX_ZOOM) {
      return false;
    }
    const bounds = renderedMapBoundsForRooms(canvas, rooms, zoom, null);
    const maxPanX = Math.max(bounds.width, canvas.width) * 1.25;
    const maxPanY = Math.max(bounds.height, canvas.height) * 1.25;
    if (Math.abs(Number(camera.pan?.x || 0)) > maxPanX || Math.abs(Number(camera.pan?.y || 0)) > maxPanY) {
      return false;
    }

    const usableWidth = Math.max(40, canvas.width - 48);
    const usableHeight = Math.max(40, canvas.height - 48);
    const fitted = fitRoomsToCanvas(canvas, rooms, BUILDER_ZONE_MIN_ZOOM);
    const minReasonableZoom = Math.max(BUILDER_ZONE_MIN_ZOOM, Number(fitted.scale || BUILDER_ZONE_MIN_ZOOM) * 0.35);
    const coversTooLittleSpace = bounds.width < usableWidth * 0.35 && bounds.height < usableHeight * 0.35;
    if (coversTooLittleSpace && zoom < minReasonableZoom) {
      return false;
    }

    return true;
  }

  function centerZoneMapOnRoom(roomId) {
    const canvas = zoneMapCanvas();
    const position = builderZoneWorldPosition(roomId);
    if (!canvas || !position) {
      return;
    }
    builderState.zonePan = {
      x: Math.round(canvas.width / 2 - position.x * builderState.zoneZoom),
      y: Math.round(canvas.height / 2 - position.y * builderState.zoneZoom),
    };
    builderState.zoneZoomInitialized = true;
    builderState.zoneMapNeedsFit = false;
    saveZoneCamera();
    renderZoneMap();
  }

  function ensureZoneMapCanvas(viewport) {
    let canvas = zoneMapCanvas();
    if (!canvas) {
      return null;
    }
    const nextWidth = Math.max(320, Math.round(viewport.clientWidth || 320));
    const nextHeight = Math.max(320, Math.round(viewport.clientHeight || 320));
    if (canvas.width !== nextWidth) {
      canvas.width = nextWidth;
    }
    if (canvas.height !== nextHeight) {
      canvas.height = nextHeight;
    }
    return canvas;
  }

  function summarizeBuilderRoomExits(room) {
    const rawExits = Array.isArray(room?.exits)
      ? room.exits
      : Object.entries(room?.exitMap || {}).map(([direction, target_id]) => ({ direction, target_id }));
    const exitGroups = splitBuilderExits(rawExits);
    return {
      roomId: Number(room?.id || 0),
      roomName: room?.name || `Room ${room?.id || "?"}`,
      rawExits: rawExits.map((exit) => ({
        direction: exit.direction || "",
        target_id: Number(exit.target_id || 0),
      })),
      normalizedExits: exitGroups.normalized.map((exit) => ({
        rawDirection: exit.rawDirection,
        direction: exit.direction,
        target_id: exit.target_id,
      })),
      renderableExits: exitGroups.spatial.map((exit) => ({ direction: exit.direction, target_id: exit.target_id })),
      nonSpatialExits: exitGroups.special.map((exit) => ({ direction: exit.direction, target_id: exit.target_id })),
    };
  }

  function renderBuilderConnectOverlay(canvas) {
    if (!builderState.connectMode || !builderState.connectFrom) {
      return;
    }
    const sourcePosition = builderState.zoneRoomPositions.get(builderRoomKey(builderState.connectFrom));
    if (!sourcePosition) {
      return;
    }
    const previewTargetId = builderRoomKey(builderState.hoveredRoomId || "");
    const previewTargetPosition = previewTargetId && previewTargetId !== builderRoomKey(builderState.connectFrom)
      ? builderState.zoneRoomPositions.get(previewTargetId)
      : null;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    ctx.save();
    ctx.strokeStyle = "rgba(255, 214, 132, 0.95)";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(sourcePosition.x, sourcePosition.y, 12, 0, Math.PI * 2);
    ctx.stroke();
    if (previewTargetPosition) {
      ctx.setLineDash([8, 6]);
      ctx.beginPath();
      ctx.moveTo(sourcePosition.x, sourcePosition.y);
      ctx.lineTo(previewTargetPosition.x, previewTargetPosition.y);
      ctx.stroke();
    }
    ctx.restore();
  }

  function updateBuilderMapPresentation(rooms, edges, edgeSummary) {
    console.log("BUILDER ROOMS:", rooms.length);
    console.log("BUILDER SAMPLE:", rooms[0] || null);
    console.log("builder edge counters", edgeSummary.counters);
    updateBuilderMapMeta(rooms, edges);
    const currentRoom = rooms.find((room) => builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId));
    byId("builder-map-room-name").textContent = currentRoom ? currentRoom.name : "Awaiting room data";
    if (currentRoom) {
      const currentRoomSummary = summarizeBuilderRoomExits(currentRoom);
      window.__dragonsireMapDebug = window.__dragonsireMapDebug || {};
      window.__dragonsireMapDebug.builderSelectedRoom = currentRoomSummary;
      console.log("builder selected room exits", currentRoomSummary);
    }
  }

  function mapEdgesFromZoneRooms(rooms) {
    const edges = [];
    const seen = new Set();
    const counters = {
      totalExits: 0,
      spatialExits: 0,
      diagonalExits: 0,
      verticalExits: 0,
      specialExits: 0,
      droppedExits: 0,
    };
    for (const room of rooms || []) {
      const rawExits = Array.isArray(room.exits)
        ? room.exits
        : Object.entries(room.exitMap || {}).map(([direction, target_id]) => ({ direction, target_id }));
      const exitGroups = splitBuilderExits(rawExits);
      counters.totalExits += exitGroups.normalized.length;
      counters.spatialExits += exitGroups.spatial.length;
      counters.diagonalExits += exitGroups.normalized.filter((exit) => exit.isDiagonal).length;
      counters.verticalExits += exitGroups.vertical.length;
      counters.specialExits += exitGroups.special.length;
      counters.droppedExits += exitGroups.dropped.length;
      for (const exit of exitGroups.spatial) {
        const fromId = builderRoomKey(room.id);
        const toId = builderRoomKey(exit.target_id);
        const signature = [fromId, toId].sort().join(":");
        if (seen.has(signature)) {
          continue;
        }
        seen.add(signature);
        edges.push({ from: fromId, to: toId, dir: exit.direction, vector: DIR_VECTOR[exit.direction] || null });
      }
    }
    return { edges, counters };
  }

  function summarizeExplicitBuilderEdges(explicitEdges, roomIds) {
    const edges = [];
    const counters = {
      totalExits: 0,
      spatialExits: 0,
      diagonalExits: 0,
      verticalExits: 0,
      specialExits: 0,
      droppedExits: 0,
    };
    const seen = new Set();
    for (const edge of explicitEdges || []) {
      const classified = classifyBuilderExit({ direction: edge?.dir || edge?.direction || "", target_id: edge?.to || 0 });
      counters.totalExits += 1;
      counters.diagonalExits += classified.isDiagonal ? 1 : 0;
      counters.verticalExits += classified.isVertical ? 1 : 0;
      counters.specialExits += classified.isSpecial ? 1 : 0;
      counters.droppedExits += classified.dropped ? 1 : 0;
      const fromId = builderRoomKey(edge?.from || "");
      const toId = builderRoomKey(edge?.to || "");
      if (!roomIds.has(fromId) || !roomIds.has(toId)) {
        continue;
      }
      if (!classified.isSpatial) {
        continue;
      }
      const signature = [fromId, toId].sort().join(":");
      if (seen.has(signature)) {
        continue;
      }
      seen.add(signature);
      counters.spatialExits += 1;
      edges.push({ from: fromId, to: toId, dir: classified.direction, vector: DIR_VECTOR[classified.direction] || null });
    }
    return { edges, counters };
  }

  function buildBuilderEdgeSummary(rooms, explicitEdges = null) {
    if (Array.isArray(explicitEdges) && explicitEdges.length) {
      return summarizeExplicitBuilderEdges(explicitEdges, new Set((rooms || []).map((room) => builderRoomKey(room.id))));
    }
    return mapEdgesFromZoneRooms(rooms);
  }

  function renderZoneMap() {
    const viewport = builderMapPanel();
    if (!viewport) {
      return;
    }
    const useReactFlow = builderUsesReactFlow();
    setBuilderMapRenderMode(useReactFlow);
    const payload = builderState.zone;
    if (!payload || !Array.isArray(payload.rooms) || !payload.rooms.length) {
      if (useReactFlow) {
        renderBuilderReactFlowMap({ rooms: [] });
      }
      const canvas = zoneMapCanvas();
      const ctx = canvas?.getContext("2d");
      if (ctx && canvas) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
      byId("builder-map-room-name").textContent = "Awaiting room data";
      updateBuilderMapMeta([], []);
      return;
    }
    if (useReactFlow) {
      renderBuilderReactFlowMap(payload);
      return;
    }

    const canvas = ensureZoneMapCanvas(viewport);
    if (!canvas) {
      return;
    }

    const rooms = normalizeBuilderZoneRooms(payload.rooms);

    const canvasSizeChanged = builderState.zoneCanvasSize.width !== canvas.width || builderState.zoneCanvasSize.height !== canvas.height;
    builderState.zoneCanvasSize = { width: canvas.width, height: canvas.height };

    if (builderState.zoneForceFitOnce) {
      builderState.zoneForceFitOnce = false;
      fitZoneMapToViewport();
    } else if (!builderState.zoneZoomInitialized || (builderState.zoneMapNeedsFit && canvasSizeChanged)) {
      const savedCamera = loadZoneCamera(builderState.currentZoneId);
      if (isZoneCameraValid(savedCamera, rooms, canvas)) {
        builderState.zonePan = savedCamera.pan;
        builderState.zoneZoom = savedCamera.zoom;
        builderState.zoneZoomInitialized = true;
        builderState.zoneMapNeedsFit = false;
      } else {
        fitZoneMapToViewport();
      }
    }
    const edgeSummary = buildBuilderEdgeSummary(rooms, payload.edges || []);
    const edges = edgeSummary.edges;
    const rendered = renderZoneCanvasMap({
      canvas,
      rooms,
      edges,
      mode: "builder",
      scale: builderState.zoneZoom,
      getPosition: (room) => builderZoneScreenPosition(room.id),
      getColor: (room) => roomColor(room),
      getRadius: (room) => mapRoomRadiusForHover(room, false, builderState.hoveredRoomId),
      hoveredRoomId: builderState.hoveredRoomId,
      selectedRoomId: builderRoomKey(builderState.currentRoomId),
      showLabels: false,
      edgeColor: () => "rgba(195, 164, 104, 0.6)",
      edgeWidth: () => 1.5,
      debugTransform: {
        zoom: builderState.zoneZoom,
        pan: builderState.zonePan,
        edgeCounters: edgeSummary.counters,
        usesStoredRoomCoordinates: true,
      },
    });
    builderState.zoneRoomPositions = rendered.positions;
    renderBuilderConnectOverlay(canvas);
    updateBuilderMapPresentation(rooms, edges, edgeSummary);
  }

  function syncZoneGraphRoom(roomPayload) {
    if (!builderState.zone || !roomPayload) {
      return;
    }
    updateBuilderZoneRoom(roomPayload.id, roomPayload);
  }

  async function loadBuilderZone(zoneId, options = {}) {
    const requestedZoneId = builderZoneRequestId(zoneId);
    const normalizedZoneId = normalizeBuilderZoneId(zoneId);
    const graphZoneId = normalizeBuilderZoneId(builderState.zone?.zone_id || "");
    if (!options.force
      && normalizeBuilderZoneId(builderState.currentZoneId) === normalizedZoneId
      && builderState.zone
      && graphZoneId === normalizedZoneId
      && Array.isArray(builderState.zone.rooms)
      && builderState.zone.rooms.length) {
      return;
    }
    const payload = await builderFetchJson(`/builder/api/zone/${encodeURIComponent(requestedZoneId)}/`);
    replaceBuilderZone(payload, { fallbackZoneId: normalizedZoneId });
    persistBuilderZoneSelection(builderState.currentZoneId);
    renderBuilderRoomList();
    highlightSelectedBuilderRoom();
    renderZoneMap();
  }

  function applyBuilderMapPayload(mapPayload, fallbackZoneId = "") {
    if (!mapPayload || !Array.isArray(mapPayload.rooms)) {
      return false;
    }
    replaceBuilderZone(mapPayload, { fallbackZoneId });
    return true;
  }

  async function builderFetchJson(url, options) {
    const response = await window.fetch(url, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch (error) {
      payload = {};
    }
    if (!response.ok) {
      const message = payload.error || payload.detail || `Request failed (${response.status})`;
      throw new Error(message);
    }
    return payload;
  }

  async function loadBuilderRoom(id) {
    if (!id) {
      return;
    }
    const roomId = builderRoomKey(id);
    const data = builderRoomById(roomId);
    if (!data) {
      throw new Error(`Unable to find room ${roomId}.`);
    }
    builderState.currentRoomId = roomId;
    builderState.selectedRoom = roomId;
    window.localStorage.setItem(BUILDER_LAST_ROOM_STORAGE_KEY, String(roomId));
    highlightSelectedBuilderRoom();
    setBuilderPageStatus(`Editing ${data.name || `room ${roomId}`}`);
    builderState.currentZoneId = normalizeBuilderZoneId(data.zone_id || builderState.currentZoneId);
    persistBuilderZoneSelection(builderState.currentZoneId || builderState.zone?.zone_id || "");
    syncBuilderZoneMenus();
    renderBuilderRoomList();
    highlightSelectedBuilderRoom();
    builderState.currentRoom = data;
    if (byId("room-name")) {
      byId("room-name").value = data.name || "";
    }
    if (byId("room-short-desc")) {
      byId("room-short-desc").value = deriveBuilderShortDesc(data);
    }
    if (byId("room-desc")) {
      byId("room-desc").value = data.desc || "";
    }
    renderBuilderStatefulDescList(data.stateful_descs || {});
    renderBuilderDetailList(data.details || {});
    if (byId("room-active-states")) {
      byId("room-active-states").value = (data.room_states || []).join(", ");
    }
    if (byId("room-ambient-rate")) {
      byId("room-ambient-rate").value = String(data.ambient?.rate || 0);
    }
    if (byId("room-ambient-messages")) {
      byId("room-ambient-messages").value = (data.ambient?.messages || []).join("\n");
    }
    if (byId("room-environment")) {
      byId("room-environment").value = data.environment || "city";
    }
    if (byId("room-zone")) {
      byId("room-zone").value = builderZoneSelectValue(data.zone_id || "");
    }
    if (byId("room-map-x")) {
      byId("room-map-x").value = String(data.map?.x ?? data.map_x ?? data.x ?? 0);
    }
    if (byId("room-map-y")) {
      byId("room-map-y").value = String(data.map?.y ?? data.map_y ?? data.y ?? 0);
    }
    if (byId("room-map-layer")) {
      byId("room-map-layer").value = String(data.map?.layer ?? data.map_layer ?? 0);
    }
    renderBuilderExitList(builderRoomExitsArray(data));
    renderBuilderPreview(data);
    renderZoneMap();
  }

  async function loadBuilderRoomList() {
    builderState.rooms = builderVisibleRooms();
    const list = byId("room-list");
    const savedScrollTop = Number(window.localStorage.getItem(BUILDER_ROOM_LIST_SCROLL_STORAGE_KEY) || 0);
    if (list && Number.isFinite(savedScrollTop) && savedScrollTop > 0) {
      list.scrollTop = savedScrollTop;
    }
  }

  async function loadBuilderZones() {
    builderState.zones = await builderFetchJson("/builder/api/zones/");
    syncBuilderZoneMenus();
  }

  async function refreshBuilderZoneFromYaml(options = {}) {
    const zoneId = normalizeBuilderZoneId(options.zoneId || builderState.currentZoneId || builderState.zone?.zone_id || "");
    if (!zoneId) {
      return;
    }
    const preservedRoomId = builderRoomKey(options.preserveRoomId ?? builderState.currentRoomId ?? "");
    await loadBuilderZone(zoneId, { force: true });
    if (preservedRoomId && builderRoomById(preservedRoomId)) {
      await loadBuilderRoom(preservedRoomId);
    }
  }

  function setBuilderRoomCoordinates(roomId, mapX, mapY) {
    const normalizedRoomId = builderRoomKey(roomId);
    if (!normalizedRoomId) {
      return;
    }
    const nextMapX = Number.isFinite(Number(mapX)) ? Math.round(Number(mapX)) : 0;
    const nextMapY = Number.isFinite(Number(mapY)) ? Math.round(Number(mapY)) : 0;

    if (normalizedRoomId === builderRoomKey(builderState.currentRoomId)) {
      if (byId("room-map-x")) {
        byId("room-map-x").value = String(nextMapX);
      }
      if (byId("room-map-y")) {
        byId("room-map-y").value = String(nextMapY);
      }
      if (builderState.currentRoom) {
        builderState.currentRoom.map = { ...(builderState.currentRoom.map || {}), x: nextMapX, y: nextMapY };
        builderState.currentRoom.map_x = nextMapX;
        builderState.currentRoom.map_y = nextMapY;
        builderState.currentRoom.x = nextMapX;
        builderState.currentRoom.y = nextMapY;
      }
    }

    const zoneRoom = builderRoomById(normalizedRoomId);
    if (zoneRoom) {
      zoneRoom.map = { ...(zoneRoom.map || {}), x: nextMapX, y: nextMapY };
      zoneRoom.map_x = nextMapX;
      zoneRoom.map_y = nextMapY;
      zoneRoom.x = nextMapX;
      zoneRoom.y = nextMapY;
    }
  }

  async function switchBuilderZone(zoneId, options = {}) {
    const normalizedZoneId = normalizeBuilderZoneId(zoneId);
    const currentRoomStillVisible = builderVisibleRooms().some((room) => (
      builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId)
        && normalizeBuilderZoneId(room.zone_id) === normalizedZoneId
    ));
    if (!currentRoomStillVisible) {
      builderState.currentRoomId = null;
      builderState.selectedRoom = null;
      builderState.currentRoom = null;
    }
    builderState.currentZoneId = normalizedZoneId;
    persistBuilderZoneSelection(normalizedZoneId);
    syncBuilderZoneMenus();
    renderBuilderRoomList();

    await loadBuilderZone(zoneId, { force: true });

    const filteredRooms = builderVisibleRooms();
    const currentFilteredRoomVisible = filteredRooms.some((room) => builderRoomKey(room.id) === builderRoomKey(builderState.currentRoomId));
    if (currentFilteredRoomVisible && options.preserveSelection !== false) {
      highlightSelectedBuilderRoom();
      return;
    }

    if (filteredRooms.length && options.autoSelectRoom !== false) {
      await loadBuilderRoom(filteredRooms[0].id);
      return;
    }

    clearBuilderEditor(`${currentBuilderZoneLabel()} ready.`, `${currentBuilderZoneLabel()} has no rooms yet.`);
  }

  async function initializeBuilderData() {
    setBuilderPageStatus("Loading builder data...");
    await loadBuilderZones();

    const persistedRoomId = builderRoomKey(window.localStorage.getItem(BUILDER_LAST_ROOM_STORAGE_KEY) || "");
    const persistedZoneId = normalizeBuilderZoneId(window.localStorage.getItem(BUILDER_LAST_ZONE_STORAGE_KEY) || "");
    if (builderState.zones.length) {
      const nextZoneId = builderState.zones.some((zone) => normalizeBuilderZoneId(zone.id) === persistedZoneId)
        ? persistedZoneId
        : defaultAssignableZoneId(builderState.zones[0].id) || normalizeBuilderZoneId(builderState.zones[0].id);
      await switchBuilderZone(nextZoneId);
      if (persistedRoomId && builderRoomById(persistedRoomId)) {
        await loadBuilderRoom(persistedRoomId);
      }
      return;
    }

    clearBuilderEditor("No rooms found.", "Create a zone, then create the first room.");
  }

  async function saveBuilderRoom() {
    const draft = currentBuilderDraft();
    if (!draft.id) {
      toast("Select a room first.");
      return;
    }
    if (!draft.name.trim()) {
      toast("Room name cannot be empty.");
      return;
    }
    if (!draft.desc.trim()) {
      toast("Room description cannot be empty.");
      return;
    }
    if (!draft.zone_id) {
      toast("Room must belong to a zone.");
      return;
    }
    const exitValidation = validateBuilderExits(draft.exits);
    if (exitValidation) {
      toast(exitValidation);
      return;
    }
    showSavingState();
    setBuilderPageStatus(`Updating ${draft.name} in YAML...`);
    try {
      const response = await saveBuilderRoomPayload(draft.id, {
        name: draft.name,
        desc: draft.desc,
        short_desc: draft.shortDesc || null,
        stateful_descs: draft.stateful_descs,
        details: draft.details,
        room_states: draft.room_states,
        ambient: draft.ambient,
        environment: draft.environment,
        exits: draft.exits,
        zone_id: draft.zone_id,
        map_x: draft.map_x,
        map_y: draft.map_y,
        map_layer: draft.map_layer,
      });
      syncBuilderZoneMenus();
      renderBuilderRoomList();
      await loadBuilderRoom(draft.id);
      renderBuilderPreview(response.room || builderState.currentRoom || draft, { flash: true });
      setBuilderPageStatus(`Updated ${draft.name} in YAML. Save zone to persist.`);
      showSavedState();
    } catch (error) {
      resetSaveState();
      throw error;
    }
  }

  async function createBuilderZone() {
    const name = String(byId("builder-zone-name-input")?.value || "").trim();
    const area = String(byId("builder-zone-area-input")?.value || "").trim();
    if (!name) {
      toast("Zone name is required.");
      return;
    }
    if (!area) {
      toast("Area id is required.");
      return;
    }
    setBuilderPageStatus(`Creating zone ${name}...`);
    const response = await builderFetchJson("/builder/api/zones/create/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name, area }),
    });
    await loadBuilderZones();
    closeBuilderDialog("builder-zone-dialog");
    toast(`Created zone ${response.zone?.name || name}`);
    await switchBuilderZone(response.zone?.id || area, { autoSelectRoom: false, preserveSelection: false });
  }

  async function createBuilderRoom() {
    if (!requireActiveBuilderZone()) {
      return;
    }
    const name = String(byId("builder-room-name-input")?.value || "").trim();
    const desc = String(byId("builder-room-desc-input")?.value || "").trim();
    const environment = String(byId("builder-room-environment-input")?.value || "city").trim().toLowerCase();
    const zoneId = normalizeBuilderZoneId(byId("builder-room-zone-input")?.value || builderState.currentZoneId || "");
    if (!name) {
      toast("Room name is required.");
      return;
    }
    if (!desc) {
      toast("Room description is required.");
      return;
    }
    if (!zoneId) {
      toast("Room must belong to a zone.");
      return;
    }
    const position = builderCreateRoomPosition();
    const roomId = uniqueBuilderRoomId(name);
    const room = normalizeBuilderYamlRoom(
      {
        id: roomId,
        name,
        desc,
        typeclass: "typeclasses.rooms_extended.ExtendedDireRoom",
        stateful_descs: {},
        details: {},
        room_states: [],
        ambient: { rate: 0, messages: [] },
        environment,
        zone_id: zoneId,
        map: { x: position.x, y: position.y, layer: 0 },
        exits: {},
      },
      builderVisibleRooms().length,
      zoneId
    );
    builderState.zone.rooms.push(room);
    rebuildBuilderRoomIndexes();
    setBuilderDirty(true);
    closeBuilderDialog("builder-room-dialog");
    toast(`Created room ${name}`);
    await loadBuilderRoom(room.id);
  }

  async function deleteBuilderRoom() {
    const roomId = builderRoomKey(builderState.currentRoomId || "");
    const roomName = builderState.currentRoom?.name || byId("room-name")?.value || `room ${roomId}`;
    if (!roomId) {
      toast("Select a room first.");
      return;
    }
    if (!window.confirm(`Delete ${roomName}? This also removes exits pointing to it.`)) {
      return;
    }
    setBuilderPageStatus(`Deleting ${roomName}...`);
    builderState.zone.rooms = builderState.zone.rooms
      .filter((room) => builderRoomKey(room.id) !== roomId)
      .map((room) => normalizeBuilderYamlRoom(
        {
          ...room,
          exits: Object.fromEntries(
            Object.entries(room.exitMap || room.exits || {}).filter(([, targetId]) => builderRoomKey(targetId) !== roomId)
          ),
        },
        0,
        builderState.currentZoneId || builderState.zone?.zone_id || ""
      ));
    rebuildBuilderRoomIndexes();
    setBuilderDirty(true);
    toast(`Deleted ${roomName}`);
    const remainingRooms = builderVisibleRooms();
    if (remainingRooms.length) {
      await loadBuilderRoom(remainingRooms[0].id);
      return;
    }
    clearBuilderEditor(`${currentBuilderZoneLabel()} is empty.`, `${currentBuilderZoneLabel()} has no rooms yet.`);
  }

  async function saveBuilderZone() {
    if (!builderState.zone || !builderState.currentZoneId) {
      throw new Error("No zone loaded.");
    }
    const payload = builderState.zone;
    console.log("Saving zone payload:", payload);
    setBuilderPageStatus(`Saving ${builderState.currentZoneId}...`);
    const response = await builderFetchJson("/builder/api/save-zone/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    console.log("Save response:", response);
    await loadBuilderZones();
    await refreshBuilderZoneFromYaml();
    setBuilderDirty(false);
    setBuilderPageStatus(response.status === "ok" ? `Saved successfully: ${builderState.currentZoneId}` : `Save failed: ${builderState.currentZoneId}`);
    toast("Saved successfully");
  }

  function formatBuilderReloadResult(result) {
    if (!result) {
      return "Zone loaded successfully";
    }
    return [
      "Zone loaded successfully",
      `${result.rooms || 0} rooms`,
      `${result.exits || 0} exits`,
      `${result.npcs || 0} NPCs`,
      `${result.items || 0} items`,
    ].join("\n");
  }

  async function reloadBuilderZone() {
    if (!builderState.currentZoneId) {
      throw new Error("No zone selected.");
    }
    setBuilderPageStatus(`Reloading ${builderState.currentZoneId}...`);
    const response = await builderFetchJson("/builder/api/reload-zone/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ zone_id: builderState.currentZoneId }),
    });
    console.log("Reload response:", response);
    await refreshBuilderZoneFromYaml();
    setBuilderDirty(false);
    setBuilderPageStatus(formatBuilderReloadResult(response.result));
    toast("Zone loaded successfully");
  }

  function bindBuilderInputs() {
    [
      "room-name",
      "room-short-desc",
      "room-desc",
      "room-desc-spring",
      "room-desc-summer",
      "room-desc-autumn",
      "room-desc-winter",
      "room-active-states",
      "room-ambient-rate",
      "room-ambient-messages",
      "room-environment",
      "room-zone",
      "room-map-x",
      "room-map-y",
      "room-map-layer",
    ].forEach((id) => {
      byId(id)?.addEventListener("input", () => {
        scheduleBuilderPreviewUpdate();
      });
      byId(id)?.addEventListener("change", () => {
        scheduleBuilderPreviewUpdate();
      });
    });

    byId("builder-preview-state")?.addEventListener("change", () => {
      renderBuilderPreview(builderState.currentRoom || currentBuilderDraft(), { flash: true });
    });

    byId("builder-add-custom-stateful-desc")?.addEventListener("click", () => {
      const list = byId("builder-custom-stateful-desc-list");
      if (!list) {
        return;
      }
      list.insertAdjacentHTML("beforeend", `
        <div class="builder-kv-row builder-state-row">
          <input class="builder-custom-state-key" type="text" value="" placeholder="State name" autocomplete="off">
          <textarea class="builder-custom-state-text builder-compact-textarea" placeholder="Description"></textarea>
          <button type="button" class="builder-kv-remove">Delete</button>
        </div>
      `);
    });

    byId("builder-add-detail")?.addEventListener("click", () => {
      const list = byId("builder-detail-list");
      if (!list) {
        return;
      }
      list.insertAdjacentHTML("beforeend", `
        <div class="builder-kv-row builder-detail-row">
          <input class="builder-detail-key" type="text" value="" placeholder="detail key" autocomplete="off">
          <textarea class="builder-detail-text builder-compact-textarea" placeholder="Detail description"></textarea>
          <button type="button" class="builder-kv-remove">Delete</button>
        </div>
      `);
    });

    byId("room-editor")?.addEventListener("click", (event) => {
      const button = event.target.closest(".builder-kv-remove");
      if (!button) {
        return;
      }
      event.preventDefault();
      button.closest(".builder-kv-row")?.remove();
      scheduleBuilderPreviewUpdate();
    });

    byId("room-editor")?.addEventListener("input", (event) => {
      if (event.target.closest(".builder-kv-row")) {
        scheduleBuilderPreviewUpdate();
      }
      const exitRow = event.target.closest(".builder-exit-row");
      if (exitRow) {
        const preview = exitRow.querySelector(".builder-exit-preview");
        if (preview) {
          preview.textContent = exitTravelPreview({
            direction: exitRow.querySelector(".builder-exit-direction")?.value || "",
            target_id: exitRow.querySelector(".builder-exit-target")?.value || "",
            typeclass: exitRow.querySelector(".builder-exit-type")?.value === "slow" ? DEFAULT_SLOW_EXIT_TYPECLASS : DEFAULT_EXIT_TYPECLASS,
            speed: exitRow.querySelector(".builder-exit-speed")?.value || "",
            travel_time: exitRow.querySelector(".builder-exit-travel-time")?.value || 0,
          });
        }
      }
    });

    byId("room-list")?.addEventListener("scroll", (event) => {
      window.localStorage.setItem(BUILDER_ROOM_LIST_SCROLL_STORAGE_KEY, String(event.target.scrollTop || 0));
    });

    byId("save-room")?.addEventListener("click", () => {
      void saveBuilderRoom().catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Room update failed.");
        resetSaveState();
        toast(error.message || "Room update failed.");
      });
    });

    byId("save-zone")?.addEventListener("click", () => {
      void saveBuilderZone().catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Zone save failed.");
        toast(error.message || "Zone save failed.");
      });
    });

    byId("reload-zone")?.addEventListener("click", () => {
      void reloadBuilderZone().catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Zone reload failed.");
        toast(error.message || "Zone reload failed.");
      });
    });

    byId("delete-room")?.addEventListener("click", () => {
      void deleteBuilderRoom().catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Delete failed.");
        toast(error.message || "Delete failed.");
      });
    });

    ["builder-zone-select", "builder-zone-select-top"].forEach((controlId) => {
      byId(controlId)?.addEventListener("change", (event) => {
        clearBuilderConnectMode();
        void switchBuilderZone(event.target.value).catch((error) => {
          console.error(error);
          setBuilderPageStatus(error.message || "Unable to switch zone.");
          toast(error.message || "Unable to switch zone.");
        });
      });
    });

    byId("builder-new-zone")?.addEventListener("click", () => {
      if (byId("builder-zone-name-input")) {
        byId("builder-zone-name-input").value = "";
      }
      if (byId("builder-zone-area-input")) {
        byId("builder-zone-area-input").value = "";
      }
      openBuilderDialog("builder-zone-dialog");
    });

    byId("builder-zone-create-submit")?.addEventListener("click", () => {
      void createBuilderZone().catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Unable to create zone.");
        toast(error.message || "Unable to create zone.");
      });
    });

    byId("builder-create-room")?.addEventListener("click", () => {
      if (!requireActiveBuilderZone()) {
        return;
      }
      if (byId("builder-room-name-input")) {
        byId("builder-room-name-input").value = "";
      }
      if (byId("builder-room-desc-input")) {
        byId("builder-room-desc-input").value = "";
      }
      if (byId("builder-room-environment-input")) {
        byId("builder-room-environment-input").value = "city";
      }
      syncBuilderZoneMenus();
      if (byId("builder-room-zone-input")?.options.length) {
        byId("builder-room-zone-input").value = builderZoneSelectValue(defaultAssignableZoneId(builderState.currentZoneId));
      }
      openBuilderDialog("builder-room-dialog");
    });

    byId("builder-room-create-submit")?.addEventListener("click", () => {
      void createBuilderRoom().catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Unable to create room.");
        toast(error.message || "Unable to create room.");
      });
    });

    byId("add-exit")?.addEventListener("click", () => {
      const exits = collectBuilderExits();
      const nextDirection = DIRECTIONS.find((direction) => !exits.some((exit) => exit.direction === direction)) || DIRECTIONS[0];
      renderBuilderExitList(exits.concat([{ direction: nextDirection, target_id: 0 }]));
      scheduleBuilderPreviewUpdate();
    });

    byId("zone-map-center-selected")?.addEventListener("click", () => {
      if (builderState.currentRoomId) {
        centerZoneMapOnRoom(builderState.currentRoomId);
      }
    });

    document.addEventListener("click", (event) => {
      const roomItem = event.target.closest(".room-item");
      if (!roomItem) {
        return;
      }
      void loadBuilderRoom(roomItem.dataset.id).catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Unable to load room.");
      });
    });

    document.addEventListener("click", (event) => {
      const removeButton = event.target.closest(".builder-exit-remove");
      if (removeButton) {
        removeButton.closest(".builder-exit-row")?.remove();
        scheduleBuilderPreviewUpdate();
        return;
      }

      const mapNode = event.target.closest(".builder-map-node");
      if (!mapNode) {
        return;
      }
    });

    document.addEventListener("change", (event) => {
      if (!event.target.closest("#exit-list")) {
        return;
      }
      scheduleBuilderPreviewUpdate();
    });

    const zoneMap = zoneMapCanvas();
    const mapPanel = builderMapPanel();
    zoneMap?.addEventListener("mousemove", (event) => {
      const panelRect = mapPanel?.getBoundingClientRect();
      const room = builderRoomAtCanvasEvent(event, zoneMap, builderCanvasHitRadius());
      const nextHoveredRoomId = room ? builderRoomKey(room.id || "") : null;
      zoneMap.style.cursor = room ? "pointer" : (builderState.zoneDrag ? "grabbing" : "grab");
      if (panelRect) {
        updateBuilderMapTooltip(event.clientX - panelRect.left, event.clientY - panelRect.top, room);
      }
      if (nextHoveredRoomId === builderState.hoveredRoomId) {
        return;
      }
      builderState.hoveredRoomId = nextHoveredRoomId;
      renderZoneMap();
    });

    zoneMap?.addEventListener("mouseleave", () => {
      zoneMap.style.cursor = builderState.zoneDrag ? "grabbing" : "grab";
      updateBuilderMapTooltip(0, 0, null);
      if (builderState.hoveredRoomId === null) {
        return;
      }
      builderState.hoveredRoomId = null;
      renderZoneMap();
    });

    zoneMap?.addEventListener("click", (event) => {
      const room = builderRoomAtCanvasEvent(event, zoneMap, builderCanvasHitRadius());
      if (!room) {
        if (builderState.connectMode) {
          clearBuilderConnectMode({ clearHover: true });
          setBuilderPageStatus("Connect mode cancelled.");
        }
        return;
      }
      const roomId = builderRoomKey(room.id || "");
      if (builderState.connectMode) {
        if (!builderState.connectFrom) {
          builderState.connectFrom = roomId;
          builderState.connectFromRoomId = roomId;
          setBuilderPageStatus(`Connect mode: source ${room.name || roomNameById(roomId)} selected. Click a target room.`);
          renderZoneMap();
          return;
        }
        if (roomId === builderRoomKey(builderState.connectFrom)) {
          clearBuilderConnectMode();
          setBuilderPageStatus("Connect mode cancelled.");
          return;
        }
        const fromId = builderRoomKey(builderState.connectFrom);
        clearBuilderConnectMode();
        void createExitBetweenRooms(fromId, roomId).catch((error) => {
          console.error(error);
          setBuilderPageStatus(error.message || "Unable to connect rooms.");
          toast(error.message || "Unable to connect rooms.");
        });
        return;
      }
      if (!roomId || roomId === builderRoomKey(builderState.currentRoomId)) {
        return;
      }
      void loadBuilderRoom(roomId).catch((error) => {
        console.error(error);
        setBuilderPageStatus(error.message || "Unable to load room.");
      });
    });

    zoneMap?.addEventListener("wheel", (event) => {
      event.preventDefault();
      const nextZoom = event.deltaY < 0 ? builderState.zoneZoom * 1.1 : builderState.zoneZoom / 1.1;
      builderState.zoneZoom = Math.min(Math.max(nextZoom, BUILDER_ZONE_MIN_ZOOM), BUILDER_ZONE_MAX_ZOOM);
      builderState.zoneZoomInitialized = true;
      builderState.zoneMapNeedsFit = false;
      saveZoneCamera();
      renderZoneMap();
    }, { passive: false });

    zoneMap?.addEventListener("pointerdown", (event) => {
      const room = builderRoomAtCanvasEvent(event, zoneMap, builderCanvasHitRadius());
      const roomId = builderRoomKey(room?.id || "");
      if (roomId && roomId === builderRoomKey(builderState.currentRoomId)) {
        const sourceRoom = builderRoomById(roomId) || builderState.currentRoom || room;
        builderState.zoneDrag = {
          mode: "room",
          pointerId: event.pointerId,
          startX: event.clientX,
          startY: event.clientY,
          roomId,
          roomMapX: Number(sourceRoom?.map_x ?? sourceRoom?.x ?? 0),
          roomMapY: Number(sourceRoom?.map_y ?? sourceRoom?.y ?? 0),
          moved: false,
        };
        try {
          zoneMap.setPointerCapture?.(event.pointerId);
        } catch (error) {
          console.debug("builder room drag pointer capture unavailable", error);
        }
        zoneMap.style.cursor = "grabbing";
        zoneMap.classList.add("is-dragging");
        event.preventDefault();
        return;
      }
      if (roomId) {
        return;
      }
      builderState.zoneDrag = {
        mode: "pan",
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        panX: builderState.zonePan.x,
        panY: builderState.zonePan.y,
      };
      try {
        zoneMap.setPointerCapture?.(event.pointerId);
      } catch (error) {
        console.debug("builder map pan pointer capture unavailable", error);
      }
      zoneMap.style.cursor = "grabbing";
      zoneMap.classList.add("is-dragging");
    });

    zoneMap?.addEventListener("pointermove", (event) => {
      if (!builderState.zoneDrag) {
        return;
      }
      if (builderState.zoneDrag.pointerId !== undefined && event.pointerId !== builderState.zoneDrag.pointerId) {
        return;
      }
      const deltaX = event.clientX - builderState.zoneDrag.startX;
      const deltaY = event.clientY - builderState.zoneDrag.startY;
      if (builderState.zoneDrag.mode === "room") {
        const nextMapX = Number(builderState.zoneDrag.roomMapX || 0) + (deltaX / Math.max(builderState.zoneZoom || 1, 0.0001));
        const nextMapY = Number(builderState.zoneDrag.roomMapY || 0) + (deltaY / Math.max(builderState.zoneZoom || 1, 0.0001));
        const roundedMapX = Math.round(nextMapX);
        const roundedMapY = Math.round(nextMapY);
        const currentMapX = Number(byId("room-map-x")?.value || builderState.currentRoom?.map_x || 0);
        const currentMapY = Number(byId("room-map-y")?.value || builderState.currentRoom?.map_y || 0);
        if (roundedMapX === currentMapX && roundedMapY === currentMapY) {
          return;
        }
        builderState.zoneDrag.moved = true;
        setBuilderRoomCoordinates(builderState.zoneDrag.roomId, roundedMapX, roundedMapY);
        renderZoneMap();
        return;
      }
      builderState.zonePan = {
        x: builderState.zoneDrag.panX + deltaX,
        y: builderState.zoneDrag.panY + deltaY,
      };
      builderState.zoneZoomInitialized = true;
      builderState.zoneMapNeedsFit = false;
      renderZoneMap();
    });

    ["pointerup", "pointerleave", "pointercancel"].forEach((eventName) => {
      zoneMap?.addEventListener(eventName, (event) => {
        if (!builderState.zoneDrag) {
          return;
        }
        const completedDrag = builderState.zoneDrag;
        if (completedDrag.pointerId !== undefined && event.pointerId !== undefined && event.pointerId !== completedDrag.pointerId) {
          return;
        }
        builderState.zoneDrag = null;
        zoneMap.classList.remove("is-dragging");
        try {
          zoneMap.releasePointerCapture?.(completedDrag.pointerId);
        } catch (error) {
          console.debug("builder drag pointer release unavailable", error);
        }
        if (completedDrag.mode === "room" && completedDrag.moved) {
          void persistBuilderRoomCoordinates(
            completedDrag.roomId,
            Number(byId("room-map-x")?.value || 0),
            Number(byId("room-map-y")?.value || 0)
          ).catch((error) => {
            console.error(error);
            setBuilderPageStatus(error.message || "Unable to save room position.");
            toast(error.message || "Unable to save room position.");
          });
        }
        zoneMap.style.cursor = builderState.hoveredRoomId ? "pointer" : "grab";
        saveZoneCamera();
      });
    });

    byId("builder-map-fit-toggle")?.addEventListener("click", () => {
      if (builderUsesReactFlow()) {
        queueBuilderReactFlowViewport("fit");
        return;
      }
      builderState.zoneForceFitOnce = true;
      builderState.zoneZoomInitialized = false;
      builderState.zoneMapNeedsFit = true;
      renderZoneMap();
    });

    byId("builder-map-center-toggle")?.addEventListener("click", () => {
      if (builderUsesReactFlow()) {
        queueBuilderReactFlowViewport("center");
        return;
      }
      if (builderState.currentRoomId) {
        centerZoneMapOnRoom(builderState.currentRoomId);
      }
    });

    byId("builder-connect-toggle")?.addEventListener("click", () => {
      if (!builderState.connectMode) {
        beginBuilderConnectMode();
        return;
      }
      clearBuilderConnectMode({ clearHover: true });
      setBuilderPageStatus("Connect mode cancelled.");
    });

    byId("builder-map-fullscreen-toggle")?.addEventListener("click", () => {
      const panel = builderMapPanel();
      panel?.classList.toggle("fullscreen");
      renderZoneMap();
    });
  }

  function initBuilderPage() {
    bindBuilderInputs();
    syncBuilderZoneMenus();
    renderBuilderExitList([]);
    renderBuilderPreview({
      name: "No room selected",
      desc: "Choose a room from the list to inspect and edit it.",
      environment: "city",
      exits: [],
    });
    renderZoneMap();
    initializeBuilderData().catch((error) => {
      console.error(error);
      setBuilderPageStatus(error.message || "Unable to load builder rooms.");
    });
    window.addEventListener("resize", () => {
      builderState.zoneMapNeedsFit = true;
      builderState.zoneZoomInitialized = false;
      window.requestAnimationFrame(() => renderZoneMap());
    });
  }

  function getCanvasPoint(event, canvas) {
    if (!event || !canvas) {
      return { x: 0, y: 0 };
    }
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || canvas.width || 1;
    const height = rect.height || canvas.height || 1;
    return {
      x: ((event.clientX - rect.left) / width) * canvas.width,
      y: ((event.clientY - rect.top) / height) * canvas.height,
    };
  }

  function builderZoneRequestId(zoneId) {
    const normalizedZoneId = normalizeBuilderZoneId(zoneId);
    return normalizedZoneId || BUILDER_UNASSIGNED_ZONE_VALUE;
  }

  function builderRoomAtCanvasEvent(event, canvas, radius = 12) {
    return findRenderedRoomAtPoint(
      getCanvasPoint(event, canvas),
      builderState.zoneRoomPositions || new Map(),
      builderState.zone?.rooms || [],
      radius
    );
  }

  function builderCanvasHitRadius() {
    return builderState.connectMode ? 24 : 18;
  }

  function findRenderedRoomAtPoint(point, positions, rooms, radius = 8) {
    let found = null;
    let bestDistanceSquared = Infinity;
    const radiusSquared = radius * radius;

    for (const room of rooms || []) {
      const pos = positions.get(room.id);
      if (!pos) {
        continue;
      }
      const dx = point.x - pos.x;
      const dy = point.y - pos.y;
      const distanceSquared = dx * dx + dy * dy;
      if (distanceSquared <= radiusSquared && distanceSquared < bestDistanceSquared) {
        found = room;
        bestDistanceSquared = distanceSquared;
      }
    }

    return found;
  }

  function sceneImageCatalog(preferredFileName) {
    const catalog = Array.from(new Set(Object.values(ROOM_IMAGE_LIBRARY)));
    if (!preferredFileName) {
      return catalog;
    }
    return [preferredFileName].concat(catalog.filter((fileName) => fileName !== preferredFileName));
  }

  function currentSceneRoom() {
    return roomById(state.map.player_room_id);
  }

  function resolveRoomImage(currentRoom) {
    if (!currentRoom) {
      return {
        src: staticRoomImageUrl(ROOM_IMAGE_LIBRARY.fallback),
        caption: "Dragonsire",
        rotationKey: "fallback",
        images: sceneImageCatalog(ROOM_IMAGE_LIBRARY.fallback),
      };
    }

    if (currentRoom.image_key) {
      const fileName = String(currentRoom.image_key);
      return {
        src: fileName.startsWith("/")
          ? fileName
          : staticRoomImageUrl(fileName),
        caption: currentRoom.name || "Dragonsire",
        rotationKey: `explicit:${fileName}`,
        images: [fileName],
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
    const preferredFileName = matched ? matched[1] : ROOM_IMAGE_LIBRARY.fallback;
    return {
      src: staticRoomImageUrl(preferredFileName),
      caption: currentRoom.name || String(state.map.zone || "Dragonsire"),
      rotationKey: `${currentRoom.id || currentRoom.name || "room"}:${preferredFileName}`,
      images: sceneImageCatalog(preferredFileName),
    };
  }

  function updateSceneImage(currentRoom) {
    const sceneImage = byId("scene-image");
    if (!sceneImage) return;
    const resolved = resolveRoomImage(currentRoom);
    if (state.sceneRotation.key !== resolved.rotationKey) {
      state.sceneRotation.key = resolved.rotationKey;
      state.sceneRotation.index = 0;
    }
    const images = Array.isArray(resolved.images) && resolved.images.length ? resolved.images : [ROOM_IMAGE_LIBRARY.fallback];
    const fileName = images[state.sceneRotation.index % images.length];
    const imageUrl = fileName.startsWith("/") ? fileName : staticRoomImageUrl(fileName);
    sceneImage.style.backgroundImage = `linear-gradient(180deg, rgba(15, 11, 8, 0.08), rgba(15, 11, 8, 0.35)), url("${imageUrl}")`;
    sceneImage.dataset.caption = resolved.caption || "";
    sceneImage.setAttribute("aria-label", resolved.caption || "Room illustration");
    sceneImage.title = resolved.caption || "";
  }

  function advanceSceneImageRotation() {
    const currentRoom = currentSceneRoom();
    const resolved = resolveRoomImage(currentRoom);
    const images = Array.isArray(resolved.images) ? resolved.images : [];
    if (images.length <= 1) {
      updateSceneImage(currentRoom);
      return;
    }
    if (state.sceneRotation.key !== resolved.rotationKey) {
      state.sceneRotation.key = resolved.rotationKey;
      state.sceneRotation.index = 0;
    } else {
      state.sceneRotation.index = (state.sceneRotation.index + 1) % images.length;
    }
    updateSceneImage(currentRoom);
  }

  function startSceneImageRotation() {
    if (state.sceneRotation.timer) {
      return;
    }
    state.sceneRotation.timer = window.setInterval(() => {
      advanceSceneImageRotation();
    }, SCENE_IMAGE_ROTATION_MS);
  }

  function updateWindowFitShell() {
    const modePlay = byId("mode-play");
    if (!modePlay) {
      return;
    }

    if (state.mode !== "play") {
      modePlay.removeAttribute("data-shell-fit");
      modePlay.style.setProperty("--window-shell-scale", "1");
      modePlay.style.setProperty("--window-shell-unscale", "1");
      return;
    }

    const availableWidth = Math.max(window.innerWidth - 24, 0);
    const availableHeight = Math.max(window.innerHeight - 24, 0);

    if (availableWidth < 1100) {
      modePlay.removeAttribute("data-shell-fit");
      modePlay.style.setProperty("--window-shell-scale", "1");
      modePlay.style.setProperty("--window-shell-unscale", "1");
      return;
    }

    const widthScale = availableWidth / DESKTOP_SHELL_FIT_WIDTH;
    const heightScale = availableHeight / DESKTOP_SHELL_FIT_HEIGHT;
    const scale = Math.min(widthScale, heightScale, 1);

    if (scale >= 0.995) {
      modePlay.removeAttribute("data-shell-fit");
      modePlay.style.setProperty("--window-shell-scale", "1");
      modePlay.style.setProperty("--window-shell-unscale", "1");
      return;
    }

    const appliedScale = Math.max(scale, 0.68);
    modePlay.dataset.shellFit = "scaled";
    modePlay.style.setProperty("--window-shell-scale", String(appliedScale));
    modePlay.style.setProperty("--window-shell-unscale", String(1 / appliedScale));
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
    updateWindowFitShell();
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

  function mapBoundsForRooms(rooms) {
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

  function mapBounds() {
    return mapBoundsForRooms(state.map.rooms || []);
  }

  function mapRoomRadiusForHover(room, compactMap, hoveredRoomId = state.hoveredRoomId) {
    if (isPlayerRoom(room)) {
      return compactMap ? 9 : 6;
    }
    if (room.id === hoveredRoomId) {
      return compactMap ? 6 : 4;
    }
    return compactMap ? 5 : 3;
  }

  function mapRoomRadius(room, compactMap) {
    return mapRoomRadiusForHover(room, compactMap, state.hoveredRoomId);
  }

  function renderedMapBoundsForRooms(canvas, rooms, scale, hoveredRoomId = state.hoveredRoomId) {
    if (!canvas || !rooms.length) {
      return { minX: 0, maxX: 1, minY: 0, maxY: 1, width: 1, height: 1 };
    }

    const compactMap = rooms.length > 0 && rooms.length <= 16;
    const ctx = canvas.getContext("2d");
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;

    for (const room of rooms) {
      const roomX = (Number(room.x) || 0) * scale;
      const roomY = (Number(room.y) || 0) * scale;
      const radius = mapRoomRadiusForHover(room, compactMap, hoveredRoomId);
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

  function renderedMapBounds(canvas, scale) {
    return renderedMapBoundsForRooms(canvas, state.map.rooms || [], scale, state.hoveredRoomId);
  }

  function fitRoomsToCanvas(canvas, rooms, minScale = 0.12) {
    const padding = 24;
    const usableWidth = Math.max(40, canvas.width - padding * 2);
    const usableHeight = Math.max(40, canvas.height - padding * 2);
    const rawBounds = mapBoundsForRooms(rooms);
    let nextScale = Math.min(
      BUILDER_ZONE_MAX_ZOOM,
      Math.max(minScale, Math.min(usableWidth / rawBounds.width, usableHeight / rawBounds.height)),
    );

    for (let attempt = 0; attempt < 4; attempt += 1) {
      const bounds = renderedMapBoundsForRooms(canvas, rooms, nextScale, null);
      const scaleFactor = Math.min(usableWidth / bounds.width, usableHeight / bounds.height);
      if (!Number.isFinite(scaleFactor) || scaleFactor <= 0) {
        break;
      }
      const adjustedScale = Math.min(BUILDER_ZONE_MAX_ZOOM, Math.max(minScale, nextScale * scaleFactor));
      if (Math.abs(adjustedScale - nextScale) < 0.01) {
        nextScale = adjustedScale;
        break;
      }
      nextScale = adjustedScale;
    }

    const bounds = renderedMapBoundsForRooms(canvas, rooms, nextScale, null);
    return {
      scale: nextScale,
      offset: {
        x: padding + (usableWidth - bounds.width) / 2 - bounds.minX,
        y: padding + (usableHeight - bounds.height) / 2 - bounds.minY,
      },
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
    const fitted = fitRoomsToCanvas(canvas, state.map.rooms || [], 0.12);
    state.mapScale = fitted.scale;
    state.mapOffset.x = fitted.offset.x;
    state.mapOffset.y = fitted.offset.y;
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

  function debugMapSnapshot(label, rooms, edges, transform, options = {}) {
    const snapshot = {
      roomCount: rooms.length,
      edgeCount: edges.length,
      sampleRoomIds: rooms.slice(0, 20).map((room) => room.id),
      sampleRooms: rooms.slice(0, 20).map((room) => ({
        id: room.id,
        x: room.x ?? room.map_x ?? 0,
        y: room.y ?? room.map_y ?? 0,
      })),
      selectedRoomId: transform.selectedRoomId ?? null,
      renderedBounds: transform.renderedBounds || null,
      transform,
    };

    if (options.positions) {
      snapshot.sampleScreenPositions = rooms.slice(0, 20).map((room) => {
        const position = options.positions.get(room.id);
        return {
          id: room.id,
          x: position ? Number(position.x.toFixed(2)) : null,
          y: position ? Number(position.y.toFixed(2)) : null,
        };
      });
    }

    window.__dragonsireMapDebug = window.__dragonsireMapDebug || {};
    window.__dragonsireMapDebug[label] = snapshot;
    console.log(label, snapshot);
    return snapshot;
  }

  function drawCanvasMap(canvas, rooms, edges, options = {}) {
    if (!canvas || !Array.isArray(rooms)) {
      return new Map();
    }
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const positions = new Map();
    const getPosition = options.getPosition || ((room) => ({ x: 0, y: 0 }));
    const getColor = options.getColor || (() => "#5f8f57");
    const getRadius = options.getRadius || (() => 4);
    const linkedRoomIds = options.linkedRoomIds || new Set();
    const hoveredRoomId = options.hoveredRoomId;
    const selectedRoomId = options.selectedRoomId;
    const showLabels = Boolean(options.showLabels);
    const drawEdge = options.drawEdge || ((drawCtx, from, to) => {
      drawCtx.beginPath();
      drawCtx.moveTo(from.x, from.y);
      drawCtx.lineTo(to.x, to.y);
      drawCtx.stroke();
    });

    rooms.forEach((room) => {
      positions.set(room.id, getPosition(room));
    });

    (edges || []).forEach((edge) => {
      const from = positions.get(edge.from);
      const to = positions.get(edge.to);
      if (!from || !to) return;
      ctx.strokeStyle = options.edgeColor ? options.edgeColor(edge) : "rgba(195, 164, 104, 0.6)";
      ctx.lineWidth = options.edgeWidth ? options.edgeWidth(edge) : 1.5;
      drawEdge(ctx, from, to, edge);
    });

    rooms.forEach((room) => {
      const pos = positions.get(room.id);
      const radius = getRadius(room);
      const selected = room.id === selectedRoomId;
      const linked = linkedRoomIds.has(room.id);
      if (room.id === hoveredRoomId) {
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 5, 0, Math.PI * 2);
        ctx.fill();
      }
      if (selected) {
        ctx.strokeStyle = "rgba(255, 240, 200, 0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = linked ? "#69b8ff" : getColor(room);
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fill();

      if (showLabels) {
        ctx.fillStyle = selected ? "rgba(255, 245, 220, 0.96)" : "rgba(230, 219, 194, 0.88)";
        ctx.font = selected ? "600 12px Georgia" : "11px Georgia";
        ctx.textAlign = "center";
        ctx.textBaseline = "bottom";
        ctx.fillText(room.name, pos.x, pos.y - (radius + 8));
      }
    });

    return positions;
  }

  function assertSpatialRooms(mode, rooms) {
    if (mode === "builder") {
      console.log("BUILDER ROOMS:", rooms.length);
      console.log("BUILDER SAMPLE:", rooms[0] || null);
    }
    for (const room of rooms || []) {
      const roomX = Number(room.x ?? room.map_x);
      const roomY = Number(room.y ?? room.map_y);
      if (!Number.isFinite(roomX) || !Number.isFinite(roomY)) {
        console.error("Missing coords", { mode, room });
      }
    }
  }

  function renderZoneCanvasMap({
    canvas,
    rooms,
    edges,
    mode = "play",
    scale = 1,
    getPosition,
    getColor,
    getRadius,
    hoveredRoomId = null,
    selectedRoomId = null,
    showLabels = false,
    edgeColor,
    edgeWidth,
    linkedRoomIds,
    drawEdge,
    debugTransform = {},
  } = {}) {
    assertSpatialRooms(mode, rooms);
    const renderedBounds = renderedMapBoundsForRooms(
      canvas,
      rooms,
      Number(scale || 1),
      hoveredRoomId ?? null
    );
    const positions = drawCanvasMap(canvas, rooms, edges, {
      getPosition,
      getColor,
      getRadius,
      hoveredRoomId,
      selectedRoomId,
      showLabels,
      edgeColor,
      edgeWidth,
      linkedRoomIds,
      drawEdge,
    });
    debugMapSnapshot(mode, rooms, edges, {
      ...debugTransform,
      selectedRoomId,
      renderedBounds,
      canvas: { width: canvas.width, height: canvas.height },
    }, {
      positions,
    });
    return { positions, renderedBounds };
  }

  window.renderZoneCanvasMap = renderZoneCanvasMap;

  function renderPlayerMapCanvas(canvas) {
    const compactMap = isCompactMap();
    const rooms = state.map.rooms || [];
    const edges = mapEdges();
    const rendered = renderZoneCanvasMap({
      canvas,
      rooms,
      edges,
      mode: "play",
      scale: state.mapScale,
      getPosition: (room) => worldPosition(room, canvas),
      getColor: (room) => roomColor(room),
      getRadius: (room) => mapRoomRadius(room, compactMap),
      hoveredRoomId: state.hoveredRoomId,
      selectedRoomId: state.map.player_room_id,
      showLabels: compactMap,
      edgeColor: () => compactMap ? "rgba(220, 188, 120, 0.82)" : "rgba(195, 164, 104, 0.6)",
      edgeWidth: () => compactMap ? 2.4 : 1.5,
      debugTransform: {
        scale: state.mapScale,
        offset: state.mapOffset,
      },
    });
    state.roomPositions = rendered.positions;
  }

  function renderMap() {
    const canvas = byId("map-canvas");
    if (!canvas) return;
    resizeMapCanvas();
    fitMapToCanvas();

    if (!state.map || !Array.isArray(state.map.rooms)) {
      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    renderPlayerMapCanvas(canvas);

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
    return roomAtPosition(x, y, state.map.rooms || [], state.roomPositions, 12);
  }

  function roomAtPosition(x, y, rooms, positions, radius = 12) {
    return findRenderedRoomAtPoint({ x, y }, positions, rooms, radius);
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
      updateWindowFitShell();
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
    if (hasInitialized) {
      return;
    }
    hasInitialized = true;

    if (isBuilderPage()) {
      initBuilderPage();
      return;
    }

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
    startSceneImageRotation();
    updateWindowFitShell();
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
  }
  window.addEventListener("load", init);
})();
