# AWS ECS 服务间通信分析与优化建议

## 🔍 当前架构分析

### 网络架构

**VPC配置：**
- ✅ Private Subnets: ECS任务运行在私有子网中
- ✅ Service Discovery: 使用 `${local.name_prefix}.local` 命名空间
- ✅ Security Groups: 配置了适当的inter-service通信规则

**负载均衡器：**
- 🌐 **External ALB** (`aws_lb.main`): 面向公网，处理外部流量
- 🏠 **Internal ALB** (`aws_lb.internal`): 面向内网，处理服务间流量

### 服务发现配置

所有服务都配置了AWS Service Discovery：
```
api-gateway.starmates-ai-team.local:8000
workflow-agent.starmates-ai-team.local:8001  
workflow-engine.starmates-ai-team.local:8002
workflow-scheduler.starmates-ai-team.local:8003
```

## ⚠️ 当前配置问题

### 1. 混合的URL配置方式

**API Gateway 环境变量:**
- ❌ `WORKFLOW_AGENT_URL="http://${aws_lb.internal.dns_name}/process-conversation"`
- ❌ `WORKFLOW_ENGINE_URL="http://${aws_lb.internal.dns_name}"`

**Workflow Agent 环境变量:**
- ✅ `WORKFLOW_ENGINE_URL="http://workflow-engine.${local.name_prefix}.local:8002"`
- ✅ `API_GATEWAY_URL="http://api-gateway.${local.name_prefix}.local:8000"`

**Workflow Scheduler 环境变量:**
- ❌ `WORKFLOW_ENGINE_URL="http://${aws_lb.internal.dns_name}/v1"`
- ❌ `API_GATEWAY_URL="http://${aws_lb.main.dns_name}"`

### 2. 性能和复杂性问题

**不必要的网络跳转:**
- API Gateway → Internal ALB → Workflow Agent (3跳)
- 应该是: API Gateway → Workflow Agent (直连)

**路由复杂性:**
- Load Balancer需要维护路径路由规则
- 增加了故障点和延迟

## ✅ 优化建议

### 推荐架构：直接Service Discovery通信

```
用户请求 → External ALB → API Gateway
                        ↓ (Service Discovery)
                   Workflow Agent ←→ Workflow Engine
                        ↓ (Service Discovery)  
                   Workflow Scheduler
```

### 优化后的环境变量配置

**API Gateway Task Definition:**
```hcl
environment = [
  {
    name  = "DEBUG"
    value = "false"
  },
  {
    name  = "WORKFLOW_AGENT_URL"
    value = "http://workflow-agent.${local.name_prefix}.local:8001"
  },
  {
    name  = "WORKFLOW_ENGINE_URL"
    value = "http://workflow-engine.${local.name_prefix}.local:8002"
  },
  # ... 其他配置
]
```

**Workflow Scheduler Task Definition:**
```hcl
environment = [
  # ... 其他配置 ...
  {
    name  = "WORKFLOW_ENGINE_URL"
    value = "http://workflow-engine.${local.name_prefix}.local:8002"
  },
  {
    name  = "API_GATEWAY_URL"
    value = "http://api-gateway.${local.name_prefix}.local:8000"
  },
  # ... 其他配置
]
```

## 🎯 优化效果

### 性能提升
- ⚡ **减少网络延迟**: 去除不必要的Load Balancer跳转
- 🚀 **提高吞吐量**: 直连减少网络瓶颈
- 💾 **降低资源消耗**: 减少ALB处理负载

### 可靠性提升  
- 🛡️ **减少故障点**: fewer hops = fewer potential failures
- 📈 **提高可用性**: 服务直连更加稳定
- 🔧 **简化故障排查**: 减少网络层复杂性

### 成本优化
- 💰 **减少ALB成本**: 降低Internal ALB的处理请求数
- ⚡ **减少数据传输费用**: 减少跨AZ流量（如果适用）

## 🔧 实施步骤

### 1. 修改Terraform配置
```bash
# 修改 infra/ecs.tf 中的环境变量配置
terraform plan   # 查看变更
terraform apply  # 应用变更
```

### 2. 验证内网通信
```bash
# ECS Exec进入容器测试
aws ecs execute-command --cluster starmates-ai-team-cluster \
  --task TASK_ID --container api-gateway \
  --command "/bin/bash" --interactive

# 容器内测试Service Discovery
nslookup workflow-agent.starmates-ai-team.local
curl http://workflow-agent.starmates-ai-team.local:8001/health
```

### 3. 监控指标
- 监控服务响应时间
- 检查错误率变化  
- 观察ALB请求数变化

## 🚨 注意事项

1. **保留External ALB**: 仍需要面向公网的Load Balancer
2. **保留Internal ALB**: 可能有其他用途，先保留配置
3. **逐步迁移**: 可以先测试一个服务，再全面推广
4. **回滚准备**: 保留原配置作为备份

## ✅ 当前配置是否满足需求？

**答案: 部分满足，但不是最优**

- ✅ **网络连通性**: Security Groups配置正确，服务可以互相访问
- ✅ **服务发现**: AWS Service Discovery已正确配置
- ⚠️ **性能**: 当前通过Load Balancer的路由增加了不必要的延迟
- ⚠️ **一致性**: 配置不一致，部分用Service Discovery，部分用Load Balancer

**建议：应用上述优化配置以获得最佳性能和一致性。**