import sys
import time
from pathlib import Path

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, TriggerInfo
from shared.models.node_enums import (
    ActionSubtype,
    FlowSubtype,
    HumanLoopSubtype,
    MemorySubtype,
    NodeType,
    TriggerSubtype,
)
from shared.models.workflow_new import Connection, Workflow, WorkflowMetadata, WorkflowStatistics
from workflow_engine_v2 import ExecutionEngine
from workflow_engine_v2.core.spec import coerce_node_to_v2, get_spec


def build_simple_workflow():
    # Build nodes from specs and coerce to v2 models
    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    act_spec = get_spec(NodeType.ACTION.value, ActionSubtype.HTTP_REQUEST.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("trigger_1"))
    n2 = coerce_node_to_v2(act_spec.create_node_instance("action_1"))

    meta = WorkflowMetadata(
        id="wf_001",
        name="Simple Webhook to HTTP",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )

    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2],
        connections=[Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result")],
        triggers=[n1.id],
    )
    return wf


def test_engine_runs_simple_graph():
    engine = ExecutionEngine()
    wf = build_simple_workflow()
    trigger = TriggerInfo(
        trigger_type="WEBHOOK",
        trigger_data={"msg": "hello"},
        timestamp=int(time.time() * 1000),
    )

    result = engine.run(wf, trigger)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.execution_sequence == ["trigger_1", "action_1"]
    assert set(result.node_executions.keys()) == {"trigger_1", "action_1"}
    assert result.node_executions["trigger_1"].status.value == "completed"
    assert result.node_executions["action_1"].status.value == "completed"


def test_flow_sort_and_pass_through():
    engine = ExecutionEngine()

    # Specs
    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    sort_spec = get_spec(NodeType.FLOW.value, FlowSubtype.SORT.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("t1"))
    n2 = coerce_node_to_v2(sort_spec.create_node_instance("s1"))
    # Configure sort by key_path 'value'
    n2.configurations.update({"key_path": "value", "descending": False})

    meta = WorkflowMetadata(
        id="wf_sort",
        name="SortFlow",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2],
        connections=[Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result")],
        triggers=[n1.id],
    )

    items = [{"value": 3}, {"value": 1}, {"value": 2}]
    trigger = TriggerInfo(
        trigger_type="WEBHOOK", trigger_data=items, timestamp=int(time.time() * 1000)
    )
    res = engine.run(wf, trigger)
    assert res.status == ExecutionStatus.SUCCESS
    sorted_items = res.node_executions["s1"].output_data.get("main")
    assert sorted_items[0]["value"] == 1
    assert sorted_items[-1]["value"] == 3


def test_hil_pause_and_resume():
    engine = ExecutionEngine()

    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    hil_spec = get_spec(NodeType.HUMAN_IN_THE_LOOP.value, HumanLoopSubtype.SLACK_INTERACTION.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("t1"))
    n2 = coerce_node_to_v2(hil_spec.create_node_instance("hil1"))

    meta = WorkflowMetadata(
        id="wf_hil",
        name="HILFlow",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2],
        connections=[Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result")],
        triggers=[n1.id],
    )

    trigger = TriggerInfo(
        trigger_type="WEBHOOK", trigger_data={"msg": "approve?"}, timestamp=int(time.time() * 1000)
    )
    paused = engine.run(wf, trigger)
    assert paused.status in (ExecutionStatus.WAITING_FOR_HUMAN, ExecutionStatus.WAITING)
    # Resume with user input
    resumed = engine.resume_with_user_input(
        paused.execution_id, node_id="hil1", input_data={"approved": True}
    )
    assert resumed.status == ExecutionStatus.SUCCESS


def test_wait_pause_and_resume():
    engine = ExecutionEngine()

    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    wait_spec = get_spec(NodeType.FLOW.value, FlowSubtype.WAIT.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("t1"))
    n2 = coerce_node_to_v2(wait_spec.create_node_instance("w1"))

    meta = WorkflowMetadata(
        id="wf_wait",
        name="WaitFlow",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2],
        connections=[Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result")],
        triggers=[n1.id],
    )
    paused = engine.run(
        wf,
        TriggerInfo(
            trigger_type="WEBHOOK", trigger_data={"x": 1}, timestamp=int(time.time() * 1000)
        ),
    )
    assert paused.status == ExecutionStatus.WAITING
    resumed = engine.resume_with_user_input(paused.execution_id, node_id="w1", input_data={"x": 1})
    assert resumed.status == ExecutionStatus.SUCCESS


def test_delay_resume_due_timer():
    engine = ExecutionEngine()

    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    delay_spec = get_spec(NodeType.FLOW.value, FlowSubtype.DELAY.value)
    action_spec = get_spec(NodeType.ACTION.value, ActionSubtype.HTTP_REQUEST.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("t1"))
    n2 = coerce_node_to_v2(delay_spec.create_node_instance("d1"))
    n3 = coerce_node_to_v2(action_spec.create_node_instance("a1"))
    # Zero delay for immediate timer trigger
    n2.configurations.update({"duration_seconds": 0})

    meta = WorkflowMetadata(
        id="wf_delay",
        name="DelayFlow",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2, n3],
        connections=[
            Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result"),
            Connection(id="c2", from_node=n2.id, to_node=n3.id, output_key="result"),
        ],
        triggers=[n1.id],
    )
    paused = engine.run(
        wf,
        TriggerInfo(
            trigger_type="WEBHOOK", trigger_data={"x": 1}, timestamp=int(time.time() * 1000)
        ),
    )
    assert paused.status == ExecutionStatus.WAITING
    # Resume due timers; zero ms should be due immediately
    engine.resume_due_timers()
    # After timers resume, execution should complete
    # We don't have direct return here; in a real environment, repository/event would notify.
    # For test: call resume_timer directly as the engine stored current node.
    resumed = engine.resume_timer(paused.execution_id, node_id="d1")
    assert resumed.status == ExecutionStatus.SUCCESS


def test_memory_set_and_get():
    engine = ExecutionEngine()

    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    mem_spec = get_spec(NodeType.MEMORY.value, MemorySubtype.KEY_VALUE_STORE.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("t1"))
    n2 = coerce_node_to_v2(mem_spec.create_node_instance("mset"))
    n3 = coerce_node_to_v2(mem_spec.create_node_instance("mget"))
    n2.configurations.update({"operation": "set", "key": "k"})
    n3.configurations.update({"operation": "get", "key": "k"})

    meta = WorkflowMetadata(
        id="wf_mem",
        name="MemoryFlow",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2, n3],
        connections=[
            Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result"),
            Connection(id="c2", from_node=n2.id, to_node=n3.id, output_key="result"),
        ],
        triggers=[n1.id],
    )
    res = engine.run(
        wf,
        TriggerInfo(
            trigger_type="WEBHOOK", trigger_data={"foo": 123}, timestamp=int(time.time() * 1000)
        ),
    )
    assert res.status == ExecutionStatus.SUCCESS
    assert res.node_executions["mget"].output_data["main"] == {"foo": 123}


def test_loop_range_aggregates_results():
    engine = ExecutionEngine()

    trig_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    loop_spec = get_spec(NodeType.FLOW.value, FlowSubtype.LOOP.value)

    n1 = coerce_node_to_v2(trig_spec.create_node_instance("t1"))
    n2 = coerce_node_to_v2(loop_spec.create_node_instance("loop1"))
    n2.configurations.update(
        {
            "loop_type": "for_range",
            "start_value": 1,
            "end_value": 3,
            "step_value": 1,
            "iteration_variable": "i",
        }
    )

    meta = WorkflowMetadata(
        id="wf_loop",
        name="LoopFlow",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[n1, n2],
        connections=[Connection(id="c1", from_node=n1.id, to_node=n2.id, output_key="result")],
        triggers=[n1.id],
    )
    res = engine.run(
        wf,
        TriggerInfo(
            trigger_type="WEBHOOK", trigger_data={"x": 1}, timestamp=int(time.time() * 1000)
        ),
    )
    assert res.status == ExecutionStatus.SUCCESS
    it = res.node_executions["loop1"].output_data["iteration"]
    assert len(it) == 3
    assert it[0]["i"] == 1 and it[-1]["i"] == 3
