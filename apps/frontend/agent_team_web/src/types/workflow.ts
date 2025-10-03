/**
 * Workflow Types - Based on API Definition
 * Aligned with backend API schema from api.json
 */

import {
  WorkflowType,
  WorkflowStatus,
  NodeType,
  ErrorPolicy,
  CallerPolicy
} from './workflow-enums';

// ============== Base Types ==============

// 位置数据
export interface PositionData {
  x: number;
  y: number;
}

// 重试策略
export interface RetryPolicy {
  max_tries: number;
  wait_between_tries: number;
}

// ============== Node Types ==============

// 工作流节点模型 (based on WorkflowNode from API)
export interface WorkflowNode {
  id: string;                           // 节点唯一标识符
  type: NodeType | string;              // 节点类型 (使用枚举或字符串以支持扩展)
  name: string;                          // 节点名称
  description?: string | null;          // 节点描述
  config?: Record<string, unknown>;     // 节点配置
  position?: PositionData;              // 节点位置
  inputs?: Record<string, unknown>;     // 输入参数
  outputs?: Record<string, unknown>;    // 输出参数
  metadata?: Record<string, unknown>;   // 元数据

  // Additional fields for compatibility with existing code
  subtype?: string;                     // 节点子类型
  type_version?: number;                // 类型版本
  parameters?: Record<string, unknown>; // 参数（兼容旧版）
  credentials?: Record<string, unknown>;// 凭证
  disabled?: boolean;                   // 是否禁用
  on_error?: ErrorPolicy | string;      // 错误处理策略
  retry_policy?: RetryPolicy;           // 重试策略
  notes?: Record<string, unknown>;      // 备注
  webhooks?: string[];                  // Webhook列表
}

// ============== Edge Types ==============

// 工作流边模型 (based on WorkflowEdge from API)
export interface WorkflowEdge {
  id: string;                           // 边的唯一标识符
  source: string;                       // 源节点ID
  target: string;                       // 目标节点ID
  condition?: string | null;            // 边的条件表达式
  label?: string | null;                // 边的标签

  // Additional fields for React Flow compatibility
  type?: string;                        // 边的类型（如 'default', 'smoothstep'）
  sourceHandle?: string | null;         // 源节点句柄
  targetHandle?: string | null;         // 目标节点句柄
  data?: Record<string, unknown>;      // 自定义数据
}

// ============== Connection Types ==============

// 工作流连接节点
export interface WorkflowConnection {
  node: string;
  type?: string;
  index?: number;
}

// 连接类型结构
export interface ConnectionType {
  connection_types?: {
    main?: {
      connections?: WorkflowConnection[];
    };
  };
  main?: WorkflowConnection[][];
}

// 工作流数据结构（用于API响应处理）
export interface WorkflowDataStructure {
  id?: string;
  name?: string;
  nodes?: unknown[];
  edges?: WorkflowEdge[];
  connections?: Record<string, unknown>;
  workflow_data?: string | WorkflowDataStructure;
  [key: string]: unknown;
}

// ============== Workflow Settings ==============

// 工作流设置数据
export interface WorkflowSettingsData {
  timezone?: Record<string, string>;
  save_execution_progress?: boolean;
  save_manual_executions?: boolean;
  timeout?: number;
  error_policy?: ErrorPolicy | string;
  caller_policy?: CallerPolicy | string;
}

// ============== Workflow Entity ==============

// 工作流实体模型 (based on WorkflowEntity from API)
export interface WorkflowEntity {
  // Timestamps
  created_at?: string | null;           // 创建时间
  updated_at?: string | null;           // 更新时间

  // Basic info
  id: string;                           // 唯一标识符
  user_id: string;                      // 工作流所有者用户ID
  name: string;                         // 工作流名称
  description?: string | null;          // 工作流描述

  // Workflow configuration
  type: WorkflowType | string;          // 工作流类型
  status: WorkflowStatus | string;      // 工作流状态
  version: number;                      // 工作流版本

  // Workflow structure
  nodes: WorkflowNode[];                // 工作流节点列表
  edges?: WorkflowEdge[];               // 工作流连接边列表 (可选，某些API返回connections)
  connections?: Record<string, unknown>; // n8n风格的连接信息 (可选，某些API返回这个而不是edges)

  // Additional data
  variables?: Record<string, unknown>;  // 工作流变量
  settings?: Record<string, unknown>;   // 工作流设置
  tags?: string[];                      // 标签列表

  // Execution info
  execution_count: number;              // 执行次数
  last_execution?: string | null;       // 最后执行时间
}

// ============== API Request/Response Types ==============

// 创建工作流请求
export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  nodes: Omit<WorkflowNode, 'id'>[];   // 创建时节点可能没有ID
  connections?: Record<string, unknown>;    // 连接信息（n8n格式）
  settings?: WorkflowSettingsData;
  static_data?: Record<string, unknown>;
  tags?: string[];
  user_id?: string;
  session_id?: string;
}

// 更新工作流请求
export interface UpdateWorkflowRequest {
  workflow_id: string;
  name?: string;
  description?: string;
  nodes?: WorkflowNode[];
  connections?: Record<string, unknown>;  // 连接信息（n8n格式）
  settings?: WorkflowSettingsData;
  static_data?: Record<string, unknown>;
  tags?: string[];
  active?: boolean;
  user_id?: string;
  session_id?: string;
}

// 工作流响应模型 (单个工作流详情)
export interface WorkflowResponse {
  found?: boolean;                      // 是否找到工作流
  workflow: WorkflowEntity;             // 工作流信息
  message?: string | null;              // 响应消息
}

// 工作流摘要模型 (列表视图，不包含nodes)
export interface WorkflowSummary {
  id: string;
  name: string;
  description?: string | null;
  tags: string[];
  active: boolean;
  created_at?: number | null;
  updated_at?: number | null;
  version: string;
  logo_url?: string | null;             // 映射自backend的icon_url
  deployment_status?: string | null;
  latest_execution_status?: string | null;
  latest_execution_time?: string | null;
}

// 工作流列表响应模型
export interface WorkflowListResponse {
  workflows: WorkflowSummary[];
  total_count: number;
  has_more: boolean;
}

// 工作流执行请求
export interface WorkflowExecutionRequest {
  inputs?: Record<string, unknown>;     // 执行时的输入参数
  settings?: Record<string, unknown> | null; // 执行时的特殊设置
  metadata?: Record<string, unknown> | null; // 执行元数据
}

// 工作流执行响应
export interface WorkflowExecutionResponse {
  execution_id: string;                 // 执行ID
  workflow_id: string;                  // 工作流ID
  status: string;                       // 执行状态
  started_at: string;                   // 开始时间
  message?: string;                     // 响应消息
}

// ============== Type Aliases for Compatibility ==============

// 为了兼容性，将 WorkflowEntity 作为 Workflow 的别名
export type Workflow = WorkflowEntity;

// 为了兼容性，将 Workflow 作为 WorkflowData 的别名
export type WorkflowData = Workflow;

// 连接类型（用于兼容旧代码）
export type WorkflowConnections = Record<string, unknown>;
