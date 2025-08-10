import React from 'react';
import { NodeProps } from 'reactflow';
import { Wrench, Code } from 'lucide-react';
import BaseNode from './BaseNode';

const ToolNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'TOOL_FUNCTION':
        return Code;
      default:
        return Wrench;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="Tool"
      color="cyan"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'TOOL_FUNCTION' && 'Function Call'}
      </div>
    </BaseNode>
  );
};

export default ToolNode; 