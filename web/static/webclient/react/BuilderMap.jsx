import React, { useCallback, useEffect, useMemo } from 'react';
import '@xyflow/react/dist/style.css';
import { BuilderCanvas } from './builder/BuilderCanvas.tsx';
import { buildRenderedBuilderEdges } from './builder/BuilderEdges.tsx';
import { BuilderStoreProvider, useBuilderStore } from './builder/BuilderStore.ts';
import { BuilderToolbar } from './builder/BuilderToolbar.tsx';

function BuilderBridge({ bridgeApi = null }) {
  const {
    deleteSelectedEdge,
    updateSelectedEdge,
    updateSelectedRoomColor,
  } = useBuilderStore();

  useEffect(() => {
    if (!bridgeApi) {
      return undefined;
    }

    bridgeApi.setSelectedRoomColor = (color) => {
      updateSelectedRoomColor(String(color || 'standard'));
    };
    bridgeApi.updateSelectedEdge = (updates) => {
      updateSelectedEdge(updates || {});
    };
    bridgeApi.deleteSelectedEdge = () => {
      deleteSelectedEdge();
    };

    return () => {
      delete bridgeApi.setSelectedRoomColor;
      delete bridgeApi.updateSelectedEdge;
      delete bridgeApi.deleteSelectedEdge;
    };
  }, [bridgeApi, deleteSelectedEdge, updateSelectedEdge, updateSelectedRoomColor]);

  return null;
}

function normalizeInitialRooms(zonePrefix, rooms = []) {
  return (Array.isArray(rooms) ? rooms : []).map((room, index) => {
    const roomId = String(room?.id || `${zonePrefix}_${index}_0`);
    return {
      id: roomId,
      x: Math.round(Number(room?.map?.x ?? room?.map_x ?? room?.x ?? 0) || 0),
      y: Math.round(Number(room?.map?.y ?? room?.map_y ?? room?.y ?? 0) || 0),
      exits: Object.entries(room?.exitMap || room?.exits || {}).reduce((accumulator, [direction, spec]) => {
        const targetId = typeof spec === 'string'
          ? String(spec || '')
          : String(spec?.target_id || spec?.target || '');
        if (targetId) {
          accumulator[String(direction || '').toLowerCase()] = {
            targetId,
            type: String(spec?.label || '').trim() ? 'special' : 'spatial',
            label: String(spec?.label || ''),
          };
        }
        return accumulator;
      }, {}),
      color: String(room?.color || 'standard'),
    };
  });
}

export default function BuilderMap({
  zone = null,
  zonePrefix = 'ZONE',
  selectedRoomId = null,
  viewportRequest = null,
  onBuilderStateChange,
  bridgeApi = null,
}) {
  const initialRooms = useMemo(() => normalizeInitialRooms(zonePrefix, zone?.rooms || []), [zone?.rooms, zonePrefix]);
  const resetKey = String(zone?.zone_id || zonePrefix || 'builder-phase1');

  const handleBuilderStateChange = useCallback((state) => {
    const renderedEdges = buildRenderedBuilderEdges(state);
    const selectedEdge = renderedEdges.find((edge) => edge.id === state.selectedEdgeId) || null;
    const rooms = Object.values(state.roomsById)
      .sort((left, right) => left.id.localeCompare(right.id))
      .map((room) => ({
        id: room.id,
        x: room.x,
        y: room.y,
        exits: Object.entries(room.exits || {}).reduce((accumulator, [direction, spec]) => {
          accumulator[direction] = {
            targetId: spec?.targetId || '',
            type: spec?.type || 'spatial',
            label: spec?.label || '',
          };
          return accumulator;
        }, {}),
        color: room.color || 'standard',
        meta: { ...(room.meta || {}) },
      }));

    onBuilderStateChange?.({
      state,
      rooms,
      selectedRoomId: state.selectedRoomId,
      edgeCount: renderedEdges.length,
      selectedEdge: selectedEdge
        ? {
            id: selectedEdge.id,
            source: selectedEdge.source,
            target: selectedEdge.target,
            direction: selectedEdge.data?.direction || null,
            dirFrom: selectedEdge.data?.dirFrom || null,
            dirTo: selectedEdge.data?.dirTo || null,
            type: selectedEdge.data?.type || 'spatial',
            label: selectedEdge.data?.label || "",
          }
        : null,
    });
  }, [onBuilderStateChange]);

  return (
    <div className="builder-phase1-root">
      <BuilderStoreProvider
        key={resetKey}
        zonePrefix={zonePrefix}
        initialRooms={initialRooms}
        initialSelectedRoomId={selectedRoomId}
        resetKey={resetKey}
        onStateChange={handleBuilderStateChange}
      >
        <BuilderBridge bridgeApi={bridgeApi} />
        <BuilderToolbar />
        <BuilderCanvas viewportRequest={viewportRequest} />
      </BuilderStoreProvider>
    </div>
  );
}