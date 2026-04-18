import React, { useEffect, useMemo } from 'react';
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

const GRID_SIZE = 80;

function RoomNode({ data, selected }) {
  const showLabel = Boolean(selected || data?.selected);
  return (
    <div className={`builder-reactflow-node${showLabel ? ' is-selected' : ''}`}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      <div className="builder-reactflow-node-core" />
      {showLabel ? <div className="builder-reactflow-node-label">{data?.label || 'Room'}</div> : null}
    </div>
  );
}

function snapToGrid(value) {
  return Math.round(Number(value || 0) / GRID_SIZE) * GRID_SIZE;
}

function BuilderMapSurface({
  nodes = [],
  edges = [],
  selectedRoomId,
  viewportRequest,
  onSelectRoom,
  onMoveRoom,
  onConnectRooms,
  onDeleteEdges,
}) {
  const reactFlow = useReactFlow();

  useEffect(() => {
    if (!viewportRequest?.token) {
      return;
    }
    if (viewportRequest.type === 'fit') {
      reactFlow.fitView({ duration: 180, padding: 0.24 });
      return;
    }
    if (viewportRequest.type === 'center' && selectedRoomId) {
      const selectedNode = (nodes || []).find((node) => String(node.id) === String(selectedRoomId));
      if (selectedNode) {
        reactFlow.setCenter(selectedNode.position.x, selectedNode.position.y, { duration: 180, zoom: Math.max(reactFlow.getZoom(), 1.4) });
      }
    }
  }, [nodes, reactFlow, selectedRoomId, viewportRequest]);

  const nodeTypes = useMemo(() => ({ builderRoom: RoomNode }), []);

  return (
    <ReactFlow
      className="builder-reactflow-root"
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      snapToGrid
      snapGrid={[GRID_SIZE, GRID_SIZE]}
      minZoom={0.1}
      maxZoom={2.5}
      nodesDraggable
      nodesConnectable
      elementsSelectable
      panOnDrag
      zoomOnScroll
      onNodeClick={(_, node) => onSelectRoom?.(String(node.id))}
      onConnect={({ source, target }) => {
        if (!source || !target) {
          return;
        }
        onConnectRooms?.({
          source: String(source),
          target: String(target),
        });
      }}
      onEdgesDelete={(deletedEdges) => onDeleteEdges?.(deletedEdges || [])}
      onNodeDragStop={(_, node) => {
        const snappedX = snapToGrid(node.position.x);
        const snappedY = snapToGrid(node.position.y);
        onMoveRoom?.({
          roomId: String(node.id),
          map_x: snappedX,
          map_y: snappedY,
        });
      }}
      deleteKeyCode={['Backspace', 'Delete']}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={GRID_SIZE} size={1} color="rgba(214, 176, 97, 0.14)" />
      <Controls showInteractive={false} />
    </ReactFlow>
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