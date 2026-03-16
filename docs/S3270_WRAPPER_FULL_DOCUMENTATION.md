# s3270 Terminal Wrapper: Full Technical Documentation

## Purpose

This document describes the current TypeScript design in a language-neutral way so a new implementation (for example in Python) can be built with equivalent behavior.

It covers:

- Process and protocol model
- Command/response parsing
- Command queue behavior and why it exists
- Public API behavior method-by-method
- State model and status parsing
- Error handling and edge cases
- Implementation checklist for a port

## High-Level Architecture

The library has two core runtime components:

1. `Terminal`
2. User-facing API
3. Starts/stops the `s3270` subprocess
4. Sends commands and parses responses
5. Maintains screen buffer and last status line
6. Exposes high-level methods (`connect`, `read`, `write`, `waitFor`, `pf`, etc.)
7. `CommandQueue`
8. Internal serialization layer
9. Ensures one in-flight command at a time
10. Associates each outgoing command with exactly one response/rejection
11. Handles per-command timeout and cleanup when process exits/stops

## Why the Command Queue Is Needed

The `s3270 -script` protocol is command/response based and practically single-flight. If multiple commands are written concurrently:

- output can interleave,
- the wrong caller may receive the wrong response,
- timeouts and cleanup become nondeterministic.

The queue guarantees:

- strict ordering,
- exactly one active command,
- deterministic timeout handling,
- predictable shutdown behavior (reject pending work on stop/exit).

## s3270 Script Protocol Model

## Process start

- Spawn executable with arguments: `['-script', ...args]`
- Communicate via stdin/stdout.

## Response framing

Output is buffered until a terminal line appears:

- `ok`
- or `error...` (line starts with `error`)

A complete response consists of:

1. zero or more data lines
2. status line (penultimate line)
3. terminal line (`ok` or `error...`)

The wrapper maps this into:

- `ok: boolean`
- `data: string` (data lines joined by `\n`)
- `status: string` (status line)
- `raw: string[]` (all lines in the response)

## Core Types

## TerminalOptions

- `executable?: string` default `s3270`
- `args?: string[]` default `[]`
- `verbose?: boolean` default `false`
- `timeout?: number` default `30000` ms

## TerminalResponse

- `ok: boolean`
- `data: string`
- `status: string`
- `raw: string[]`

## Enums used by API

- `TerminalMode`: `P | S | N | L | B`
- `TerminalSetting`: `ConnectionState | Host | Model | LuName | Encoding | CodePage | Aid | BindPluName`
- `StatusFlag`: `Formatted | KeyboardLock | Printer | Secure | Tn3270e`
- `KeyboardState`: `U | L | E`
- `ScreenFormatting`: `F | U`
- `FieldProtection`: `P | U`
- `ConnectionState`: `C | N`
- `EmulatorMode`: `I | L | C | P | N`

## Data interfaces

- `ScreenPosition`: `{ row, col }`
- `ScreenSize`: `{ rows, cols }`
- `StatusInfo`:

  - `keyboardState`
  - `screenFormatting`
  - `fieldProtection`
  - `connectionState`
  - `connectionHost?`
  - `emulatorMode`
  - `modelNumber`
  - `rows`
  - `columns`
  - `cursorRow`
  - `cursorColumn`
  - `windowId`
  - `commandExecutionTime` (`number | null`)

- `FieldDefinition`:

  - `row`, `col`, `length`
  - `type?: 'string' | 'number'`
  - `trim?: boolean`

- `FieldDefinitionRecord`: map of `string -> string | number | null`

## Terminal Internal State

- `process: ChildProcess | null`
- `buffer: string` (stdout accumulator)
- `commandQueue: CommandQueue`
- `options: Required<TerminalOptions>`
- `connected: boolean`
- `screenBuffer: string[]`
- `lastStatusLine: string`
- `defaultTimeout: number` (10000 ms)

## Terminal Public API

## Lifecycle

### `start(): Promise<void>`

Behavior:

- Idempotent; if process exists, return immediately.
- Spawn `s3270` in script mode.
- Attach stdout handler to parse responses.
- Attach stderr handler for verbose logging.
- On process `error`: emit error and reject startup promise.
- On process `exit`: reset process/connection state and stop command queue.

### `stop(): Promise<void>`

Behavior:

- If no process, return immediately.
- Kill process and wait for exit event.
- Reset process/connection state.
- Stop queue (reject current/pending commands).

## Command execution

### `command(cmd: string, timeout?: number): Promise<TerminalResponse>`

Behavior:

- Throws if process is not started.
- Enqueues command into `CommandQueue`.
- Resolves/rejects when queue receives response/error/timeout.

### `sendCommandToProcess(command: string): void` (internal)

Behavior:

- Writes command + newline to stdin.
- Throws if process/stdin unavailable.

## Connectivity

### `connect(hostname: string, port: number, mode?: TerminalMode, LUName?: string)`

Behavior:

- Auto-calls `start()`.
- Build connection string:

  1. base: `hostname:port` (lowercased)
  2. prepend `LUName@` if provided
  3. prepend `mode:` if provided

- Executes `connect <connectionString>`.
- Sets `connected` based on `response.ok`.

### `disconnect(): Promise<TerminalResponse>`

Behavior:

- If connected: execute `disconnect`, mark disconnected.
- If not connected: return synthetic successful response with status `No active connection`.
- Always call `stop()` afterward.

## Wait helpers

### `wait(ms: number): Promise<void>`

- Sleeps for clamped timeout.

### `waitOutput(timeout?: number): Promise<TerminalResponse>`

- Executes `Wait(<t>, Output)`.

### `waitUnlock(timeout?: number): Promise<TerminalResponse>`

- Executes `Wait(<t>, Unlock)`.

### `waitReady(timeout?: number): Promise<void>`

- Calls `waitOutput` then `waitUnlock`.

### `waitFor(text: string, row?: number, col?: number, timeout = 30000): Promise<boolean>`

Behavior:

- Validates `(row,col)` are both present or both absent.
- Poll until timeout:

  - positional mode: `read(row,col,text.length)` equals target
  - global mode: `screen()` contains target

- Poll interval 100 ms.
- Returns `true` when found, otherwise `false`.

## Screen operations

### `screen(refresh = false): Promise<string>`

- Refresh if requested or local buffer empty.
- Return screen lines joined by newline.

### `refresh(): Promise<boolean>`

- Executes `ascii`.
- Splits `response.data` by newline.
- If a line starts with `data:`, strip prefix.
- Stores in `screenBuffer`.
- Returns whether buffer has content.

### `getScreenBuffer(): string[]`

- Returns a copy of current screen buffer.

## Text/input helpers

### `string(str: string): Promise<TerminalResponse>`

- Validates allowed s3270 escape sequences.
- Escapes literal double quotes.
- Sends `string(<escaped>)`.
- Reference implementation: see Appendix B (`validateStringEscapeSequences` in TypeScript).

### `move(row: number, col: number): Promise<TerminalResponse>`

- Sends `movecursor(row,col)`.

### `enter(): Promise<Terminal>`

- Sends `enter`, waits ready, returns `this`.

### `tab(count = 1): Promise<Terminal>`

- Sends `tab` repeatedly `count` times.
- Waits ready and returns `this`.

### `pf(n: number): Promise<Terminal>`

- Valid range `1..24` else throw.
- Sends `pf(n)`, waits ready, returns `this`.

### `pa(n: number): Promise<Terminal>`

- Valid range `1..3` else throw.
- Sends `pa(n)`, waits ready, returns `this`.

### `clear(): Promise<Terminal>`

- Sends `clear`, waits ready, returns `this`.

## Query and status

### `query(what: string): Promise<TerminalResponse>`

- Sends `query(<what>)`.

### `get(setting: TerminalSetting): Promise<string>`

- `query(setting)` and return trimmed text.

### `is(flag: StatusFlag): Promise<boolean>`

- `query(flag)` and parse boolean-ish value.
- Returns true for `true`, `1`.
- Special case: for `KeyboardLock`, anything not exactly `false` is treated true.

### `cursor(): Promise<ScreenPosition>`

- `query('Cursor')`, parse `row,col`.

### `screenSize(): Promise<ScreenSize>`

- `query('ScreenSize')`, parse `rows,cols`.

### `currentField(): Promise<{ start: ScreenPosition; length: number } | null>`

- `query('CurrentField')`.
- Parse `row,col,length`.
- Return null on parse/query failure.

### `available(): Promise<string[]>`

- `query('query')`, split lines, remove empty.

## Read/write helpers

### `write(text: string, row: number, col: number, length?: number): Promise<TerminalResponse>`

- Moves cursor first.
- If length is set and > 0:

  - clamp length against current screen columns when available,
  - truncate or right-pad with spaces.

- Sends via `string(text)`.

### `read(row: number, col: number, length: number, trim = true): Promise<string>`

- Reads from local `screenBuffer`.
- If row is out of bounds, return empty string.
- Extract substring using 1-based coordinates.
- If `trim` true, return right-trimmed value.

### `readMany(fields: Record<string, FieldDefinition>): Promise<FieldDefinitionRecord>`

- Iterates each field definition.
- Defaults: `type='string'`, `trim=true`.
- Reads each region via `read`.
- Number type: parse float, invalid => null.

### `check(row: number, col: number, text: string): Promise<boolean>`

- Reads exact text span with `trim=false`.
- Compares strict equality.

## Status-derived getters

Computed from parsed status line:

- `status`
- `isReady`
- `isScreenFormatted`
- `host`
- `emulatorMode`
- `modelNumber`
- `statusRows`
- `statusColumns`
- `statusCursorRow`
- `statusCursorColumn`
- `windowId`
- `commandExecutionTime`

## Status Line Parsing

Expected status line has at least 12 fields:

1. Keyboard state
2. Screen formatting
3. Field protection
4. Connection state (`C(host)` or `N`)
5. Emulator mode
6. Model number
7. Rows
8. Columns
9. Cursor row
10. Cursor column
11. Window ID
12. Command execution time (`-` means null)

Parsing behavior:

- If no status line or fewer than 12 fields => return null.
- If field 4 is `C(...)`, extract `connectionHost`.
- Parse numeric fields with `parseInt/parseFloat` semantics.

## Output Processing Internals (Terminal)

## `handleOutput(data: string)`

- Append chunk to `buffer`.
- Split by newline.
- Find first line that terminates a response (`ok` or `error...`).
- Emit that complete response to `processResponse`.
- Keep remainder in buffer for next chunk.
- Repeat until no full response remains.

## `processResponse(lines: string[])`

- last line determines success/error.
- penultimate line is status.
- all previous lines are data.
- update `lastStatusLine`.
- on success -> `commandQueue.handleResponse(response)`.
- on error -> `commandQueue.handleError(Error(...))`.

## Escape Sequence Validation (`string`)

Allowed sequences:

- `\b`
- `\e` + 2-4 hex digits
- `\f`
- `\n`
- `\pa1` .. `\pa3`
- `\pf1` .. `\pf24`
- `\r`
- `\t`
- `\T`
- `\u` + 2-5 hex digits
- `\x` + 2-5 hex digits
- `\\`
- `\"`

Validation strategy:

- scan for backslash escapes,
- distinguish single-char and multichar escapes,
- reject invalid patterns with explicit error.
- For exact TypeScript behavior and regex usage, see Appendix B.

## CommandQueue Internal Design

## State

- `queue: TerminalCommand[]`
- `currentCommand: TerminalCommand | null`
- `processing: boolean`
- `stopped: boolean`

`TerminalCommand` shape:

- `command`
- `resolve(response)`
- `reject(error)`
- `timeout?`
- `timeoutId?`

## Behavior

### `enqueue(...)`

- Reject immediately if queue is stopped.
- Push command and trigger start.

### `start()`

- No-op if already processing or stopped.
- Otherwise process next command.

### `processNext()`

- Guard against concurrent entry.
- Pop one command to `currentCommand`.
- Start timeout timer.
- Send command through injected `sendCommand` callback.
- On send failure: clear timeout, reject, continue next.

### Timeout path

- If timer fires and command is still current:

  - clear current processing state,
  - reject with `Command timeout: <command>`,
  - continue next command.

### `handleResponse(response)`

- If no active command: log and ignore.
- Else clear timeout, resolve current, clear state, continue next.

### `handleError(error)`

- If no active command: log and ignore.
- Else clear timeout, reject current, clear state, continue next.

### `stop()`

- Mark stopped.
- Reject active command with `Queue stopped`.
- Reject all queued commands via `clear()`.

### `clear()`

- Reject all queued commands with `Process terminated`.

## Error Handling Contracts

- Calling `command()` before `start()` throws explicit error.
- Invalid PF/PA range throws explicit error.
- Invalid escape sequences throw explicit error.
- Process exit resets connection state and drains queue.
- Queue robustly handles unexpected response/error without active command (logs only).

## Behavioral Notes and Porting Considerations

- `connect()` lowercases the host:port string before optional mode/LU decoration.
- Screen coordinates for high-level read/write APIs are treated as 1-based.
- `screenBuffer` is not always auto-refreshed; callers often invoke `refresh()` explicitly before reads.
- `waitFor` polls local wrappers, not raw protocol events.
- `waitReady` uses two explicit `Wait(...)` commands.

## Known Interface Footguns to Decide in a Port

There are call-site inconsistencies in tests around `write()` and `waitFor()` argument ordering. For a clean new implementation, define and enforce one canonical signature, document it clearly, and keep tests consistent.

Recommended canonical signatures:

- `write(text, row, col, length=None)`
- `wait_for(text, row=None, col=None, timeout=30000)`

## Suggested Python Mapping

## Class/module structure

- `types.py`: enums/dataclasses
- `command_queue.py`: queue logic (or equivalent serialized executor)
- `terminal.py`: wrapper class
- `__init__.py`: export public API

## Concurrency model options

- Synchronous with `threading.Lock` + blocking reads
- Async with `asyncio` subprocess + `asyncio.Lock`

Either way, preserve these invariants:

- one in-flight command,
- per-command timeout,
- clean rejection on stop/exit,
- correct response framing.

## Test Matrix for Equivalent Behavior

- Process lifecycle: start/stop idempotency
- Connect/disconnect variants (mode, LU)
- Raw command success/error/timeout
- Response parser with chunked stdout
- Queue ordering and timeout behavior
- Screen refresh/read/check/write
- Cursor/key operations (`enter/tab/pf/pa/clear`)
- Query/get/is/cursor/screenSize/currentField/available
- Status parsing and getters
- Wait helpers and `waitFor` validation
- Escape sequence acceptance/rejection

## Copilot Prompt Block (Implementation-Ready)

Use the block below directly with Copilot to generate a full port:

```text
Implement a Python s3270 wrapper with full parity to this specification:

- Build Terminal + CommandQueue architecture.
- Use s3270 -script process protocol.
- Parse responses terminated by 'ok' or 'error...'.
- Expose lifecycle, connect/disconnect, command execution, wait helpers, screen ops, query/status, read/write/read_many/check, key methods, and status getters.
- Enforce escape sequence validation exactly as documented.
- Use Appendix B as the canonical TypeScript source reference for validation behavior.
- Serialize commands (one in-flight), with timeout, queue stop, and process-exit cleanup behavior.
- Include enums/dataclasses equivalent to TerminalOptions, TerminalResponse, TerminalMode, TerminalSetting, StatusFlag, KeyboardState, ScreenFormatting, FieldProtection, ConnectionState, EmulatorMode, StatusInfo, ScreenPosition, ScreenSize, FieldDefinition, FieldDefinitionRecord.
- Add tests covering parser, queue, status parsing, and all public methods.

Important behavioral constraints:
- command() before start() must fail.
- connect() auto-starts process.
- disconnect() returns synthetic success if not connected and still stops process.
- wait timeout clamped to [0, 300000].
- wait_for requires row+col together or neither.
- read uses 1-based coordinates and local screen buffer.
- process exit must reset connection and reject pending queue work.
```

## Appendix A: Enum Codes and Meanings

This appendix lists every enum and the meaning of each code/value.

### TerminalMode

- `P` (`Passthru`): Connection in passthru mode.
- `S` (`SuppressExtendedDS`): Suppress extended data stream.
- `N` (`NoTN3270E`): Disable TN3270E negotiation.
- `L` (`SSLTunnel`): Use SSL tunnel mode.
- `B` (`BindStrict`): Strict BIND behavior.

### TerminalSetting

- `ConnectionState`: Current connection state string reported by emulator.
- `Host`: Connected host/endpoint string.
- `Model`: Terminal model string (for example IBM-3279-4-E).
- `LuName`: Logical Unit name.
- `Encoding`: Current character encoding.
- `CodePage`: Active code page.
- `Aid`: Last Attention Identifier information.
- `BindPluName`: PLU name from BIND state, when available.

### StatusFlag

- `Formatted`: Whether screen is formatted.
- `KeyboardLock`: Whether keyboard is locked.
- `Printer`: Printer session state flag.
- `Secure`: Secure connection flag.
- `Tn3270e`: TN3270E mode flag.

### KeyboardState (Status Field 1)

- `U` (`Unlocked`): Keyboard is unlocked.
- `L` (`Locked`): Keyboard is locked waiting for host response or due to not connected state.
- `E` (`Error`): Keyboard is locked due to operator/input error (for example protected field or overflow).

### ScreenFormatting (Status Field 2)

- `F` (`Formatted`): Screen is formatted (3270 formatted fields present).
- `U` (`Unformatted`): Screen is unformatted or in NVT mode.

### FieldProtection (Status Field 3)

- `P` (`Protected`): Cursor is currently in a protected field.
- `U` (`Unprotected`): Cursor is in an unprotected field or screen is unformatted.

### ConnectionState (Status Field 4)

- `C` (`Connected`): Connected to a host. In status line this appears as `C(hostname)`.
- `N` (`NotConnected`): Not connected.

### EmulatorMode (Status Field 5)

- `I` (`Mode3270`): 3270 mode.
- `L` (`NVTLine`): NVT line mode.
- `C` (`NVTCharacter`): NVT character mode.
- `P` (`Unnegotiated`): Unnegotiated mode (no active BIND).
- `N` (`NotConnected`): Not connected.

### Status Line Field Map (Reference)

The parser expects these 12 fields in order:

1. Keyboard state (`U/L/E`)
2. Screen formatting (`F/U`)
3. Field protection (`P/U`)
4. Connection state (`C(host)` or `N`)
5. Emulator mode (`I/L/C/P/N`)
6. Model number (integer)
7. Rows (integer)
8. Columns (integer)
9. Cursor row (integer)
10. Cursor column (integer)
11. Window ID (string)
12. Command execution time (float seconds or `-` for null)

## Appendix B: TypeScript Reference for Escape Validation

This appendix captures the current TypeScript source implementation of `validateStringEscapeSequences` and should be treated as canonical behavior when reproducing validation logic in another language.

```typescript
private validateStringEscapeSequences(str: string): void {
  // Regex for valid escape sequences
  const validEscapes = [
    /\\b/,                          // \b - Left arrow
    /\\e[0-9a-fA-F]{2,4}/,         // \exxxx - EBCDIC character (2-4 hex digits)
    /\\f/,                          // \f - Clear
    /\\n/,                          // \n - Enter
    /\\pa[1-3](?![0-9])/,                    // \pan - PA key (n=1-3) with negative lookahead
    /\\pf(?:2[0-4]|1[0-9]|[1-9])(?![0-9])/,  // \pfnn - PF key (nn=1-24) with negative lookahead
    /\\r/,                          // \r - Newline
    /\\t/,                          // \t - Tab
    /\\T/,                          // \T - BackTab
    /\\u[0-9a-fA-F]{2,5}/,         // \uxxxx - Unicode character (2-5 hex digits)
    /\\x[0-9a-fA-F]{2,5}/,         // \xxxxx - Unicode character (2-5 hex digits)
    /\\\\/,                         // \\ - Literal backslash
    /\\"/                           // \" - Literal quote
  ];

  // Find all escape sequences in the string
  const escapePattern = /\\./g;
  let match;

  while ((match = escapePattern.exec(str)) !== null) {
    const escapeSeq = match[0];

    // Check if it's a multi-character escape sequence
    if (escapeSeq === '\\e' || escapeSeq === '\\u' || escapeSeq === '\\x' ||
      escapeSeq === '\\p') {
      // Need to check the full sequence
      const startPos = match.index;
      const remainingStr = str.slice(startPos);

      let validSequence = false;
      for (const pattern of validEscapes) {
        const fullMatch = remainingStr.match(pattern);
        if (fullMatch && fullMatch.index === 0) {
          // Advance the regex position to skip the full sequence
          escapePattern.lastIndex = startPos + fullMatch[0].length - 1;
          validSequence = true;
          break;
        }
      }

      if (!validSequence) {
        throw new Error(`Invalid escape sequence at position ${startPos}: ${remainingStr.slice(0, 6)}...`);
      }
    } else {
      // Single character escape sequence
      let validSequence = false;
      for (const pattern of validEscapes) {
        if (pattern.test(escapeSeq)) {
          validSequence = true;
          break;
        }
      }

      if (!validSequence) {
        throw new Error(`Invalid escape sequence: ${escapeSeq}`);
      }
    }
  }
}
```

## End State Definition

A compliant reimplementation is complete when:

- Public behavior matches this document,
- command serialization and parsing invariants hold under concurrency/chunking,
- tests validate normal, failure, and cleanup paths.
