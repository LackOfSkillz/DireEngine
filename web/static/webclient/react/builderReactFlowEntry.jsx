import React from 'react';
import { createRoot } from 'react-dom/client';
import BuilderMap from './BuilderMap.jsx';

const roots = new WeakMap();

export function mountBuilderReactFlow(container, props) {
  if (!container) {
    return null;
  }
  let record = roots.get(container);
  if (!record) {
    record = { root: createRoot(container), bridgeApi: {} };
    roots.set(container, record);
  }
  record.root.render(<BuilderMap {...props} bridgeApi={record.bridgeApi} />);
  return record;
}

export function setBuilderReactFlowSelectedRoomColor(container, color) {
  const record = container ? roots.get(container) : null;
  record?.bridgeApi?.setSelectedRoomColor?.(color);
}

export function updateBuilderReactFlowSelectedEdge(container, updates) {
  const record = container ? roots.get(container) : null;
  record?.bridgeApi?.updateSelectedEdge?.(updates || {});
}

export function deleteBuilderReactFlowSelectedEdge(container) {
  const record = container ? roots.get(container) : null;
  record?.bridgeApi?.deleteSelectedEdge?.();
}

export function unmountBuilderReactFlow(container) {
  const record = container ? roots.get(container) : null;
  if (!record) {
    return;
  }
  record.root.unmount();
  roots.delete(container);
}