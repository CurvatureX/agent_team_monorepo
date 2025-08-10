# 工作流编辑器详细设计文档

## 1. 组件详细设计

### 1.1 WorkflowEditor（主容器）

```typescript
interface WorkflowEditorProps {
  workflowId?: string;
  onSave?: (workflow: WorkflowData) => void;
  readOnly?: boolean;
}

功能说明：
- 三栏响应式布局（Sidebar + Canvas + Details）
- 管理全局编辑器状态
- 处理键盘快捷键
- 自动保存功能
```

### 1.2 NodeSidebar 详细设计

#### 组件结构
```typescript
interface NodeSidebarProps {
  templates: NodeTemplate[];
  onNodeSelect: (template: NodeTemplate) => void;
  className?: string;
}

interface NodeCategoryProps {
  category: string;
  templates: NodeTemplate[];
  expanded: boolean;
  onToggle: () => void;
  onNodeSelect: (template: NodeTemplate) => void;
}

interface NodeTemplateCardProps {
  template: NodeTemplate;
  onDragStart: (e: DragEvent, template: NodeTemplate) => void;
  onClick: () => void;
}
```

#### 功能特性
1. **搜索功能**
   - 实时搜索（防抖 300ms）
   - 搜索名称和描述
   - 高亮匹配文本

2. **分类展示**
   - 可折叠的分类组
   - 显示每个分类的节点数量
   - 记住用户的展开/折叠状态

3. **拖拽功能**
   - 支持拖拽到画布
   - 拖拽时显示节点预览
   - 拖拽时鼠标样式变化

#### UI 设计
```
┌─────────────────────────┐
│ 🔍 Search nodes...      │
├─────────────────────────┤
│ ▼ Trigger (7)           │
│   ┌───────────────────┐ │
│   │ 📅 Manual Trigger │ │
│   │ Manually starts   │ │
│   └───────────────────┘ │
│   ┌───────────────────┐ │
│   │ 🔗 Webhook        │ │
│   │ HTTP webhook      │ │
│   └───────────────────┘ │
│ ▶ AI Agents (4)         │
│ ▶ Actions (4)           │
│ ▼ Flow Control (6)      │
│   ...                   │
└─────────────────────────┘
```

### 1.3 WorkflowCanvas 详细设计

#### 自定义节点组件

每个节点类型都继承自 BaseNode：

```typescript
interface BaseNodeProps {
  id: string;
  data: {
    label: string;
    template: NodeTemplate;
    parameters: Record<string, any>;
    status?: 'idle' | 'running' | 'success' | 'error';
  };
  selected: boolean;
}

// 基础节点样式
const BaseNode: React.FC<BaseNodeProps> = ({ data, selected }) => {
  return (
    <div className={cn(
      "min-w-[200px] rounded-lg border-2 p-3",
      "transition-all duration-200",
      selected && "ring-2 ring-primary ring-offset-2",
      getNodeColorClass(data.template.category)
    )}>
      <div className="flex items-center gap-2 mb-2">
        <NodeIcon type={data.template.node_type} />
        <span className="font-medium text-sm">{data.label}</span>
      </div>
      
      {/* 参数预览 */}
      <div className="text-xs text-muted-foreground">
        {renderParameterPreview(data.parameters)}
      </div>
      
      {/* 连接点 */}
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
};
```

#### 节点颜色方案

```typescript
const NODE_COLORS = {
  Trigger: {
    border: 'border-green-500',
    bg: 'bg-green-50 dark:bg-green-950',
    icon: 'text-green-600'
  },
  'AI Agents': {
    border: 'border-indigo-500',
    bg: 'bg-indigo-50 dark:bg-indigo-950',
    icon: 'text-indigo-600'
  },
  Actions: {
    border: 'border-amber-500',
    bg: 'bg-amber-50 dark:bg-amber-950',
    icon: 'text-amber-600'
  },
  'Flow Control': {
    border: 'border-purple-500',
    bg: 'bg-purple-50 dark:bg-purple-950',
    icon: 'text-purple-600'
  },
  'Human Interaction': {
    border: 'border-pink-500',
    bg: 'bg-pink-50 dark:bg-pink-950',
    icon: 'text-pink-600'
  },
  Memory: {
    border: 'border-orange-500',
    bg: 'bg-orange-50 dark:bg-orange-950',
    icon: 'text-orange-600'
  },
  Tools: {
    border: 'border-cyan-500',
    bg: 'bg-cyan-50 dark:bg-cyan-950',
    icon: 'text-cyan-600'
  }
};
```

#### 画布功能

1. **拖放处理**
```typescript
const onDrop = (event: DragEvent) => {
  event.preventDefault();
  
  const templateData = event.dataTransfer.getData('nodeTemplate');
  const template = JSON.parse(templateData);
  
  const position = reactFlowInstance.project({
    x: event.clientX - reactFlowBounds.left,
    y: event.clientY - reactFlowBounds.top,
  });
  
  addNode(template, position);
};
```

2. **连接验证**
```typescript
const isValidConnection = (connection: Connection) => {
  // 防止自连接
  if (connection.source === connection.target) return false;
  
  // 防止重复连接
  const exists = edges.some(edge => 
    edge.source === connection.source && 
    edge.target === connection.target
  );
  if (exists) return false;
  
  // 检查节点类型兼容性
  return checkNodeCompatibility(connection.source, connection.target);
};
```

3. **画布控制**
```typescript
const CanvasControls = () => (
  <Panel position="top-right">
    <div className="flex gap-2">
      <Button size="sm" onClick={() => fitView()}>
        <Maximize2 className="w-4 h-4" />
      </Button>
      <Button size="sm" onClick={() => zoomIn()}>
        <ZoomIn className="w-4 h-4" />
      </Button>
      <Button size="sm" onClick={() => zoomOut()}>
        <ZoomOut className="w-4 h-4" />
      </Button>
    </div>
  </Panel>
);
```

### 1.4 NodeDetails 详细设计

#### 动态表单渲染

基于 parameter_schema 动态生成表单：

```typescript
interface FormRendererProps {
  schema: ParameterSchema;
  values: Record<string, any>;
  onChange: (values: Record<string, any>) => void;
}

const FormRenderer: React.FC<FormRendererProps> = ({ schema, values, onChange }) => {
  const renderField = (key: string, property: SchemaProperty) => {
    switch (property.type) {
      case 'string':
        if (property.enum) {
          return (
            <SelectField
              key={key}
              label={key}
              value={values[key]}
              options={property.enum}
              onChange={(value) => onChange({ ...values, [key]: value })}
            />
          );
        }
        return (
          <TextField
            key={key}
            label={key}
            value={values[key] || ''}
            onChange={(value) => onChange({ ...values, [key]: value })}
          />
        );
        
      case 'boolean':
        return (
          <BooleanField
            key={key}
            label={key}
            value={values[key] || false}
            onChange={(value) => onChange({ ...values, [key]: value })}
          />
        );
        
      case 'integer':
      case 'number':
        return (
          <NumberField
            key={key}
            label={key}
            value={values[key] || 0}
            onChange={(value) => onChange({ ...values, [key]: value })}
          />
        );
        
      case 'array':
        return (
          <ArrayField
            key={key}
            label={key}
            value={values[key] || []}
            onChange={(value) => onChange({ ...values, [key]: value })}
          />
        );
        
      case 'object':
        return (
          <ObjectField
            key={key}
            label={key}
            value={values[key] || {}}
            schema={property}
            onChange={(value) => onChange({ ...values, [key]: value })}
          />
        );
    }
  };
  
  return (
    <div className="space-y-4">
      {Object.entries(schema.properties || {}).map(([key, property]) => 
        renderField(key, property)
      )}
    </div>
  );
};
```

#### 面板布局

```
┌─────────────────────────┐
│ Node: Webhook Trigger   │
│ Type: TRIGGER           │
├─────────────────────────┤
│ Parameters              │
│                         │
│ Path                    │
│ [/webhook            ] │
│                         │
│ Method                  │
│ [POST          ▼]      │
│                         │
│ Authentication          │
│ [None          ▼]      │
├─────────────────────────┤
│ [Test] [Save] [Delete]  │
└─────────────────────────┘
```

## 2. 状态管理实现

### 2.1 Atoms 定义

```typescript
// store/atoms/workflow.ts
import { atom } from 'jotai';
import { atomWithImmer } from 'jotai-immer';

// 基础 atoms
export const workflowNodesAtom = atomWithImmer<Node[]>([]);
export const workflowEdgesAtom = atomWithImmer<Edge[]>([]);

// 派生 atoms
export const selectedNodeAtom = atom((get) => {
  const nodeId = get(selectedNodeIdAtom);
  const nodes = get(workflowNodesAtom);
  return nodes.find(n => n.id === nodeId);
});

export const nodeCountByTypeAtom = atom((get) => {
  const nodes = get(workflowNodesAtom);
  return nodes.reduce((acc, node) => {
    const type = node.data.template.node_type;
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
});

// 操作 atoms
export const addNodeAtom = atom(
  null,
  (get, set, { template, position }: { template: NodeTemplate; position: XYPosition }) => {
    const newNode: Node = {
      id: `${template.node_type}_${Date.now()}`,
      type: 'custom',
      position,
      data: {
        label: template.name,
        template,
        parameters: { ...template.default_parameters }
      }
    };
    
    set(workflowNodesAtom, (draft) => {
      draft.push(newNode);
    });
    
    set(selectedNodeIdAtom, newNode.id);
    set(detailsPanelOpenAtom, true);
    
    return newNode.id;
  }
);

export const updateNodeParametersAtom = atom(
  null,
  (get, set, { nodeId, parameters }: { nodeId: string; parameters: any }) => {
    set(workflowNodesAtom, (draft) => {
      const node = draft.find(n => n.id === nodeId);
      if (node) {
        node.data.parameters = parameters;
      }
    });
  }
);

export const deleteNodeAtom = atom(
  null,
  (get, set, nodeId: string) => {
    set(workflowNodesAtom, (draft) => {
      return draft.filter(n => n.id !== nodeId);
    });
    
    set(workflowEdgesAtom, (draft) => {
      return draft.filter(e => e.source !== nodeId && e.target !== nodeId);
    });
    
    if (get(selectedNodeIdAtom) === nodeId) {
      set(selectedNodeIdAtom, null);
      set(detailsPanelOpenAtom, false);
    }
  }
);
```

### 2.2 Custom Hooks

```typescript
// store/hooks/useNodeTemplates.ts
export const useNodeTemplates = () => {
  const [templates, setTemplates] = useAtom(nodeTemplatesAtom);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    // 加载节点模板
    fetch('/api/node-templates')
      .then(res => res.json())
      .then(data => {
        setTemplates(data.node_templates);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load node templates:', err);
        // 使用本地 JSON 作为 fallback
        import('@/lib/node-template.json').then(module => {
          setTemplates(module.default.node_templates);
          setLoading(false);
        });
      });
  }, [setTemplates]);
  
  const getTemplatesByCategory = useCallback(() => {
    return templates.reduce((acc, template) => {
      const category = template.category;
      if (!acc[category]) acc[category] = [];
      acc[category].push(template);
      return acc;
    }, {} as Record<string, NodeTemplate[]>);
  }, [templates]);
  
  return {
    templates,
    loading,
    getTemplatesByCategory
  };
};

// store/hooks/useWorkflowOperations.ts
export const useWorkflowOperations = () => {
  const addNode = useSetAtom(addNodeAtom);
  const updateNodeParameters = useSetAtom(updateNodeParametersAtom);
  const deleteNode = useSetAtom(deleteNodeAtom);
  const [nodes] = useAtom(workflowNodesAtom);
  const [edges, setEdges] = useAtom(workflowEdgesAtom);
  
  const addEdge = useCallback((connection: Connection) => {
    setEdges((draft) => {
      const newEdge: Edge = {
        id: `${connection.source}-${connection.target}`,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle,
        targetHandle: connection.targetHandle,
        type: 'smoothstep',
        animated: true
      };
      draft.push(newEdge);
    });
  }, [setEdges]);
  
  const exportWorkflow = useCallback(() => {
    return {
      nodes: nodes.map(node => ({
        id: node.id,
        type: node.data.template.node_type,
        subtype: node.data.template.node_subtype,
        position: node.position,
        parameters: node.data.parameters
      })),
      edges: edges.map(edge => ({
        source: edge.source,
        target: edge.target
      })),
      version: '1.0.0',
      created_at: Date.now()
    };
  }, [nodes, edges]);
  
  return {
    addNode,
    updateNodeParameters,
    deleteNode,
    addEdge,
    exportWorkflow
  };
};
```

## 3. 工具函数

### 3.1 节点辅助函数

```typescript
// utils/nodeHelpers.ts
export const getNodeIcon = (nodeType: string): IconType => {
  const iconMap: Record<string, IconType> = {
    TRIGGER: PlayCircle,
    AI_AGENT: Bot,
    ACTION: Zap,
    FLOW: GitBranch,
    HUMAN_IN_THE_LOOP: UserCheck,
    MEMORY: Database,
    TOOL: Wrench
  };
  
  return iconMap[nodeType] || Circle;
};

export const getNodeColor = (category: string): NodeColorScheme => {
  return NODE_COLORS[category] || {
    border: 'border-gray-500',
    bg: 'bg-gray-50 dark:bg-gray-950',
    icon: 'text-gray-600'
  };
};

export const formatParameterValue = (value: any): string => {
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.length} items]`;
  return String(value);
};
```

### 3.2 Schema 转换工具

```typescript
// utils/schemaToForm.ts
export const schemaToFormFields = (
  schema: ParameterSchema,
  values: Record<string, any>
): FormField[] => {
  const fields: FormField[] = [];
  
  Object.entries(schema.properties || {}).forEach(([key, property]) => {
    fields.push({
      name: key,
      type: mapSchemaTypeToFieldType(property.type),
      label: humanize(key),
      value: values[key],
      required: schema.required?.includes(key),
      options: property.enum,
      validation: buildValidation(property)
    });
  });
  
  return fields;
};

const mapSchemaTypeToFieldType = (schemaType: string): FieldType => {
  const typeMap: Record<string, FieldType> = {
    string: 'text',
    integer: 'number',
    number: 'number',
    boolean: 'checkbox',
    array: 'array',
    object: 'object'
  };
  
  return typeMap[schemaType] || 'text';
};
```

## 4. API 接口设计

### 4.1 节点模板接口

```typescript
// GET /api/node-templates
interface NodeTemplatesResponse {
  node_templates: NodeTemplate[];
}

// GET /api/node-templates/:id
interface NodeTemplateResponse {
  node_template: NodeTemplate;
}
```

### 4.2 工作流接口

```typescript
// POST /api/workflows
interface CreateWorkflowRequest {
  name: string;
  description?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

// PUT /api/workflows/:id
interface UpdateWorkflowRequest {
  nodes?: WorkflowNode[];
  edges?: WorkflowEdge[];
  settings?: WorkflowSettings;
}

// GET /api/workflows/:id/execute
interface ExecuteWorkflowResponse {
  execution_id: string;
  status: 'started' | 'completed' | 'failed';
}
```

## 5. 错误处理

### 5.1 节点操作错误

```typescript
const handleNodeError = (error: Error, nodeId: string) => {
  console.error(`Node ${nodeId} error:`, error);
  
  // 更新节点状态
  updateNodeStatus(nodeId, 'error');
  
  // 显示错误提示
  toast.error(`Node operation failed: ${error.message}`);
};
```

### 5.2 连接验证错误

```typescript
const validateConnection = (connection: Connection): ValidationResult => {
  if (!connection.source || !connection.target) {
    return { valid: false, error: 'Invalid connection' };
  }
  
  if (connection.source === connection.target) {
    return { valid: false, error: 'Cannot connect node to itself' };
  }
  
  // 检查循环依赖
  if (detectCycle(connection)) {
    return { valid: false, error: 'Connection would create a cycle' };
  }
  
  return { valid: true };
};
```

## 6. 性能优化

### 6.1 节点渲染优化

```typescript
// 使用 React.memo 优化节点组件
export const OptimizedNode = React.memo(BaseNode, (prevProps, nextProps) => {
  return (
    prevProps.id === nextProps.id &&
    prevProps.selected === nextProps.selected &&
    JSON.stringify(prevProps.data) === JSON.stringify(nextProps.data)
  );
});
```

### 6.2 搜索防抖

```typescript
const useDebounceSearch = (value: string, delay: number = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
};
```

## 7. 测试计划

### 7.1 单元测试

- Atoms 和 hooks 测试
- 工具函数测试
- 表单验证测试

### 7.2 集成测试

- 节点拖放测试
- 连接创建测试
- 参数更新测试
- 工作流导出测试

### 7.3 E2E 测试

- 完整工作流创建流程
- 复杂工作流编辑
- 错误处理测试