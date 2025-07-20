import React from 'react';
import { NodeProps } from 'reactflow';
import { Bot, Brain } from 'lucide-react';
import BaseNode from './BaseNode';

const AIAgentNode: React.FC<NodeProps> = (props) => {
  const { data } = props;

  return (
    <BaseNode
      {...props}
      icon={Bot}
      title="AI Agent"
      color="indigo"
    >
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Brain className="w-3 h-3 text-indigo-500" />
          <span className="text-xs text-muted-foreground">Intelligent Processing</span>
        </div>
        {data?.parameters?.model && (
          <div className="text-xs bg-muted px-2 py-1 rounded">
            Model: {data.parameters.model}
          </div>
        )}
      </div>
    </BaseNode>
  );
};

export default AIAgentNode; 