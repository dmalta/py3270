# Plan: py3270 Python s3270 Wrapper

**TL;DR**: Implement a Python package that wraps the `s3270 -script` subprocess protocol with an async-first `AsyncTerminal` class (asyncio + typed dataclasses) and a thin `SyncTerminal` wrapper backed by a background event loop thread. The codebase lives in a `src/` layout, uses Python 3.13+ features throughout, and is tested with pytest + pytest-asyncio.

--------------------------------------------------------------------------------

## Phase 1 -- Foundation _(all parallel)_

1. **Project scaffold** -- `pyproject.toml` (hatchling/flit backend), `src/py3270/__init__.py` (public re-exports), `tests/conftest.py` (shared mock-subprocess fixtures)

2. **`src/py3270/_types.py`** -- All enums as `StrEnum` (Pythonic snake_case values): `TerminalMode`, `TerminalSetting`, `StatusFlag`, `KeyboardState`, `ScreenFormatting`, `FieldProtection`, `ConnectionState`, `EmulatorMode`. Frozen `@dataclass(slots=True, frozen=True)` for `TerminalResponse`, `ScreenPosition`, `ScreenSize`, `StatusInfo`, `FieldDefinition`. Mutable `TerminalOptions` with sane defaults + **new fields**: `max_retries: int = 0`, `retry_delay_ms: int = 500`. `FieldDefinitionRecord = dict[str, str | int | float | None]`.

3. **`src/py3270/_parser.py`** -- `parse_response(lines)` mapping the last line to `ok/error`, penultimate to status, rest to data. `parse_status(line)` parsing all 12 fields, extracting `C(host)` from field 4, returning `StatusInfo | None`.

4. **`src/py3270/_escape.py`** -- `validate_escape_sequences(s: str) -> None`, a direct Python port of Appendix B TypeScript logic using `re`. Raises `ValueError` on any invalid escape.

--------------------------------------------------------------------------------

## Phase 2 -- Async Core _(step 5 before 6)_

1. **`src/py3270/_queue.py`** -- `CommandQueue`

  - `_TerminalCommand` dataclass: `command`, `asyncio.Future[TerminalResponse]`, `timeout: float`
  - Background `_worker_task` (started lazily): dequeue → call `send_fn(cmd)` → `asyncio.wait_for(asyncio.shield(future), timeout)` → on `TimeoutError` set exception on the future
  - `handle_response(resp)` / `handle_error(err)` -- called by stdout reader, resolves/rejects `_current` future
  - `enqueue(cmd, timeout) -> TerminalResponse` -- creates Future, puts on queue, `await`s Future (the caller suspends here)
  - `stop()` -- rejects active command with `"Queue stopped"`, drains queue with `"Process terminated"`, cancels worker task

2. **`src/py3270/_terminal.py`** -- `AsyncTerminal`

  - `asyncio.create_subprocess_exec` with `PIPE` on stdin/stdout/stderr (cross-platform)
  - `_reader_task` reads stdout chunks → `_handle_output(chunk)` → accumulates buffer → detects `ok`/`error…` terminal lines → calls `_process_response(lines)`
  - `_process_response` updates `_screen_buffer`, `_last_status_line`; delegates to `CommandQueue.handle_response / handle_error`
  - `command()` implements retry loop (up to `max_retries`) on `asyncio.TimeoutError` with exponential backoff
  - All public methods as `async def`: lifecycle, connect/disconnect, wait helpers, screen ops, text/input helpers, query/status, read/write
  - `__aenter__` returns `self` (no auto-start); `__aexit__` calls `stop()`
  - stderr routed to `logging.getLogger("py3270.stderr")` at DEBUG level -- no `verbose` flag

--------------------------------------------------------------------------------

## Phase 3 -- Sync Wrapper _(depends on Phase 2)_

1. **`src/py3270/_sync.py`** -- `SyncTerminal`

  - Constructor spawns a daemon `threading.Thread` running `asyncio.new_event_loop().run_forever()`
  - `_run(coro)` helper: `asyncio.run_coroutine_threadsafe(coro, self._loop).result()`
  - Every `AsyncTerminal` public method proxied synchronously (one `_run(...)` call each)
  - `__enter__` / `__exit__`: exit calls `stop()` → `loop.call_soon_threadsafe(loop.stop)` → `thread.join()`

--------------------------------------------------------------------------------

## Phase 4 -- Tests _(parallel, depend on Phase 1–3)_

1. **`tests/test_parser.py`** -- parse_response variations (zero/many data lines, error terminal line, chunked accumulation); parse_status (12 fields, <12 fields, `C(host)`, `-` time)

2. **`tests/test_escape.py`** -- every valid sequence passes; invalid sequences raise `ValueError`; mixed strings

3. **`tests/test_queue.py`** -- FIFO ordering; timeout fires and rejects; `stop()` drains active + pending; late `handle_response` after stop is no-op

4. **`tests/test_terminal.py`** -- mock subprocess via `pytest-mock` / `AsyncMock`; lifecycle idempotency; connect string variants (mode, LUName, lowercase); disconnect connected vs. not-connected; `command()` before `start()` raises; `wait_for` row+col validation; `pf`/`pa` range checks; `read` 1-based math; `write` length clamp + space-padding; status getters

5. **`tests/test_sync.py`** -- smoke test context manager; method proxying; stop/cleanup

--------------------------------------------------------------------------------

## Phase 5 -- Packaging _(parallel with tests)_

1. **`pyproject.toml`** -- `requires-python = ">=3.13"`, stdlib-only runtime deps, `[project.optional-dependencies] dev = ["pytest", "pytest-asyncio", "pytest-mock"]`

2. **`README.md`** -- async + sync usage examples with context manager, logging config note

--------------------------------------------------------------------------------

## Relevant files (all new)

Path                      | Purpose
------------------------- | --------------------------
`pyproject.toml`          | Build/package metadata
`src/py3270/__init__.py`  | Public re-exports
`src/py3270/_types.py`    | Enums + dataclasses
`src/py3270/_parser.py`   | Response + status parsing
`src/py3270/_escape.py`   | Escape sequence validation
`src/py3270/_queue.py`    | Async command queue
`src/py3270/_terminal.py` | AsyncTerminal
`src/py3270/_sync.py`     | SyncTerminal
`tests/conftest.py`       | Shared fixtures
`tests/test_*.py`         | Test files per module

--------------------------------------------------------------------------------

## Key design improvements over spec

- **`verbose` removed** -- use `logging.basicConfig(level=logging.DEBUG)` or `logging.getLogger("py3270")`; internally logs at DEBUG/WARNING
- **Retry on timeout** -- `TerminalOptions.max_retries` + `retry_delay_ms`; retries only `asyncio.TimeoutError`, not logic errors or escape validation failures
- **Frozen dataclasses** -- `TerminalResponse`, `StatusInfo`, `ScreenPosition` etc. are immutable value objects
- **`StrEnum`** -- all enums are string-comparable, JSON-serialisable, and readable in logs

## Scope exclusions

- No CLI entrypoint
- No streaming screen-update API
- No TLS configuration (handled natively by s3270)

--------------------------------------------------------------------------------

## Further Considerations

1. **Package name clash**: `py3270` already exists on PyPI (a different library). Recommend using `s3270-wrapper` or `py3270x` as the distribution name while keeping `py3270` as the import name. Do you have a preference?

2. **`wait_for` polling interval**: spec says 100ms. Should this be configurable in `TerminalOptions`, or is 100ms hardcoded fine?

3. **`SyncTerminal` method return types**: some async methods return `Terminal` (for chaining, e.g. `enter().pf(1)`). In the sync layer, should method chaining be preserved (return `SyncTerminal`), or is a flat call style preferred?
