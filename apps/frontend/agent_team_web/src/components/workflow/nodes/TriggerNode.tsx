import React from 'react';
import { NodeProps } from 'reactflow';
import { Play, Calendar, Webhook, Clock } from 'lucide-react';
import BaseNode from './BaseNode';

const TriggerNode: React.FC<NodeProps> = (props) => {
  const { data } = props;
  
  // Select icon based on subtype
  const getIcon = () => {
    switch (data?.subtype) {
      case 'TRIGGER_CALENDAR':
        return Calendar;
      case 'TRIGGER_WEBHOOK':
        return Webhook;
      case 'TRIGGER_SCHEDULE':
        return Clock;
      default:
        return Play;
    }
  };

  return (
    <BaseNode
      {...props}
      icon={getIcon()}
      title="Trigger"
      color="green"
    >
      <div className="text-xs text-muted-foreground">
        {data?.subtype === 'TRIGGER_CALENDAR' && 'When calendar event occurs'}
        {data?.subtype === 'TRIGGER_WEBHOOK' && 'When webhook is received'}
        {data?.subtype === 'TRIGGER_SCHEDULE' && 'Run on schedule'}
      </div>
    </BaseNode>
  );
};

export default TriggerNode; 