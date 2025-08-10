import React from 'react';
import { NodeProps } from 'reactflow';
import { User, MessageCircle, Mail } from 'lucide-react';
import BaseNode from './BaseNode';

const HumanInTheLoopNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'HUMAN_DISCORD':
        return MessageCircle;
      case 'HUMAN_GMAIL':
        return Mail;
      default:
        return User;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="Human Review"
      color="pink"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'HUMAN_DISCORD' && 'Input via Discord'}
        {data?.subtype === 'HUMAN_GMAIL' && 'Input via Gmail'}
      </div>
    </BaseNode>
  );
};

export default HumanInTheLoopNode; 