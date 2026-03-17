# Advanced Usage

This chapter covers configuration, orchestration, and diagnostic features for experienced users.

## Terminal Options

When creating a Terminal, you can customize behavior using `TerminalOptions`:

```python
from py3270 import Terminal, TerminalOptions

options = TerminalOptions(
    executable="/usr/local/bin/s3270",
    args=["-xrm", "s3270.debug: true"],
    verbose=True,
    timeout=10_000
)
term = Terminal(options)
```

### Configuration Parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `executable` | `str` | `"s3270"` | Path to s3270 binary; searches PATH if not absolute |
| `args` | `list[str]` | `[]` | Additional command-line args passed to s3270 |
| `verbose` | `bool` | `False` | Enable debug logging to stderr |
| `timeout` | `int` | `30_000` | Default timeout in milliseconds for operations |

### Custom Executable Path

If s3270 is not in your system PATH, provide the full path:

```python
options = TerminalOptions(
    executable="C:\\Program Files\\x3270\\s3270.exe"
)
term = Terminal(options)
term.start()
```

### Custom Arguments

Pass additional arguments to s3270:

```python
options = TerminalOptions(
    args=[
        "-xrm", "s3270.utf8: true",
        "-xrm", "s3270.model: 527"
    ]
)
term = Terminal(options)
```

Consult the [s3270 documentation](http://x3270.bgp.nu/wc3270-man.html) for available options.

### Verbose Mode

Enable verbose output for troubleshooting:

```python
options = TerminalOptions(verbose=True)
term = Terminal(options)
term.start()
```

This logs detailed protocol interactions to help diagnose connection issues.

### Timeout Configuration

Set a default timeout for all operations:

```python
# Increase timeout to 20 seconds for slow networks
options = TerminalOptions(timeout=20_000)
term = Terminal(options)
term.start()

# Operations use this timeout by default
term.wait_ready()  # Uses 20_000 ms
```

You can override the default on a per-call basis:

```python
term.wait_for("READY", timeout=5_000)  # Override to 5 seconds
```

## Query Host Configuration

Use `query()` to request configuration information:

```python
from py3270 import TerminalSetting

term = Terminal()
term.start()
term.connect("host.example.com", 23)

# Query the model number
response = term.query(TerminalSetting.Model)
print(f"Model: {response.data}")

# Query the host name
response = term.query(TerminalSetting.Host)
print(f"Host: {response.data}")

# Query the LU name
response = term.query(TerminalSetting.LuName)
print(f"LU Name: {response.data}")
```

Available settings:

| Setting | Purpose |
|---------|---------|
| `TerminalSetting.ConnectionState` | Current connection state |
| `TerminalSetting.Host` | Connected host name |
| `TerminalSetting.LuName` | Logical Unit name |
| `TerminalSetting.Model` | Terminal model number |
| `TerminalSetting.Encoding` | Character encoding |
| `TerminalSetting.CodePage` | Code page in use |

## Multiple Sessions with SessionManager

For applications that need multiple simultaneous sessions, use `SessionManager`:

```python
from py3270 import SessionManager, TerminalOptions

# Create a manager
manager = SessionManager()

# Create two sessions
options1 = TerminalOptions(executable="s3270", timeout=10_000)
options2 = TerminalOptions(executable="s3270", timeout=10_000)

session_id_1 = manager.create_session(options1, start=True)
session_id_2 = manager.create_session(options2, start=True)

# Get the terminals
term1 = manager.get_session(session_id_1)
term2 = manager.get_session(session_id_2)

# Use them independently
term1.connect("host1.example.com", 23)
term2.connect("host2.example.com", 23)

# Work with each session
term1.string("user1")
term1.enter()

term2.string("user2")
term2.enter()

# Close all when done
manager.close_all()
```

### SessionManager API

| Method | Purpose |
|--------|---------|
| `create_session(options, start=False)` | Create a new terminal, optionally start it |
| `get_session(session_id)` | Retrieve a terminal by ID |
| `close_session(session_id)` | Close a specific terminal |
| `close_all()` | Close all managed terminals |
| `list_sessions()` | Get all session IDs |

## Lifecycle Pattern with try/finally

Always use `try/finally` to ensure cleanup:

```python
from py3270 import Terminal, SessionTimeoutError

term = Terminal()

try:
    term.start()
    term.connect("host.example.com", 23)
    
    # Do work
    term.string("data")
    term.enter()
    term.wait_ready(timeout=5_000)
    term.refresh()
    print(term.screen())
    
except SessionTimeoutError:
    print("Operation timed out")
    raise
except Exception as e:
    print(f"Error: {e}")
    raise
finally:
    # Clean up resources
    term.disconnect()
    term.stop()
```

The `finally` block runs regardless of success or error, ensuring s3270 processes are always terminated.

## Command Execution Variants

Three methods exist for running commands—choose based on your needs:

### `command(cmd, timeout=...)`

Raw command execution:

```python
response = term.command("Query(Host)")
print(response.ok, response.data, response.status)
```

### `run_step(cmd, timeout=...)`

Alias for `command()`:

```python
response = term.run_step("Enter")
```

### `run_workflow(commands, timeout=...)`

Run multiple commands in sequence:

```python
commands = [
    "String(user123)",
    "Tab",
    "String(pass456)",
    "Enter",
]
responses = term.run_workflow(commands, timeout=5_000)
for response in responses:
    print(response.ok)
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
term = Terminal(TerminalOptions(verbose=True))
```

### Inspect Raw Response

```python
response = term.command("Query(Model)")
print(response.raw)  # List of raw output lines
print(response.data)  # Parsed data field
print(response.status)  # Status line
```

### Check Terminal State

```python
print(f"State: {term.state}")
print(f"Available: {term.available()}")
print(f"Cursor: {term.cursor()}")
print(f"Screen size: {term.screen_size()}")
```

## Next Steps

- See [Troubleshooting](08_troubleshooting.md) for solutions to common problems
- Review [Reading the Screen](04_reading_the_screen.md) for data extraction techniques
