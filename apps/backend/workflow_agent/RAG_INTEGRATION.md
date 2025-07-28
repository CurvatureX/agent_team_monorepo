# RAG集成指南

本文档说明如何在Workflow Agent中使用RAG (Retrieval-Augmented Generation) 系统来增强智能工作流生成能力。

## 概述

RAG系统通过集成Supabase向量数据库，为工作流生成提供智能的节点知识检索和推荐功能。系统包含以下核心组件：

- **Supabase Vector Store**: 存储节点知识向量嵌入
- **NodeKnowledgeRAG**: 智能检索和推荐服务
- **Enhanced Engines**: 增强的分析、协商和设计引擎

## 功能特性

### 🎯 智能能力扫描
- 基于需求自动识别所需节点类型
- RAG推荐替代方案和最佳实践
- 动态复杂度评估和风险分析

### 🏗️ 智能节点选择
- 基于任务描述推荐最合适的节点类型
- 提供配置建议和参数优化
- 集成历史案例和经验知识

### 🤝 增强协商体验
- RAG支持的解决方案推荐
- 基于知识库的最佳实践建议
- 智能权衡分析和风险评估

## 配置要求

### 环境变量

```bash
# Supabase配置 (只需要SECRET_KEY)
SUPABASE_URL=your_supabase_url
SUPABASE_SECRET_KEY=your_service_key

# OpenAI配置 (用于向量嵌入)
OPENAI_API_KEY=your_openai_key

# RAG配置
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_DIMENSIONS=1536
RAG_SIMILARITY_THRESHOLD=0.3
RAG_MAX_RESULTS=5
RAG_ENABLE_RERANKING=true
```

### 数据库迁移

确保Supabase数据库已应用vector store迁移：

```sql
-- 位于 supabase/migrations/20250715000002_node_knowledge_vectors.sql
-- 包含node_knowledge_vectors表和match_node_knowledge函数
```

## 使用指南

### 1. 初始化节点知识数据

运行示例脚本插入节点知识：

```bash
cd apps/backend/workflow_agent
python scripts/insert_node_knowledge.py
```

### 2. 测试RAG功能

测试RAG检索功能：

```bash
python scripts/insert_node_knowledge.py test
```

### 3. 在代码中使用RAG

```python
from core.vector_store import get_node_knowledge_rag

# 获取RAG实例
rag = get_node_knowledge_rag()

# 获取能力推荐
recommendations = await rag.get_capability_recommendations(
    ["email_monitoring", "ai_analysis"],
    context={"complexity_preference": "medium"}
)

# 获取节点类型建议
suggestions = await rag.get_node_type_suggestions(
    "analyze customer emails and route to appropriate handler"
)

# 获取集成指导
guidance = await rag.get_integration_guidance(
    "slack",
    {"data_direction": "output", "authentication": True}
)
```

## 核心组件

### SupabaseVectorStore

负责与Supabase pgvector的交互：

```python
# 相似度搜索
results = await vector_store.similarity_search(
    query="email processing workflow",
    node_type_filter="TRIGGER_EMAIL",
    similarity_threshold=0.5,
    max_results=5
)

# 基于能力搜索
results = await vector_store.search_by_capabilities(
    ["email_monitoring", "content_analysis"],
    complexity_preference="low"
)
```

### NodeKnowledgeRAG

提供高级RAG功能：

```python
# 能力推荐
capability_rec = await rag.get_capability_recommendations(capabilities)

# 节点建议
node_suggestions = await rag.get_node_type_suggestions(task_description)

# 集成指导
integration_guide = await rag.get_integration_guidance(integration_type, requirements)
```

### 增强的智能引擎

#### IntelligentAnalyzer增强
- `perform_capability_scan()`: 结合RAG的能力扫描
- RAG洞察包含覆盖率评分和替代方案推荐

#### IntelligentDesigner增强
- `_generate_node_mappings()`: RAG支持的节点映射
- `enhance_architecture_with_rag()`: 架构RAG增强
- 集成特定设计推荐

#### IntelligentNegotiator增强
- `_generate_recommendation()`: RAG增强的推荐生成
- 基于知识库的最佳实践建议

## 数据结构

### 节点知识条目

```python
{
    "node_type": "TRIGGER_EMAIL",
    "node_subtype": "TRIGGER_EMAIL_GMAIL",
    "title": "Gmail邮件触发器",
    "description": "监控Gmail邮箱中的新邮件...",
    "content": "详细的功能说明和使用指南...",
    "metadata": {
        "complexity": "low",
        "setup_time": "15分钟",
        "capabilities": ["email_monitoring", "real_time_trigger"],
        "best_practices": ["使用标签过滤...", "设置轮询频率..."],
        "example_config": {...}
    }
}
```

### RAG推荐结果

```python
{
    "capability_matches": {
        "email_monitoring": [NodeKnowledgeEntry, ...],
        "ai_analysis": [NodeKnowledgeEntry, ...]
    },
    "missing_capabilities": ["custom_capability"],
    "alternatives": [NodeKnowledgeEntry, ...],
    "coverage_score": 0.85,
    "total_matches": 12
}
```

## 最佳实践

### 🎯 节点知识管理
- 保持知识条目的及时更新
- 确保metadata字段的完整性
- 使用描述性的标题和内容
- 包含真实的配置示例

### 🔍 RAG检索优化
- 调整相似度阈值平衡精度和召回
- 使用节点类型过滤器提高精确度
- 监控检索质量和用户反馈

### 💡 集成最佳实践
- 在IntelligentAnalyzer中结合静态库和RAG结果
- 使用RAG置信度指导推荐权重
- 为低置信度结果提供人工备选方案

### 🛡️ 错误处理
- 实施RAG服务的降级机制
- 记录RAG调用失败的详细日志
- 提供静态规则作为后备方案

## 性能优化

### 缓存策略
- 实施查询结果缓存减少重复检索
- 使用会话级缓存提高响应速度
- 定期清理过期缓存数据

### 向量优化
- 监控嵌入质量和相关性
- 定期重新计算向量嵌入
- 优化数据库索引配置

### 扩展考虑
- 实施连接池管理数据库连接
- 使用异步处理提高并发性能
- 监控RAG服务的资源使用情况

## 故障排除

### 常见问题

**RAG检索无结果**
- 检查Supabase连接配置
- 验证向量数据是否正确插入
- 调整相似度阈值设置

**嵌入生成失败**
- 验证OpenAI API密钥配置
- 检查网络连接和API限制
- 确认嵌入模型配置正确

**性能问题**
- 检查数据库索引效率
- 监控向量维度和数据量
- 优化查询条件和过滤器

### 调试工具

使用内置的测试脚本验证功能：

```bash
# 测试基本RAG功能
python scripts/insert_node_knowledge.py test

# 检查向量存储状态
python -c "
from core.vector_store import SupabaseVectorStore
store = SupabaseVectorStore()
# 执行测试查询
"
```

## 未来增强

### 计划功能
- 动态学习用户偏好
- 多语言节点知识支持
- 高级重排序算法
- 实时知识更新机制

### 扩展可能性
- 集成更多向量数据库
- 支持图像和多模态内容
- 实施联邦学习机制
- 增加知识图谱支持

---

通过这个RAG集成，Workflow Agent现在具备了真正的智能推荐能力，能够基于丰富的节点知识库为用户提供精准的工作流设计建议和最佳实践指导。
