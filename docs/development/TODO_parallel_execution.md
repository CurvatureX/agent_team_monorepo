# TODO: Implement Parallel Node Execution

**Status:** Not Started
**Priority:** Medium
**Estimated Effort:** 4-6 hours
**Created:** 2025-10-13

## Problem Statement

Currently, the workflow engine executes nodes **sequentially** even when multiple independent nodes are ready to run in parallel. This leads to unnecessary execution time when an AI node outputs to multiple external action nodes.

### Current Behavior (Sequential)
```
AI_NODE completes → EXTERNAL_ACTION_1, EXTERNAL_ACTION_2 both become ready
                 → Queue: [ACTION_1, ACTION_2]
                 → ACTION_1 executes (waits 5s)
                 → ACTION_2 executes (waits 5s)
                 → Total time: 10s ❌
```

### Desired Behavior (Parallel)
```
AI_NODE completes → ACTION_1, ACTION_2 both become ready
                 → Submit BOTH to thread pool
                 → ACTION_1 executes (5s) } Concurrent
                 → ACTION_2 executes (5s) }
                 → Total time: 5s ✅
```

## Root Cause Analysis

**File:** `apps/backend/workflow_engine_v2/core/engine.py`

**Problem Location:** Lines 356-1065 (main execution loop)

```python
# Current implementation: Sequential queue processing
while queue:
    task = queue.pop(0)  # ❌ Processes ONE node at a time
    current_node_id = task["node_id"]
    # ... execute node ...
    # Add ready successors to queue
    for successor_node in successors:
        if self._is_node_ready(graph, successor_node, pending_inputs):
            queue.append({"node_id": successor_node, "override": None})
```

The engine already has a `ThreadPoolExecutor` (line 193), but it's only used for:
- Individual node timeout handling (line 435-436)
- NOT for executing multiple ready nodes concurrently

## Implementation Plan

### Phase 1: Analyze Execution Graph Structure

**Goal:** Determine execution levels where parallel execution is safe

**Tasks:**
- [ ] Identify nodes at the same "depth level" (no dependencies between them)
- [ ] Group ready nodes by execution layer
- [ ] Ensure no data race conditions between parallel nodes

### Phase 2: Refactor Execution Loop

**Goal:** Replace sequential queue with level-by-level parallel execution

**Current Pattern:**
```python
while queue:
    task = queue.pop(0)
    execute_node(task)
    add_successors_to_queue()
```

**New Pattern:**
```python
while pending_nodes:
    # Collect all ready nodes at current level
    ready_nodes = get_all_ready_nodes()

    # Execute all ready nodes in parallel
    futures = {
        executor.submit(execute_node, node): node
        for node in ready_nodes
    }

    # Wait for all to complete
    done, pending = concurrent.futures.wait(futures)

    # Process results and propagate to successors
    for future in done:
        result = future.result()
        propagate_to_successors(result)
```

**Implementation Checklist:**
- [ ] Create `_get_ready_nodes_at_current_level()` helper method
- [ ] Modify main loop to use `concurrent.futures.wait()`
- [ ] Handle exceptions from parallel execution
- [ ] Preserve execution sequence ordering for logs
- [ ] Update `_persist_execution()` calls to handle concurrent writes

### Phase 3: Handle Edge Cases

**Critical Considerations:**

1. **Node Readiness Check**
   - [ ] Ensure `_is_node_ready()` is thread-safe
   - [ ] Check if `pending_inputs` dictionary needs locking

2. **State Management**
   - [ ] Verify `execution_context` is safe for concurrent access
   - [ ] Ensure `workflow_execution.node_executions` dict is thread-safe
   - [ ] Test concurrent updates to `execution_sequence`

3. **Fan-out Execution (LOOP nodes)**
   - [ ] Verify fan-out override mechanism works with parallel execution
   - [ ] Test iteration items executing in parallel

4. **Error Handling**
   - [ ] If one parallel node fails, decide: fail-fast or complete others?
   - [ ] Current behavior: fail-fast (line 555-556, `queue.clear()`)
   - [ ] Maintain fail-fast semantics in parallel execution

5. **HIL (Human-in-the-Loop) Pauses**
   - [ ] Ensure workflow pause during parallel execution is safe
   - [ ] Test: What happens if one parallel node triggers HIL pause?

### Phase 4: Performance Optimization

**Optimizations:**
- [ ] Limit max parallel nodes (avoid overwhelming thread pool)
- [ ] Use `max_workers` parameter from `__init__` (line 184)
- [ ] Add configuration for parallel execution degree
- [ ] Consider async/await instead of threads for I/O-bound operations

### Phase 5: Testing

**Test Scenarios:**

1. **Basic Parallel Execution**
   - [ ] AI node → 2 external actions (no dependencies)
   - [ ] Verify both execute concurrently
   - [ ] Check execution time is ~max(action1, action2), not sum

2. **Error Handling**
   - [ ] One parallel node fails → workflow should fail
   - [ ] Verify other parallel nodes are cancelled
   - [ ] Check error propagation

3. **Complex Workflows**
   - [ ] Diamond pattern: A → B,C → D (B and C parallel)
   - [ ] Fan-out + parallel: LOOP → [ACTION1, ACTION2] x N items
   - [ ] Mixed serial + parallel execution

4. **State Consistency**
   - [ ] Verify `node_executions` records are correct
   - [ ] Check `execution_sequence` maintains logical ordering
   - [ ] Test database persistence under concurrent writes

5. **HIL Integration**
   - [ ] Parallel nodes + HIL pause
   - [ ] Resume after HIL with parallel successors

## Code Locations

**Files to Modify:**

1. **Main Execution Loop**
   - `apps/backend/workflow_engine_v2/core/engine.py:356-1065`
   - Replace queue-based with level-based execution

2. **Node Readiness Check**
   - `apps/backend/workflow_engine_v2/core/engine.py:1936-1949`
   - Verify thread-safety of `_is_node_ready()`

3. **Successor Propagation**
   - `apps/backend/workflow_engine_v2/core/engine.py:956-1055`
   - Handle concurrent successor propagation

4. **Resume Methods**
   - `apps/backend/workflow_engine_v2/core/engine.py:1207-1411` (resume_with_user_input)
   - `apps/backend/workflow_engine_v2/core/engine.py:1690-1895` (resume_timer)
   - Apply parallel execution to resume flows

## Potential Issues & Solutions

### Issue 1: Race Conditions on `pending_inputs`

**Problem:** Multiple threads updating `pending_inputs[successor_node]` simultaneously

**Solution:** Use `threading.Lock()` per successor node or `queue.Queue` for thread-safe input collection

### Issue 2: Execution Sequence Ordering

**Problem:** Parallel nodes have no deterministic order in `execution_sequence`

**Solution:**
- Sort by start_time before appending to sequence
- Or accept non-deterministic ordering (document this behavior)

### Issue 3: Database Write Conflicts

**Problem:** Concurrent `_persist_execution()` calls may cause conflicts

**Solution:**
- Use database transaction locking
- Or serialize persistence (use a persistence queue)

### Issue 4: Log Interleaving

**Problem:** Parallel node logs may interleave in confusing ways

**Solution:**
- Add thread ID or execution layer to log messages
- Buffer logs per node, flush after completion

## Success Criteria

- [ ] Multiple independent successor nodes execute concurrently
- [ ] Total execution time reduced (verified with timing tests)
- [ ] All existing tests pass
- [ ] New parallel execution tests added and passing
- [ ] No race conditions or data corruption
- [ ] Error handling maintains fail-fast semantics
- [ ] HIL workflow patterns work correctly

## References

- **Existing ThreadPoolExecutor:** `engine.py:193` (`self._pool`)
- **concurrent.futures docs:** https://docs.python.org/3/library/concurrent.futures.html
- **Node Execution Context:** `workflow_engine_v2/core/state.py:ExecutionContext`
- **Workflow Graph:** `workflow_engine_v2/core/graph.py:WorkflowGraph`

## Related Issues

- Notion External Action completion error (Fixed: 2025-10-13)
- AI node sentinel action handling (Fixed: 2025-10-13)

## Notes

- Current engine already supports timeout-based parallel execution per node
- The ThreadPoolExecutor is initialized with `max_workers=8` by default
- Consider whether async/await would be better for I/O-bound external actions
- Python GIL may limit CPU-bound parallelism, but external actions are I/O-bound
