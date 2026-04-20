import React from "react";
import { useBuilderStore } from "./BuilderStore";
import type { EditorMode } from "./BuilderTypes";

const MODES: Array<{ mode: EditorMode; label: string }> = [
  { mode: "select", label: "⌖" },
  { mode: "room", label: "+" },
  { mode: "delete", label: "D" },
];

const MODE_TITLES: Record<EditorMode, string> = {
  select: "Select",
  room: "Room",
  connect: "Connect",
  delete: "Delete",
};

export function BuilderToolbar() {
  const {
    applyLayout,
    clearLayout,
    isSelectedRoomLocked,
    layoutMode,
    mode,
    previewLayout,
    selectedRoomId,
    setMode,
    statusMessage,
    toggleSelectedRoomLock,
  } = useBuilderStore();
  let statusText = `MODE: ${String(mode || "select").toUpperCase()}`;
  if (statusMessage) {
    statusText = statusMessage;
  }
  if (layoutMode === "preview") {
    statusText = "Previewing tidy layout ghost positions.";
  } else if (layoutMode === "applied") {
    statusText = "Tidy layout applied in the canvas view.";
  }
  if (selectedRoomId && isSelectedRoomLocked) {
    statusText = `${selectedRoomId} is locked from tidy movement.`;
  }

  return (
    <div className="builder-phase1-toolbar">
      <div className="builder-phase1-toolbar-buttons">
        {MODES.map(({ mode: nextMode, label }) => (
          <button
            key={nextMode}
            type="button"
            className={`builder-phase1-mode-button${mode === nextMode ? " is-active" : ""}`}
            onClick={() => setMode(nextMode)}
            title={MODE_TITLES[nextMode]}
            aria-label={MODE_TITLES[nextMode]}
          >
            {label}
          </button>
        ))}
        <button
          type="button"
          className={`builder-phase1-tool-button${layoutMode === "preview" ? " is-active" : ""}`}
          onClick={previewLayout}
          title="Preview Tidy"
          aria-label="Preview Tidy"
        >
          Preview
        </button>
        <button
          type="button"
          className={`builder-phase1-tool-button${layoutMode === "applied" ? " is-active" : ""}`}
          onClick={applyLayout}
          title="Tidy"
          aria-label="Tidy"
        >
          Tidy
        </button>
        <button
          type="button"
          className="builder-phase1-tool-button"
          onClick={clearLayout}
          title="Reset Layout"
          aria-label="Reset Layout"
        >
          Reset
        </button>
        <button
          type="button"
          className={`builder-phase1-tool-button${isSelectedRoomLocked ? " is-active" : ""}`}
          onClick={toggleSelectedRoomLock}
          title="Lock Selected"
          aria-label="Lock Selected"
          disabled={!selectedRoomId}
        >
          Lock
        </button>
      </div>
      <div className="builder-phase1-status" aria-live="polite">{statusText}</div>
    </div>
  );
}