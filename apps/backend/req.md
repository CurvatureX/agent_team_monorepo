1. 总共4个node, clarification, gap analysis, workflow generation, debug
2. clarification node 逻辑：
   1. 用户每次 input 都是进入 clarification
   2. clarification 分析历史所有对话(user + assistant)，看一下是否还有必要澄清，如果没有必要的话就生成 intent_summary，进入 gap analysis, 否则生成 question 给到 user，结束 graph
3. gap analysis node 逻辑：
   1. 根据历史对话和 intent_summary 分析现有能力是否有 gap，有的话生成 gap，发送消息给用户(此时也是一条 system message)，然后进入 clarification node，结束 graph，没有则进入 workflow generation
4. workflow generation node 和 debug node 的具体 prompt 还没写完，待定
