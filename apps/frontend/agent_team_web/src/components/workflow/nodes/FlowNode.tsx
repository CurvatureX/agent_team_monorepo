import React from 'react';
import { NodeProps } from 'reactflow';
import { GitBranch, Filter, ToggleLeft } from 'lucide-react';
import BaseNode from './BaseNode';

const FlowNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'FLOW_FILTER':
        return Filter;
      case 'FLOW_SWITCH':
        return ToggleLeft;
      default:
        return GitBranch;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="Flow Control"
      color="purple"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'FLOW_FILTER' && 'Condition Filter'}
        {data?.subtype === 'FLOW_SWITCH' && 'Branch Selection'}
      </div>
    </BaseNode>
  );
};

export default FlowNode; 