# Waiting for Changes

This chapter covers how to coordinate with asynchronous host responses using py3270's waiting helpers.

## Why Waiting Matters

When you send input to the host (using `enter()`, `pf()`, etc.), the host doesn't respond instantly. It needs time to process your command, perform business logic, and generate a response screen.

If you try to read the screen immediately after sending input, you'll see the _old_ screen, not the result. Waiting helpers block until the host is ready, ensuring you read fresh data.

## Wait for Text to Appear

Use `wait_for(text, timeout)` to poll the screen until a specific string appears:

```python
term.enter()

# Wait up to 5 seconds (5000 milliseconds) for "WELCOME" to appear
if term.wait_for("WELCOME", timeout=5_000):
    print("Host is ready")
else:
    print("Timeout: WELCOME never appeared")
```

`wait_for()` returns:

- `True` if the text appeared within the timeout
- `False` if the timeout expired without finding the text

> **Important**: `wait_for()` does not raise an exception on timeout; it returns `False`.

## Wait for Text at a Specific Position

You can also wait for text at a specific row and column:

```python
term.enter()

# Wait for "OK" at row 24, column 1
if term.wait_for("OK", row=24, col=1, timeout=5_000):
    print("Operation successful")
else:
    print("No OK message")
```

When you specify `row` and `col`, `wait_for()` checks only that exact position instead of searching the entire screen.

## Wait for Host Readiness (Semantic Waits)

Some operations benefit from waiting for specific host states rather than text:

### `wait_unlock()`

Waits until the keyboard is unlocked (host finished processing):

```python
term.enter()
response = term.wait_unlock(timeout=5_000)
print(response.ok)  # True if unlocked, False if timeout
```

Returns a `TerminalResponse` object with `ok` indicating success.

### `wait_output()`

Waits until the host has generated new output:

```python
term.enter()
response = term.wait_output(timeout=5_000)
if response.ok:
    term.refresh()
    print(term.screen())
```

### `wait_ready()`

A convenience wrapper that waits for both unlock and output:

```python
term.enter()
term.wait_ready(timeout=5_000)  # Returns None
term.refresh()
print(term.screen())
```

`wait_ready()` is ideal for simple "send and wait" patterns.

## Timeout Behavior Differences

Different waits handle timeouts differently:

### `wait_for()` Timeout

Returns `False` (does not raise):

```python
if not term.wait_for("READY", timeout=5_000):
    # Handle missing text gracefully
    term.refresh()
    raise RuntimeError(f"Expected 'READY' but got:\n{term.screen()}")
```

### `wait_unlock()` / `wait_output()` Timeout

Raises `SessionTimeoutError`:

```python
try:
    term.wait_unlock(timeout=5_000)
except SessionTimeoutError:
    print("Host not responding")
```

Wrap these in try/except if you want to handle timeouts gracefully.

### `wait_ready()` Timeout

Raises `SessionTimeoutError` (same as `wait_unlock()` and `wait_output()`):

```python
try:
    term.wait_ready(timeout=5_000)
except SessionTimeoutError:
    print("Host not responding")
    raise
```

## Practical Workflow Pattern

Here's a robust pattern for sending input and reading results:

```python
from py3270 import Terminal, SessionTimeoutError

term = Terminal()
term.start()
term.connect("host.example.com", 23)

try:
    # Type username and password
    term.string("user123")
    term.tab()
    term.string("pass456")

    # Send the form
    term.enter()

    # Wait for host to respond
    try:
        term.wait_ready(timeout=5_000)
    except SessionTimeoutError:
        print("Login timeout")
        raise

    # Refresh and check result
    term.refresh()
    if term.check("ERROR", 1, 1):
        print("Login failed")
        print(term.screen())
    else:
        print("Login successful")

except Exception as e:
    print(f"Error: {e}")
finally:
    term.disconnect()
    term.stop()
```

## Timeout Units

All timeout parameters are in **milliseconds**, not seconds:

```python
term.wait_for("READY", timeout=300)      # 300 milliseconds = 0.3 seconds
term.wait_for("READY", timeout=5_000)    # 5000 milliseconds = 5 seconds
term.wait_for("READY", timeout=60_000)   # 60000 milliseconds = 60 seconds
```

Use `5_000` (with underscores for readability) or `5000` for 5 seconds.

## Polling Internals

Internally, `wait_for()` polls the screen repeatedly every 100 milliseconds and checks for your text. This means `wait_for()` is cheap CPU-wise but responsive--it will detect text within ~100 ms of it appearing.

## When to Use Which Wait

Scenario                   | Use
-------------------------- | ------------------------------------------
Check for specific text    | `wait_for(text)`
Wait for specific position | `wait_for(text, row, col)`
Just wait for readiness    | `wait_ready()`
Handle timeout gracefully  | `wait_for()` (returns False)
Fail hard on timeout       | `wait_unlock()` / `wait_output()` (raises)

## Next Steps

- Combine waiting with [input](05_sending_input.md) for multi-step workflows
- Combine waiting with [screen reading](04_reading_the_screen.md) to extract results
