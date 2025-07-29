我在重构api-gateway的/sessions和/chat/stream接口，主要改动是更新了 /backend/shared/workflow_agent.proto 的 IDL。请你根据最新的 IDL 完成以下改动：
1. 把最新的 IDL 生成对应的 pb rpc client 和 rpc server 到 api-gateway 和 workflow_agent 目录下，项目结构可以参考目前的结构
2. 更新 /sessions 接口，在请求 /sessions 接口时只 init 一个 session，不新建 workflow_agent_state
3. workflow_agent_state 的 CRUD 操作全部放到 workflow_agent 服务中，在 api-gateway 里只做对 workflow_agent 接口的传参和返回，不做具体的业务逻辑
4. api-gateway 的 /sessions 和 /chat/stream 接口的逻辑也要按照 proto 文件来处理，比如 action 是 edit|copy|create，review 并修改 api-gateway 的代码逻辑
5. 删除现有的测试文件，重新写测试

注意代码的架构清晰和整洁！！！