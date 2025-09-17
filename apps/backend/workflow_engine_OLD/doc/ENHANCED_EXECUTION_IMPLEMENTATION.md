# Enhanced Execution Engine Implementation

## 概述

本文档详细说明了如何扩展RunData结构和在WorkflowExecutionEngine中实现详细的数据收集，以支持Agent的自动调试功能。

## 1. 扩展RunData结构

### 1.1 修改的文件
- `apps/backend/shared/proto/engine/execution.proto`

### 1.2 主要扩展内容

#### 1.2.1 新增执行路径信息 (ExecutionPath)
```protobuf
message ExecutionPath {
  repeated PathStep steps = 1;                    // 执行步骤
  map<string, BranchDecision> branch_decisions = 2;  // 分支决策
  repeated LoopInfo loop_info = 3;               // 循环信息
  repeated string skipped_nodes = 4;             // 跳过的节点
  map<string, int32> node_execution_counts = 5;  // 节点执行次数
}
```

**功能说明：**
- **PathStep**: 记录每个节点的详细执行信息
- **BranchDecision**: 记录条件分支的决策过程
- **LoopInfo**: 记录循环节点的执行情况
- **skipped_nodes**: 记录被跳过的节点
- **node_execution_counts**: 记录每个节点的执行次数

#### 1.2.2 新增节点入参信息 (NodeInputData)
```protobuf
message NodeInputData {
  string node_id = 1;
  string node_name = 2;
  map<string, DataItem> input_data = 3;          // 实际输入数据
  repeated ConnectionData connections = 4;        // 连接数据
  map<string, string> parameters = 5;            // 节点参数
  map<string, string> credentials = 6;           // 凭证信息
  map<string, string> static_data = 7;           // 静态数据
  int64 timestamp = 8;                           // 记录时间戳
}
```

**功能说明：**
- **input_data**: 记录节点的实际输入数据
- **connections**: 记录数据来源和连接信息
- **parameters**: 记录节点的配置参数
- **credentials**: 记录使用的凭证（脱敏处理）
- **static_data**: 记录静态数据
- **timestamp**: 记录数据收集时间

#### 1.2.3 新增执行上下文 (ExecutionContext)
```protobuf
message ExecutionContext {
  map<string, string> environment_variables = 1;  // 环境变量
  map<string, string> global_parameters = 2;      // 全局参数
  map<string, string> workflow_variables = 3;     // 工作流变量
  int64 execution_start_time = 4;                 // 执行开始时间
  string execution_mode = 5;                      // 执行模式
  string triggered_by = 6;                        // 触发者
  map<string, string> metadata = 7;               // 元数据
}
```

**功能说明：**
- **environment_variables**: 记录执行时的环境变量
- **global_parameters**: 记录全局参数
- **workflow_variables**: 记录工作流变量
- **execution_start_time**: 记录执行开始时间
- **execution_mode**: 记录执行模式
- **triggered_by**: 记录触发者信息
- **metadata**: 记录其他元数据

#### 1.2.4 增强现有结构
- **NodeRunData**: 添加输入数据和执行步骤
- **TaskData**: 添加输入数据、执行路径、上下文变量等
- **NodeExecutionData**: 添加数据类型、时间戳、元数据
- **DataItem**: 添加数据来源、格式、大小、修改状态
- **ErrorData**: 添加错误类型、代码、时间、建议、调试信息

### 1.3 扩展后的RunData结构
```protobuf
message RunData {
  map<string, NodeRunData> node_data = 1;        // 节点运行数据
  ExecutionPath execution_path = 2;               // 执行路径信息
  map<string, NodeInputData> node_inputs = 3;     // 节点入参信息
  ExecutionContext execution_context = 4;         // 执行上下文
}
```

## 2. 增强WorkflowExecutionEngine

### 2.1 修改的文件
- `apps/backend/workflow_engine/workflow_engine/execution_engine.py`

### 2.2 主要增强内容

#### 2.2.1 新增EnhancedWorkflowExecutionEngine类
```python
class EnhancedWorkflowExecutionEngine:
    """Enhanced workflow execution engine with detailed data collection for Agent debugging."""
```

**核心特性：**
- 详细的数据收集和跟踪
- 执行路径记录
- 性能指标监控
- 数据流分析
- 错误记录和分析

#### 2.2.2 增强的执行状态初始化
```python
def _initialize_enhanced_execution_state(self, workflow_id, execution_id, workflow_definition, initial_data, credentials):
    """Initialize enhanced execution state with detailed tracking."""

    return {
        # 基础信息
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "status": "running",
        "start_time": datetime.now().isoformat(),
        "nodes": workflow_definition.get("nodes", []),
        "connections": workflow_definition.get("connections", {}),
        "node_results": {},
        "execution_order": [],
        "errors": [],

        # 增强数据收集
        "execution_path": {
            "steps": [],
            "branch_decisions": {},
            "loop_info": [],
            "skipped_nodes": [],
            "node_execution_counts": {}
        },
        "node_inputs": {},
        "execution_context": {
            "environment_variables": dict(os.environ),
            "global_parameters": {},
            "workflow_variables": {},
            "execution_start_time": int(time.time()),
            "execution_mode": "manual",
            "triggered_by": "system",
            "metadata": {}
        },
        "performance_metrics": {
            "total_execution_time": 0,
            "node_execution_times": {},
            "memory_usage": {},
            "cpu_usage": {}
        },
        "data_flow": {
            "data_transfers": [],
            "data_transformations": [],
            "data_sources": {}
        }
    }
```

#### 2.2.3 增强的节点执行跟踪
```python
def _execute_node_with_enhanced_tracking(self, node_id, workflow_definition, execution_state, initial_data, credentials):
    """Execute a single node with enhanced tracking and data collection."""

    # 记录执行开始时间
    node_start_time = time.time()
    execution_state["performance_metrics"]["node_execution_times"][node_id] = {
        "start_time": node_start_time,
        "end_time": None,
        "duration": None
    }

    # 准备输入数据并跟踪
    input_data = self._prepare_node_input_data_with_tracking(node_id, workflow_definition, execution_state, initial_data)

    # 记录节点输入数据
    self._record_node_input_data(execution_state["execution_id"], node_id, node_def, input_data, credentials)

    # 执行节点
    result = executor.execute(context)

    # 记录执行结束时间和数据流
    node_end_time = time.time()
    execution_state["performance_metrics"]["node_execution_times"][node_id].update({
        "end_time": node_end_time,
        "duration": node_end_time - node_start_time
    })

    # 记录数据流
    self._record_data_flow(execution_state["execution_id"], node_id, input_data, result.output_data, node_def)

    # 记录执行路径
    self._record_execution_path_step(execution_id, node_id, node_result, workflow_definition)

    return result
```

#### 2.2.4 数据收集方法

**执行路径记录：**
```python
def _record_execution_path_step(self, execution_id, node_id, node_result, workflow_definition):
    """Record a step in the execution path."""

    path_step = {
        "node_id": node_id,
        "node_name": node_def.get("name", ""),
        "node_type": node_def.get("type", ""),
        "node_subtype": node_def.get("subtype", ""),
        "start_time": execution_state["performance_metrics"]["node_execution_times"][node_id]["start_time"],
        "end_time": execution_state["performance_metrics"]["node_execution_times"][node_id]["end_time"],
        "execution_time": execution_state["performance_metrics"]["node_execution_times"][node_id]["duration"],
        "status": node_result["status"],
        "input_sources": self._get_input_sources(node_id, workflow_definition),
        "output_targets": self._get_output_targets(node_id, workflow_definition),
        "connections": self._get_connection_info(node_id, workflow_definition),
        "context_variables": {},
        "error": node_result.get("error_message") if node_result["status"] == "error" else None
    }

    execution_state["execution_path"]["steps"].append(path_step)
```

**节点输入数据记录：**
```python
def _record_node_input_data(self, execution_id, node_id, node_def, input_data, credentials):
    """Record node input data for debugging."""

    node_input_data = {
        "node_id": node_id,
        "node_name": node_def.get("name", ""),
        "input_data": input_data,
        "connections": self._get_connection_data(node_id, execution_state),
        "parameters": node_def.get("parameters", {}),
        "credentials": {k: "***" if "password" in k.lower() or "token" in k.lower() else v
                       for k, v in credentials.items()},
        "static_data": {},
        "timestamp": int(time.time())
    }

    execution_state["node_inputs"][node_id] = node_input_data
```

**数据流记录：**
```python
def _record_data_flow(self, execution_id, node_id, input_data, output_data, node_def):
    """Record data flow information."""

    data_transfer = {
        "node_id": node_id,
        "node_name": node_def.get("name", ""),
        "node_type": node_def.get("type", ""),
        "input_data_size": len(str(input_data)),
        "output_data_size": len(str(output_data)),
        "data_transformation": self._detect_data_transformation(input_data, output_data),
        "timestamp": int(time.time())
    }

    execution_state["data_flow"]["data_transfers"].append(data_transfer)
```

#### 2.2.5 执行报告生成
```python
def _generate_execution_report(self, execution_id, execution_state):
    """Generate comprehensive execution report for Agent debugging."""

    report = {
        "execution_summary": {
            "execution_id": execution_id,
            "workflow_id": execution_state["workflow_id"],
            "status": execution_state["status"],
            "total_execution_time": total_execution_time,
            "nodes_executed": len(execution_state["execution_path"]["steps"]),
            "nodes_failed": len([step for step in execution_state["execution_path"]["steps"]
                               if step["status"] == "error"]),
            "start_time": execution_state["start_time"],
            "end_time": execution_state["end_time"]
        },
        "execution_path": execution_state["execution_path"],
        "node_inputs": execution_state["node_inputs"],
        "performance_metrics": execution_state["performance_metrics"],
        "data_flow": execution_state["data_flow"],
        "execution_context": execution_state["execution_context"],
        "errors": execution_state.get("error_records", [])
    }

    return report
```

## 3. 测试验证

### 3.1 测试文件
- `apps/backend/workflow_engine/test_enhanced_execution.py`

### 3.2 测试内容
1. **基本执行测试**: 验证增强执行引擎的基本功能
2. **数据收集测试**: 验证执行路径、节点输入、性能指标等数据收集
3. **错误处理测试**: 验证错误记录和分析功能
4. **报告生成测试**: 验证执行报告的生成和内容

### 3.3 运行测试
```bash
cd apps/backend/workflow_engine
python test_enhanced_execution.py
```

## 4. Agent集成支持

### 4.1 提供给Agent的信息

**执行结果：**
- 完整的执行状态和结果
- 每个节点的执行结果
- 错误信息和调试数据

**执行路径：**
- 实际执行的节点顺序
- 每个节点的执行时间
- 分支决策和循环信息
- 跳过的节点

**节点入参：**
- 每个节点的实际输入数据
- 数据来源和连接信息
- 节点参数和配置
- 执行上下文

### 4.2 Agent可以进行的分析

1. **执行路径分析**：
   - 识别实际执行的路径
   - 分析分支决策的正确性
   - 检测循环执行效率

2. **数据流分析**：
   - 追踪数据在节点间的传递
   - 分析数据转换和丢失
   - 检测数据依赖关系

3. **性能分析**：
   - 识别性能瓶颈
   - 分析节点执行时间
   - 优化执行顺序

4. **错误诊断**：
   - 分析错误原因
   - 提供修复建议
   - 预测潜在问题

## 5. 使用示例

### 5.1 基本使用
```python
from workflow_engine.execution_engine import EnhancedWorkflowExecutionEngine

# 创建增强执行引擎
engine = EnhancedWorkflowExecutionEngine()

# 执行工作流
result = engine.execute_workflow(
    workflow_id="test-workflow",
    execution_id="test-execution-001",
    workflow_definition=workflow_definition,
    initial_data={"user_input": "test"},
    credentials={"api_key": "test"}
)

# 获取执行报告
report = engine.get_execution_report("test-execution-001")
```

### 5.2 分析执行路径
```python
# 获取执行路径
execution_path = report["execution_path"]

# 分析执行步骤
for step in execution_path["steps"]:
    print(f"Node: {step['node_name']}")
    print(f"Status: {step['status']}")
    print(f"Time: {step['execution_time']:.3f}s")
    print(f"Input sources: {step['input_sources']}")
```

### 5.3 分析节点输入
```python
# 获取节点输入数据
node_inputs = report["node_inputs"]

# 分析特定节点的输入
for node_id, input_data in node_inputs.items():
    print(f"Node: {input_data['node_name']}")
    print(f"Input keys: {list(input_data['input_data'].keys())}")
    print(f"Parameters: {input_data['parameters']}")
```

## 6. 总结

### 6.1 实现的功能
1. ✅ **扩展RunData结构**: 支持执行路径、节点入参、执行上下文
2. ✅ **增强执行引擎**: 详细的数据收集和跟踪
3. ✅ **性能监控**: 执行时间和资源使用监控
4. ✅ **数据流分析**: 数据传递和转换跟踪
5. ✅ **错误记录**: 详细的错误信息和调试数据
6. ✅ **执行报告**: 完整的执行报告生成

### 6.2 对Agent的支持
1. ✅ **执行结果获取**: Agent可以获取完整的执行结果
2. ✅ **执行路径分析**: Agent可以分析实际执行路径
3. ✅ **节点入参分析**: Agent可以分析每个节点的输入参数
4. ✅ **性能优化**: Agent可以基于性能数据进行优化
5. ✅ **错误诊断**: Agent可以基于错误信息进行诊断和修复

### 6.3 下一步工作
1. **集成到Agent系统**: 将增强的执行引擎集成到workflow_agent
2. **自动调试服务**: 基于收集的数据实现自动调试功能
3. **性能优化**: 优化数据收集的性能和存储
4. **可视化支持**: 为前端提供执行数据的可视化支持

这个实现为Agent提供了完整的执行信息，支持真正的自动调试和优化功能。
