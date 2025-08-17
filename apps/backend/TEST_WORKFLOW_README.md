# Workflow 验证测试脚本

## 用途
用于验证 workflow 创建和执行功能，特别是在修改 prompt 或 hardcode 逻辑后确保系统正常工作。

## 功能特点
- ✅ 测试 workflow 创建成功率
- ✅ 验证参数格式正确性（无占位符、无模板变量）
- ✅ 测试 workflow 执行功能
- ✅ 简洁清晰的日志输出
- ✅ 彩色终端输出，易于识别成功/失败

## 使用方法

### 基本使用
```bash
# 运行所有测试
python test_workflow_validation.py

# 快速测试（仅第一个用例）
python test_workflow_validation.py --quick

# 详细日志模式
python test_workflow_validation.py --verbose

# 运行特定测试用例
python test_workflow_validation.py --case TC002
```

### 环境配置
确保 `.env` 文件包含以下配置：
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=your-password
API_BASE_URL=http://localhost:8000  # 可选，默认值
```

## 测试用例

| ID | 名称 | 描述 | 验证内容 |
|---|------|------|----------|
| TC001 | GitHub to Webhook | GitHub issue 触发 webhook | 参数格式、节点类型、执行测试 |
| TC002 | Scheduled Task | 定时任务创建 | Cron 表达式验证、仅创建测试 |
| TC003 | Slack Integration | Webhook 触发 Slack 消息 | 外部集成节点验证 |
| TC004 | AI Processing | AI 处理邮件分类 | AI 节点参数验证 |
| TC005 | Complex Workflow | 多步骤复杂流程 | 复杂 workflow 结构验证 |

## 输出说明

### 日志级别
- `ℹ INFO` - 一般信息（蓝色）
- `✓ SUCCESS` - 成功操作（绿色）
- `✗ ERROR` - 错误信息（红色）
- `⚠ WARNING` - 警告信息（黄色）

### 测试结果
```
Results:
  ✓ TC001: PASS  # 测试通过
  ✗ TC002: FAIL  # 测试失败
  ○ TC003: SKIP  # 测试跳过

Summary:
  Total:   5
  Passed:  3
  Failed:  1
  Skipped: 1

Success Rate: 80.0%
```

### 结论提示
- ✅ 100% 通过：系统工作正常
- ⚠️ 部分失败：需要检查失败的测试
- ❌ 多个失败：系统需要修复

## 验证规则

### 参数验证
- 不允许占位符：`<OWNER>/<REPO>`, `<YOUR_TOKEN>`
- 不允许模板变量：`{{trigger.xxx}}`, `${env.xxx}`
- ID/number 字段不能为 0
- 节点类型不能有 `_NODE` 后缀

### 结构验证
- 必须包含期望的节点类型
- 参数必须符合类型要求（string, integer, boolean）
- URL 必须以 http/https 开头
- Repository 必须包含 `/` 且格式正确

## 扩展测试用例

如需添加新的测试用例，在 `get_test_cases()` 函数中添加：

```python
TestCase(
    id="TC006",
    name="新测试名称",
    description="测试描述",
    user_request="用户请求的 workflow 描述",
    expected_nodes=["TRIGGER", "ACTION"],  # 期望的节点类型
    validation_rules={
        "TRIGGER": {
            "param_name": lambda v: validation_function(v),
        }
    },
    execution_data={...},  # 可选，执行测试数据
    tags=["tag1", "tag2"]
)
```

## 故障排查

### 常见问题

1. **认证失败**
   - 检查 `.env` 中的凭据是否正确
   - 确认测试账号存在于 Supabase

2. **Workflow 创建失败**
   - 检查 workflow-agent 服务是否运行
   - 查看 Docker logs 确认错误原因

3. **执行失败**
   - 确认 workflow-engine 服务正常
   - 检查执行数据格式是否正确

4. **超时错误**
   - 增加 timeout 参数值
   - 检查网络连接

## 维护建议

1. 定期运行测试确保系统稳定性
2. 在修改 prompt 模板后必须运行测试
3. 在修改参数验证逻辑后必须运行测试
4. 保持测试用例与实际使用场景同步