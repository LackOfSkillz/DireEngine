import type { BuilderDirection, BuilderHandleId, RoomColor, RoomNode } from "./BuilderTypes";

export const BUILDER_DIRECTIONS: BuilderDirection[] = [
  "north",
  "east",
  "south",
  "west",
  "northeast",
  "northwest",
  "southeast",
  "southwest",
  "up",
  "down",
];

export const LOGICAL_CELL_SIZE = 96;
export const GRID_SIZE = 50;
export const ROOM_NODE_SIZE = 72;
export const ROOM_BODY_SIZE = 40;
export const ROOM_BODY_OFFSET = (ROOM_NODE_SIZE - ROOM_BODY_SIZE) / 2;
export const NODE_SPACING_MULTIPLIER = 1.2;
export const RENDER_GRID_SCALE = (LOGICAL_CELL_SIZE / GRID_SIZE) * NODE_SPACING_MULTIPLIER;
export const ROOM_COLORS: Record<RoomColor, string> = {
  standard: "#888888",
  poi: "#00FF00",
  shop: "#FF0000",
  training: "#FFFF00",
  portal: "#FF00FF",
  home: "#00FFFF",
  water: "#0000FF",
  underwater: "#000088",
};
export const CORRIDOR_SPACING = 60;
export const HUB_RADIUS = 80;
export const CLUSTER_RADIUS = 80;
export const CLUSTER_THRESHOLD = 6;
export const MAX_LAYOUT_MOVE = 100;
export const CORRIDOR_ENDPOINT_LIMIT = 25;
export const CROSSING_PASSES = 10;
export const FINAL_SOFT_PUSH_DISTANCE = 44;

export const OPPOSITE: Record<BuilderDirection, BuilderDirection> = {
  north: "south",
  south: "north",
  east: "west",
  west: "east",
  northeast: "southwest",
  southwest: "northeast",
  northwest: "southeast",
  southeast: "northwest",
  up: "down",
  down: "up",
};

export const DIRECTION_TO_HANDLE_ID: Record<BuilderDirection, BuilderHandleId> = {
  north: "n",
  east: "e",
  south: "s",
  west: "w",
  northeast: "ne",
  northwest: "nw",
  southeast: "se",
  southwest: "sw",
  up: "u",
  down: "d",
};

export const HANDLE_ID_TO_DIRECTION: Record<BuilderHandleId, BuilderDirection> = {
  n: "north",
  e: "east",
  s: "south",
  w: "west",
  ne: "northeast",
  nw: "northwest",
  se: "southeast",
  sw: "southwest",
  u: "up",
  d: "down",
};

export type CanvasPoint = {
  x: number;
  y: number;
};

export type GraphRoomLike = {
  id: string;
  x: number;
  y: number;
  exits?: Partial<Record<BuilderDirection, string>>;
  meta?: RoomNode["meta"];
};

export type GraphRenderMeta = {
  isCorridor: boolean;
  isHub: boolean;
  locked: boolean;
};

type CorridorOrientation = "horizontal" | "vertical" | "diagonal";

type CorridorChain = {
  roomIds: string[];
  orientation: CorridorOrientation;
};

export type GraphRenderTransform = {
  centerX: number;
  centerY: number;
  scale: number;
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  width: number;
  height: number;
  positionsByRoomId: Record<string, CanvasPoint>;
  metaByRoomId: Record<string, GraphRenderMeta>;
};

type GraphRenderTransformOptions = {
  tidy?: boolean;
};

export function coordKey(x: number, y: number): string {
  return `${x},${y}`;
}

export function buildRoomId(zonePrefix: string, x: number, y: number): string {
  void zonePrefix;
  return `CRO_${x}_${y}`;
}

export function oppositeDirection(direction: BuilderDirection): BuilderDirection | null {
  return OPPOSITE[direction] || null;
}

export function directionToHandleId(direction: BuilderDirection): BuilderHandleId {
  return DIRECTION_TO_HANDLE_ID[direction];
}

export function handleIdToDirection(handleId: string): BuilderDirection | null {
  return HANDLE_ID_TO_DIRECTION[handleId as BuilderHandleId] || null;
}

function normalizeDirectionLike(value: string): BuilderDirection | null {
  if (isBuilderDirection(value)) {
    return value;
  }
  return handleIdToDirection(value);
}

export function isValidPair(a: string, b: string): boolean {
  const left = normalizeDirectionLike(a);
  const right = normalizeDirectionLike(b);
  if (!left || !right) {
    return false;
  }
  return oppositeDirection(left) === right;
}

export function edgeKey(fromRoomId: string, direction: BuilderDirection): string {
  return `${fromRoomId}:${direction}`;
}

export function isBuilderDirection(value: string): value is BuilderDirection {
  return BUILDER_DIRECTIONS.includes(value as BuilderDirection);
}

export function isRoomColor(value: string): value is RoomColor {
  return Object.prototype.hasOwnProperty.call(ROOM_COLORS, String(value || ""));
}

export function logicalToCanvas(x: number, y: number): CanvasPoint {
  return {
    x,
    y,
  };
}

export function canvasToLogical(x: number, y: number): CanvasPoint {
  return {
    x: Math.round(x / GRID_SIZE) * GRID_SIZE,
    y: Math.round(y / GRID_SIZE) * GRID_SIZE,
  };
}

export function buildGraphRenderTransform(
  rooms: GraphRoomLike[],
  canvasWidth: number,
  canvasHeight: number,
  options: GraphRenderTransformOptions = {},
): GraphRenderTransform {
  void canvasWidth;
  void canvasHeight;
  if (!rooms.length) {
    return {
      centerX: 0,
      centerY: 0,
      scale: 1,
      minX: 0,
      maxX: 0,
      minY: 0,
      maxY: 0,
      width: 1,
      height: 1,
      positionsByRoomId: {},
      metaByRoomId: {},
    };
  }

  const minX = Math.min(...rooms.map((room) => room.x));
  const maxX = Math.max(...rooms.map((room) => room.x));
  const minY = Math.min(...rooms.map((room) => room.y));
  const maxY = Math.max(...rooms.map((room) => room.y));
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const width = Math.max(maxX - minX, GRID_SIZE);
  const height = Math.max(maxY - minY, GRID_SIZE);
  const scale = RENDER_GRID_SCALE;

  const positionsByRoomId = rooms.reduce<Record<string, CanvasPoint>>((accumulator, room) => {
    accumulator[room.id] = {
      x: (room.x - centerX) * scale,
      y: (room.y - centerY) * scale,
    };
    return accumulator;
  }, {});
  const metaByRoomId = rooms.reduce<Record<string, GraphRenderMeta>>((accumulator, room) => {
    accumulator[room.id] = {
      isCorridor: false,
      isHub: false,
      locked: Boolean(room.meta?.locked),
    };
    return accumulator;
  }, {});

  if (options.tidy) {
    applyTidyLayout(rooms, positionsByRoomId, metaByRoomId);
  }

  return {
    centerX,
    centerY,
    scale,
    minX,
    maxX,
    minY,
    maxY,
    width,
    height,
    positionsByRoomId,
    metaByRoomId,
  };
}

function applyTidyLayout(
  rooms: GraphRoomLike[],
  positionsByRoomId: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  const roomsById = rooms.reduce<Record<string, GraphRoomLike>>((accumulator, room) => {
    accumulator[room.id] = room;
    return accumulator;
  }, {});
  const originalPositions = clonePositions(positionsByRoomId);
  const corridorIds = detectCorridorNodes(rooms, roomsById, metaByRoomId);
  const chains = groupCorridorChains(corridorIds, roomsById, metaByRoomId);

  for (const chain of chains) {
    straightenCorridorChain(chain, positionsByRoomId, originalPositions, metaByRoomId);
    distributeCorridorChain(chain, positionsByRoomId, originalPositions, metaByRoomId);
  }

  const hubIds = detectHubNodes(rooms, roomsById, metaByRoomId);
  spreadHubNeighbors(hubIds, roomsById, positionsByRoomId, originalPositions, metaByRoomId);
  expandDenseClusters(rooms, positionsByRoomId, metaByRoomId);
  snapAlignedLines(positionsByRoomId, metaByRoomId, "horizontal");
  snapAlignedLines(positionsByRoomId, metaByRoomId, "vertical");
  reduceEdgeCrossings(roomsById, positionsByRoomId, originalPositions, metaByRoomId);
  applyFinalSoftPush(positionsByRoomId, metaByRoomId);
  clampMovement(positionsByRoomId, originalPositions, MAX_LAYOUT_MOVE);
}

function clonePositions(positionsByRoomId: Record<string, CanvasPoint>): Record<string, CanvasPoint> {
  return Object.entries(positionsByRoomId).reduce<Record<string, CanvasPoint>>((accumulator, [roomId, point]) => {
    accumulator[roomId] = { x: point.x, y: point.y };
    return accumulator;
  }, {});
}

function getConnectedDirections(room: GraphRoomLike, roomsById: Record<string, GraphRoomLike>): BuilderDirection[] {
  return Object.entries(room.exits || {})
    .filter(([direction, targetRoomId]) => isBuilderDirection(direction) && Boolean(targetRoomId) && Boolean(roomsById[String(targetRoomId || "")]))
    .map(([direction]) => direction as BuilderDirection);
}

function directionAxis(direction: BuilderDirection): CorridorOrientation | null {
  if (direction === "east" || direction === "west") {
    return "horizontal";
  }
  if (direction === "north" || direction === "south") {
    return "vertical";
  }
  if (direction === "northeast" || direction === "northwest" || direction === "southeast" || direction === "southwest") {
    return "diagonal";
  }
  return null;
}

function isCorridorPair(first: BuilderDirection, second: BuilderDirection): boolean {
  return (
    (first === "north" && second === "south")
    || (first === "south" && second === "north")
    || (first === "east" && second === "west")
    || (first === "west" && second === "east")
    || (first === "northeast" && second === "southwest")
    || (first === "southwest" && second === "northeast")
    || (first === "northwest" && second === "southeast")
    || (first === "southeast" && second === "northwest")
  );
}

function detectCorridorNodes(
  rooms: GraphRoomLike[],
  roomsById: Record<string, GraphRoomLike>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): Set<string> {
  const corridorIds = new Set<string>();
  for (const room of rooms) {
    const exits = getConnectedDirections(room, roomsById);
    if (exits.length === 2 && isCorridorPair(exits[0], exits[1])) {
      corridorIds.add(room.id);
      metaByRoomId[room.id].isCorridor = true;
    }
  }
  return corridorIds;
}

function groupCorridorChains(
  corridorIds: Set<string>,
  roomsById: Record<string, GraphRoomLike>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): CorridorChain[] {
  const visited = new Set<string>();
  const chains: CorridorChain[] = [];

  for (const roomId of corridorIds) {
    if (visited.has(roomId)) {
      continue;
    }

    const queue = [roomId];
    const chainRoomIds: string[] = [];
    visited.add(roomId);

    while (queue.length) {
      const currentRoomId = queue.shift() || "";
      const room = roomsById[currentRoomId];
      if (!room) {
        continue;
      }
      chainRoomIds.push(currentRoomId);
      for (const targetRoomId of Object.values(room.exits || {})) {
        const normalizedTargetRoomId = String(targetRoomId || "");
        if (!corridorIds.has(normalizedTargetRoomId) || visited.has(normalizedTargetRoomId)) {
          continue;
        }
        visited.add(normalizedTargetRoomId);
        queue.push(normalizedTargetRoomId);
      }
    }

    if (chainRoomIds.length) {
      chains.push({
        roomIds: chainRoomIds,
        orientation: detectCorridorOrientation(chainRoomIds, roomsById),
      });
    }
  }

  return chains;
}

function detectCorridorOrientation(roomIds: string[], roomsById: Record<string, GraphRoomLike>): CorridorOrientation {
  let horizontal = 0;
  let vertical = 0;
  let diagonal = 0;

  for (const roomId of roomIds) {
    const room = roomsById[roomId];
    if (!room) {
      continue;
    }
    for (const direction of getConnectedDirections(room, roomsById)) {
      const axis = directionAxis(direction);
      if (axis === "horizontal") {
        horizontal += 1;
      } else if (axis === "vertical") {
        vertical += 1;
      } else if (axis === "diagonal") {
        diagonal += 1;
      }
    }
  }

  if (horizontal >= vertical && horizontal >= diagonal) {
    return "horizontal";
  }
  if (vertical >= horizontal && vertical >= diagonal) {
    return "vertical";
  }
  return "diagonal";
}

function straightenCorridorChain(
  chain: CorridorChain,
  positionsByRoomId: Record<string, CanvasPoint>,
  originalPositions: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  if (chain.roomIds.length < 2) {
    return;
  }

  const orderedIds = orderChainAlongAxis(chain, positionsByRoomId);
  const movableIds = orderedIds.filter((roomId) => !metaByRoomId[roomId]?.locked);
  if (!movableIds.length) {
    return;
  }

  if (chain.orientation === "horizontal") {
    const averageY = average(movableIds.map((roomId) => positionsByRoomId[roomId].y));
    orderedIds.forEach((roomId, index) => {
      if (metaByRoomId[roomId]?.locked) {
        return;
      }
      const limit = index === 0 || index === orderedIds.length - 1 ? CORRIDOR_ENDPOINT_LIMIT : MAX_LAYOUT_MOVE;
      positionsByRoomId[roomId].y = clampWithinLimit(originalPositions[roomId].y, averageY, limit);
    });
    return;
  }

  if (chain.orientation === "vertical") {
    const averageX = average(movableIds.map((roomId) => positionsByRoomId[roomId].x));
    orderedIds.forEach((roomId, index) => {
      if (metaByRoomId[roomId]?.locked) {
        return;
      }
      const limit = index === 0 || index === orderedIds.length - 1 ? CORRIDOR_ENDPOINT_LIMIT : MAX_LAYOUT_MOVE;
      positionsByRoomId[roomId].x = clampWithinLimit(originalPositions[roomId].x, averageX, limit);
    });
    return;
  }

  const slope = diagonalSlope(orderedIds, originalPositions);
  const intercept = average(movableIds.map((roomId) => positionsByRoomId[roomId].y - slope * positionsByRoomId[roomId].x));
  orderedIds.forEach((roomId, index) => {
    if (metaByRoomId[roomId]?.locked) {
      return;
    }
    const targetY = slope * positionsByRoomId[roomId].x + intercept;
    const limit = index === 0 || index === orderedIds.length - 1 ? CORRIDOR_ENDPOINT_LIMIT : MAX_LAYOUT_MOVE;
    positionsByRoomId[roomId].y = clampWithinLimit(originalPositions[roomId].y, targetY, limit);
  });
}

function distributeCorridorChain(
  chain: CorridorChain,
  positionsByRoomId: Record<string, CanvasPoint>,
  originalPositions: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  if (chain.roomIds.length < 3) {
    return;
  }

  const orderedIds = orderChainAlongAxis(chain, positionsByRoomId);
  if (!orderedIds.length) {
    return;
  }

  if (chain.orientation === "horizontal") {
    distributeAlongAxis(orderedIds, positionsByRoomId, originalPositions, metaByRoomId, "x", CORRIDOR_SPACING);
    return;
  }
  if (chain.orientation === "vertical") {
    distributeAlongAxis(orderedIds, positionsByRoomId, originalPositions, metaByRoomId, "y", CORRIDOR_SPACING);
    return;
  }

  const centerX = average(orderedIds.map((roomId) => positionsByRoomId[roomId].x));
  const startX = centerX - ((orderedIds.length - 1) * (CORRIDOR_SPACING / Math.sqrt(2))) / 2;
  const slope = diagonalSlope(orderedIds, originalPositions);
  const intercept = average(orderedIds.map((roomId) => positionsByRoomId[roomId].y - slope * positionsByRoomId[roomId].x));
  orderedIds.forEach((roomId, index) => {
    if (metaByRoomId[roomId]?.locked) {
      return;
    }
    const targetX = startX + index * (CORRIDOR_SPACING / Math.sqrt(2));
    const targetY = slope * targetX + intercept;
    const limit = index === 0 || index === orderedIds.length - 1 ? CORRIDOR_ENDPOINT_LIMIT : MAX_LAYOUT_MOVE;
    positionsByRoomId[roomId].x = clampWithinLimit(originalPositions[roomId].x, targetX, limit);
    positionsByRoomId[roomId].y = clampWithinLimit(originalPositions[roomId].y, targetY, limit);
  });
}

function orderChainAlongAxis(chain: CorridorChain, positionsByRoomId: Record<string, CanvasPoint>): string[] {
  return [...chain.roomIds].sort((left, right) => {
    const leftPoint = positionsByRoomId[left] || { x: 0, y: 0 };
    const rightPoint = positionsByRoomId[right] || { x: 0, y: 0 };
    if (chain.orientation === "vertical") {
      return leftPoint.y - rightPoint.y;
    }
    return leftPoint.x - rightPoint.x;
  });
}

function distributeAlongAxis(
  orderedIds: string[],
  positionsByRoomId: Record<string, CanvasPoint>,
  originalPositions: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
  axis: "x" | "y",
  spacing: number,
): void {
  const center = average(orderedIds.map((roomId) => positionsByRoomId[roomId][axis]));
  const start = center - ((orderedIds.length - 1) * spacing) / 2;
  orderedIds.forEach((roomId, index) => {
    if (metaByRoomId[roomId]?.locked) {
      return;
    }
    const limit = index === 0 || index === orderedIds.length - 1 ? CORRIDOR_ENDPOINT_LIMIT : MAX_LAYOUT_MOVE;
    positionsByRoomId[roomId][axis] = clampWithinLimit(originalPositions[roomId][axis], start + index * spacing, limit);
  });
}

function detectHubNodes(
  rooms: GraphRoomLike[],
  roomsById: Record<string, GraphRoomLike>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): string[] {
  const hubIds: string[] = [];
  for (const room of rooms) {
    if (getConnectedDirections(room, roomsById).length >= 3) {
      metaByRoomId[room.id].isHub = true;
      hubIds.push(room.id);
    }
  }
  return hubIds;
}

function spreadHubNeighbors(
  hubIds: string[],
  roomsById: Record<string, GraphRoomLike>,
  positionsByRoomId: Record<string, CanvasPoint>,
  originalPositions: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  for (const hubId of hubIds) {
    const hub = roomsById[hubId];
    const hubPoint = positionsByRoomId[hubId];
    if (!hub || !hubPoint) {
      continue;
    }

    const neighbors = Object.entries(hub.exits || {})
      .filter(([direction, targetRoomId]) => isBuilderDirection(direction) && Boolean(targetRoomId) && Boolean(positionsByRoomId[String(targetRoomId || "")]))
      .map(([direction, targetRoomId]) => ({ direction: direction as BuilderDirection, roomId: String(targetRoomId || "") }));

    const fallbackStep = neighbors.length ? (Math.PI * 2) / neighbors.length : 0;
    neighbors.forEach(({ direction, roomId }, index) => {
      if (metaByRoomId[roomId]?.locked) {
        return;
      }
      const angle = directionAngle(direction) ?? index * fallbackStep;
      const targetX = hubPoint.x + Math.cos(angle) * HUB_RADIUS;
      const targetY = hubPoint.y + Math.sin(angle) * HUB_RADIUS;
      const adjusted = enforceDirectionalIntent(direction, hubPoint, { x: targetX, y: targetY });
      positionsByRoomId[roomId].x = clampWithinLimit(originalPositions[roomId].x, adjusted.x, MAX_LAYOUT_MOVE);
      positionsByRoomId[roomId].y = clampWithinLimit(originalPositions[roomId].y, adjusted.y, MAX_LAYOUT_MOVE);
    });
  }
}

function expandDenseClusters(
  rooms: GraphRoomLike[],
  positionsByRoomId: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  for (const room of rooms) {
    const centerPoint = positionsByRoomId[room.id];
    if (!centerPoint) {
      continue;
    }
    const clusterIds = rooms
      .filter((candidate) => distance(centerPoint, positionsByRoomId[candidate.id]) <= CLUSTER_RADIUS)
      .map((candidate) => candidate.id);

    if (clusterIds.length <= CLUSTER_THRESHOLD) {
      continue;
    }

    const clusterCenter = {
      x: average(clusterIds.map((roomId) => positionsByRoomId[roomId].x)),
      y: average(clusterIds.map((roomId) => positionsByRoomId[roomId].y)),
    };

    for (const roomId of clusterIds) {
      if (metaByRoomId[roomId]?.locked) {
        continue;
      }
      const point = positionsByRoomId[roomId];
      point.x += (point.x - clusterCenter.x) * 0.2;
      point.y += (point.y - clusterCenter.y) * 0.2;
    }
  }
}

function snapAlignedLines(
  positionsByRoomId: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
  axis: "horizontal" | "vertical",
): void {
  const groups = new Map<number, string[]>();
  const bucketAxis = axis === "horizontal" ? "y" : "x";

  for (const [roomId, point] of Object.entries(positionsByRoomId)) {
    const key = Math.round(point[bucketAxis] / 10);
    const current = groups.get(key) || [];
    current.push(roomId);
    groups.set(key, current);
  }

  for (const roomIds of groups.values()) {
    if (roomIds.length < 3) {
      continue;
    }
    const values = roomIds.map((roomId) => positionsByRoomId[roomId][bucketAxis]);
    if (variance(values) >= 10) {
      continue;
    }
    const target = average(values);
    for (const roomId of roomIds) {
      if (metaByRoomId[roomId]?.locked) {
        continue;
      }
      positionsByRoomId[roomId][bucketAxis] = target;
    }
  }
}

function reduceEdgeCrossings(
  roomsById: Record<string, GraphRoomLike>,
  positionsByRoomId: Record<string, CanvasPoint>,
  originalPositions: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  for (let iteration = 0; iteration < CROSSING_PASSES; iteration += 1) {
    const edges = collectLayoutEdges(roomsById, positionsByRoomId);
    let moved = false;

    for (let edgeIndex = 0; edgeIndex < edges.length; edgeIndex += 1) {
      for (let compareIndex = edgeIndex + 1; compareIndex < edges.length; compareIndex += 1) {
        const left = edges[edgeIndex];
        const right = edges[compareIndex];
        if (sharesEndpoint(left.roomIds, right.roomIds)) {
          continue;
        }
        if (!linesIntersect(left.start, left.end, right.start, right.end)) {
          continue;
        }

        const candidateRoomId = pickMovableIntersectionNode([...left.roomIds, ...right.roomIds], metaByRoomId);
        if (!candidateRoomId) {
          continue;
        }

        const offset = deterministicOffset(candidateRoomId, iteration);
        positionsByRoomId[candidateRoomId].x = clampWithinLimit(
          originalPositions[candidateRoomId].x,
          positionsByRoomId[candidateRoomId].x + offset.x,
          MAX_LAYOUT_MOVE,
        );
        positionsByRoomId[candidateRoomId].y = clampWithinLimit(
          originalPositions[candidateRoomId].y,
          positionsByRoomId[candidateRoomId].y + offset.y,
          MAX_LAYOUT_MOVE,
        );
        moved = true;
      }
    }

    if (!moved) {
      break;
    }
  }
}

function applyFinalSoftPush(
  positionsByRoomId: Record<string, CanvasPoint>,
  metaByRoomId: Record<string, GraphRenderMeta>,
): void {
  const roomIds = Object.keys(positionsByRoomId);
  for (let leftIndex = 0; leftIndex < roomIds.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < roomIds.length; rightIndex += 1) {
      const leftRoomId = roomIds[leftIndex];
      const rightRoomId = roomIds[rightIndex];
      const left = positionsByRoomId[leftRoomId];
      const right = positionsByRoomId[rightRoomId];
      const currentDistance = distance(left, right);
      if (currentDistance >= FINAL_SOFT_PUSH_DISTANCE || currentDistance === 0) {
        continue;
      }

      const push = (FINAL_SOFT_PUSH_DISTANCE - currentDistance) / 2;
      const dx = (right.x - left.x) / currentDistance;
      const dy = (right.y - left.y) / currentDistance;
      if (!metaByRoomId[leftRoomId]?.locked) {
        left.x -= dx * push;
        left.y -= dy * push;
      }
      if (!metaByRoomId[rightRoomId]?.locked) {
        right.x += dx * push;
        right.y += dy * push;
      }
    }
  }
}

function clampMovement(
  positionsByRoomId: Record<string, CanvasPoint>,
  originalPositions: Record<string, CanvasPoint>,
  limit: number,
): void {
  for (const [roomId, point] of Object.entries(positionsByRoomId)) {
    const original = originalPositions[roomId];
    if (!original) {
      continue;
    }
    const deltaX = point.x - original.x;
    const deltaY = point.y - original.y;
    const movement = Math.hypot(deltaX, deltaY);
    if (movement <= limit || movement === 0) {
      continue;
    }
    const ratio = limit / movement;
    point.x = original.x + deltaX * ratio;
    point.y = original.y + deltaY * ratio;
  }
}

function diagonalSlope(roomIds: string[], positionsByRoomId: Record<string, CanvasPoint>): number {
  if (roomIds.length < 2) {
    return 1;
  }
  const first = positionsByRoomId[roomIds[0]];
  const last = positionsByRoomId[roomIds[roomIds.length - 1]];
  return last.y >= first.y ? 1 : -1;
}

function average(values: number[]): number {
  if (!values.length) {
    return 0;
  }
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function variance(values: number[]): number {
  if (!values.length) {
    return 0;
  }
  const mean = average(values);
  return Math.max(...values.map((value) => Math.abs(value - mean)));
}

function clampWithinLimit(original: number, target: number, limit: number): number {
  return Math.max(original - limit, Math.min(original + limit, target));
}

function directionAngle(direction: BuilderDirection): number | null {
  switch (direction) {
    case "east":
      return 0;
    case "northeast":
      return -Math.PI / 4;
    case "north":
    case "up":
      return -Math.PI / 2;
    case "northwest":
      return (-3 * Math.PI) / 4;
    case "west":
      return Math.PI;
    case "southwest":
      return (3 * Math.PI) / 4;
    case "south":
    case "down":
      return Math.PI / 2;
    case "southeast":
      return Math.PI / 4;
    default:
      return null;
  }
}

function enforceDirectionalIntent(direction: BuilderDirection, hub: CanvasPoint, point: CanvasPoint): CanvasPoint {
  return {
    x: direction.includes("east") ? Math.max(point.x, hub.x + 24) : direction.includes("west") ? Math.min(point.x, hub.x - 24) : point.x,
    y: direction.includes("north") || direction === "up"
      ? Math.min(point.y, hub.y - 24)
      : direction.includes("south") || direction === "down"
        ? Math.max(point.y, hub.y + 24)
        : point.y,
  };
}

function distance(left: CanvasPoint, right?: CanvasPoint | null): number {
  if (!right) {
    return Number.POSITIVE_INFINITY;
  }
  return Math.hypot(left.x - right.x, left.y - right.y);
}

function collectLayoutEdges(
  roomsById: Record<string, GraphRoomLike>,
  positionsByRoomId: Record<string, CanvasPoint>,
): Array<{ roomIds: [string, string]; start: CanvasPoint; end: CanvasPoint }> {
  const dedupe = new Set<string>();
  const edges: Array<{ roomIds: [string, string]; start: CanvasPoint; end: CanvasPoint }> = [];

  for (const room of Object.values(roomsById)) {
    for (const targetRoomId of Object.values(room.exits || {})) {
      const normalizedTargetRoomId = String(targetRoomId || "");
      if (!roomsById[normalizedTargetRoomId]) {
        continue;
      }
      const key = [room.id, normalizedTargetRoomId].sort().join("|");
      if (dedupe.has(key)) {
        continue;
      }
      dedupe.add(key);
      edges.push({
        roomIds: [room.id, normalizedTargetRoomId],
        start: positionsByRoomId[room.id],
        end: positionsByRoomId[normalizedTargetRoomId],
      });
    }
  }

  return edges;
}

function sharesEndpoint(left: [string, string], right: [string, string]): boolean {
  return left.some((roomId) => right.includes(roomId));
}

function pickMovableIntersectionNode(roomIds: string[], metaByRoomId: Record<string, GraphRenderMeta>): string | null {
  const ranked = [...new Set(roomIds)]
    .filter((roomId) => !metaByRoomId[roomId]?.locked)
    .sort((left, right) => layoutPriority(metaByRoomId[left]) - layoutPriority(metaByRoomId[right]) || left.localeCompare(right));
  return ranked[0] || null;
}

function layoutPriority(meta?: GraphRenderMeta): number {
  if (meta?.isCorridor) {
    return 1;
  }
  if (meta?.isHub) {
    return 3;
  }
  return 2;
}

function deterministicOffset(roomId: string, iteration: number): CanvasPoint {
  let seed = iteration + 1;
  for (const character of roomId) {
    seed = (seed * 31 + character.charCodeAt(0)) % 9973;
  }
  return {
    x: ((seed % 41) - 20),
    y: (((Math.floor(seed / 41)) % 41) - 20),
  };
}

function linesIntersect(a1: CanvasPoint, a2: CanvasPoint, b1: CanvasPoint, b2: CanvasPoint): boolean {
  const denominator = ((b2.y - b1.y) * (a2.x - a1.x)) - ((b2.x - b1.x) * (a2.y - a1.y));
  if (denominator === 0) {
    return false;
  }
  const ua = (((b2.x - b1.x) * (a1.y - b1.y)) - ((b2.y - b1.y) * (a1.x - b1.x))) / denominator;
  const ub = (((a2.x - a1.x) * (a1.y - b1.y)) - ((a2.y - a1.y) * (a1.x - b1.x))) / denominator;
  return ua > 0 && ua < 1 && ub > 0 && ub < 1;
}

export function rawToRenderPoint(x: number, y: number, transform: GraphRenderTransform): CanvasPoint {
  return {
    x: (x - transform.centerX) * transform.scale,
    y: (y - transform.centerY) * transform.scale,
  };
}

export function renderToRawPoint(x: number, y: number, transform: GraphRenderTransform): CanvasPoint {
  const safeScale = Math.max(transform.scale, 0.0001);
  return {
    x: x / safeScale + transform.centerX,
    y: y / safeScale + transform.centerY,
  };
}

export function handleAnchor(direction: BuilderDirection): CanvasPoint {
  switch (direction) {
    case "north":
      return { x: ROOM_NODE_SIZE / 2, y: 12 };
    case "east":
      return { x: ROOM_NODE_SIZE - 12, y: ROOM_NODE_SIZE / 2 };
    case "south":
      return { x: ROOM_NODE_SIZE / 2, y: ROOM_NODE_SIZE - 12 };
    case "west":
      return { x: 12, y: ROOM_NODE_SIZE / 2 };
    case "northeast":
      return { x: ROOM_NODE_SIZE - 12, y: 12 };
    case "northwest":
      return { x: 12, y: 12 };
    case "southeast":
      return { x: ROOM_NODE_SIZE - 12, y: ROOM_NODE_SIZE - 12 };
    case "southwest":
      return { x: 12, y: ROOM_NODE_SIZE - 12 };
    case "up":
      return { x: ROOM_NODE_SIZE / 2, y: 2 };
    case "down":
      return { x: ROOM_NODE_SIZE / 2, y: ROOM_NODE_SIZE - 2 };
    default:
      return { x: ROOM_NODE_SIZE / 2, y: ROOM_NODE_SIZE / 2 };
  }
}

export function roomHandleAnchor(x: number, y: number, direction: BuilderDirection): CanvasPoint {
  const roomPosition = logicalToCanvas(x, y);
  const anchor = handleAnchor(direction);
  return {
    x: roomPosition.x + anchor.x,
    y: roomPosition.y + anchor.y,
  };
}

export function renderedRoomHandleAnchor(position: CanvasPoint, direction: BuilderDirection): CanvasPoint {
  const anchor = handleAnchor(direction);
  return {
    x: position.x + anchor.x,
    y: position.y + anchor.y,
  };
}

export function buildDirectionalPath(start: CanvasPoint, end: CanvasPoint, direction: BuilderDirection): string {
  switch (direction) {
    case "east":
    case "west": {
      const midX = start.x + (end.x - start.x) / 2;
      return `M ${start.x},${start.y} H ${midX} V ${end.y} H ${end.x}`;
    }
    case "north":
    case "south": {
      const midY = start.y + (end.y - start.y) / 2;
      return `M ${start.x},${start.y} V ${midY} H ${end.x} V ${end.y}`;
    }
    case "up":
    case "down": {
      const midY = start.y + (end.y - start.y) / 2;
      return `M ${start.x},${start.y} V ${midY} H ${end.x} V ${end.y}`;
    }
    case "northeast":
    case "northwest":
    case "southeast":
    case "southwest":
    default:
      return `M ${start.x},${start.y} L ${end.x},${end.y}`;
  }
}

export function normalizedConnectionKey(
  fromRoomId: string,
  direction: BuilderDirection,
  targetRoomId: string,
): string {
  const reverse = oppositeDirection(direction) || direction;
  const rooms = [fromRoomId, targetRoomId].sort();
  const directions = [direction, reverse].sort();
  return `${rooms[0]}|${rooms[1]}|${directions[0]}|${directions[1]}`;
}