# Sending Input

This chapter covers how to interact with 3270 screens by typing text and pressing keys.

## Type Text

Use `string(text)` to send text to the current cursor position:

```python
from py3270 import Terminal

term = Terminal()
term.start()
term.connect("host.example.com", 23)

term.string("myusername")  # Types "myusername"
```

The text is sent character-by-character to the host, just as if a human typed it.

## Press Enter

Use `enter()` to submit the current screen (equivalent to pressing the Enter key):

```python
term.string("myusername")
term.enter()  # Submits the form
```

After pressing Enter, the host processes your input and returns a new screen. Always use `wait_for()` or `wait_unlock()` to synchronize before reading the next screen (see [Waiting for Changes](06_waiting_for_changes.md)).

## Press Program Function Keys

Use `pf(n)` to press a Program Function key (PF1 through PF24):

```python
term.pf(1)   # Press PF1
term.pf(3)   # Press PF3 (usually "Exit")
term.pf(24)  # Press PF24 (highest PF key)
```

Each application defines what each PF key does. Common conventions:

Key | Often Means
--- | ------------------
PF1 | Help
PF3 | Exit
PF4 | Delete
PF5 | Refresh
PF7 | Back/Previous page
PF8 | Forward/Next page

Check your application's documentation for the specific meanings.

## Press Program Attention Keys

Use `pa(n)` to press a Program Attention key (PA1, PA2, or PA3):

```python
term.pa(1)   # Press PA1
term.pa(2)   # Press PA2
term.pa(3)   # Press PA3
```

PA keys interrupt the current operation and signal the host. Common uses:

Key | Often Means
--- | ---------------------
PA1 | Attention / Interrupt
PA2 | Reshow / Refresh
PA3 | Clear / Reset

## Press Tab

Use `tab()` to move to the next unprotected field:

```python
term.tab()  # Move to next input field
```

This is useful when navigating between form fields.

## Move Cursor

Use `move(row, col)` to position the cursor at a specific location:

```python
term.move(5, 10)  # Move to row 5, column 10
```

This is useful when you want to start typing in a specific field without using Tab repeatedly.

## Clear the Screen

Use `clear()` to clear all data on the current screen:

```python
term.clear()  # Clear screen
term.wait_ready(timeout=5_000)  # Wait for host to respond
```

This is rarely used in normal workflows but exists for completeness.

## Control Characters and Escape Sequences

Some terminal interactions require special characters. py3270 supports escape sequences for these:

```python
# Send backspace
term.string("text\x08")  # \x08 = backspace

# Send tab character (same as tab() method)
term.string("\t")

# Send Home key
term.string("\u001b[H")
```

Common escape sequences:

Sequence   | Meaning
---------- | ---------
`\t`       | Tab
`\x08`     | Backspace
`\u001b[H` | Home

If py3270 rejects an escape sequence, it will raise an error explaining why. This prevents accidentally sending invalid control codes that could corrupt the host session.

## Practical Example: Login Flow

```python
from py3270 import Terminal

term = Terminal()
term.start()
try:
    term.connect("host.example.com", 23)

    # Wait for login screen
    if not term.wait_for("User ID:", timeout=5_000):
        raise RuntimeError("Login screen not found")

    # Type username
    term.string("john.doe")

    # Tab to password field
    term.tab()

    # Type password
    term.string("SecurePassword123")

    # Press Enter to submit
    term.enter()

    # Wait for host to process login
    term.wait_unlock(timeout=5_000)

    # Refresh and check if we're logged in
    term.refresh()
    if term.check("Welcome", 1, 1):
        print("Login successful")
    else:
        print("Login may have failed")
        print(term.screen())

finally:
    term.disconnect()
    term.stop()
```

## Next Steps

- [Wait for changes](06_waiting_for_changes.md) to coordinate with the host's asynchronous responses
- [Read the screen](04_reading_the_screen.md) to extract results after sending input
