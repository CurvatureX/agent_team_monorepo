import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import {
  Plus,
  Users,
  Mail,
  MessageSquare,
  Hash,
  Smartphone,
  Monitor,
} from "lucide-react";

interface HumanInTheLoopNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
  onStartConnection?: (nodeId: string, handle: string) => void;
}

const HumanInTheLoopNode: React.FC<NodeProps<HumanInTheLoopNodeData>> = ({
  id,
  data,
  selected,
}) => {
  const handleAddNode = () => {
    data.onAddNode(id, "output");
  };

  // Get subtype-specific icon and styling
  const getSubtypeIcon = () => {
    switch (data.subtype) {
      case "HUMAN_GMAIL":
        return <Mail className="h-4 w-4 text-white" />;
      case "HUMAN_SLACK":
        return <Hash className="h-4 w-4 text-white" />;
      case "HUMAN_DISCORD":
        return <MessageSquare className="h-4 w-4 text-white" />;
      case "HUMAN_TELEGRAM":
        return <Smartphone className="h-4 w-4 text-white" />;
      case "HUMAN_APP":
        return <Monitor className="h-4 w-4 text-white" />;
      default:
        return <Users className="h-4 w-4 text-white" />;
    }
  };

  const getSubtypeLabel = () => {
    switch (data.subtype) {
      case "HUMAN_GMAIL":
        return "Gmail";
      case "HUMAN_SLACK":
        return "Slack";
      case "HUMAN_DISCORD":
        return "Discord";
      case "HUMAN_TELEGRAM":
        return "Telegram";
      case "HUMAN_APP":
        return "App";
      default:
        return "Human Input";
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Rounded rectangle for human interaction */}
      <div
        className={`bg-gradient-to-r from-amber-100 to-amber-50 border-2 border-amber-300 rounded-lg px-4 py-3 min-w-[200px] shadow-lg hover:shadow-xl transition-all duration-200 ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div className="flex items-center space-x-2 mb-2">
          <div className="bg-amber-500 rounded p-1">{getSubtypeIcon()}</div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-amber-800">
              {data.label}
            </div>
            <div className="text-xs text-amber-600">
              Human Input • {getSubtypeLabel()}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-center text-xs text-amber-600 border-t border-amber-200 pt-2">
          <Users className="h-3 w-3 mr-1" />
          <span>Awaiting human interaction</span>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className="w-3 h-3 bg-amber-500 border-2 border-white"
      />

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="w-3 h-3 bg-amber-500 border-2 border-white"
      />

      {/* Add Node Button positioned away from handle */}
      <button
        onClick={handleAddNode}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-amber-500 hover:bg-amber-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ top: "50%", right: "-20px", transform: "translateY(-50%)" }}
        title="Add connected node"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
};

export default HumanInTheLoopNode;
