import React, { useEffect, useMemo, useRef, useState } from "react";
import { Background, ConnectionMode, Controls, MiniMap, ReactFlow, ReactFlowProvider, applyNodeChanges, useNodesInitialized, useReactFlow, type Connection, type Node, type NodeChange, type NodeDragHandler } from "@xyflow/react";
import { useBuilderStore } from "./BuilderStore";
import { buildRenderedBuilderEdges, BuilderDirectionalEdge } from "./BuilderEdges";
import {
  buildGraphRenderTransform,
  canvasToLogical,
  GRID_SIZE,
  handleIdToDirection,
  renderToRawPoint,
  ROOM_NODE_SIZE,
} from "./BuilderUtils";
import { RoomNode as BuilderRoomNode } from "./RoomNode";

const MIN_ZOOM = 0.2;
const MAX_ZOOM = 2.5;
const LABEL_VISIBILITY_ZOOM = 0.6;

function scheduleFitView(reactFlow: ReturnType<typeof useReactFlow>, duration: number) {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      reactFlow.fitView({ padding: 0.2, includeHiddenNodes: true, duration });
    });
  });
}

type BuilderCanvasProps = {
  viewportRequest?: { type?: string; token?: number } | null;
};

function BuilderCanvasSurface({ viewportRequest = null }: BuilderCanvasProps) {
  const {
    applyLayout,
    clearLayout,
    createRoomAt,
    deleteRoom,
    layoutMode,
    mode,
    roomsById,
    selectedEdgeId,
    selectedRoomId,
    setMode,
    setSelectedEdge,
    setSelectedRoom,
    updateRoomPosition,
    tryConnect,
  } = useBuilderStore();
  const reactFlow = useReactFlow();
  const nodesInitialized = useNodesInitialized();
  const isDraggingRef = useRef(false);
  const lastViewportTokenRef = useRef<number | null>(null);
  const didInitialAutoFitRef = useRef(false);
  const shellRef = useRef<HTMLDivElement | null>(null);
  const [viewportState, setViewportState] = useState({ x: 0, y: 0, zoom: 1 });
  const [shellSize, setShellSize] = useState({ width: 0, height: 0 });
  const [zoomLevel, setZoomLevel] = useState(1);
  const [activeSourceHandleId, setActiveSourceHandleId] = useState<string | null>(null);

  useEffect(() => {
    if (!shellRef.current || typeof ResizeObserver === "undefined") {
      return undefined;
    }

    const observer = new ResizeObserver((entries) => {
      const nextEntry = entries[0];
      if (!nextEntry) {
        return;
      }
      setShellSize({
        width: Math.max(0, Math.round(nextEntry.contentRect.width)),
        height: Math.max(0, Math.round(nextEntry.contentRect.height)),
      });
    });

    observer.observe(shellRef.current);
    return () => observer.disconnect();
  }, []);

  const roomList = useMemo(() => (
    Object.values(roomsById).sort((left, right) => left.id.localeCompare(right.id))
  ), [roomsById]);

  const baseTransform = useMemo(
    () => buildGraphRenderTransform(roomList, shellSize.width, shellSize.height),
    [roomList, shellSize.height, shellSize.width],
  );
  const tidyTransform = useMemo(
    () => buildGraphRenderTransform(roomList, shellSize.width, shellSize.height, { tidy: true }),
    [roomList, shellSize.height, shellSize.width],
  );
  const renderTransform = layoutMode === "applied" ? tidyTransform : baseTransform;

  const baseNodes = useMemo<Array<Node<{ roomId: string }>>>(() => (
    roomList
      .map((room) => {
        const position = renderTransform.positionsByRoomId[room.id]
          || { x: room.x, y: room.y };
        const meta = renderTransform.metaByRoomId[room.id];
        return {
          id: room.id,
          type: "builderRoom",
          draggable: true,
          dragHandle: ".builder-phase1-node",
          selectable: true,
          position,
          width: ROOM_NODE_SIZE,
          height: ROOM_NODE_SIZE,
          data: {
            roomId: room.id,
            showLabel: zoomLevel >= LABEL_VISIBILITY_ZOOM,
            isLocked: Boolean(meta?.locked),
            isCorridor: Boolean(meta?.isCorridor),
            isHub: Boolean(meta?.isHub),
            isPreviewGhost: false,
            color: room.color || "standard",
            activeSourceHandleId,
          },
        };
      })
  ), [activeSourceHandleId, renderTransform.positionsByRoomId, roomList, zoomLevel]);
  const [canvasNodes, setCanvasNodes] = useState<Array<Node<{ roomId: string }>>>(baseNodes);

  useEffect(() => {
    if (isDraggingRef.current) {
      return;
    }
    setCanvasNodes(baseNodes);
  }, [baseNodes]);

  const canvasNodePositionsByRoomId = useMemo(() => (
    canvasNodes.reduce<Record<string, { x: number; y: number }>>((accumulator, node) => {
      accumulator[node.id] = node.position;
      return accumulator;
    }, {})
  ), [canvasNodes]);

  const edges = useMemo(() => buildRenderedBuilderEdges({
    mode,
    selectedRoomId,
    selectedEdgeId,
    connection: { active: false, fromRoomId: null, fromDirection: null },
    zonePrefix: "",
    roomsById,
    roomIdByCoord: {},
  }, canvasNodePositionsByRoomId), [canvasNodePositionsByRoomId, mode, roomsById, selectedEdgeId, selectedRoomId]);

  const nodeTypes = useMemo(() => ({ builderRoom: BuilderRoomNode }), []);
  const edgeTypes = useMemo(() => ({ builderDirectional: BuilderDirectionalEdge }), []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }
      setMode("select");
      setSelectedRoom(null);
      setSelectedEdge(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setMode, setSelectedEdge, setSelectedRoom]);

  useEffect(() => {
    if (!roomList.length || !nodesInitialized || !shellSize.width || !shellSize.height) {
      return;
    }

    if (isDraggingRef.current) {
      return;
    }

    if (didInitialAutoFitRef.current) {
      return;
    }
    didInitialAutoFitRef.current = true;

    scheduleFitView(reactFlow, 400);
  }, [nodesInitialized, reactFlow, roomList.length, shellSize.height, shellSize.width]);
  useEffect(() => {
    if (!nodesInitialized) {
      return;
    }
    setZoomLevel(reactFlow.getZoom());
    setViewportState(reactFlow.getViewport());
  }, [nodesInitialized, reactFlow]);


  useEffect(() => {
    if (!viewportRequest?.token) {
      return;
    }
    if (lastViewportTokenRef.current === viewportRequest.token) {
      return;
    }
    lastViewportTokenRef.current = viewportRequest.token;

    if (viewportRequest.type === "fit") {
      scheduleFitView(reactFlow, 180);
      return;
    }

    if (viewportRequest.type === "center" && selectedRoomId) {
      const node = canvasNodes.find((candidate) => candidate.id === selectedRoomId);
      if (!node) {
        return;
      }
      reactFlow.fitView({ nodes: [node], padding: 0.4, duration: 180 });
      return;
    }

    if (viewportRequest.type === "center") {
      reactFlow.setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 180 });
    }
  }, [canvasNodes, reactFlow, selectedRoomId, viewportRequest]);

  const onPaneClick = (event: React.MouseEvent<Element>) => {
    const flowPosition = reactFlow.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });
    const rawPoint = renderToRawPoint(flowPosition.x, flowPosition.y, baseTransform);
    const logical = canvasToLogical(rawPoint.x, rawPoint.y);

    if (mode === "room") {
      createRoomAt(logical.x, logical.y);
      return;
    }

    setSelectedRoom(null);
    setSelectedEdge(null);
  };

  const onNodesChange = useMemo(() => (changes: NodeChange<Node<{ roomId: string }>>[]) => {
    setCanvasNodes((previous) => applyNodeChanges(changes, previous));
  }, []);

  const onNodeDragStop = useMemo<NodeDragHandler>(() => (_event, node) => {
    isDraggingRef.current = false;
    if (mode !== "select") {
      return;
    }
    const rawPoint = renderToRawPoint(node.position.x, node.position.y, renderTransform);
    const didMove = updateRoomPosition(node.id, rawPoint.x, rawPoint.y);
    if (didMove && layoutMode !== "none") {
      clearLayout();
    }
  }, [clearLayout, layoutMode, mode, renderTransform, updateRoomPosition]);

  const onConnect = useMemo(() => (connectionAttempt: Connection) => {
    console.log("CONNECT FIRED:", connectionAttempt);

    const sourceRoomId = String(connectionAttempt.source || "");
    const targetRoomId = String(connectionAttempt.target || "");
    const sourceDirection = handleIdToDirection(String(connectionAttempt.sourceHandle || ""));
    const targetDirection = handleIdToDirection(String(connectionAttempt.targetHandle || ""));

    if (!sourceRoomId || !targetRoomId || !sourceDirection || !targetDirection) {
      return;
    }

    tryConnect(sourceRoomId, sourceDirection, targetRoomId, targetDirection);
  }, [tryConnect]);

  const previewOverlay = useMemo(() => {
    if (layoutMode !== "preview" || !shellRef.current) {
      return null;
    }

    const shellBounds = shellRef.current.getBoundingClientRect();
    const screenPositions = Object.entries(tidyTransform.positionsByRoomId).reduce<Record<string, { x: number; y: number }>>((accumulator, [roomId, point]) => {
      const screenPoint = reactFlow.flowToScreenPosition(point);
      accumulator[roomId] = {
        x: screenPoint.x - shellBounds.left,
        y: screenPoint.y - shellBounds.top,
      };
      return accumulator;
    }, {});

    const previewEdges = buildRenderedBuilderEdges({
      mode,
      selectedRoomId,
      selectedEdgeId,
      connection: { active: false, fromRoomId: null, fromDirection: null },
      zonePrefix: "",
      roomsById,
      roomIdByCoord: {},
    }, tidyTransform.positionsByRoomId);

    return { previewEdges, screenPositions };
  }, [layoutMode, mode, reactFlow, roomsById, selectedEdgeId, selectedRoomId, tidyTransform.positionsByRoomId, viewportState.x, viewportState.y, viewportState.zoom]);

  return (
    <div
      ref={shellRef}
      className={`builder-phase1-canvas-shell${mode === "room" ? " is-mode-room" : mode === "delete" ? " is-mode-delete" : ""}`}
    >
      <ReactFlow
        className="builder-reactflow-root builder-phase1-flow"
        nodes={canvasNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        nodesDraggable={true}
        nodesConnectable={true}
        elementsSelectable
        panOnDrag={true}
        panOnScroll={false}
        selectionOnDrag={false}
        zoomOnScroll
        zoomOnPinch
        zoomOnDoubleClick={false}
        connectionMode={ConnectionMode.Loose}
        proOptions={{ hideAttribution: true }}
        onConnectStart={(_event, params) => {
          console.log("CONNECT START", params);
          setActiveSourceHandleId(String(params?.handleId || "") || null);
        }}
        onConnectEnd={() => {
          console.log("CONNECT END");
          setActiveSourceHandleId(null);
        }}
        onMove={(_event, viewport) => {
          setZoomLevel(viewport.zoom);
          setViewportState(viewport);
        }}
        onNodeClick={(event, node) => {
          const eventTarget = event.target as HTMLElement | null;
          if (eventTarget?.closest(".builder-phase1-handle")) {
            return;
          }

          if (mode === "delete") {
            if (!window.confirm("Delete this room?")) {
              return;
            }
            deleteRoom(node.id);
            return;
          }

          if (mode !== "select") {
            return;
          }

          setSelectedEdge(null);
          setSelectedRoom(node.id);
        }}
        onPaneClick={onPaneClick}
        onEdgeClick={(_event, edge) => {
          setSelectedRoom(null);
          setSelectedEdge(edge.id);
        }}
        onConnect={onConnect}
        onNodesChange={onNodesChange}
        onNodeDragStart={() => {
          isDraggingRef.current = true;
          console.log("DRAG START");
        }}
        onNodeDrag={() => {
          console.log("DRAGGING");
        }}
        onNodeDragStop={onNodeDragStop}
      >
        <Background gap={GRID_SIZE} size={1} color="rgba(214, 176, 97, 0.14)" />
        <Controls showInteractive={false} />
        <MiniMap
          pannable
          zoomable
          position="bottom-right"
          style={{
            background: "rgba(19, 13, 9, 0.94)",
            border: "1px solid rgba(214, 176, 97, 0.22)",
          }}
          nodeColor={() => "rgba(214, 176, 97, 0.72)"}
          maskColor="rgba(8, 8, 7, 0.62)"
        />
      </ReactFlow>
      {previewOverlay ? (
        <div className="builder-phase1-layout-preview" aria-hidden="true">
          <svg className="builder-phase1-preview-layer">
            {previewOverlay.previewEdges.map((edge) => {
              const start = previewOverlay.screenPositions[edge.source];
              const end = previewOverlay.screenPositions[edge.target];
              if (!start || !end) {
                return null;
              }
              return (
                <path
                  key={`preview-${edge.id}`}
                  d={buildDirectionalPath(start, end, edge.data?.direction || "east")}
                  className="builder-phase1-preview-line is-layout-preview"
                />
              );
            })}
          </svg>
          {roomList.map((room) => {
            const point = previewOverlay.screenPositions[room.id];
            const meta = tidyTransform.metaByRoomId[room.id];
            if (!point) {
              return null;
            }
            return (
              <div
                key={`ghost-${room.id}`}
                className={`builder-phase1-ghost-node${meta?.locked ? " is-locked" : ""}${meta?.isHub ? " is-hub" : ""}${meta?.isCorridor ? " is-corridor" : ""}`}
                style={{
                  left: point.x - (ROOM_NODE_SIZE / 2),
                  top: point.y - (ROOM_NODE_SIZE / 2),
                  width: ROOM_NODE_SIZE,
                  height: ROOM_NODE_SIZE,
                }}
              />
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export function BuilderCanvas(props: BuilderCanvasProps) {
  return (
    <ReactFlowProvider>
      <BuilderCanvasSurface {...props} />
    </ReactFlowProvider>
  );
}