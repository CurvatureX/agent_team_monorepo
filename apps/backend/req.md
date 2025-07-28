我现在要进行一个大的升级，包含以下几个需求，你需要先详细了解 api-gateway 和 workflow_agent 的代码架构，然后帮我完成以下需求:
1. 我定义了新的 workflow_agent.proto 文件，在 shared/proto 里，根据这个文件更新 rpc_client 和 rpc_servedr
2. 这是目前的 workflow_agent_states table 的 schema，api-gateway 在 /chat/stream 每次根据 session_id 先读取 workflow_agent_state，放到 rpc request 内，然后流式地读取 rpc response，rpc response 是 workflow_agent 返回的，现在 workflow_agent 只返回最新的 agentState, 处理逻辑放在 api-gateway 中。api-gateway 每次会保存最新的 agentState，然后处理业务逻辑，API 接口会返回三种类型：1. ai message，就是纯 text 2. 生成的 workflow，仅当 debug 或者 workflow_generation 节点生成 workflow data 的时候, 3. error message.
```
create table public.workflow_agent_states (
  id uuid not null default gen_random_uuid (),
  session_id character varying(255) not null,
  user_id character varying(255) not null,
  created_at bigint not null,
  updated_at bigint not null default (
    EXTRACT(
      epoch
      from
        now()
    ) * (1000)::numeric
  ),
  stage character varying(50) not null default 'clarification'::character varying,
  previous_stage character varying(50) null,
  execution_history text[] null,
  intent_summary text null default ''::text,
  clarification_context jsonb not null default '{}'::jsonb,
  workflow_context jsonb null default '{}'::jsonb,
  conversations jsonb not null default '[]'::jsonb,
  gaps text[] null,
  alternatives jsonb null default '[]'::jsonb,
  current_workflow_json text null default ''::text,
  debug_result text null default ''::text,
  debug_loop_count integer null default 0,
  rag_context jsonb null,
  constraint workflow_agent_states_pkey primary key (id)
) TABLESPACE pg_default;
```