export type BuilderDirection =
  | "north"
  | "east"
  | "south"
  | "west"
  | "northeast"
  | "northwest"
  | "southeast"
  | "southwest"
  | "up"
  | "down";

export type BuilderHandleId = "n" | "e" | "s" | "w" | "ne" | "nw" | "se" | "sw" | "u" | "d";

export type BuilderEdgeType = "spatial" | "special";

export type RoomColor = "standard" | "poi" | "shop" | "training" | "portal" | "home" | "water" | "underwater";

export type BuilderExit = {
  targetId: string;
  type?: BuilderEdgeType;
  label?: string;
};

export type Mode = "select" | "room" | "connect" | "delete";

export type EditorMode = Mode;

export type LayoutMode = "none" | "preview" | "applied";

export type RoomNodeMeta = {
  locked?: boolean;
  isCorridor?: boolean;
  isHub?: boolean;
};

export type RoomNode = {
  id: string;
  x: number;
  y: number;
  exits: Partial<Record<BuilderDirection, BuilderExit>>;
  color?: RoomColor;
  meta?: RoomNodeMeta;
};

export type ConnectionState = {
  active: boolean;
  fromRoomId: string | null;
  fromDirection: BuilderDirection | null;
};

export type BuilderEdgeRecord = {
  id: string;
  source: string;
  target: string;
  direction: BuilderDirection;
  dirFrom: BuilderHandleId;
  dirTo: BuilderHandleId;
  type?: BuilderEdgeType;
  label?: string;
};

export type BuilderState = {
  mode: Mode;
  selectedRoomId: string | null;
  selectedEdgeId: string | null;
  connection: ConnectionState;
  zonePrefix: string;
  roomsById: Record<string, RoomNode>;
  roomIdByCoord: Record<string, string>;
};