import React from 'react';
import { NodeProps } from 'reactflow';
import { ExternalLink, Github, MessageSquare } from 'lucide-react';
import BaseNode from './BaseNode';

const ExternalActionNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'EXTERNAL_GITHUB':
        return Github;
      case 'EXTERNAL_SLACK':
        return MessageSquare;
      default:
        return ExternalLink;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="External Action"
      color="blue"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'EXTERNAL_GITHUB' && 'GitHub Integration'}
        {data?.subtype === 'EXTERNAL_SLACK' && 'Slack Integration'}
      </div>
    </BaseNode>
  );
};

export default ExternalActionNode; 