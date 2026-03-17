# Troubleshooting

This chapter covers diagnosing and fixing common problems with py3270.

## s3270 Not Found

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 's3270'`

**Cause**: s3270 is not installed or not in your system PATH.

**Solutions**:

1. **Install s3270** (see [Installation](01_installation.md)):

  ```bash
  # macOS
  brew install x3270

  # Linux (Debian/Ubuntu)
  sudo apt-get install x3270

  # Windows
  Download from http://x3270.bgp.nu/
  ```

2. **Verify installation**:

  ```bash
  s3270 -h
  ```

  Should show help text.

3. **Add to PATH** (if installed to non-standard location):

  - **Windows**: Add the installation directory to your system PATH
  - **Linux/macOS**: Create a symlink or add directory to PATH

4. **Use absolute path** (temporary workaround):

  ```python
  from py3270 import Terminal, TerminalOptions

  options = TerminalOptions(
      executable="/usr/local/bin/s3270"
  )
  term = Terminal(options)
  ```

## Terminal Not Running

**Error**: `SessionDisconnectedError: Terminal is not running`

**Cause**: You called a method (like `connect()` or `refresh()`) without first calling `start()`.

**Solution**:

```python
from py3270 import Terminal

term = Terminal()
term.start()  # Always start first!
term.connect("host.example.com", 23)
```

## Connection Failed

**Error**: Connection to host fails or times out.

**Cause**: Host is unreachable, wrong port, or network issues.

**Steps to diagnose**:

1. **Verify host is online**:

  ```bash
  ping host.example.com
  telnet host.example.com 23
  ```

2. **Check port number** (usually 23 or 3270):

  ```python
  term.connect("host.example.com", 3270)  # Try alternative port
  ```

3. **Verify credentials** (if required):

  ```python
  term.connect("host.example.com", 23, lu_name="YOUR_LU_NAME")
  ```

4. **Check network/firewall**:

  - Is there a corporate firewall blocking the connection?
  - Are you on the correct VPN?

5. **Add verbose logging**:

  ```python
  from py3270 import TerminalOptions

  options = TerminalOptions(verbose=True)
  term = Terminal(options)
  term.start()
  ```

## Timeout Errors

**Error**: `SessionTimeoutError: operation timed out`

**Cause**: Host took longer than the timeout to respond.

**Solutions**:

1. **Increase timeout**:

  ```python
  from py3270 import TerminalOptions

  # Set global timeout to 20 seconds
  options = TerminalOptions(timeout=20_000)
  term = Terminal(options)
  term.start()
  ```

2. **Increase specific operation timeout**:

  ```python
  term.wait_ready(timeout=10_000)  # 10 seconds
  ```

3. **Check if host is slow**:

  - Try typing manually with a real 3270 emulator
  - If slow there too, increase your script timeout
  - Do not use timeouts below 2000 ms (2 seconds)

4. **Check network latency**:

  ```bash
  ping -c 10 host.example.com
  ```

## Wait Fails (wait_for returns False)

**Error**: `wait_for()` returns `False` instead of `True`.

**Cause**: Expected text did not appear on screen within the timeout.

**Steps to diagnose**:

1. **Check what's actually on screen**:

  ```python
  if not term.wait_for("READY", timeout=5_000):
      term.refresh()
      print(term.screen())
      print("---")
      # Look for typos or unexpected text
  ```

2. **Check case sensitivity** (text is case-sensitive):

  ```python
  # Wrong
  term.wait_for("ready")  # lowercase

  # Correct
  term.wait_for("READY")  # uppercase
  ```

3. **Trim whitespace** (if searching for fixed text):

  ```python
  # Get screen and look for exact text
  term.refresh()
  print(repr(term.screen()))  # Show whitespace visually
  ```

4. **Use a less specific search**:

  ```python
  # Instead of exact match
  if term.wait_for("ERROR MESSAGE SPECIFIC", timeout=5_000):
      pass

  # Try broader search
  if term.wait_for("ERROR", timeout=5_000):
      pass
  ```

## Invalid Escape Sequence Error

**Error**: `ValueError: Invalid escape sequence: ...`

**Cause**: Tried to send an unsupported control character.

**Solutions**:

1. **Avoid special characters** in plain strings:

  ```python
  # Wrong (invalid escape)
  term.string("data\x00")

  # Correct (only use supported escapes)
  term.string("data\t")  # Tab is fine
  ```

2. **Use double-backslash for literal backslash**:

  ```python
  # Wrong
  term.string("path\file")  # \f is interpreted as escape

  # Correct
  term.string("path\\file")  # Literal backslash
  ```

3. **Check escape sequence documentation** (see [Sending Input](05_sending_input.md))

## Keyboard Lock / Cannot Type

**Error**: `enter()` or `string()` works but keyboard appears locked on screen.

**Cause**: Host is processing a previous command; keyboard not yet unlocked.

**Solution**: Use `wait_unlock()`:

```python
term.string("data")
term.enter()

# Wait for keyboard to unlock
term.wait_unlock(timeout=5_000)

# Now safe to type again
term.string("next_input")
```

## Screen Data Messed Up or Invalid

**Error**: `read()` returns garbage or wrong data.

**Cause**: Screen buffer not refreshed after host action.

**Solution**: Always call `refresh()` before reading:

```python
term.enter()
term.wait_ready(timeout=5_000)

# Refresh first!
term.refresh()

# Now read
user_id = term.read(2, 12, 8)
```

## Coordinates Off by One or Wrong Position

**Error**: `read()` returns data from wrong position.

**Cause**: Pyth ons are 0-indexed, but py3270 uses 1-indexed 3270 coordinates.

**Example**:

```python
# Screen: "Welcome" at visual position top-left
# py3270 uses 1-indexed: row 1, col 1
term.read(1, 1, 7)  # Get "Welcome"

# Do NOT use 0
term.read(0, 0, 7)  # Wrong: gets out-of-bounds
```

## py3270 Import Fails

**Error**: `ModuleNotFoundError: No module named 'py3270'`

**Cause**: py3270 not installed in your Python environment.

**Solutions**:

1. **Install py3270**:

  ```bash
  pip install py3270
  ```

2. **Check environment**:

  ```bash
  which python  # Or 'where python' on Windows
  python -m pip list | grep py3270
  ```

3. **Use correct virtual environment**:

  ```bash
  source env/bin/activate  # Linux/macOS
  env\Scripts\activate     # Windows
  pip install py3270
  python your_script.py
  ```

## Performance Issues

**Problem**: Script runs slowly.

**Possible causes**:

1. **Slow network**: Increase timeout, but understand the host is slow
2. **Excessive `refresh()` calls**: Minimize calls to `refresh()`
3. **S3270 busy**: Check if s3270 is under high load (unlikely)

**Solutions**:

- Use `wait_for()` instead of polling manually
- Batch operations: read multiple fields with `read_many()` instead of individual `read()` calls
- Reduce timeout for faster failure detection if expected

## Getting Help

If you cannot solve the problem:

1. **Enable verbose logging** to see protocol details:

  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)

  term = Terminal(TerminalOptions(verbose=True))
  ```

2. **Capture output and examine it** for error messages

3. **Test manually** with a real 3270 emulator (`x3270` or `c3270`) to verify the host works

4. **Check s3270 documentation**: <http://x3270.bgp.nu/>

## Next Steps

- Review [Advanced Usage](07_advanced_usage.md) for command-line options
- Check the [Glossary](GLOSSARY.md) for terminology clarification
