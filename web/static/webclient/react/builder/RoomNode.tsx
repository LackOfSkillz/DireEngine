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
  npcCatalog?: Record<string, { id?: string; name?: string; type?: string; vendor?: { enabled?: boolean } }>;
  onNpcDrop?: ((npcId: string, roomId: string) => void) | null;
  onNpcRemove?: ((npcId: string, roomId: string) => void) | null;
  onItemDrop?: ((itemId: string, roomId: string, count?: number) => void) | null;
};

const NPC_BADGE_MAX_VISIBLE = 2;

const NPC_TYPE_STYLES: Record<string, string> = {
  vendor: "is-vendor",
  hostile: "is-hostile",
  neutral: "is-neutral",
};

function normalizeNpcType(npc: { type?: string; vendor?: { enabled?: boolean } } | null | undefined) {
  if (Boolean(npc?.vendor?.enabled) || String(npc?.type || "").trim().toLowerCase() === "vendor") {
    return "vendor";
  }
  const normalized = String(npc?.type || "").trim().toLowerCase();
  if (normalized === "hostile") {
    return "hostile";
  }
  return "neutral";
}

function humanizeNpcId(npcId: string) {
  return String(npcId || "")
    .split(/[_-]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function truncateNpcBadgeLabel(label: string, maxLength = 12) {
  const normalized = String(label || "").trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, Math.max(1, maxLength - 1)).trimEnd()}...`;
}

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
  const npcIds = Array.isArray(room?.npcIds) ? room.npcIds : [];
  const npcCount = npcIds.length;
  const npcCatalog = data?.npcCatalog || {};
  const [isDropTarget, setIsDropTarget] = React.useState(false);
  const visibleNpcBadges = npcIds.slice(0, NPC_BADGE_MAX_VISIBLE).map((npcId) => {
    const npc = npcCatalog[String(npcId || "")] || null;
    const npcName = String(npc?.name || humanizeNpcId(npcId) || npcId);
    const npcType = normalizeNpcType(npc);
    return {
      id: String(npcId || ""),
      label: truncateNpcBadgeLabel(npcName),
      fullLabel: npcName,
      type: npcType,
    };
  });
  const hiddenNpcCount = Math.max(0, npcCount - visibleNpcBadges.length);
  const npcTooltip = npcIds.map((npcId) => {
    const npc = npcCatalog[String(npcId || "")] || null;
    const npcName = String(npc?.name || humanizeNpcId(npcId) || npcId);
    const npcType = normalizeNpcType(npc);
    return `${npcName} • ${npcType}`;
  }).join("\n");

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    const payloadTypes = Array.from(event.dataTransfer.types || []);
    const hasNpcPayload = payloadTypes.includes("application/x-dragonsire-npc-id");
    const hasItemPayload = payloadTypes.includes("application/x-dragonsire-room-item");
    if (!hasNpcPayload && !hasItemPayload) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = hasItemPayload ? "copy" : "move";
    setIsDropTarget(true);
  };

  const handleDragLeave = () => {
    setIsDropTarget(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    const npcId = String(event.dataTransfer.getData("application/x-dragonsire-npc-id") || event.dataTransfer.getData("text/plain") || "").trim();
    event.preventDefault();
    setIsDropTarget(false);
    if (npcId) {
      data?.onNpcDrop?.(npcId, roomId);
      return;
    }
    const itemId = String(event.dataTransfer.getData("application/x-dragonsire-room-item") || "").trim();
    if (itemId) {
      data?.onItemDrop?.(itemId, roomId, 1);
    }
  };

  const handleNpcBadgeRemove = (event: React.MouseEvent<HTMLButtonElement>, npcId: string) => {
    event.preventDefault();
    event.stopPropagation();
    data?.onNpcRemove?.(npcId, roomId);
  };

  return (
    <div className={[
      "builder-phase1-node",
      isSelected ? "is-selected" : "",
      isLocked ? "is-locked" : "",
      isCorridor ? "is-corridor" : "",
      isHub ? "is-hub" : "",
      isDropTarget ? "is-npc-drop-target" : "",
    ].filter(Boolean).join(" ")}
      onDragOver={handleDragOver}
      onDragEnter={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}>
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
        {npcCount ? (
          <div className="builder-phase1-room-npc-badges" title={npcTooltip || `${npcCount} NPC${npcCount === 1 ? "" : "s"} assigned`}>
            {visibleNpcBadges.map((npcBadge) => (
              <span
                key={npcBadge.id}
                className={[
                  "builder-phase1-room-npc-badge",
                  NPC_TYPE_STYLES[npcBadge.type] || NPC_TYPE_STYLES.neutral,
                ].join(" ")}
                title={`${npcBadge.fullLabel} • ${npcBadge.type}`}
              >
                <span className="builder-phase1-room-npc-badge-label">{npcBadge.label}</span>
                <button
                  type="button"
                  className="builder-phase1-room-npc-badge-remove"
                  aria-label={`Remove ${npcBadge.fullLabel}`}
                  title={`Remove ${npcBadge.fullLabel}`}
                  onClick={(event) => handleNpcBadgeRemove(event, npcBadge.id)}
                >
                  x
                </button>
              </span>
            ))}
            {hiddenNpcCount ? (
              <span className="builder-phase1-room-npc-badge is-overflow" title={npcTooltip}>+{hiddenNpcCount}</span>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}