import React from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { BuilderDirection, RoomColor } from "./BuilderTypes";
import { useBuilderStore } from "./BuilderStore";
import { BUILDER_DIRECTIONS, ROOM_BODY_OFFSET, ROOM_BODY_SIZE, ROOM_COLORS, directionToHandleId } from "./BuilderUtils";

const ROOM_BODY_MIN = ROOM_BODY_OFFSET;
const ROOM_BODY_MAX = ROOM_BODY_OFFSET + ROOM_BODY_SIZE;
const ROOM_BODY_CENTER = ROOM_BODY_OFFSET + (ROOM_BODY_SIZE / 2);
const HANDLE_OUTSIDE_OFFSET = 6;
const VERTICAL_HANDLE_OFFSET = 12;

const HANDLE_LAYOUT: Record<BuilderDirection, { position: Position; style: React.CSSProperties }> = {
  north: { position: Position.Top, style: { top: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET, left: ROOM_BODY_CENTER, transform: "translate(-50%, -50%)" } },
  east: { position: Position.Right, style: { top: ROOM_BODY_CENTER, left: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET, transform: "translate(-50%, -50%)" } },
  south: { position: Position.Bottom, style: { top: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET, left: ROOM_BODY_CENTER, transform: "translate(-50%, -50%)" } },
  west: { position: Position.Left, style: { top: ROOM_BODY_CENTER, left: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET, transform: "translate(-50%, -50%)" } },
  northeast: { position: Position.Top, style: { top: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET, left: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET, transform: "translate(-50%, -50%)" } },
  northwest: { position: Position.Top, style: { top: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET, left: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET, transform: "translate(-50%, -50%)" } },
  southeast: { position: Position.Bottom, style: { top: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET, left: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET, transform: "translate(-50%, -50%)" } },
  southwest: { position: Position.Bottom, style: { top: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET, left: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET, transform: "translate(-50%, -50%)" } },
  up: { position: Position.Top, style: { top: ROOM_BODY_MIN - HANDLE_OUTSIDE_OFFSET - VERTICAL_HANDLE_OFFSET, left: ROOM_BODY_CENTER, transform: "translate(-50%, -50%)" } },
  down: { position: Position.Bottom, style: { top: ROOM_BODY_MAX + HANDLE_OUTSIDE_OFFSET + VERTICAL_HANDLE_OFFSET, left: ROOM_BODY_CENTER, transform: "translate(-50%, -50%)" } },
};

type BuilderRoomNodeData = {
  roomId: string;
  showLabel?: boolean;
  isLocked?: boolean;
  isCorridor?: boolean;
  isHub?: boolean;
  isPreviewGhost?: boolean;
  color?: RoomColor;
  activeSourceHandleId?: string | null;
};

const HANDLE_TITLES: Record<BuilderDirection, string> = {
  north: "North",
  east: "East",
  south: "South",
  west: "West",
  northeast: "Northeast",
  northwest: "Northwest",
  southeast: "Southeast",
  southwest: "Southwest",
  up: "Up",
  down: "Down",
};

const OPPOSITE_HANDLE_ID: Record<string, string> = {
  n: "s",
  s: "n",
  e: "w",
  w: "e",
  ne: "sw",
  sw: "ne",
  nw: "se",
  se: "nw",
  u: "d",
  d: "u",
};

export function RoomNode({ data }: NodeProps<BuilderRoomNodeData>) {
  const {
    roomsById,
    selectedRoomId,
  } = useBuilderStore();

  const roomId = String(data?.roomId || "");
  const room = roomsById[roomId];
  const showLabel = Boolean(data?.showLabel);
  const isSelected = roomId === selectedRoomId;
  const isLocked = Boolean(data?.isLocked);
  const isCorridor = Boolean(data?.isCorridor);
  const isHub = Boolean(data?.isHub);
  const roomColor = ROOM_COLORS[data?.color || "standard"] || ROOM_COLORS.standard;
  const activeSourceHandleId = String(data?.activeSourceHandleId || "").trim() || null;
  const validTargetHandleId = activeSourceHandleId ? OPPOSITE_HANDLE_ID[activeSourceHandleId] || null : null;
  const roomLabel = room?.id || roomId;

  return (
    <div className={[
      "builder-phase1-node",
      isSelected ? "is-selected" : "",
      isLocked ? "is-locked" : "",
      isCorridor ? "is-corridor" : "",
      isHub ? "is-hub" : "",
    ].filter(Boolean).join(" ")}>
      {BUILDER_DIRECTIONS.map((direction) => {
        const handleId = directionToHandleId(direction);
        const handleLayout = HANDLE_LAYOUT[direction];
        const isSource = Boolean(activeSourceHandleId && activeSourceHandleId === handleId);
        const isValidTarget = Boolean(validTargetHandleId && validTargetHandleId === handleId);
        const isDimmed = Boolean(activeSourceHandleId && !isSource && !isValidTarget);
        const glyphStyle = direction === "down"
          ? {
            ...handleLayout.style,
            transform: `${String(handleLayout.style.transform || "")} translateY(-2px)`.trim(),
          }
          : handleLayout.style;

        return (
          <React.Fragment key={direction}>
            <Handle
              id={handleId}
              type="source"
              position={handleLayout.position}
              className={[
                "builder-phase1-handle",
                `is-${direction}`,
                isSource ? "is-source" : "",
                isValidTarget ? "is-valid-target" : "",
                isDimmed ? "is-dimmed" : "",
              ].filter(Boolean).join(" ")}
              style={handleLayout.style}
              data-direction={direction}
              data-handle-id={handleId}
              title={`${HANDLE_TITLES[direction]} (${handleId})`}
              aria-label={`${HANDLE_TITLES[direction]} handle`}
              isConnectable={true}
            />
            {direction === "up" || direction === "down" ? (
              <span
                className={`builder-phase1-handle-glyph is-${direction}`}
                style={glyphStyle}
                aria-hidden="true"
              >
                {direction === "up" ? "↑" : "↓"}
              </span>
            ) : null}
          </React.Fragment>
        );
      })}
      <div
        className="builder-phase1-room-body"
        style={{
          left: ROOM_BODY_OFFSET,
          top: ROOM_BODY_OFFSET,
          width: ROOM_BODY_SIZE,
          height: ROOM_BODY_SIZE,
          backgroundColor: roomColor,
          pointerEvents: "none",
        }}
        title={roomLabel}
      >
        <span className={`builder-phase1-room-label${showLabel ? "" : " is-hidden-by-zoom"}`}>{roomLabel}</span>
      </div>
    </div>
  );
}