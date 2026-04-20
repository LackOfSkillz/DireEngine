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
    record = { root: createRoot(container) };
    roots.set(container, record);
  }
  record.root.render(<BuilderMap {...props} />);
  return record;
}

export function unmountBuilderReactFlow(container) {
  const record = container ? roots.get(container) : null;
  if (!record) {
    return;
  }
  record.root.unmount();
  roots.delete(container);
}