---
id: workflow-agent-architecture
title: "Workflow Agent 技术架构设计"
sidebar_label: "Workflow Agent 架构"
sidebar_position: 5
slug: /tech-design/workflow-agent-architecture
---

# Workflow Agent 技术架构设计

Workflow Agent 是基于 LangGraph 构建的智能工作流生成服务，将用户的描述转换为可执行的工作流, 自动调试并完成部署。

## 核心设计理念

咨询顾问式交互 + 前置能力检测 + 智能协商机制
需求捕获 → 能力边界检测 → 协商调整 → 设计实现 → 测试部署 → 持续优化

## 整体流程设计

```mermaid
flowchart TD
    A["Clarification Node"] -- If something needs clarification --> n1["Negotiation Node"]
    A -- context is enough --> n2["Gap Analysis Node"]
    n2 -- If there is gap between capabilities and requirement --> n3["Alternative Solution Generation Node"]
    n2 -- If no gap --> n4["Workflow Generation Node"]
    n3 --> n1
    n1 -- User adds context --> A
    n4 --> n5["Debug Node"] & n6["End"]
    n5 --> n4
```

## 🔄 核心创新：前置协商流程

### 我们的创新流程

```
用户需求 → 能力扫描 → 发现约束 → 协商调整 → 确认方案 → 精准设计
```

## 📊 节点分类与状态管理

### 主要节点类型

#### 1. 咨询类节点 (Consultant Nodes)
- **Clarification Node** - 解析和澄清用户意图，支持多种澄清目的（初始意图、模板选择、模板修改、能力差距解决、调试问题）。
- **Negotiation Node** - 与用户协商，获取额外信息或在备选方案中选择。
- **Gap Analysis Node** - 分析需求与现有能力之间的差距。
- **Alternative Solution Generation Node** - 当存在能力差距时，生成替代解决方案。

#### 2. 设计与执行类节点 (Design & Execution Nodes)
- **Workflow Generation Node** - 根据确定的需求生成工作流。
- **Debug Node** - 测试生成的工作流，发现并尝试修复错误。

## 🌊 状态流转设计

### 核心状态数据结构

```typescript
interface Conversation {
  role: string;
  text: string;
}

interface WorkflowState {
  // 元数据
  metadata: {
    session_id: string;
    user_id: string;
    created_at: Date;
    updated_at: Date;
  };

  // 当前阶段
  stage: 'clarification' | 'negotiation' | 'gap_analysis' | 'generation' | 'debugging';

  // 澄清阶段上下文
  clarification_context?: {
    purpose:
      | 'initial_intent'        // 澄清用户的初始目标或需求
      | 'template_selection'    // 确认/选择模板
      | 'template_modification' // 澄清如何修改模板
      | 'gap_resolution'        // 澄清如何解决能力差距
      | 'debug_issue';          // 澄清调试中遇到的问题

    origin: 'new_workflow' | 'from_template';
    pending_questions: string[];   // 当前 Clarification 阶段待确认的问题
  };

  conversations: Conversation[]; // 用户和AI Agent的全部对话
  intent_summary: string; // AI根据对话总结的用户意图
  gaps: string[]; // 能力差距分析结果
  alternatives: string[]; // 提供的替代方案

  // 模板工作流支持
  template_workflow?: {
    id: string;                     // 模板 ID
    original_workflow: object;      // 模板的原始内容
  };

  current_workflow: object; // 当前生成的workflow
  debug_result: string; // 调试结果
  debug_loop_count: number;
}
```

## 🔀 节点流转逻辑

### 关键决策点设计

#### 决策点 1：能力缺口分析
```mermaid
graph TD
    A[Gap Analysis Node] --> B{有能力缺口?}
    B -->|无缺口| C[Workflow Generation Node]
    B -->|有缺口| D[Alternative Solution Generation Node]
    D --> E[Negotiation Node]
```

#### 决策点 2：用户协商反馈
```mermaid
graph TD
    A[Negotiation Node] --> B{用户提供新信息?}
    B -->|是| C[Clarification Node]
    B -->|否, 等待用户...| A
```

#### 决策点 3：测试错误处理
```mermaid
graph TD
    A[Debug Node] --> B{测试通过?}
    B -->|是| C[End]
    B -->|否, 发现错误| D[Workflow Generation Node]
```

## 节点流转图

```mermaid
graph TD
    START([用户输入/模板选择]) --> A["Clarification Node"]
    A -- "需要澄清" --> n1["Negotiation Node"]
    A -- "信息充足" --> n2["Gap Analysis Node"]
    n2 -- "存在能力差距" --> n3["Alternative Solution Generation Node"]
    n2 -- "能力匹配" --> n4["Workflow Generation Node"]
    n3 --> n1
    n1 -- "用户提供新信息" --> A
    n4 --> n5["Debug Node"]
    n5 -- "测试通过" --> n6([End])
    n5 -- "实现问题" --> n4
    n5 -- "需求理解问题" --> A
```

## 详细交互流程

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent

    U->>A: 我想要一个工作流.../基于模板X修改工作流
    A->>A: **Clarification Node**: 分析请求
    Note over A: 设置澄清上下文 (purpose, origin, pending_questions)

    A->>U: 我需要更多关于X的细节
    Note over A: **Negotiation Node**

    U->>A: 这是关于X的细节
    A->>A: **Clarification Node**: 重新分析
    Note over A: 请求已清晰

    A->>A: **Gap Analysis Node**: 检查能力
    Note over A: 发现能力差距

    A->>A: **Alternative Solution Generation Node**: 生成备选方案
    A->>U: 我无法直接实现Z，但可以提供P或Q方案
    Note over A: **Negotiation Node**

    U->>A: 我们用P方案
    A->>A: **Clarification Node** -> **Gap Analysis Node**
    Note over A: 差距已解决

    A->>A: **Workflow Generation Node**: 创建工作流
    A->>A: **Debug Node**: 测试工作流
    Note over A: 测试失败，正在修复...

    A->>A: **Clarification Node**: 重新澄清问题，然后生成工作流
    A->>A: **Debug Node**: 再次测试
    Note over A: 测试通过

    A->>U: 您的工作流已准备就绪
```

## 状态数据流 流转过程

```mermaid
graph TD
    Start[用户输入/模板选择] --> Clarification["Clarification<br/>- clarification_context<br/>- intent_summary<br/>- template_workflow"]
    Clarification -- "需要澄清" --> Negotiation["Negotiation<br/>- pending_questions"]
    Negotiation -- "用户提供信息" --> Clarification
    Clarification -- "信息充足" --> GapAnalysis["Gap Analysis<br/>- gaps"]
    GapAnalysis -- "无差距" --> WorkflowGeneration["Workflow Generation<br/>- current_workflow"]
    GapAnalysis -- "有差距" --> AlternativeGeneration["Alternative Generation<br/>- alternatives"]
    AlternativeGeneration --> Negotiation
    WorkflowGeneration --> Debug["Debug<br/>- debug_result"]
    Debug -- "实现问题" --> WorkflowGeneration
    Debug -- "需求理解问题" --> Clarification
    Debug -- "测试成功" --> End([End])
```
