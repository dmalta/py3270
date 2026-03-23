# Quickstart

Let's write your first ibm3270 automation script.

## Prerequisites

- ibm3270 and s3270 are installed (see [Installation](01_installation.md))
- You have access to a TN3270 host (or you can test with a public demo if available)

## Your First Script

Create a file called `quickstart.py`:

```python
from ibm3270 import Terminal


def main() -> None:
    # Create and start a terminal
    term = Terminal()
    term.start()
    try:
        # Connect to a mainframe
        term.connect("example.mainframe.com", 23)

        # Wait for the host to respond
        term.wait_for("READY", timeout=5_000)

        # Refresh the screen buffer
        term.refresh()

        # Print what you see
        print(term.screen())

        # Disconnect
        term.disconnect()
    finally:
        # Always stop the terminal
        term.stop()


if __name__ == "__main__":
    main()
```

Replace `"example.mainframe.com"` with the actual hostname of your target mainframe.

## Running the Script

```bash
python quickstart.py
```

The script will:

1. Start the s3270 terminal emulator
2. Connect to the host
3. Wait up to 5 seconds for "READY" to appear on the screen
4. Display the screen contents
5. Disconnect and shut down gracefully

## What Happens Behind the Scenes

- **`term.start()`**: Launches the s3270 process locally
- **`term.connect(host, port)`**: Tells s3270 to establish a TN3270 connection to the host
- **`term.wait_for(text, timeout)`**: Polls the screen until `text` appears or the timeout expires
- **`term.refresh()`**: Retrieves the current screen from s3270 and caches it in Python
- **`term.screen()`**: Returns the cached screen as a string
- **`term.disconnect()`**: Closes the mainframe connection (s3270 stays running)
- **`term.stop()`**: Shuts down the s3270 process

The `try/finally` block ensures `term.stop()` runs even if an error occurs, preventing orphaned s3270 processes.

## Error Handling

If the connection fails or the host does not respond, `wait_for()` returns `False` after the timeout:

```python
if not term.wait_for("READY", timeout=5_000):
    term.refresh()
    print("Host not ready. Screen:")
    print(term.screen())
    raise RuntimeError("Connection failed")
```

For more advanced error handling, see [Troubleshooting](08_troubleshooting.md).

## Next Steps

Now that you have a working script, learn how to:

- [**Connect** to different hosts and handle modes](03_connecting.md)
- [**Read** data from the screen](04_reading_the_screen.md)
- [**Send input** by typing and pressing keys](05_sending_input.md)
- [**Wait intelligently** for host responses](06_waiting_for_changes.md)
