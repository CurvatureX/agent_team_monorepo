import React from 'react';
import { NodeProps } from 'reactflow';
import { Zap, Database, Send } from 'lucide-react';
import BaseNode from './BaseNode';

const ActionNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'ACTION_DATA_TRANSFORMATION':
        return Database;
      case 'ACTION_HTTP_REQUEST':
        return Send;
      default:
        return Zap;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="Action"
      color="amber"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'ACTION_DATA_TRANSFORMATION' && 'Data Transformation'}
        {data?.subtype === 'ACTION_HTTP_REQUEST' && 'HTTP Request'}
      </div>
    </BaseNode>
  );
};

export default ActionNode; 