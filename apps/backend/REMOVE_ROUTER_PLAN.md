# 移除 Router 节点的实施方案

## 理由

1. **所有请求都从 clarification 开始**
   - 新建 workflow：需要理解用户需求
   - Resume workflow：处理用户新输入
   - 没有需要从其他节点开始的场景

2. **Router 只是一个中转站**
   - 没有业务逻辑
   - 只是根据 stage 转发
   - 增加了不必要的复杂性

## 实施步骤

### 1. 修改 workflow_agent.py

```python
def _setup_graph(self):
    """Setup the simplified LangGraph workflow"""
    workflow = StateGraph(WorkflowState)
    
    # 直接添加节点，不需要 router
    workflow.add_node("clarification", self.nodes.clarification_node)
    workflow.add_node("gap_analysis", self.nodes.gap_analysis_node)
    workflow.add_node("alternative_generation", self.nodes.alternative_solution_generation_node)
    workflow.add_node("workflow_generation", self.nodes.workflow_generation_node)
    workflow.add_node("debug", self.nodes.debug_node)
    
    # 直接设置 clarification 为入口
    workflow.set_entry_point("clarification")
    
    # 保持原有的条件边
    workflow.add_conditional_edges(
        "clarification",
        self.nodes.should_continue,
        {
            "clarification": "clarification",
            "gap_analysis": "gap_analysis",
            "END": END,
        },
    )
    # ... 其他边保持不变
```

### 2. 移除 fastapi_server.py 中的特殊处理

```python
# 移除 is_from_router 相关逻辑
# 移除 if node_name == 'router' 的特殊处理
# 简化 _should_terminate_workflow 方法
```

### 3. 测试验证

- 新建 workflow 流程
- Resume workflow 流程
- 多轮对话流程

## 预期收益

1. **性能提升**：减少一个节点的执行时间
2. **代码简化**：移除特殊处理逻辑
3. **可维护性**：更直观的流程
4. **日志清晰**：不再有 router 的干扰日志

## 风险评估

- **低风险**：Router 没有业务逻辑，移除影响小
- **易回滚**：如果发现问题，可以快速恢复

## 结论

移除 Router 是一个合理的架构优化，可以简化系统而不影响功能。