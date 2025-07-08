import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import {
  Plus,
  Play,
  ExternalLink,
  Code,
  Globe,
  Image,
  Search,
  Database,
  FileText,
  RefreshCw,
  Github,
  Calendar,
  Trello,
  Mail,
  Hash,
  Webhook,
  Bell,
} from "lucide-react";

interface ActionNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
  onStartConnection?: (nodeId: string, handle: string) => void;
}

const ActionNode: React.FC<NodeProps<ActionNodeData>> = ({
  id,
  data,
  selected,
}) => {
  const handleAddNode = () => {
    data.onAddNode(id, "output");
  };

  const isExternalAction = data.nodeType === "external_action";

  const getSubtypeIcon = () => {
    if (isExternalAction) {
      switch (data.subtype) {
        case "EXTERNAL_GITHUB":
          return <Github className="h-5 w-5 text-white" />;
        case "EXTERNAL_GOOGLE_CALENDAR":
          return <Calendar className="h-5 w-5 text-white" />;
        case "EXTERNAL_TRELLO":
          return <Trello className="h-5 w-5 text-white" />;
        case "EXTERNAL_EMAIL":
          return <Mail className="h-5 w-5 text-white" />;
        case "EXTERNAL_SLACK":
          return <Hash className="h-5 w-5 text-white" />;
        case "EXTERNAL_API_CALL":
          return <Globe className="h-5 w-5 text-white" />;
        case "EXTERNAL_WEBHOOK":
          return <Webhook className="h-5 w-5 text-white" />;
        case "EXTERNAL_NOTIFICATION":
          return <Bell className="h-5 w-5 text-white" />;
        default:
          return <ExternalLink className="h-5 w-5 text-white" />;
      }
    } else {
      switch (data.subtype) {
        case "ACTION_RUN_CODE":
          return <Code className="h-5 w-5 text-white" />;
        case "ACTION_SEND_HTTP_REQUEST":
          return <Globe className="h-5 w-5 text-white" />;
        case "ACTION_PARSE_IMAGE":
          return <Image className="h-5 w-5 text-white" />;
        case "ACTION_WEB_SEARCH":
          return <Search className="h-5 w-5 text-white" />;
        case "ACTION_DATABASE_OPERATION":
          return <Database className="h-5 w-5 text-white" />;
        case "ACTION_FILE_OPERATION":
          return <FileText className="h-5 w-5 text-white" />;
        case "ACTION_DATA_TRANSFORMATION":
          return <RefreshCw className="h-5 w-5 text-white" />;
        default:
          return <Play className="h-5 w-5 text-white" />;
      }
    }
  };

  const getSubtypeLabel = () => {
    if (isExternalAction) {
      switch (data.subtype) {
        case "EXTERNAL_GITHUB":
          return "GitHub";
        case "EXTERNAL_GOOGLE_CALENDAR":
          return "Google Calendar";
        case "EXTERNAL_TRELLO":
          return "Trello";
        case "EXTERNAL_EMAIL":
          return "Email";
        case "EXTERNAL_SLACK":
          return "Slack";
        case "EXTERNAL_API_CALL":
          return "API Call";
        case "EXTERNAL_WEBHOOK":
          return "Webhook";
        case "EXTERNAL_NOTIFICATION":
          return "Notification";
        default:
          return "External Action";
      }
    } else {
      switch (data.subtype) {
        case "ACTION_RUN_CODE":
          return "Run Code";
        case "ACTION_SEND_HTTP_REQUEST":
          return "HTTP Request";
        case "ACTION_PARSE_IMAGE":
          return "Parse Image";
        case "ACTION_WEB_SEARCH":
          return "Web Search";
        case "ACTION_DATABASE_OPERATION":
          return "Database Op";
        case "ACTION_FILE_OPERATION":
          return "File Operation";
        case "ACTION_DATA_TRANSFORMATION":
          return "Data Transform";
        default:
          return "Action Node";
      }
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Square */}
      <div
        className={`${
          isExternalAction
            ? "bg-gradient-to-r from-purple-100 to-purple-50 border-purple-300"
            : "bg-gradient-to-r from-green-100 to-green-50 border-green-300"
        } border-2 rounded-lg px-4 py-3 w-[160px] h-[120px] shadow-lg hover:shadow-xl transition-all duration-200 flex flex-col justify-center items-center ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div
          className={`${
            isExternalAction ? "bg-purple-500" : "bg-green-500"
          } rounded p-2 mb-2`}
        >
          {getSubtypeIcon()}
        </div>

        <div className="text-center">
          <div
            className={`text-sm font-semibold ${
              isExternalAction ? "text-purple-800" : "text-green-800"
            }`}
          >
            {data.label}
          </div>
          <div
            className={`text-xs ${
              isExternalAction ? "text-purple-600" : "text-green-600"
            } mt-1`}
          >
            {getSubtypeLabel()}
          </div>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        className={`w-3 h-3 ${
          isExternalAction ? "bg-purple-500" : "bg-green-500"
        } border-2 border-white`}
      />

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        className={`w-3 h-3 ${
          isExternalAction ? "bg-purple-500" : "bg-green-500"
        } border-2 border-white`}
      />

      {/* Add Node Button */}
      <button
        onClick={handleAddNode}
        className={`absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 ${
          isExternalAction
            ? "bg-purple-500 hover:bg-purple-600"
            : "bg-green-500 hover:bg-green-600"
        } text-white rounded-full p-1 shadow-lg z-10 nodrag`}
        style={{ top: "50%", right: "-20px", transform: "translateY(-50%)" }}
        title="Add connected node"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
};

export default ActionNode;
