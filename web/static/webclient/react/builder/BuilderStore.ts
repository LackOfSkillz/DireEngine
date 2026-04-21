import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { BuilderDirection, BuilderEdgeType, BuilderState, ConnectionState, EditorMode, LayoutMode, RoomColor, RoomNode } from "./BuilderTypes";
import { buildRoomId, canvasToLogical, coordKey, GRID_SIZE, isBuilderDirection, isRoomColor, isValidPair, oppositeDirection } from "./BuilderUtils";

type BuilderStoreValue = BuilderState & {
  layoutMode: LayoutMode;
  isSelectedRoomLocked: boolean;
  statusMessage: string | null;
  setMode: (mode: EditorMode) => void;
  previewLayout: () => void;
  applyLayout: () => void;
  clearLayout: () => void;
  toggleSelectedRoomLock: () => void;
  setSelectedRoom: (roomId: string | null) => void;
  setSelectedEdge: (edgeId: string | null) => void;
  deleteRoom: (roomId: string) => boolean;
  updateRoomPosition: (roomId: string, x: number, y: number) => boolean;
  updateSelectedRoomColor: (color: RoomColor) => void;
  updateSelectedEdge: (updates: { type?: BuilderEdgeType; label?: string }) => boolean;
  deleteSelectedEdge: () => boolean;
  createRoomAt: (x: number, y: number) => string | null;
  tryConnect: (
    startRoomId: string,
    startDirection: BuilderDirection,
    targetRoomId: string,
    targetDirection: BuilderDirection,
  ) => boolean;
};

type BuilderStoreProviderProps = {
  children: React.ReactNode;
  zonePrefix: string;
  initialRooms: RoomNode[];
  initialSelectedRoomId?: string | null;
  resetKey: string;
  onStateChange?: (state: BuilderState) => void;
};

const BuilderStoreContext = createContext<BuilderStoreValue | null>(null);
const persistedModeByResetKey = new Map<string, EditorMode>();

const EMPTY_CONNECTION: ConnectionState = {
  active: false,
  fromRoomId: null,
  fromDirection: null,
};

function normalizeExitSpec(spec: unknown) {
  if (typeof spec === "string") {
    return { targetId: String(spec || ""), type: "spatial" as const, label: "" };
  }

  return {
    targetId: String((spec as { targetId?: string; target?: string } | null)?.targetId || (spec as { target?: string } | null)?.target || ""),
    type: String((spec as { type?: string } | null)?.type || "spatial") === "special" ? "special" as const : "spatial" as const,
    label: String((spec as { label?: string } | null)?.label || ""),
  };
}

function createInitialBuilderState(
  zonePrefix: string,
  rooms: RoomNode[] = [],
  selectedRoomId: string | null = null,
  initialMode: EditorMode = "select",
): BuilderState {
  const roomsById: Record<string, RoomNode> = {};
  const roomIdByCoord: Record<string, string> = {};

  for (const room of rooms) {
    const normalizedRoom: RoomNode = {
      id: String(room.id),
      x: Math.round(Number(room.x) || 0),
      y: Math.round(Number(room.y) || 0),
      exits: Object.entries(room.exits || {}).reduce((accumulator, [direction, spec]) => {
        if (isBuilderDirection(direction)) {
          const normalized = normalizeExitSpec(spec);
          if (normalized.targetId) {
            accumulator[direction] = normalized;
          }
        }
        return accumulator;
      }, {} as RoomNode["exits"]),
      color: isRoomColor(String(room.color || "")) ? room.color : "standard",
      meta: { ...(room.meta || {}) },
    };
    roomsById[normalizedRoom.id] = normalizedRoom;
    roomIdByCoord[coordKey(normalizedRoom.x, normalizedRoom.y)] = normalizedRoom.id;
  }

  return {
    mode: initialMode,
    selectedRoomId: selectedRoomId && roomsById[selectedRoomId] ? selectedRoomId : null,
    selectedEdgeId: null,
    connection: EMPTY_CONNECTION,
    zonePrefix,
    roomsById,
    roomIdByCoord,
  };
}

export function BuilderStoreProvider({
  children,
  zonePrefix,
  initialRooms,
  initialSelectedRoomId = null,
  resetKey,
  onStateChange,
}: BuilderStoreProviderProps) {
  const suppressNextStateChangeRef = useRef(true);
  const onStateChangeRef = useRef(onStateChange);
  const [layoutMode, setLayoutMode] = useState<LayoutMode>("none");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const resolvedInitialMode = persistedModeByResetKey.get(resetKey) || "select";
  const [state, setState] = useState<BuilderState>(() => (
    createInitialBuilderState(zonePrefix, initialRooms, initialSelectedRoomId, resolvedInitialMode)
  ));

  useEffect(() => {
    onStateChangeRef.current = onStateChange;
  }, [onStateChange]);

  useEffect(() => {
    suppressNextStateChangeRef.current = true;
    setLayoutMode("none");
    setStatusMessage(null);
    setState(createInitialBuilderState(
      zonePrefix,
      initialRooms,
      initialSelectedRoomId,
      persistedModeByResetKey.get(resetKey) || "select",
    ));
  }, [resetKey, zonePrefix]);

  useEffect(() => {
    if (initialSelectedRoomId === undefined) {
      return;
    }

    setState((previous) => {
      const nextSelectedRoomId = initialSelectedRoomId && previous.roomsById[initialSelectedRoomId]
        ? initialSelectedRoomId
        : null;

      if (previous.selectedRoomId === nextSelectedRoomId) {
        return previous;
      }

      return {
        ...previous,
        selectedRoomId: nextSelectedRoomId,
        selectedEdgeId: null,
      };
    });
  }, [initialSelectedRoomId]);

  useEffect(() => {
    if (suppressNextStateChangeRef.current) {
      suppressNextStateChangeRef.current = false;
      return;
    }
    onStateChangeRef.current?.(state);
  }, [state]);

  const setMode = useCallback((mode: EditorMode) => {
    persistedModeByResetKey.set(resetKey, mode);
    setStatusMessage(null);
    setState((previous) => ({
      ...previous,
      mode,
      connection: EMPTY_CONNECTION,
    }));
  }, [resetKey]);

  const previewLayout = useCallback(() => {
    setLayoutMode((previous) => (previous === "preview" ? "none" : "preview"));
  }, []);

  const applyLayout = useCallback(() => {
    setLayoutMode("applied");
  }, []);

  const clearLayout = useCallback(() => {
    setLayoutMode("none");
  }, []);

  const toggleSelectedRoomLock = useCallback(() => {
    setState((previous) => {
      const roomId = previous.selectedRoomId;
      if (!roomId) {
        return previous;
      }

      const room = previous.roomsById[roomId];
      if (!room) {
        return previous;
      }

      return {
        ...previous,
        roomsById: {
          ...previous.roomsById,
          [roomId]: {
            ...room,
            meta: {
              ...(room.meta || {}),
              locked: !room.meta?.locked,
            },
          },
        },
      };
    });
  }, []);

  const setSelectedRoom = useCallback((roomId: string | null) => {
    setStatusMessage(null);
    setState((previous) => ({
      ...previous,
      selectedRoomId: roomId,
      selectedEdgeId: null,
    }));
  }, []);

  const setSelectedEdge = useCallback((edgeId: string | null) => {
    setStatusMessage(null);
    setState((previous) => ({
      ...previous,
      selectedRoomId: null,
      selectedEdgeId: edgeId,
    }));
  }, []);

  const createRoomAt = useCallback((x: number, y: number) => {
    let roomId: string | null = null;
    setState((previous) => {
      const nextX = Math.round(Number(x) || 0);
      const nextY = Math.round(Number(y) || 0);
      const key = coordKey(nextX, nextY);
      const existingRoomId = previous.roomIdByCoord[key] || null;

      if (existingRoomId) {
        roomId = existingRoomId;
        return {
          ...previous,
          selectedRoomId: existingRoomId,
          selectedEdgeId: null,
        };
      }

      roomId = buildRoomId(previous.zonePrefix, nextX, nextY);
      return {
        ...previous,
        selectedRoomId: roomId,
        selectedEdgeId: null,
        roomsById: {
          ...previous.roomsById,
          [roomId]: {
            id: roomId,
            x: nextX,
            y: nextY,
            exits: {},
            color: "standard",
            meta: {},
          },
        },
        roomIdByCoord: {
          ...previous.roomIdByCoord,
          [key]: roomId,
        },
      };
    });
    return roomId;
  }, []);

  const tryConnect = useCallback((
    startRoomId: string,
    startDirection: BuilderDirection,
    targetRoomId: string,
    targetDirection: BuilderDirection,
  ) => {
    let didConnect = false;

    setState((previous) => {
      const startRoom = previous.roomsById[startRoomId] || null;
      const targetRoom = previous.roomsById[targetRoomId] || null;
      if (!startRoom || !targetRoom) {
        return previous;
      }

      if (!isBuilderDirection(startDirection)) {
        return previous;
      }

      if (!isBuilderDirection(targetDirection)) {
        return previous;
      }

      if (!isValidPair(startDirection, targetDirection)) {
        setStatusMessage("Invalid direction pairing.");
        return previous;
      }

      if (startRoomId === targetRoomId) {
        return previous;
      }

      if (startRoom.exits[startDirection]?.targetId) {
        setStatusMessage("That source handle is already connected.");
        return previous;
      }

      if (targetRoom.exits[targetDirection]?.targetId) {
        setStatusMessage("That target handle is already connected.");
        return previous;
      }

      didConnect = true;
      return {
        ...previous,
        selectedRoomId: targetRoomId,
        selectedEdgeId: `${startRoomId}:${startDirection}`,
        connection: EMPTY_CONNECTION,
        roomsById: {
          ...previous.roomsById,
          [startRoomId]: {
            ...startRoom,
            exits: {
              ...startRoom.exits,
              [startDirection]: {
                targetId: targetRoomId,
                type: "spatial",
                label: "",
              },
            },
          },
          [targetRoomId]: {
            ...targetRoom,
            exits: {
              ...targetRoom.exits,
              [targetDirection]: {
                targetId: startRoomId,
                type: "spatial",
                label: "",
              },
            },
          },
        },
      };
    });

    return didConnect;
  }, []);

  const deleteRoom = useCallback((roomId: string) => {
    let didDelete = false;
    setStatusMessage(null);
    setState((previous) => {
      if (previous.mode !== "delete") {
        return previous;
      }

      const room = previous.roomsById[roomId];
      if (!room) {
        return previous;
      }

      const nextRoomsById = Object.entries(previous.roomsById).reduce<Record<string, RoomNode>>((accumulator, [candidateRoomId, candidateRoom]) => {
        if (candidateRoomId === roomId) {
          return accumulator;
        }

        accumulator[candidateRoomId] = {
          ...candidateRoom,
          exits: Object.entries(candidateRoom.exits || {}).reduce((exitAccumulator, [direction, spec]) => {
            if (spec?.targetId !== roomId) {
              exitAccumulator[direction as BuilderDirection] = spec;
            }
            return exitAccumulator;
          }, {} as RoomNode["exits"]),
        };
        return accumulator;
      }, {});

      const nextRoomIdByCoord = Object.entries(previous.roomIdByCoord).reduce<Record<string, string>>((accumulator, [key, value]) => {
        if (value !== roomId) {
          accumulator[key] = value;
        }
        return accumulator;
      }, {});

      didDelete = true;
      return {
        ...previous,
        mode: "select",
        selectedRoomId: previous.selectedRoomId === roomId ? null : previous.selectedRoomId,
        selectedEdgeId: previous.selectedEdgeId?.startsWith(`${roomId}:`) ? null : previous.selectedEdgeId,
        connection: previous.connection.fromRoomId === roomId ? EMPTY_CONNECTION : previous.connection,
        roomsById: nextRoomsById,
        roomIdByCoord: nextRoomIdByCoord,
      };
    });
    if (didDelete) {
      setStatusMessage(`Deleted ${roomId}.`);
    }
    return didDelete;
  }, []);

  const updateRoomPosition = useCallback((roomId: string, x: number, y: number) => {
    let didMove = false;
    setStatusMessage(null);
    setState((previous) => {
      if (previous.mode !== "select") {
        return previous;
      }

      const room = previous.roomsById[roomId];
      if (!room) {
        return previous;
      }

      const snapped = canvasToLogical(x, y);
      const nextX = Math.round(snapped.x / GRID_SIZE) * GRID_SIZE;
      const nextY = Math.round(snapped.y / GRID_SIZE) * GRID_SIZE;
      const nextKey = coordKey(nextX, nextY);
      const currentKey = coordKey(room.x, room.y);
      const occupyingRoomId = previous.roomIdByCoord[nextKey] || null;
      if (occupyingRoomId && occupyingRoomId !== roomId) {
        setStatusMessage("Target grid cell is occupied.");
        return previous;
      }
      if (nextKey === currentKey) {
        return previous;
      }

      const nextRoomIdByCoord = { ...previous.roomIdByCoord };
      delete nextRoomIdByCoord[currentKey];
      nextRoomIdByCoord[nextKey] = roomId;
      didMove = true;
      return {
        ...previous,
        roomsById: {
          ...previous.roomsById,
          [roomId]: {
            ...room,
            x: nextX,
            y: nextY,
          },
        },
        roomIdByCoord: nextRoomIdByCoord,
      };
    });
    return didMove;
  }, []);

  const updateSelectedRoomColor = useCallback((color: RoomColor) => {
    setStatusMessage(null);
    setState((previous) => {
      const roomId = previous.selectedRoomId;
      if (!roomId || !previous.roomsById[roomId]) {
        return previous;
      }
      return {
        ...previous,
        roomsById: {
          ...previous.roomsById,
          [roomId]: {
            ...previous.roomsById[roomId],
            color,
          },
        },
      };
    });
  }, []);

  const updateSelectedEdge = useCallback((updates: { type?: BuilderEdgeType; label?: string }) => {
    let didUpdate = false;
    setStatusMessage(null);
    setState((previous) => {
      const selectedEdgeId = previous.selectedEdgeId;
      if (!selectedEdgeId) {
        return previous;
      }

      const [roomId, rawDirection] = selectedEdgeId.split(":");
      const direction = rawDirection as BuilderDirection;
      const room = previous.roomsById[roomId];
      const exit = room?.exits?.[direction];
      if (!room || !exit?.targetId) {
        return previous;
      }

      const reverseDirection = oppositeDirection(direction);
      if (!reverseDirection) {
        return previous;
      }

      const targetRoom = previous.roomsById[exit.targetId];
      if (!targetRoom) {
        return previous;
      }

      const nextType = updates.type === "special" ? "special" : "spatial";
      const nextLabel = String(updates.label || "").trim();
      didUpdate = true;
      return {
        ...previous,
        roomsById: {
          ...previous.roomsById,
          [roomId]: {
            ...room,
            exits: {
              ...room.exits,
              [direction]: {
                ...exit,
                type: nextType,
                label: nextLabel,
              },
            },
          },
          [targetRoom.id]: {
            ...targetRoom,
            exits: {
              ...targetRoom.exits,
              [reverseDirection]: {
                ...(targetRoom.exits[reverseDirection] || { targetId: roomId }),
                targetId: roomId,
                type: nextType,
                label: nextLabel,
              },
            },
          },
        },
      };
    });
    return didUpdate;
  }, []);

  const deleteSelectedEdge = useCallback(() => {
    let didDelete = false;
    setStatusMessage(null);
    setState((previous) => {
      const selectedEdgeId = previous.selectedEdgeId;
      if (!selectedEdgeId) {
        return previous;
      }
      const [roomId, rawDirection] = selectedEdgeId.split(":");
      const direction = rawDirection as BuilderDirection;
      const room = previous.roomsById[roomId];
      const exit = room?.exits?.[direction];
      const reverseDirection = oppositeDirection(direction);
      const targetRoom = previous.roomsById[exit?.targetId || ""];
      if (!room || !exit?.targetId || !reverseDirection || !targetRoom) {
        return previous;
      }
      const nextRoomExits = { ...room.exits };
      delete nextRoomExits[direction];
      const nextTargetExits = { ...targetRoom.exits };
      delete nextTargetExits[reverseDirection];
      didDelete = true;
      return {
        ...previous,
        selectedEdgeId: null,
        roomsById: {
          ...previous.roomsById,
          [roomId]: {
            ...room,
            exits: nextRoomExits,
          },
          [targetRoom.id]: {
            ...targetRoom,
            exits: nextTargetExits,
          },
        },
      };
    });
    return didDelete;
  }, []);

  const value = useMemo<BuilderStoreValue>(() => ({
    ...state,
    layoutMode,
    isSelectedRoomLocked: Boolean(state.selectedRoomId && state.roomsById[state.selectedRoomId]?.meta?.locked),
    statusMessage,
    setMode,
    previewLayout,
    applyLayout,
    clearLayout,
    toggleSelectedRoomLock,
    setSelectedRoom,
    setSelectedEdge,
    deleteRoom,
    updateRoomPosition,
    updateSelectedRoomColor,
    updateSelectedEdge,
    deleteSelectedEdge,
    createRoomAt,
    tryConnect,
  }), [
    applyLayout,
    clearLayout,
    createRoomAt,
    deleteRoom,
    deleteSelectedEdge,
    layoutMode,
    previewLayout,
    setMode,
    setSelectedEdge,
    setSelectedRoom,
    state,
    statusMessage,
    toggleSelectedRoomLock,
    tryConnect,
    updateRoomPosition,
    updateSelectedEdge,
    updateSelectedRoomColor,
  ]);

  return React.createElement(BuilderStoreContext.Provider, { value }, children);
}

export function useBuilderStore(): BuilderStoreValue {
  const context = useContext(BuilderStoreContext);
  if (!context) {
    throw new Error("BuilderStoreProvider is required.");
  }
  return context;
}