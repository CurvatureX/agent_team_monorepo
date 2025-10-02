import sys
import time
from pathlib import Path

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models import ExecutionStatus, TriggerInfo
from shared.models.node_enums import ActionSubtype, FlowSubtype, NodeType, TriggerSubtype
from shared.models.workflow_new import Connection, Workflow, WorkflowMetadata, WorkflowStatistics
from workflow_engine_v2 import ExecutionEngine
from workflow_engine_v2.core.spec import coerce_node_to_v2, get_spec


def build_wait_foreach_workflow():
    trig = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    wait = get_spec(NodeType.FLOW.value, FlowSubtype.WAIT.value)
    foreach = get_spec(NodeType.FLOW.value, FlowSubtype.FOR_EACH.value)
    http = get_spec(NodeType.ACTION.value, ActionSubtype.HTTP_REQUEST.value)

    t1 = coerce_node_to_v2(trig.create_node_instance("t1"))
    w1 = coerce_node_to_v2(wait.create_node_instance("w1"))
    f1 = coerce_node_to_v2(foreach.create_node_instance("f1"))
    a1 = coerce_node_to_v2(http.create_node_instance("a1"))
    # Configure wait to pass immediately if condition true
    w1.configurations.update({"wait_condition": "$json.ready == true"})
    # Action targets httpbin (use dummy endpoint)
    a1.configurations.update({"method": "GET", "url": "https://example.com/test"})

    meta = WorkflowMetadata(
        id="wf_wf",
        name="WaitForEach",
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )
    wf = Workflow(
        metadata=meta,
        nodes=[t1, w1, f1, a1],
        connections=[
            Connection(id="c1", from_node=t1.id, to_node=w1.id, output_key="result"),
            Connection(id="c2", from_node=w1.id, to_node=f1.id, output_key="completed"),
            Connection(id="c3", from_node=f1.id, to_node=a1.id, output_key="iteration"),
        ],
        triggers=[t1.id],
    )
    return wf


def test_wait_then_foreach_fanout():
    eng = ExecutionEngine()
    wf = build_wait_foreach_workflow()
    trig = TriggerInfo(
        trigger_type="WEBHOOK",
        trigger_data={"ready": True, "items": [1, 2, 3]},
        timestamp=int(time.time() * 1000),
    )
    res = eng.run(wf, trig)
    assert res.status in (ExecutionStatus.SUCCESS, ExecutionStatus.WAITING)
