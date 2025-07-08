import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import {
  GitBranch,
  Filter,
  RotateCcw,
  Merge,
  Shuffle,
  Clock,
} from "lucide-react";

interface FlowNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
}

const FlowNode: React.FC<NodeProps<FlowNodeData>> = ({
  id,
  data,
  selected,
}) => {

  const isLoopNode = data.subtype === "FLOW_LOOP";
  const isIfNode = data.subtype === "FLOW_IF";

  const getSubtypeIcon = () => {
    switch (data.subtype) {
      case "FLOW_IF":
        return <GitBranch className="h-5 w-5 text-white" />;
      case "FLOW_FILTER":
        return <Filter className="h-5 w-5 text-white" />;
      case "FLOW_LOOP":
        return <RotateCcw className="h-5 w-5 text-white" />;
      case "FLOW_MERGE":
        return <Merge className="h-5 w-5 text-white" />;
      case "FLOW_SWITCH":
        return <Shuffle className="h-5 w-5 text-white" />;
      case "FLOW_WAIT":
        return <Clock className="h-5 w-5 text-white" />;
      default:
        return <GitBranch className="h-5 w-5 text-white" />;
    }
  };

  const getSubtypeLabel = () => {
    switch (data.subtype) {
      case "FLOW_IF":
        return "If Condition";
      case "FLOW_FILTER":
        return "Filter";
      case "FLOW_LOOP":
        return "Loop";
      case "FLOW_MERGE":
        return "Merge";
      case "FLOW_SWITCH":
        return "Switch";
      case "FLOW_WAIT":
        return "Wait";
      default:
        return "Flow Control";
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Rectangle */}
      <div
        className={`bg-gradient-to-r from-amber-100 to-amber-50 border-2 border-amber-300 rounded-lg px-4 py-3 min-w-[180px] shadow-lg hover:shadow-xl transition-all duration-200 ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div className="flex items-center space-x-2 mb-2">
          <div className="bg-amber-500 rounded p-1">{getSubtypeIcon()}</div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-amber-800">
              {data.label}
            </div>
            <div className="text-xs text-amber-600">{getSubtypeLabel()}</div>
          </div>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="w-3 h-3 bg-amber-500 border-2 border-white"
      />

      {/* Output Handles - Different flow nodes have different outputs */}
      {isLoopNode ? (
        <>
          {/* Loop Handle (top right) */}
          <Handle
            type="source"
            position={Position.Right}
            id="loop"
            style={{ top: "30%" }}
            className="w-3 h-3 bg-blue-500 border-2 border-white"
          />
          {/* Loop Label */}
          <div className="absolute right-4 top-[30%] transform -translate-y-1/2 text-xs text-blue-600 font-medium bg-white px-1 rounded">
            Loop
          </div>

          {/* Done Handle (bottom right) */}
          <Handle
            type="source"
            position={Position.Right}
            id="done"
            style={{ top: "70%" }}
            className="w-3 h-3 bg-green-500 border-2 border-white"
          />
          {/* Done Label */}
          <div className="absolute right-4 top-[70%] transform -translate-y-1/2 text-xs text-green-600 font-medium bg-white px-1 rounded">
            Done
          </div>
        </>
      ) : isIfNode ? (
        <>
          {/* True Handle (top right) */}
          <Handle
            type="source"
            position={Position.Right}
            id="true"
            style={{ top: "30%" }}
            className="w-3 h-3 bg-green-500 border-2 border-white"
          />
          {/* True Label */}
          <div className="absolute right-4 top-[30%] transform -translate-y-1/2 text-xs text-green-600 font-medium bg-white px-1 rounded">
            True
          </div>

          {/* False Handle (bottom right) */}
          <Handle
            type="source"
            position={Position.Right}
            id="false"
            style={{ top: "70%" }}
            className="w-3 h-3 bg-red-500 border-2 border-white"
          />
          {/* False Label */}
          <div className="absolute right-4 top-[70%] transform -translate-y-1/2 text-xs text-red-600 font-medium bg-white px-1 rounded">
            False
          </div>
        </>
      ) : (
        /* Single Output Handle for other flow nodes */
        <Handle
          type="source"
          position={Position.Right}
          id="output"
          className="w-3 h-3 bg-amber-500 border-2 border-white"
        />
      )}

      {/* Plus buttons positioned away from handles */}
      {isLoopNode ? (
        <>
          {/* Loop Plus Button */}
          <div
            onClick={() => data.onAddNode(id, "loop")}
            className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-5 h-5 bg-blue-500 border border-white rounded-full flex items-center justify-center cursor-pointer z-10 nodrag"
            style={{ top: "30%", right: "-20px", transform: "translateY(-50%)" }}
            title="Add loop node"
          >
            <div className="text-white text-xs font-bold">+</div>
          </div>

          {/* Done Plus Button */}
          <div
            onClick={() => data.onAddNode(id, "done")}
            className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-5 h-5 bg-green-500 border border-white rounded-full flex items-center justify-center cursor-pointer z-10 nodrag"
            style={{ top: "70%", right: "-20px", transform: "translateY(-50%)" }}
            title="Add done node"
          >
            <div className="text-white text-xs font-bold">+</div>
          </div>
        </>
      ) : isIfNode ? (
        <>
          {/* True Plus Button */}
          <div
            onClick={() => data.onAddNode(id, "true")}
            className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-5 h-5 bg-green-500 border border-white rounded-full flex items-center justify-center cursor-pointer z-10 nodrag"
            style={{ top: "30%", right: "-20px", transform: "translateY(-50%)" }}
            title="Add true node"
          >
            <div className="text-white text-xs font-bold">+</div>
          </div>

          {/* False Plus Button */}
          <div
            onClick={() => data.onAddNode(id, "false")}
            className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-5 h-5 bg-red-500 border border-white rounded-full flex items-center justify-center cursor-pointer z-10 nodrag"
            style={{ top: "70%", right: "-20px", transform: "translateY(-50%)" }}
            title="Add false node"
          >
            <div className="text-white text-xs font-bold">+</div>
          </div>
        </>
      ) : (
        /* Single Plus Button for other flow nodes */
        <div
          onClick={() => data.onAddNode(id, "output")}
          className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 w-5 h-5 bg-amber-500 border border-white rounded-full flex items-center justify-center cursor-pointer z-10 nodrag"
          style={{ top: "50%", right: "-20px", transform: "translateY(-50%)" }}
          title="Add connected node"
        >
          <div className="text-white text-xs font-bold">+</div>
        </div>
      )}
    </div>
  );
};

export default FlowNode;
