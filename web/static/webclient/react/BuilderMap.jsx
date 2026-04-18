import React, { useEffect, useMemo, useRef } from 'react';
import {
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

function RoomNode({ data, selected }) {
  const showLabel = Boolean(selected || data?.selected);
  return (
    <div className={`builder-reactflow-node${showLabel ? ' is-selected' : ''}`}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <div className="builder-reactflow-node-core" style={{ background: data?.color || '#5f8f57' }} />
      {showLabel ? <div className="builder-reactflow-node-label">{data?.label || 'Room'}</div> : null}
    </div>
  );
}

function fitViewportForNodes(nodes, width, height) {
  if (!Array.isArray(nodes) || !nodes.length || !Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return DEFAULT_VIEWPORT;
  }
  const xs = nodes.map((node) => Number(node?.position?.x || 0));
  const ys = nodes.map((node) => Number(node?.position?.y || 0));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const boundsWidth = Math.max(120, maxX - minX + 14);
  const boundsHeight = Math.max(120, maxY - minY + 14);
  const usableWidth = Math.max(80, width - VIEWPORT_PADDING * 2);
  const usableHeight = Math.max(80, height - VIEWPORT_PADDING * 2);
  const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.min(usableWidth / boundsWidth, usableHeight / boundsHeight)));
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  return {
    x: width / 2 - centerX * zoom,
    y: height / 2 - centerY * zoom,
    zoom,
  };
}

function BuilderMapSurface({
  nodes = [],
  edges = [],
  selectedRoomId,
  viewportRequest,
  onSelectRoom,
}) {
  const reactFlow = useReactFlow();
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (!viewportRequest?.token) {
      return;
    }
    if (viewportRequest.type === 'fit') {
      const bounds = wrapperRef.current?.getBoundingClientRect();
      const viewport = fitViewportForNodes(nodes, bounds?.width || 0, bounds?.height || 0);
      reactFlow.setViewport(viewport, { duration: 180 });
      return;
    }
    if (viewportRequest.type === 'center' && selectedRoomId) {
      const selectedNode = (nodes || []).find((node) => String(node.id) === String(selectedRoomId));
      if (selectedNode) {
        reactFlow.setCenter(selectedNode.position.x, selectedNode.position.y, { duration: 180, zoom: Math.max(reactFlow.getZoom(), DEFAULT_VIEWPORT.zoom) });
      }
    }
  }, [nodes, reactFlow, selectedRoomId, viewportRequest]);

  const nodeTypes = useMemo(() => ({ builderRoom: RoomNode }), []);

  return (
    <div ref={wrapperRef} style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        className="builder-reactflow-root"
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        defaultViewport={DEFAULT_VIEWPORT}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
        panOnDrag
        zoomOnScroll
        onNodeClick={(_, node) => onSelectRoom?.(String(node.id))}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={BACKGROUND_GRID_SIZE} size={1} color="rgba(214, 176, 97, 0.14)" />
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