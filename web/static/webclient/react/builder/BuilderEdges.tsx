import React, { useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { Edge, EdgeProps } from "@xyflow/react";
import type { BuilderDirection, BuilderEdgeType, BuilderState } from "./BuilderTypes";
import {
  buildDirectionalPath,
  directionToHandleId,
  edgeKey,
  normalizedConnectionKey,
  oppositeDirection,
  renderedRoomHandleAnchor,
  type CanvasPoint,
} from "./BuilderUtils";
import { useBuilderStore } from "./BuilderStore";

type BuilderEdgeData = {
  id: string;
  source: string;
  target: string;
  direction: BuilderDirection;
  dirFrom: string;
  dirTo: string;
  type?: BuilderEdgeType;
  label?: string;
  start: { x: number; y: number };
  end: { x: number; y: number };
};

export function BuilderDirectionalEdge({
  id,
  data,
  style,
}: EdgeProps<Edge<BuilderEdgeData>>) {
  const { selectedEdgeId } = useBuilderStore();
  const [isHovered, setIsHovered] = useState(false);
  const direction = data?.direction || "east";
  const path = useMemo(
    () => buildDirectionalPath(data?.start || { x: 0, y: 0 }, data?.end || { x: 0, y: 0 }, direction),
    [data?.end, data?.start, direction],
  );
  const isSelected = selectedEdgeId === id;
  const nextStyle: CSSProperties = {
    ...(style || {}),
    stroke: isSelected
      ? "rgba(255, 232, 179, 1)"
      : isHovered
        ? "rgba(243, 205, 143, 0.96)"
        : (style?.stroke || "rgba(214, 184, 122, 0.84)"),
    strokeWidth: isSelected ? 4 : isHovered ? 3.25 : (style?.strokeWidth || 2.5),
    strokeDasharray: direction === "up" || direction === "down" ? "6 4" : style?.strokeDasharray,
    filter: isSelected || isHovered ? "drop-shadow(0 0 6px rgba(255, 227, 173, 0.55))" : undefined,
    pointerEvents: "auto",
  };

  const midpoint = data ? {
    x: ((data.start?.x || 0) + (data.end?.x || 0)) / 2,
    y: ((data.start?.y || 0) + (data.end?.y || 0)) / 2,
  } : null;

  return React.createElement(
    "g",
    null,
    React.createElement("path", {
      d: path,
      fill: "none",
      style: nextStyle,
    }),
    React.createElement("path", {
      d: path,
      fill: "none",
      stroke: "transparent",
      strokeWidth: 18,
      style: { cursor: "pointer", pointerEvents: "stroke" },
      onMouseEnter: () => setIsHovered(true),
      onMouseLeave: () => setIsHovered(false),
    }),
    data?.label ? React.createElement("text", {
      x: midpoint?.x || 0,
      y: (midpoint?.y || 0) - 6,
      textAnchor: "middle",
      fill: "rgba(245, 232, 206, 0.92)",
      fontSize: 10,
      style: { pointerEvents: "none" },
      children: data.label,
    }) : null,
  );
}

export function buildRenderedBuilderEdges(
  state: BuilderState,
  positionsByRoomId: Record<string, CanvasPoint> = {},
): Array<Edge<BuilderEdgeData>> {
  const renderedEdges: Array<Edge<BuilderEdgeData>> = [];
  const dedupe = new Set<string>();
  const roomIds = Object.keys(state.roomsById).sort();

  for (const roomId of roomIds) {
    const room = state.roomsById[roomId];
    const exits = room?.exits || {};

    for (const [rawDirection, targetRoomId] of Object.entries(exits)) {
      const direction = rawDirection as BuilderDirection;
      const exit = typeof targetRoomId === "string" ? { targetId: String(targetRoomId || ""), type: "spatial" as const, label: "" } : targetRoomId;
      const normalizedTargetRoomId = String(exit?.targetId || "");
      const targetRoom = state.roomsById[normalizedTargetRoomId] || null;
      const targetDirection = oppositeDirection(direction);

      if (!targetRoom || !targetDirection) {
        continue;
      }

      const normalizedKey = normalizedConnectionKey(roomId, direction, normalizedTargetRoomId);
      if (dedupe.has(normalizedKey)) {
        continue;
      }
      dedupe.add(normalizedKey);

      renderedEdges.push({
        id: edgeKey(roomId, direction),
        source: roomId,
        target: normalizedTargetRoomId,
        sourceHandle: directionToHandleId(direction),
        targetHandle: directionToHandleId(targetDirection),
        type: "builderDirectional",
        selectable: true,
        focusable: true,
        data: {
          id: edgeKey(roomId, direction),
          source: roomId,
          target: normalizedTargetRoomId,
          direction,
          dirFrom: directionToHandleId(direction),
          dirTo: directionToHandleId(targetDirection),
          type: exit?.type || "spatial",
          label: exit?.label || "",
          start: renderedRoomHandleAnchor(
            positionsByRoomId[roomId] || { x: room.x, y: room.y },
            direction,
          ),
          end: renderedRoomHandleAnchor(
            positionsByRoomId[normalizedTargetRoomId] || { x: targetRoom.x, y: targetRoom.y },
            targetDirection,
          ),
        },
        style: {
          stroke: "rgba(214, 184, 122, 0.6)",
          strokeWidth: 2.5,
        },
        interactionWidth: 18,
      });
    }
  }

  return renderedEdges;
}