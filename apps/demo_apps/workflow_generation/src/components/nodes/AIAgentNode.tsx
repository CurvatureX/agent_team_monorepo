import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Plus, Bot, Database, Wrench } from "lucide-react";

interface AIAgentNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
  onStartConnection?: (nodeId: string, handle: string) => void;
}

const AIAgentNode: React.FC<NodeProps<AIAgentNodeData>> = ({
  id,
  data,
  selected,
}) => {
  const handleAddNode = () => {
    data.onAddNode(id, "output");
  };

  const handleAddMemory = () => {
    data.onAddNode(id, "memory");
  };

  const handleAddTool = () => {
    data.onAddNode(id, "tool");
  };

  const getSubtypeLabel = () => {
    switch (data.subtype) {
      case "AI_AGENT":
        return "AI Agent";
      case "AI_CLASSIFIER":
        return "AI Classifier";
      default:
        return "AI Agent";
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Rectangle */}
      <div
        className={`bg-gradient-to-r from-blue-100 to-blue-50 border-2 border-blue-300 rounded-lg px-4 py-3 min-w-[220px] shadow-lg hover:shadow-xl transition-all duration-200 ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div className="flex items-center space-x-2 mb-2">
          <div className="bg-blue-500 rounded p-1">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-blue-800">
              {data.label}
            </div>
            <div className="text-xs text-blue-600">{getSubtypeLabel()}</div>
          </div>
        </div>

        {/* Connection indicators */}
        <div className="flex justify-between text-xs text-blue-500 border-t border-blue-200 pt-2">
          <div className="flex items-center space-x-1">
            <Database className="h-3 w-3" />
            <span>Memory</span>
          </div>
          <div className="flex items-center space-x-1">
            <Wrench className="h-3 w-3" />
            <span>Tool</span>
          </div>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="w-3 h-3 bg-blue-500 border-2 border-white"
      />

      {/* Memory Handle (bottom left) */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="memory"
        style={{ left: "25%" }}
        className="w-3 h-3 bg-purple-500 border-2 border-white"
      />

      {/* Tool Handle (bottom right) */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="tool"
        style={{ left: "75%" }}
        className="w-3 h-3 bg-green-500 border-2 border-white"
      />

      {/* Add Node Buttons positioned away from handles */}
      <button
        onClick={handleAddNode}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-blue-500 hover:bg-blue-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ top: "50%", right: "-20px", transform: "translateY(-50%)" }}
        title="Add connected node"
      >
        <Plus className="h-3 w-3" />
      </button>

      {/* Add Memory Button */}
      <button
        onClick={handleAddMemory}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-purple-500 hover:bg-purple-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ left: "25%", bottom: "-20px", transform: "translateX(-50%)" }}
        title="Add memory node"
      >
        <Database className="h-3 w-3" />
      </button>

      {/* Add Tool Button */}
      <button
        onClick={handleAddTool}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-green-500 hover:bg-green-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ left: "75%", bottom: "-20px", transform: "translateX(-50%)" }}
        title="Add tool node"
      >
        <Wrench className="h-3 w-3" />
      </button>
    </div>
  );
};

export default AIAgentNode;
