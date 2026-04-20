import React, { useEffect, useMemo, useRef } from 'react';
import {
  BaseEdge,
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const BACKGROUND_GRID_SIZE = 60;
const DEFAULT_VIEWPORT = { x: 0, y: 0, zoom: 0.8 };
const VIEWPORT_PADDING = 48;
const MIN_ZOOM = 0.05;
const MAX_ZOOM = 4;

function snapToGrid(value, gridSize) {
  const normalizedGridSize = Math.max(1, Number(gridSize) || BACKGROUND_GRID_SIZE);
  return Math.round(Number(value || 0) / normalizedGridSize) * normalizedGridSize;
}

function RoomNode({ data, selected }) {
  const showLabel = Boolean(selected || data?.selected);
  return (
    <div className={`builder-reactflow-node${showLabel ? ' is-selected' : ''}`}>
      <Handle id="target-top" type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle id="target-right" type="target" position={Position.Right} style={{ opacity: 0 }} />
      <Handle id="target-bottom" type="target" position={Position.Bottom} style={{ opacity: 0 }} />
      <Handle id="target-left" type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle id="source-top" type="source" position={Position.Top} style={{ opacity: 0 }} />
      <Handle id="source-right" type="source" position={Position.Right} style={{ opacity: 0 }} />
      <Handle id="source-bottom" type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <Handle id="source-left" type="source" position={Position.Left} style={{ opacity: 0 }} />
      <div className="builder-reactflow-node-core" style={{ background: data?.color || '#5f8f57' }} />
      {showLabel ? <div className="builder-reactflow-node-label">{data?.label || 'Room'}</div> : null}
    </div>
  );
}

function builderDirectionalPath({ sourceX, sourceY, targetX, targetY, direction }) {
  const normalizedDirection = String(direction || '').toLowerCase();
  if (["northeast", "northwest", "southeast", "southwest"].includes(normalizedDirection)) {
    return `M ${sourceX},${sourceY} L ${targetX},${targetY}`;
  }
  if (["east", "west"].includes(normalizedDirection)) {
    if (sourceY === targetY) {
      return `M ${sourceX},${sourceY} L ${targetX},${targetY}`;
    }
    const midX = sourceX + (targetX - sourceX) / 2;
    return `M ${sourceX},${sourceY} H ${midX} V ${targetY} H ${targetX}`;
  }
  if (["north", "south"].includes(normalizedDirection)) {
    if (sourceX === targetX) {
      return `M ${sourceX},${sourceY} L ${targetX},${targetY}`;
    }
    const midY = sourceY + (targetY - sourceY) / 2;
    return `M ${sourceX},${sourceY} V ${midY} H ${targetX} V ${targetY}`;
  }
  return `M ${sourceX},${sourceY} L ${targetX},${targetY}`;
}

function BuilderDirectionalEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
  style,
  markerEnd,
  markerStart,
  interactionWidth,
}) {
  const path = builderDirectionalPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    direction: data?.direction,
  });
  return (
    <BaseEdge
      id={id}
      path={path}
      style={style}
      markerEnd={markerEnd}
      markerStart={markerStart}
      interactionWidth={interactionWidth}
    />
  );
}

function BuilderMapSurface({
  nodes = [],
  edges = [],
  selectedRoomId,
  viewportRequest,
  gridSize = BACKGROUND_GRID_SIZE,
  coordinateMode = 'legacy',
  onSelectRoom,
  onMoveRoom,
}) {
  const reactFlow = useReactFlow();
  const wrapperRef = useRef(null);
  const lastViewportTokenRef = useRef(null);
  const fitRequestToken = viewportRequest?.type === 'fit' ? viewportRequest.token : 0;
  const flowKey = fitRequestToken ? `fit-${fitRequestToken}` : 'builder-reactflow';

  useEffect(() => {
    if (!viewportRequest?.token) {
      return;
    }
    if (lastViewportTokenRef.current === viewportRequest.token) {
      return;
    }
    lastViewportTokenRef.current = viewportRequest.token;
    if (viewportRequest.type === 'center' && selectedRoomId) {
      const selectedNode = (nodes || []).find((node) => String(node.id) === String(selectedRoomId));
      if (selectedNode) {
        reactFlow.setCenter(selectedNode.position.x, selectedNode.position.y, { duration: 180, zoom: Math.max(reactFlow.getZoom(), DEFAULT_VIEWPORT.zoom) });
      }
    }
  }, [nodes, reactFlow, selectedRoomId, viewportRequest]);

  const nodeTypes = useMemo(() => ({ builderRoom: RoomNode }), []);
  const edgeTypes = useMemo(() => ({ builderDirectional: BuilderDirectionalEdge }), []);

  return (
    <div ref={wrapperRef} style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        key={flowKey}
        className="builder-reactflow-root"
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultViewport={DEFAULT_VIEWPORT}
        fitView={Boolean(fitRequestToken)}
        fitViewOptions={{ padding: 0.3, includeHiddenNodes: true }}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        snapToGrid
        snapGrid={[gridSize, gridSize]}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        panOnDrag
        zoomOnScroll
        onNodeClick={(_, node) => onSelectRoom?.(String(node.id))}
        onNodeDragStop={(_, node) => {
          const snappedX = snapToGrid(node?.position?.x, gridSize);
          const snappedY = snapToGrid(node?.position?.y, gridSize);
          onMoveRoom?.({
            roomId: String(node.id),
            map_x: coordinateMode === 'absolute' ? Math.round(snappedX) : Math.round(snappedX / gridSize),
            map_y: coordinateMode === 'absolute' ? Math.round(snappedY) : Math.round(snappedY / gridSize),
          });
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={gridSize} size={1} color="rgba(214, 176, 97, 0.14)" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

export default function BuilderMap(props) {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlowProvider>
        <BuilderMapSurface {...props} />
      </ReactFlowProvider>
    </div>
  );
}