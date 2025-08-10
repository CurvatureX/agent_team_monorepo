# 工作流编辑器架构设计方案

## 1. 概述

本文档描述了基于 React 19 和 React Flow 的工作流编辑器架构设计方案。该编辑器将提供类似 n8n 的可视化工作流构建体验，包含节点模板侧边栏、中央画布和节点详情面板三个主要部分。

## 2. 技术栈

### 核心技术（基于现有 package.json）
- **框架**: React 19 + TypeScript 5
- **路由**: Next.js 15.3.5 (App Router)
- **流程图库**: React Flow 11.11.4
- **状态管理**: Jotai + Immer（需要安装）
- **样式**: TailwindCSS 4
- **动画**: Framer Motion 12.23.0
- **图标**: Lucide React 0.525.0
- **UI组件**: Radix UI

### 需要安装的依赖
```bash
yarn add jotai jotai-immer immer
yarn add -D @types/immer
```

## 3. 架构设计

### 3.1 整体布局

```
┌─────────────────────────────────────────────────────────────┐
│                     WorkflowEditor                          │
│  ┌────────────┬─────────────────────┬──────────────────┐  │
│  │            │                     │                  │  │
│  │  NodeSidebar│   WorkflowCanvas   │  NodeDetails    │  │
│  │   (250px)  │     (flexible)      │    (350px)      │  │
│  │            │                     │                  │  │
│  │  - Search   │   - React Flow    │  - Form Fields  │  │
│  │  - Categories│   - Node Render   │  - Validation   │  │
│  │  - Templates│   - Connections    │  - Preview      │  │
│  │  - Drag&Drop│   - Zoom/Pan      │  - Actions      │  │
│  │            │                     │                  │  │
│  └────────────┴─────────────────────┴──────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              State Management (Jotai)                │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 目录结构

```
src/
├── components/
│   └── workflow/
│       ├── WorkflowEditor/
│       │   ├── index.tsx               # 主编辑器容器
│       │   └── WorkflowEditor.tsx      # 编辑器逻辑
│       ├── NodeSidebar/
│       │   ├── index.tsx               # 侧边栏主组件
│       │   ├── NodeCategory.tsx        # 节点分类组件
│       │   ├── NodeTemplateCard.tsx    # 节点模板卡片
│       │   └── SearchBar.tsx           # 搜索组件
│       ├── WorkflowCanvas/
│       │   ├── index.tsx               # 画布主组件
│       │   ├── nodes/                  # 自定义节点组件
│       │   │   ├── BaseNode.tsx        # 基础节点组件
│       │   │   ├── TriggerNode.tsx     # 触发器节点
│       │   │   ├── AIAgentNode.tsx     # AI代理节点
│       │   │   └── ...                 # 其他节点类型
│       │   ├── edges/
│       │   │   └── CustomEdge.tsx      # 自定义连线
│       │   └── CanvasControls.tsx      # 画布控制器
│       └── NodeDetails/
│           ├── index.tsx               # 详情面板主组件
│           ├── FormRenderer.tsx        # 动态表单渲染
│           ├── fields/                 # 表单字段组件
│           │   ├── TextField.tsx
│           │   ├── SelectField.tsx
│           │   ├── BooleanField.tsx
│           │   └── ...
│           └── NodeActions.tsx         # 节点操作按钮
├── store/
│   ├── atoms/
│   │   ├── workflow.ts                 # 工作流相关原子
│   │   ├── ui.ts                       # UI状态原子
│   │   └── nodeTemplates.ts            # 节点模板原子
│   └── hooks/
│       ├── useWorkflow.ts              # 工作流操作钩子
│       ├── useNodeOperations.ts        # 节点操作钩子
│       └── useNodeTemplates.ts         # 节点模板钩子
├── types/
│   ├── node-template.ts                # 节点模板类型定义
│   └── workflow-editor.ts              # 编辑器类型定义
└── utils/
    ├── nodeHelpers.ts                  # 节点辅助函数
    └── schemaToForm.ts                 # Schema转表单工具
```

## 4. 状态管理设计

### 4.1 Jotai Atoms 结构

```typescript
// store/atoms/workflow.ts
import { atom } from 'jotai';
import { atomWithImmer } from 'jotai-immer';
import type { Node, Edge } from 'reactflow';

// 工作流节点
export const workflowNodesAtom = atomWithImmer<Node[]>([]);

// 工作流连线
export const workflowEdgesAtom = atomWithImmer<Edge[]>([]);

// 工作流设置
export const workflowSettingsAtom = atom({
  name: 'Untitled Workflow',
  description: '',
  version: '1.0.0'
});

// store/atoms/ui.ts
export const selectedNodeIdAtom = atom<string | null>(null);
export const sidebarCollapsedAtom = atom(false);
export const detailsPanelOpenAtom = atom(false);
export const searchQueryAtom = atom('');
export const selectedCategoryAtom = atom<string | null>(null);

// store/atoms/nodeTemplates.ts
export const nodeTemplatesAtom = atom<NodeTemplate[]>([]);
export const filteredTemplatesAtom = atom((get) => {
  const templates = get(nodeTemplatesAtom);
  const query = get(searchQueryAtom);
  const category = get(selectedCategoryAtom);
  
  return templates.filter(template => {
    const matchesSearch = !query || 
      template.name.toLowerCase().includes(query.toLowerCase()) ||
      template.description.toLowerCase().includes(query.toLowerCase());
    
    const matchesCategory = !category || template.category === category;
    
    return matchesSearch && matchesCategory;
  });
});
```

### 4.2 自定义 Hooks

```typescript
// store/hooks/useWorkflow.ts
export const useWorkflow = () => {
  const [nodes, setNodes] = useAtom(workflowNodesAtom);
  const [edges, setEdges] = useAtom(workflowEdgesAtom);
  
  const addNode = useCallback((nodeTemplate: NodeTemplate, position: { x: number; y: number }) => {
    const newNode: Node = {
      id: `node_${Date.now()}`,
      type: nodeTemplate.node_type,
      position,
      data: {
        label: nodeTemplate.name,
        template: nodeTemplate,
        parameters: { ...nodeTemplate.default_parameters }
      }
    };
    
    setNodes((draft) => {
      draft.push(newNode);
    });
    
    return newNode.id;
  }, [setNodes]);
  
  // 其他操作方法...
  
  return { nodes, edges, addNode, /* ... */ };
};
```

## 5. 核心组件设计

### 5.1 NodeSidebar 组件

```typescript
interface NodeSidebarProps {
  onNodeDragStart: (nodeTemplate: NodeTemplate) => void;
}

主要功能：
- 显示节点分类（基于 category 字段）
- 搜索过滤功能
- 拖拽添加节点
- 响应式折叠/展开
```

### 5.2 WorkflowCanvas 组件

```typescript
主要功能：
- 集成 React Flow
- 自定义节点渲染（根据 node_type）
- 处理节点拖放
- 连接验证
- 画布操作（缩放、平移、适应视图）
```

### 5.3 NodeDetails 组件

```typescript
主要功能：
- 动态表单生成（基于 parameter_schema）
- 实时验证
- 参数更新
- 节点信息展示
- 删除节点操作
```

## 6. 节点类型映射

基于 node-template.json 中的数据：

```typescript
const NODE_TYPE_COMPONENTS = {
  TRIGGER: TriggerNode,
  AI_AGENT: AIAgentNode,
  ACTION: ActionNode,
  FLOW: FlowNode,
  HUMAN_IN_THE_LOOP: HumanInTheLoopNode,
  MEMORY: MemoryNode,
  TOOL: ToolNode,
};

const NODE_CATEGORY_COLORS = {
  'Trigger': { primary: '#10b981', secondary: '#d1fae5' },
  'AI Agents': { primary: '#6366f1', secondary: '#e0e7ff' },
  'Actions': { primary: '#f59e0b', secondary: '#fef3c7' },
  'Flow Control': { primary: '#8b5cf6', secondary: '#ede9fe' },
  'Human Interaction': { primary: '#ec4899', secondary: '#fce7f3' },
  'Memory': { primary: '#f97316', secondary: '#fed7aa' },
  'Tools': { primary: '#06b6d4', secondary: '#cffafe' },
};
```

## 7. 数据流

### 7.1 节点添加流程

```
1. 用户从侧边栏拖拽节点模板
2. 拖拽结束时获取画布坐标
3. 调用 useWorkflow.addNode()
4. 创建新节点实例（包含默认参数）
5. 更新 workflowNodesAtom
6. React Flow 自动重新渲染
```

### 7.2 参数编辑流程

```
1. 用户点击节点
2. 更新 selectedNodeIdAtom
3. NodeDetails 显示该节点的参数表单
4. 用户修改表单值
5. 通过 useNodeOperations.updateNodeData() 更新
6. 节点实时显示更新后的参数
```

## 8. 性能优化策略

- 使用 React.memo 优化节点组件
- 虚拟滚动处理大量节点模板
- 防抖搜索输入
- 懒加载节点详情表单
- 使用 CSS contain 优化渲染性能

## 9. 响应式设计

- 移动端：隐藏侧边栏，底部显示节点选择器
- 平板：可折叠侧边栏
- 桌面：完整三栏布局

## 10. 后续扩展

- 撤销/重做功能
- 工作流模板保存
- 协作编辑支持
- 节点执行状态可视化
- 调试模式