import React from "react";
import { Handle, Position, NodeProps } from "reactflow";
import { Wrench, Calendar, FileText, Mail, Globe, Code, Plus } from "lucide-react";

interface ToolNodeData {
  label: string;
  nodeType: string;
  subtype?: string;
  onAddNode: (nodeId: string, handle: string) => void;
  onStartConnection?: (nodeId: string, handle: string) => void;
}

const ToolNode: React.FC<NodeProps<ToolNodeData>> = ({
  id,
  data,
  selected,
}) => {
  const handleAddNode = () => {
    data.onAddNode(id, "input");
  };
  const getSubtypeIcon = () => {
    switch (data.subtype) {
      case "TOOL_GOOGLE_CALENDAR_MCP":
        return <Calendar className="h-4 w-4 text-white" />;
      case "TOOL_NOTION_MCP":
        return <FileText className="h-4 w-4 text-white" />;
      case "TOOL_CALENDAR":
        return <Calendar className="h-4 w-4 text-white" />;
      case "TOOL_EMAIL":
        return <Mail className="h-4 w-4 text-white" />;
      case "TOOL_HTTP":
        return <Globe className="h-4 w-4 text-white" />;
      case "TOOL_CODE_EXECUTION":
        return <Code className="h-4 w-4 text-white" />;
      default:
        return <Wrench className="h-4 w-4 text-white" />;
    }
  };

  const getSubtypeLabel = () => {
    switch (data.subtype) {
      case "TOOL_GOOGLE_CALENDAR_MCP":
        return "Google Cal MCP";
      case "TOOL_NOTION_MCP":
        return "Notion MCP";
      case "TOOL_CALENDAR":
        return "Calendar";
      case "TOOL_EMAIL":
        return "Email";
      case "TOOL_HTTP":
        return "HTTP";
      case "TOOL_CODE_EXECUTION":
        return "Code Exec";
      default:
        return "Tool";
    }
  };

  return (
    <div className="relative group">
      {/* Main Node - Circle */}
      <div
        className={`bg-gradient-to-br from-emerald-100 to-emerald-50 border-2 border-emerald-300 rounded-full w-[100px] h-[100px] shadow-lg hover:shadow-xl transition-all duration-200 flex flex-col justify-center items-center ${
          selected ? "ring-2 ring-offset-2 ring-blue-500" : ""
        }`}
      >
        <div className="bg-emerald-500 rounded-full p-2 mb-1">
          {getSubtypeIcon()}
        </div>

        <div className="text-center px-2">
          <div className="text-xs font-semibold text-emerald-800 leading-tight">
            {data.label.length > 10
              ? `${data.label.substring(0, 10)}...`
              : data.label}
          </div>
          <div className="text-xs text-emerald-600 mt-0.5">{getSubtypeLabel()}</div>
        </div>
      </div>

      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        id="input"
        className="w-3 h-3 bg-emerald-500 border-2 border-white"
      />

      {/* Add Node Button positioned away from handle */}
      <button
        onClick={handleAddNode}
        className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full p-1 shadow-lg z-10 nodrag"
        style={{ top: "-20px", left: "50%", transform: "translateX(-50%)" }}
        title="Add connected node"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
};

export default ToolNode;
