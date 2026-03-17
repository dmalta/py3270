# Connecting

This chapter covers how to establish and manage connections to mainframe hosts.

## The Connection Lifecycle

Before you can interact with a mainframe application, you must establish a TN3270 connection. The terminal has distinct states:

| State | Meaning |
|-------|---------|
| **Initial** | Terminal has not been started yet |
| **Started** | s3270 is running but not connected to a host |
| **Connected** | Connected to a mainframe host |
| **Disconnected** | Disconnected from the host; s3270 still running |
| **Stopped** | s3270 has been shut down |
| **Failed** | Terminal encountered an error |

## Checking the Terminal State

Use the `state` property and `available()` method to check terminal status:

```python
from py3270 import Terminal, SessionState

term = Terminal()
term.start()

print(term.state)        # Output: SessionState.Started
print(term.available())  # Output: True

term.connect("host.example.com", 23)
print(term.state)        # Output: SessionState.Connected

term.disconnect()
print(term.state)        # Output: SessionState.Disconnected
print(term.available())  # Output: True (process still running)

term.stop()
print(term.available())  # Output: False
```

## Basic Connection

Use the `connect()` method to initiate a connection:

```python
from py3270 import Terminal

term = Terminal()
term.start()
term.connect("myhost.company.com", 23)
```

The `connect()` method takes two required parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `hostname` | `str` | The hostname or IP address of the mainframe |
| `port` | `int` | The TN3270 port (typically 23 or 3270) |

## Connection with Mode

Some hosts require a specific connection mode. Use the optional `mode` parameter:

```python
from py3270 import Terminal, TerminalMode

term = Terminal()
term.start()

# Connect in Passthru mode
term.connect("host.example.com", 23, mode=TerminalMode.Passthru)
```

Available modes:

| Mode | Value | Purpose |
|------|-------|---------|
| `TerminalMode.Passthru` | `"P"` | Pass-through mode (default) |
| `TerminalMode.SuppressExtendedDS` | `"S"` | Suppress extended data streams |
| `TerminalMode.NoTN3270E` | `"N"` | Disable TN3270E extensions |
| `TerminalMode.SSLTunnel` | `"L"` | Use SSL/TLS encryption |
| `TerminalMode.BindStrict` | `"B"` | Strict bind negotiation |

Most hosts work without specifying a mode. Consult your mainframe administrator if you need a specific mode.

## Connection with LU Name

A **Logical Unit (LU) name** is an identifier for a specific terminal session. Some applications require you to specify an LU name; others assign one automatically.

If you need to use a specific LU name:

```python
from py3270 import Terminal

term = Terminal()
term.start()
term.connect("host.example.com", 23, lu_name="LUNAME0001")
```

> **Note**: Ask your systems administrator if you need to specify an LU name. Most connections do not require one.

## Combining Mode and LU Name

You can specify both mode and LU name:

```python
term.connect(
    "host.example.com",
    23,
    mode=TerminalMode.SSLTunnel,
    lu_name="LUNAME0001"
)
```

## Checking Connection Status

After connecting, verify the connection was successful by checking session state and waiting for expected screen content:

```python
term.connect("host.example.com", 23)

if term.state.value == "CONNECTED":
    print("Connection successful")
else:
    print("Connection failed")

# Better: wait for a known screen prompt
if term.wait_for("WELCOME", timeout=5_000):
    print("Host is responding")
else:
    print("Host not responding")
```

## Disconnecting

Use `disconnect()` to end the connection:

```python
term.disconnect()
```

> **Important**: `disconnect()` is idempotent. Calling it multiple times is safe and will not raise an error.

After disconnecting, you can connect to a different host or reconnect to the same host within the same Terminal session:

```python
term.disconnect()
term.connect("other.host.com", 23)  # Works fine
```

## Full Lifecycle Example

```python
from py3270 import Terminal, SessionState

term = Terminal()

try:
    # Start the terminal
    term.start()
    assert term.state == SessionState.Started
    
    # Connect to the host
    term.connect("production.mainframe.com", 23)
    assert term.state == SessionState.Connected
    
    # Do work...
    term.refresh()
    print(term.screen())
    
    # Disconnect
    term.disconnect()
    assert term.state == SessionState.Disconnected
    
finally:
    # Always stop to clean up resources
    term.stop()
    assert not term.available()
```

## Next Steps

- [Read the screen](04_reading_the_screen.md) to extract data
- [Send input](05_sending_input.md) to interact with applications
- [Wait for changes](06_waiting_for_changes.md) to synchronize with the host
