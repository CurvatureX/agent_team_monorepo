"use client";

import React from 'react';
import { motion } from 'framer-motion';
import {
    Play,
    Bot,
    Zap,
    ExternalLink,
    GitBranch,
    User,
    Wrench,
    HardDrive,
    Plus
} from 'lucide-react';
import { NodeType, NodeSubtype } from '@/types/workflow';
import { cn } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';

interface NodeTemplate {
    type: NodeType;
    subtype: NodeSubtype;
    label: string;
    icon: React.ElementType;
    color: string;
    description: string;
}

const nodeTemplates: NodeTemplate[] = [
    {
        type: 'TRIGGER_NODE',
        subtype: 'TRIGGER_CALENDAR',
        label: 'Trigger',
        icon: Play,
        color: 'green',
        description: 'Start workflow'
    },
    {
        type: 'AI_AGENT_NODE',
        subtype: 'AI_AGENT',
        label: 'AI Agent',
        icon: Bot,
        color: 'indigo',
        description: 'Intelligent processing'
    },
    {
        type: 'ACTION_NODE',
        subtype: 'ACTION_DATA_TRANSFORMATION',
        label: 'Action',
        icon: Zap,
        color: 'amber',
        description: 'Execute operation'
    },
    {
        type: 'EXTERNAL_ACTION_NODE',
        subtype: 'EXTERNAL_GITHUB',
        label: 'External Service',
        icon: ExternalLink,
        color: 'blue',
        description: 'Connect to external API'
    },
    {
        type: 'FLOW_NODE',
        subtype: 'FLOW_FILTER',
        label: 'Flow Control',
        icon: GitBranch,
        color: 'purple',
        description: 'Conditional branching'
    },
    {
        type: 'HUMAN_IN_THE_LOOP_NODE',
        subtype: 'HUMAN_DISCORD',
        label: 'Human Review',
        icon: User,
        color: 'pink',
        description: 'Requires human confirmation'
    },
    {
        type: 'TOOL_NODE',
        subtype: 'TOOL_FUNCTION',
        label: 'Tool',
        icon: Wrench,
        color: 'cyan',
        description: 'Use tool function'
    },
    {
        type: 'MEMORY_NODE',
        subtype: 'MEMORY_STORE',
        label: 'Memory',
        icon: HardDrive,
        color: 'orange',
        description: 'Store data'
    }
];

// Define color mapping
const colorMap: Record<string, { bg: string, text: string }> = {
    green: { bg: 'bg-green-500/10', text: 'text-green-500' },
    indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-500' },
    amber: { bg: 'bg-amber-500/10', text: 'text-amber-500' },
    blue: { bg: 'bg-blue-500/10', text: 'text-blue-500' },
    purple: { bg: 'bg-purple-500/10', text: 'text-purple-500' },
    pink: { bg: 'bg-pink-500/10', text: 'text-pink-500' },
    cyan: { bg: 'bg-cyan-500/10', text: 'text-cyan-500' },
    orange: { bg: 'bg-orange-500/10', text: 'text-orange-500' },
};

interface NodePanelProps {
    onNodeAdd?: (type: NodeType, subtype: NodeSubtype) => void;
}

const NodePanel: React.FC<NodePanelProps> = ({ onNodeAdd }) => {
    const onDragStart = (event: React.DragEvent<HTMLDivElement>, nodeType: NodeType, nodeSubtype: NodeSubtype) => {
        event.dataTransfer.setData('application/reactflow', JSON.stringify({ type: nodeType, subtype: nodeSubtype }));
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <Card className="bg-background/95 backdrop-blur-sm shadow-lg">
            <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-sm">
                    <Plus className="w-4 h-4 text-primary" />
                    Add Node
                </CardTitle>
            </CardHeader>

            <CardContent className="pt-0">
                <div className="grid grid-cols-2 gap-2">
                    {nodeTemplates.map((template) => {
                        const Icon = template.icon;
                        return (
                            <div
                                key={`${template.type}-${template.subtype}`}
                                draggable
                                onDragStart={(e) => onDragStart(e, template.type, template.subtype)}
                                onClick={() => onNodeAdd?.(template.type, template.subtype)}
                            >
                                <motion.div
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                >
                                    <Card className="cursor-move hover:border-primary/50 hover:bg-accent/50 transition-all group">
                                        <CardContent className="p-3">
                                            <div className="flex items-center gap-2">
                                                <div
                                                    className={cn(
                                                        'p-1.5 rounded-md',
                                                        colorMap[template.color]?.bg || 'bg-gray-500/10'
                                                    )}
                                                >
                                                    <Icon
                                                        className={cn(
                                                            'w-4 h-4',
                                                            colorMap[template.color]?.text || 'text-gray-500'
                                                        )}
                                                    />
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-xs font-medium truncate">{template.label}</p>
                                                    <p className="text-xs text-muted-foreground truncate">{template.description}</p>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </motion.div>
                            </div>
                        );
                    })}
                </div>

                <Separator className="my-4" />

                <p className="text-xs text-muted-foreground text-center">
                    Drag nodes to canvas or click to add
                </p>
            </CardContent>
        </Card>
    );
};

export default NodePanel; 