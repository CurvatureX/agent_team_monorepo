import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Database, HardDrive, Brain, Layers, FileText, Zap, Plus } from "lucide-react";

interface MemoryNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
  onStartConnection?: (nodeId: string, handle: string) => void;
}

const MemoryNode: React.FC<NodeProps<MemoryNodeData>> = ({
  id,
  data,
  selected,
}) => {
  const handleAddNode = () => {
    data.onAddNode(id, "input");
  };
  const getSubtypeIcon = () => {
    switch (data.subtype) {
      case "MEMORY_SIMPLE":
        return <Database className="h-4 w-4 text-white" />;
      case "MEMORY_BUFFER":
        return <HardDrive className="h-4 w-4 text-white" />;
      case "MEMORY_KNOWLEDGE":
        return <Brain className="h-4 w-4 text-white" />;
      case "MEMORY_VECTOR_STORE":
        return <Layers className="h-4 w-4 text-white" />;
      case "MEMORY_DOCUMENT":
        return <FileText className="h-4 w-4 text-white" />;
      case "MEMORY_EMBEDDING":
        return <Zap className="h-4 w-4 text-white" />;
      default:
        return <Database className="h-4 w-4 text-white" />;
    }
  };

  const getSubtypeLabel = () => {
    switch (data.subtype) {
      case "MEMORY_SIMPLE":
        return "Simple";
      case "MEMORY_BUFFER":
        return "Buffer";
      case "MEMORY_KNOWLEDGE":
        return "Knowledge";
      case "MEMORY_VECTOR_STORE":
        return "Vector Store";
      case "MEMORY_DOCUMENT":
        return "Document";
      case "MEMORY_EMBEDDING":
        return "Embedding";
      default:
        return "Memory";
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Circle */}
      <div
        className={`bg-gradient-to-br from-indigo-100 to-indigo-50 border-2 border-indigo-300 rounded-full w-[100px] h-[100px] shadow-lg hover:shadow-xl transition-all duration-200 flex flex-col justify-center items-center ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div className="bg-indigo-500 rounded-full p-2 mb-1">
          {getSubtypeIcon()}
        </div>

        <div className="text-center px-2">
          <div className="text-xs font-semibold text-indigo-800 leading-tight">
            {data.label.length > 10
              ? `${data.label.substring(0, 10)}...`
              : data.label}
          </div>
          <div className="text-xs text-indigo-600 mt-0.5">{getSubtypeLabel()}</div>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        className="w-3 h-3 bg-indigo-500 border-2 border-white"
      />

      {/* Add Node Button positioned away from handle */}
      <button
        onClick={handleAddNode}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-indigo-500 hover:bg-indigo-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ top: "-20px", left: "50%", transform: "translateX(-50%)" }}
        title="Add connected node"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
};

export default MemoryNode;
