export interface WorkflowNode {
  id: string;
  name: string;
  type: string;
  position: { x: number; y: number };
  disabled?: boolean;
  parameters?: Record<string, any>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type?: string;
}

export interface WorkflowData {
  id: string;
  name: string;
  active: boolean;
  nodes: WorkflowNode[];
  edges?: WorkflowEdge[];
}

export function workflowToMermaid(workflow: WorkflowData): string {
  const nodes = workflow.nodes;
  
  let mermaidCode = 'graph TB\n';
  
  // Add node definitions with emojis and better formatting
  nodes.forEach(node => {
    const nodeId = node.id.replace(/[^a-zA-Z0-9]/g, '_');
    const nodeName = node.name;
    const nodeType = node.type;
    
    // Get emoji and description based on node type and parameters
    const { emoji, description } = getNodeEmojiAndDescription(node);
    const fullLabel = `${emoji} ${nodeName}<br/>${description}`;
    
    let nodeShape = '';
    switch (nodeType) {
      case 'trigger':
        nodeShape = `${nodeId}[${fullLabel}]`;
        break;
      case 'ai_agent':
        nodeShape = `${nodeId}[🤖 ${nodeName}<br/>${description}]`;
        break;
      case 'switch':
        nodeShape = `${nodeId}{🔀 ${nodeName}<br/>${description}}`;
        break;
      case 'ai_tool':
        nodeShape = `${nodeId}[${fullLabel}]`;
        break;
      case 'webhook':
        nodeShape = `${nodeId}[${fullLabel}]`;
        break;
      default:
        nodeShape = `${nodeId}[${fullLabel}]`;
    }
    
    mermaidCode += `    ${nodeShape}\n`;
  });
  
  mermaidCode += '\n';
  
  // Add connections with labels if available
  if (workflow.edges && workflow.edges.length > 0) {
    workflow.edges.forEach(edge => {
      const sourceId = edge.source.replace(/[^a-zA-Z0-9]/g, '_');
      const targetId = edge.target.replace(/[^a-zA-Z0-9]/g, '_');
      
      // Check if this is a switch node connection and add appropriate label
      const sourceNode = nodes.find(n => n.id === edge.source);
      if (sourceNode && sourceNode.type === 'switch') {
        const label = getSwitchLabel(sourceNode, edge);
        if (label) {
          mermaidCode += `    ${sourceId} -->|${label}| ${targetId}\n`;
        } else {
          mermaidCode += `    ${sourceId} --> ${targetId}\n`;
        }
      } else {
        mermaidCode += `    ${sourceId} --> ${targetId}\n`;
      }
    });
  } else {
    // Create intelligent connections based on node types and positions
    const connections = generateSmartConnections(nodes);
    connections.forEach(connection => {
      mermaidCode += `    ${connection}\n`;
    });
  }
  
  mermaidCode += '\n';
  
  // Add styling classes
  const styleClasses = new Set<string>();
  
  nodes.forEach(node => {
    const nodeId = node.id.replace(/[^a-zA-Z0-9]/g, '_');
    const nodeType = node.type;
    
    let styleClass = '';
    switch (nodeType) {
      case 'trigger':
        styleClass = 'trigger';
        break;
      case 'ai_agent':
        styleClass = 'agent';
        break;
      case 'switch':
        styleClass = 'switch';
        break;
      case 'ai_tool':
        styleClass = 'tool';
        break;
      case 'webhook':
        styleClass = 'webhook';
        break;
      default:
        styleClass = 'default';
    }
    
    styleClasses.add(styleClass);
    mermaidCode += `    class ${nodeId} ${styleClass}\n`;
  });
  
  // Add style definitions
  mermaidCode += '\n';
  styleClasses.forEach(styleClass => {
    const styles = getStyleForClass(styleClass);
    mermaidCode += `    classDef ${styleClass} ${styles}\n`;
  });
  
  return mermaidCode;
}

function getNodeEmojiAndDescription(node: WorkflowNode): { emoji: string; description: string } {
  const nodeType = node.type;
  const params = node.parameters || {};
  
  switch (nodeType) {
    case 'trigger':
      if (params.trigger_type === 'slack') {
        return { emoji: '💬', description: '监听用户消息' };
      } else if (params.trigger_type === 'cron') {
        return { emoji: '⏰', description: '定时触发' };
      }
      return { emoji: '🚀', description: '触发器' };
    
    case 'ai_agent':
      if (params.agent_type === 'router') {
        return { emoji: '🤖', description: '智能路由判断' };
      } else if (params.agent_type === 'analyzer') {
        return { emoji: '🤖', description: '数据分析处理' };
      }
      return { emoji: '🤖', description: 'AI智能处理' };
    
    case 'switch':
      if (params.switch_type === 'operation_type') {
        return { emoji: '🔀', description: '操作类型' };
      }
      return { emoji: '🔀', description: '条件判断' };
    
    case 'ai_tool':
      if (params.tool_type === 'calendar' || node.name.toLowerCase().includes('calendar')) {
        return { emoji: '📅', description: '日程管理' };
      } else if (params.tool_type === 'database' || node.name.toLowerCase().includes('postgres')) {
        return { emoji: '🗄️', description: '数据库操作' };
      } else if (node.name.toLowerCase().includes('icloud')) {
        return { emoji: '📱', description: 'iCloud同步' };
      }
      return { emoji: '🔧', description: '工具操作' };
    
    case 'database':
      return { emoji: '🗄️', description: '数据库操作' };
    
    case 'webhook':
      if (node.name.toLowerCase().includes('slack')) {
        return { emoji: '💬', description: '消息发送' };
      }
      return { emoji: '🔗', description: 'Webhook调用' };
    
    default:
      return { emoji: '⚙️', description: '处理节点' };
  }
}

function getSwitchLabel(switchNode: WorkflowNode, edge: WorkflowEdge): string | null {
  const params = switchNode.parameters || {};
  
  if (params.conditions && Array.isArray(params.conditions)) {
    // Try to find a matching condition for this edge
    const condition = params.conditions.find((c: any) => 
      edge.target.includes(c.type) || edge.target.includes(c.value)
    );
    if (condition) {
      return condition.value || condition.type;
    }
  }
  
  // Fallback: try to infer from target node name
  const targetNodeName = edge.target.toLowerCase();
  if (targetNodeName.includes('calendar')) {
    return '日程管理';
  } else if (targetNodeName.includes('query') || targetNodeName.includes('postgres')) {
    return '查询请求';
  } else if (targetNodeName.includes('report') || targetNodeName.includes('summary')) {
    return '总结生成';
  } else if (targetNodeName.includes('confirm') || targetNodeName.includes('select')) {
    return '确认选择';
  } else if (targetNodeName.includes('retry') || targetNodeName.includes('recommend')) {
    return '重新推荐';
  }
  
  return null;
}

function generateSmartConnections(nodes: WorkflowNode[]): string[] {
  const connections: string[] = [];
  
  // Group nodes by type and create logical flow
  const triggerNodes = nodes.filter(n => n.type === 'trigger');
  const agentNodes = nodes.filter(n => n.type === 'ai_agent');
  const switchNodes = nodes.filter(n => n.type === 'switch');
  const toolNodes = nodes.filter(n => n.type === 'ai_tool');
  const webhookNodes = nodes.filter(n => n.type === 'webhook');
  
  // Create main flow: trigger -> agent -> switch -> tools -> webhook
  if (triggerNodes.length > 0 && agentNodes.length > 0) {
    const trigger = triggerNodes[0].id.replace(/[^a-zA-Z0-9]/g, '_');
    const agent = agentNodes[0].id.replace(/[^a-zA-Z0-9]/g, '_');
    connections.push(`${trigger} --> ${agent}`);
    
    if (switchNodes.length > 0) {
      const switchNode = switchNodes[0];
      const switchId = switchNode.id.replace(/[^a-zA-Z0-9]/g, '_');
      connections.push(`${agent} --> ${switchId}`);
      
      // Create branches from switch to different tool types
      const calendarTools = toolNodes.filter(n => 
        n.name.toLowerCase().includes('calendar') || 
        n.parameters?.tool_type === 'calendar'
      );
      const databaseTools = toolNodes.filter(n => 
        n.name.toLowerCase().includes('postgres') || 
        n.parameters?.tool_type === 'database'
      );
      const otherTools = toolNodes.filter(n => 
        !calendarTools.includes(n) && !databaseTools.includes(n)
      );
      
      if (calendarTools.length > 0) {
        const calendarId = calendarTools[0].id.replace(/[^a-zA-Z0-9]/g, '_');
        connections.push(`${switchId} -->|日程管理| ${calendarId}`);
      }
      
      if (databaseTools.length > 0) {
        const dbId = databaseTools[0].id.replace(/[^a-zA-Z0-9]/g, '_');
        connections.push(`${switchId} -->|查询请求| ${dbId}`);
      }
      
      if (otherTools.length > 0) {
        const otherId = otherTools[0].id.replace(/[^a-zA-Z0-9]/g, '_');
        connections.push(`${switchId} -->|总结生成| ${otherId}`);
      }
    }
  }
  
  // Connect remaining nodes in logical sequences
  if (toolNodes.length > 1) {
    for (let i = 0; i < toolNodes.length - 1; i++) {
      const currentId = toolNodes[i].id.replace(/[^a-zA-Z0-9]/g, '_');
      const nextId = toolNodes[i + 1].id.replace(/[^a-zA-Z0-9]/g, '_');
      
      // Only connect if not already connected via switch
      const alreadyConnected = connections.some(conn => 
        conn.includes(currentId) && conn.includes(nextId)
      );
      if (!alreadyConnected) {
        connections.push(`${currentId} --> ${nextId}`);
      }
    }
  }
  
  // Connect final tools to webhooks
  if (toolNodes.length > 0 && webhookNodes.length > 0) {
    const lastTool = toolNodes[toolNodes.length - 1].id.replace(/[^a-zA-Z0-9]/g, '_');
    const webhook = webhookNodes[0].id.replace(/[^a-zA-Z0-9]/g, '_');
    connections.push(`${lastTool} --> ${webhook}`);
  }
  
  return connections;
}

function getStyleForClass(styleClass: string): string {
  switch (styleClass) {
    case 'trigger':
      return 'fill:#ff9f43,stroke:#ff6b35,stroke-width:2px,color:#fff';
    case 'agent':
      return 'fill:#5f27cd,stroke:#341f97,stroke-width:2px,color:#fff';
    case 'switch':
      return 'fill:#00d2d3,stroke:#0fb9b1,stroke-width:2px,color:#fff';
    case 'tool':
      return 'fill:#2ed573,stroke:#1e824c,stroke-width:2px,color:#fff';
    case 'webhook':
      return 'fill:#ff6b6b,stroke:#ee5a52,stroke-width:2px,color:#fff';
    default:
      return 'fill:#ddd,stroke:#999,stroke-width:2px,color:#333';
  }
}