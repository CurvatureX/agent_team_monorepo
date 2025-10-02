import sys
import time
import types as _types
from pathlib import Path

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from pprint import pprint as _pp

from shared.models import TriggerInfo
from shared.models.node_enums import ActionSubtype, FlowSubtype, NodeType, TriggerSubtype
from shared.models.workflow_new import Connection, Workflow, WorkflowMetadata, WorkflowStatistics

"""Ensure optional deps won't break imports (stub supabase)."""
if "supabase" not in sys.modules:
    _supabase = _types.ModuleType("supabase")

    def _create_client(*args, **kwargs):
        class _Dummy:
            def __getattr__(self, item):
                raise RuntimeError("supabase client is not available in tests")

        return _Dummy()

    _supabase.create_client = _create_client
    sys.modules["supabase"] = _supabase

from workflow_engine_v2 import ExecutionEngine
from workflow_engine_v2.core.spec import coerce_node_to_v2, get_spec


def _metadata(id_: str, name: str) -> WorkflowMetadata:
    return WorkflowMetadata(
        id=id_,
        name=name,
        created_time=int(time.time() * 1000),
        created_by="tester",
        statistics=WorkflowStatistics(),
    )


def test_conversion_function_routes_to_main_port():
    engine = ExecutionEngine()

    # Source: TRIGGER → provides raw webhook payload on main
    print("[STEP] Load source spec: TRIGGER.WEBHOOK")
    src_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    src = coerce_node_to_v2(src_spec.create_node_instance("src"))
    print("[STEP] Source node created:")
    _pp({"id": src.id, "type": str(src.type), "subtype": src.subtype})

    # Destination: ACTION(DATA_TRANSFORMATION) → no network, safe runner
    print("[STEP] Load destination spec: ACTION.DATA_TRANSFORMATION")
    dst_spec = get_spec(NodeType.ACTION.value, ActionSubtype.DATA_TRANSFORMATION.value)
    dst = coerce_node_to_v2(dst_spec.create_node_instance("dst"))
    # Keep default config; runner will pass-through src if no mapping set
    print("[STEP] Destination node created:")
    _pp({"id": dst.id, "type": str(dst.type), "subtype": dst.subtype})

    # Conversion: sum fields from source into nested structure expected by dst
    print("[STEP] Define conversion function (sum a+b into nested dict)")
    conv = (
        "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:\n"
        "    total = int(input_data['data'].get('a', 0)) + int(input_data['data'].get('b', 0))\n"
        "    return {'foo': {'bar': total}}\n"
    )

    print("[STEP] Compose workflow with connection: src.main -> dst.main (with conversion)")
    wf = Workflow(
        metadata=_metadata("wf_conv_main", "Conversion to main port"),
        nodes=[src, dst],
        connections=[
            Connection(
                id="c1",
                from_node=src.id,
                to_node=dst.id,
                output_key="result",
                conversion_function=conv,
            )
        ],
        triggers=[src.id],
    )

    trig = TriggerInfo(
        trigger_type="WEBHOOK",
        trigger_data={"a": 10, "b": 5},
        timestamp=int(time.time() * 1000),
    )
    print("[STEP] Trigger payload:")
    _pp(trig.trigger_data)
    print("[STEP] Execute engine")
    execu = engine.run(wf, trig)
    print("[STEP] Execution status:", execu.status.value)

    # Verify dst node saw converted input on correct port
    print("[STEP] Destination node input_data:")
    dst_inputs = execu.node_executions[dst.id].input_data
    _pp(dst_inputs)
    assert "result" in dst_inputs
    assert dst_inputs["result"]["foo"]["bar"] == 15
    print("[STEP] Destination node output_data:")
    _pp(execu.node_executions[dst.id].output_data)


def test_conversion_function_routes_to_named_port():
    engine = ExecutionEngine()

    # Source: TRIGGER
    print("[STEP] Load source spec: TRIGGER.WEBHOOK")
    src_spec = get_spec(NodeType.TRIGGER.value, TriggerSubtype.WEBHOOK.value)
    src = coerce_node_to_v2(src_spec.create_node_instance("src2"))
    print("[STEP] Source node created:")
    _pp({"id": src.id, "type": str(src.type), "subtype": src.subtype})

    # Destination: FLOW(FILTER) with override port 'filter_config'
    print("[STEP] Load destination spec: FLOW.FILTER")
    dst_spec = get_spec(NodeType.FLOW.value, FlowSubtype.FILTER.value)
    dst = coerce_node_to_v2(dst_spec.create_node_instance("flt"))
    # No static expression; we will inject expression via port
    print("[STEP] Destination node created:")
    _pp({"id": dst.id, "type": str(dst.type), "subtype": dst.subtype})

    # Conversion: build filter_config override that sets expression true
    print("[STEP] Define conversion function for filter_config port")
    conv = (
        "def convert(input_data: Dict[str, Any]) -> Dict[str, Any]:\n"
        "    # route dynamic predicate; always truthy here\n"
        "    return {'expression': 'item is not None'}\n"
    )

    print(
        "[STEP] Compose workflow with connection: src.main -> flt.filter_config (with conversion)"
    )
    wf = Workflow(
        metadata=_metadata("wf_conv_named", "Conversion to named port"),
        nodes=[src, dst],
        connections=[
            Connection(
                id="c1",
                from_node=src.id,
                to_node=dst.id,
                output_key="result",
                conversion_function=conv,
            )
        ],
        triggers=[src.id],
    )

    trig = TriggerInfo(
        trigger_type="WEBHOOK",
        trigger_data={"items": [1, 2, 3]},
        timestamp=int(time.time() * 1000),
    )
    print("[STEP] Trigger payload:")
    _pp(trig.trigger_data)
    print("[STEP] Execute engine")
    execu = engine.run(wf, trig)
    print("[STEP] Execution status:", execu.status.value)

    # Verify dst node received injected config on filter_config port
    dst_inputs = execu.node_executions[dst.id].input_data
    print("[STEP] Destination node input_data:")
    _pp(dst_inputs)
    assert "filter_config" in dst_inputs
    assert dst_inputs["filter_config"]["expression"] == "item is not None"

    # And it completed successfully with 'passed' populated due to truthy predicate
    dst_outputs = execu.node_executions[dst.id].output_data
    print("[STEP] Destination node output_data:")
    _pp(dst_outputs)
    # shaped outputs hold full object under ports; ensure port keys exist
    assert "passed" in dst_outputs or "result" in dst_outputs
