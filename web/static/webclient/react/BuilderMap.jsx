import React, { useEffect, useMemo, useState } from 'react';
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  applyEdgeChanges,
  applyNodeChanges,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

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

function BuilderMapSurface({ nodes: nextNodes, edges: nextEdges, selectedRoomId, viewportRequest, onSelectRoom, onMoveRoom }) {
  const [nodes, setNodes] = useState(nextNodes || []);
  const [edges, setEdges] = useState(nextEdges || []);
  const reactFlow = useReactFlow();

  useEffect(() => {
    setNodes(nextNodes || []);
  }, [nextNodes]);

  useEffect(() => {
    setEdges(nextEdges || []);
  }, [nextEdges]);

  useEffect(() => {
    if (!viewportRequest?.token) {
      return;
    }
    if (viewportRequest.type === 'fit') {
      reactFlow.fitView({ duration: 180, padding: 0.24 });
      return;
    }
    if (viewportRequest.type === 'center' && selectedRoomId) {
      const selectedNode = (nextNodes || []).find((node) => Number(node.id) === Number(selectedRoomId));
      if (selectedNode) {
        reactFlow.setCenter(selectedNode.position.x, selectedNode.position.y, { duration: 180, zoom: Math.max(reactFlow.getZoom(), 1.4) });
      }
    }
  }, [nextNodes, reactFlow, selectedRoomId, viewportRequest]);

  const nodeTypes = useMemo(() => ({ builderRoom: RoomNode }), []);

  return (
    <ReactFlow
      className="builder-reactflow-root"
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      minZoom={0.1}
      maxZoom={2.5}
      onNodeClick={(_, node) => onSelectRoom?.(Number(node.id))}
      onNodesChange={(changes) => setNodes((current) => applyNodeChanges(changes, current))}
      onEdgesChange={(changes) => setEdges((current) => applyEdgeChanges(changes, current))}
      onNodeDragStop={(_, node) => {
        onMoveRoom?.({
          roomId: Number(node.id),
          map_x: Math.round(node.position.x),
          map_y: Math.round(node.position.y),
        });
      }}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={24} size={1} color="rgba(214, 176, 97, 0.14)" />
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