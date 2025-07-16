
任务：
工具集成和 API 适配
任务: 第三方工具集成和 API 适配

实现完整的工具集成能力，支持现有工作流引擎的TOOL_NODE类型，集成主流第三方服务API。

核心工具集成：

集成 Google Calendar API
集成 GitHub API  
集成 Slack API
实现通用 HTTP 请求工具
工具框架设计：

实现工具节点基础框架
设计 API 调用适配器
实现 OAuth2 授权框架
创建凭证管理系统
交付物:

工具集成框架（替换现有模拟实现）
API 适配器系统（支持4个核心工具）
核心工具集成（Google Calendar、GitHub、Slack、HTTP）
OAuth2认证流程（完整授权和凭证管理）

基于技术设计文档中的一部分实现，使用定义好的接口进行实现：
agent_team_monorepo/docs/tech-design/[MVP] Workflow Data Structure Definition.md

参考现有的AI工具比如n8n等实现的接入Google Calendar等和授权