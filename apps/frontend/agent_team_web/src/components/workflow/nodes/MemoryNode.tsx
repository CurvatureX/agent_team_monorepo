import React from 'react';
import { NodeProps } from 'reactflow';
import { HardDrive, Save } from 'lucide-react';
import BaseNode from './BaseNode';

const MemoryNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'MEMORY_STORE':
        return Save;
      default:
        return HardDrive;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="Memory"
      color="orange"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'MEMORY_STORE' && 'Store Data'}
      </div>
    </BaseNode>
  );
};

export default MemoryNode; 