import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import {
  Plus,
  Zap,
  MessageSquare,
  Webhook,
  Clock,
  Play,
  Mail,
  FileText,
  Calendar,
} from "lucide-react";

interface TriggerNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
  onStartConnection?: (nodeId: string, handle: string) => void;
}

const TriggerNode: React.FC<NodeProps<TriggerNodeData>> = ({
  id,
  data,
  selected,
}) => {
  const handleAddNode = () => {
    data.onAddNode(id, "output");
  };

  const getSubtypeIcon = () => {
    switch (data.subtype) {
      case "TRIGGER_CHAT":
        return <MessageSquare className="h-4 w-4 text-white" />;
      case "TRIGGER_WEBHOOK":
        return <Webhook className="h-4 w-4 text-white" />;
      case "TRIGGER_CRON":
        return <Clock className="h-4 w-4 text-white" />;
      case "TRIGGER_MANUAL":
        return <Play className="h-4 w-4 text-white" />;
      case "TRIGGER_EMAIL":
        return <Mail className="h-4 w-4 text-white" />;
      case "TRIGGER_FORM":
        return <FileText className="h-4 w-4 text-white" />;
      case "TRIGGER_CALENDAR":
        return <Calendar className="h-4 w-4 text-white" />;
      default:
        return <Zap className="h-4 w-4 text-white" />;
    }
  };

  const getSubtypeLabel = () => {
    switch (data.subtype) {
      case "TRIGGER_CHAT":
        return "Chat";
      case "TRIGGER_WEBHOOK":
        return "Webhook";
      case "TRIGGER_CRON":
        return "Schedule";
      case "TRIGGER_MANUAL":
        return "Manual";
      case "TRIGGER_EMAIL":
        return "Email";
      case "TRIGGER_FORM":
        return "Form";
      case "TRIGGER_CALENDAR":
        return "Calendar";
      default:
        return "Trigger";
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Semi-rounded box */}
      <div
        className={`bg-gradient-to-r from-orange-100 to-orange-50 border-2 border-orange-300 rounded-2xl px-4 py-3 min-w-[200px] shadow-lg hover:shadow-xl transition-all duration-200 ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div className="flex items-center space-x-2">
          <div className="bg-orange-500 rounded-full p-1">
            {getSubtypeIcon()}
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-orange-800">
              {data.label}
            </div>
            <div className="text-xs text-orange-600">
              {data.subtype ? getSubtypeLabel() : "Trigger Node"}
            </div>
          </div>
        </div>
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className="w-3 h-3 bg-orange-500 border-2 border-white"
      />

      {/* Add Node Button positioned away from handle */}
      <button
        onClick={handleAddNode}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-blue-500 hover:bg-blue-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ top: "50%", right: "-20px", transform: "translateY(-50%)" }}
        title="Add connected node"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
};

export default TriggerNode;
