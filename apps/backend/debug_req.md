我现在需要完成 workflow_agent 中的 debug node 重构。新的 debug node 的整体逻辑我打算这样:
1. 获取 workflow generation node 生成的 JSON, 用这个 JSON 调用 workflow_engine 的 POST /api/v1/workflow 接口创建 workflow
2. 创建 workflow 后，调用 workflow_engine 的 POST /api/v1/workflow/your-workflow-id/execute 接口执行测试 workflow
3. 如果执行成功，那么结束
4. 如果执行失败，那么把返回失败的信息告诉 workflow generation node, workflow generation node 要支持根据错误的信息重新生成 workflow / node 节点，然后再跑

这是整体的思路，但是有一些细节我没想好:
1. workflow excution 时需要填写具体的参数，这个参数如何确定，是否是增加一个 LLM 来生成
2. 如果执行失败，那么有可能是node参数错误，也有可能是整个 workflow JSON 生成失败。但是我理解 workflow generation 通过 LLM 强制输出格式后不应该出现 JSON 格式问题，node 参数也是，所以这部分可以先留着，试着运行一下再看。你觉得如何？