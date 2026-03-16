from __future__ import annotations

import asyncio

import pytest

from py3270.command_queue import CommandQueue
from tests.unit.helpers import MockSendCommand, make_response


async def _tick() -> None:
    """Two event loop iterations to let _process_loop settle after an enqueue."""
    await asyncio.sleep(0)
    await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# T4: Ordering and FIFO tests
# ---------------------------------------------------------------------------


async def test_single_command_resolves() -> None:
    """A single enqueued command resolves when handle_response is called."""
    mock = MockSendCommand()
    q = CommandQueue(mock)
    task = asyncio.create_task(q.enqueue("Query(Host)"))
    await _tick()  # two iterations: enqueue puts entry, then _process_loop picks it up
    assert mock.calls == ["Query(Host)"]
    q.handle_response(make_response("mvshost"))
    result = await task
    assert result.ok is True
    assert result.data == "mvshost"
    await q.stop()


async def test_fifo_ordering() -> None:
    """Three commands resolve in enqueue order."""
    responses = [make_response(f"r{i}") for i in range(3)]
    sent_order: list[str] = []

    async def controlled_send(cmd: str) -> None:
        sent_order.append(cmd)
        await asyncio.sleep(0)

    q = CommandQueue(controlled_send)
    tasks = [asyncio.create_task(q.enqueue(f"cmd{i}")) for i in range(3)]

    for resp in responses:
        await _tick()  # allow loop to pick up next
        q.handle_response(resp)

    results = await asyncio.gather(*tasks)
    assert [r.data for r in results] == ["r0", "r1", "r2"]
    assert sent_order == ["cmd0", "cmd1", "cmd2"]
    await q.stop()


async def test_only_one_in_flight() -> None:
    """Second command is not sent until first resolves."""
    gate = asyncio.Event()
    sent: list[str] = []

    async def gated_send(cmd: str) -> None:
        sent.append(cmd)
        if cmd == "cmd0":
            await gate.wait()  # hold cmd0 until released

    q = CommandQueue(gated_send)
    t0 = asyncio.create_task(q.enqueue("cmd0"))
    t1 = asyncio.create_task(q.enqueue("cmd1"))
    await _tick()
    assert sent == ["cmd0"]  # cmd1 NOT sent yet
    q.handle_response(make_response("r0"))
    gate.set()
    await _tick()
    q.handle_response(make_response("r1"))
    results = await asyncio.gather(t0, t1)
    assert results[0].data == "r0"
    assert results[1].data == "r1"
    assert sent == ["cmd0", "cmd1"]
    await q.stop()


async def test_stress_100_concurrent() -> None:
    """100 concurrent callers all resolve in FIFO order."""
    received: list[int] = []

    async def tracking_send(cmd: str) -> None:
        received.append(int(cmd))
        await asyncio.sleep(0)

    q = CommandQueue(tracking_send)
    tasks = [asyncio.create_task(q.enqueue(str(i))) for i in range(100)]
    for i in range(100):
        await _tick()
        q.handle_response(make_response(str(i)))
    results = await asyncio.gather(*tasks)
    assert [r.data for r in results] == [str(i) for i in range(100)]
    await q.stop()


# ---------------------------------------------------------------------------
# T5: Timeout tests
# ---------------------------------------------------------------------------


async def test_command_timeout_raises() -> None:
    """Command times out and raises TimeoutError."""
    q = CommandQueue(MockSendCommand())  # never responds
    with pytest.raises(TimeoutError, match="Command timeout"):
        async with asyncio.timeout(0.05):
            await q.enqueue("SlowCmd")
    await q.stop()


async def test_timeout_does_not_block_next() -> None:
    """After timeout, the next command processes normally."""
    fast_mock = MockSendCommand()
    q = CommandQueue(fast_mock)

    # First command times out
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            await q.enqueue("slow")

    # Second command succeeds
    task = asyncio.create_task(q.enqueue("fast"))
    await _tick()
    q.handle_response(make_response("ok"))
    result = await task
    assert result.ok is True
    await q.stop()


async def test_late_response_after_timeout_is_discarded() -> None:
    """A response arriving after timeout does not corrupt the next command."""
    q = CommandQueue(MockSendCommand())

    # First command times out
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            await q.enqueue("cmd1")

    # Simulate late response for cmd1 — should be silently ignored
    q.handle_response(make_response("too_late"))

    # Next command should work fine
    task = asyncio.create_task(q.enqueue("cmd2"))
    await _tick()
    q.handle_response(make_response("cmd2_result"))
    result = await task
    assert result.data == "cmd2_result"
    await q.stop()


# ---------------------------------------------------------------------------
# T6: Stop / drain tests
# ---------------------------------------------------------------------------


async def test_stop_rejects_in_flight() -> None:
    """stop() rejects the currently in-flight command."""
    q = CommandQueue(MockSendCommand())
    task = asyncio.create_task(q.enqueue("active_cmd"))
    await asyncio.sleep(0)
    await q.stop()
    with pytest.raises((RuntimeError, asyncio.CancelledError)):
        await task


async def test_stop_rejects_pending() -> None:
    """stop() rejects all queued-but-not-yet-sent commands."""
    gate = asyncio.Event()

    async def blocking_send(cmd: str) -> None:
        await gate.wait()

    q = CommandQueue(blocking_send)
    t_active = asyncio.create_task(q.enqueue("active"))
    t_pending = asyncio.create_task(q.enqueue("pending"))
    await asyncio.sleep(0)

    await q.stop()
    gate.set()  # release blocked send

    for task in [t_active, t_pending]:
        with pytest.raises((RuntimeError, asyncio.CancelledError)):
            await task


async def test_enqueue_after_stop_raises() -> None:
    """Calling enqueue() on a stopped queue raises RuntimeError immediately."""
    q = CommandQueue(MockSendCommand())
    await q.stop()
    with pytest.raises(RuntimeError, match="stopped"):
        await q.enqueue("any")


async def test_stop_is_idempotent() -> None:
    """Calling stop() multiple times does not raise."""
    q = CommandQueue(MockSendCommand())
    await q.stop()
    await q.stop()  # should be a no-op


async def test_send_failure_advances_queue() -> None:
    """If send_command raises, current command rejects but next succeeds."""
    call_count = 0

    async def flaky_send(cmd: str) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IOError("pipe broken")
        await asyncio.sleep(0)

    q = CommandQueue(flaky_send)
    t_fail = asyncio.create_task(q.enqueue("cmd_fail"))
    t_ok = asyncio.create_task(q.enqueue("cmd_ok"))

    with pytest.raises(IOError):
        await t_fail

    await asyncio.sleep(0)
    q.handle_response(make_response("ok"))
    result = await t_ok
    assert result.ok is True
    await q.stop()


# ---------------------------------------------------------------------------
# T7: handle_error, spurious responses, reentrancy, result isolation
# ---------------------------------------------------------------------------


async def test_handle_error_rejects_in_flight() -> None:
    """handle_error() rejects the in-flight future with the given exception."""
    q = CommandQueue(MockSendCommand())
    task = asyncio.create_task(q.enqueue("cmd"))
    await _tick()
    q.handle_error(ValueError("s3270 error"))
    with pytest.raises(ValueError, match="s3270 error"):
        await task
    await q.stop()


async def test_handle_error_advances_queue() -> None:
    """After handle_error(), the next queued command is dispatched normally."""
    mock = MockSendCommand()
    q = CommandQueue(mock)
    t_fail = asyncio.create_task(q.enqueue("bad"))
    t_ok = asyncio.create_task(q.enqueue("good"))
    await _tick()
    q.handle_error(IOError("boom"))
    with pytest.raises(IOError):
        await t_fail
    await _tick()
    q.handle_response(make_response("ok"))
    result = await t_ok
    assert result.data == "ok"
    await q.stop()


async def test_handle_error_on_idle_queue_is_noop() -> None:
    """handle_error() when nothing is in-flight does not raise."""
    q = CommandQueue(MockSendCommand())
    q.handle_error(RuntimeError("spurious"))  # must not raise or corrupt state
    task = asyncio.create_task(q.enqueue("cmd"))
    await _tick()
    q.handle_response(make_response("fine"))
    result = await task
    assert result.data == "fine"
    await q.stop()


async def test_spurious_handle_response_on_idle_queue_is_noop() -> None:
    """handle_response() when nothing is in-flight does not raise or corrupt state."""
    q = CommandQueue(MockSendCommand())
    q.handle_response(make_response("ghost"))  # must not raise or corrupt state
    task = asyncio.create_task(q.enqueue("cmd"))
    await _tick()
    q.handle_response(make_response("real"))
    result = await task
    assert result.data == "real"
    await q.stop()


async def test_consecutive_timeouts_then_success() -> None:
    """Two successive timeouts followed by a normal command all behave correctly."""
    q = CommandQueue(MockSendCommand())  # never responds on its own

    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            await q.enqueue("slow1")

    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.05):
            await q.enqueue("slow2")

    task = asyncio.create_task(q.enqueue("fast"))
    await _tick()
    q.handle_response(make_response("done"))
    result = await task
    assert result.data == "done"
    await q.stop()


async def test_sequential_await_chain_reentrancy() -> None:
    """Awaiting enqueue() twice back-to-back from the same coroutine works correctly."""
    sent: list[str] = []

    async def recording_send(cmd: str) -> None:
        sent.append(cmd)
        await asyncio.sleep(0)

    q = CommandQueue(recording_send)

    task1 = asyncio.create_task(q.enqueue("cmd1"))
    await _tick()
    q.handle_response(make_response("r1"))
    r1 = await task1

    task2 = asyncio.create_task(q.enqueue("cmd2"))
    await _tick()
    q.handle_response(make_response("r2"))
    r2 = await task2

    assert r1.data == "r1"
    assert r2.data == "r2"
    assert sent == ["cmd1", "cmd2"]
    await q.stop()


async def test_per_task_result_isolation() -> None:
    """Each concurrent enqueue() caller receives exactly its own response, not another's."""
    sent_order: list[str] = []

    async def recording_send(cmd: str) -> None:
        sent_order.append(cmd)
        await asyncio.sleep(0)

    q = CommandQueue(recording_send)
    task_a = asyncio.create_task(q.enqueue("A"))
    task_b = asyncio.create_task(q.enqueue("B"))

    # Only A is in-flight; B is queued, neither resolved yet
    await _tick()
    assert sent_order == ["A"]
    assert not task_a.done()
    assert not task_b.done()

    # Resolve A; the loop then dispatches B
    q.handle_response(make_response("result_A"))
    await _tick()
    assert task_a.done()
    assert (await task_a).data == "result_A"
    assert sent_order == ["A", "B"]
    assert not task_b.done()

    # Resolve B; task_b gets its own result, not A's
    q.handle_response(make_response("result_B"))
    result_b = await task_b
    assert result_b.data == "result_B"

    await q.stop()
