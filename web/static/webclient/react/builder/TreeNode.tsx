import { useState } from "react";
import type { TreeNodeData } from "./BuilderTypes";

type TreeNodeProps = {
  node: TreeNodeData;
  depth?: number;
  defaultOpen?: boolean;
  selectedNode?: TreeNodeData | null;
  onSelect?: (node: TreeNodeData) => void;
};

export default function TreeNode({ node, depth = 0, defaultOpen = false, selectedNode = null, onSelect }: TreeNodeProps) {
  const [open, setOpen] = useState(defaultOpen);
  const hasChildren = Array.isArray(node.children) && node.children.length > 0;
  const isSelected = node.id === selectedNode?.id;

  return (
    <div className="tree-node" data-type={node.type}>
      <div
        className={`tree-label ${isSelected ? "selected" : ""}`.trim()}
        style={{ paddingLeft: depth * 12 }}
        onClick={() => onSelect?.(node)}
      >
        {hasChildren ? (
          <span
            className={`tree-arrow ${open ? "open" : ""}`}
            onClick={(event) => {
              event.stopPropagation();
              setOpen((previous) => !previous);
            }}
          >
            ▶
          </span>
        ) : (
          <span className="tree-arrow" aria-hidden="true">&nbsp;</span>
        )}
        {node.label}
      </div>

      {open && hasChildren ? (
        <div className="tree-children">
          {node.children?.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedNode={selectedNode}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}