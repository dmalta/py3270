# Reading the Screen

This chapter covers how to extract data from 3270 screens using py3270.

## The Screen Coordinate System

A 3270 screen is a grid of characters, typically 24 rows by 80 columns. **All coordinates are 1-indexed**—the top-left corner is row 1, column 1.

```
Column:   1                            40                           80
Row 1:    | HOME | WELCOME TO ACME CORP |  |                        |
Row 2:    |      | User ID: [________]  |  |                        |
Row 3:    |      | Password: [________]  |  |                        |
...
Row 24:   | Press PF3 to exit                                        |
```

## Refresh First

Before you can read screen data, you must call `refresh()` to update the cached screen buffer:

```python
from py3270 import Terminal

term = Terminal()
term.start()
term.connect("host.example.com", 23)

# Without refresh(), the screen buffer is empty
term.refresh()

# Now you can read it
screen = term.screen()
```

> **Why refresh?** The s3270 process maintains the screen internally. py3270 caches a copy locally so you can access it repeatedly without querying the host. `refresh()` synchronizes the cache.

## Get the Entire Screen

Use `screen()` to retrieve the entire cached screen as a single string:

```python
term.refresh()
screen_text = term.screen()
print(screen_text)
```

Output:

```
 Welcome to ACME Corporation
 User ID: [   ]
 Password: [   ]

 Enter your credentials and press Enter.
```

## Read a Specific Cell Range

Use `read(row, col, length)` to extract a substring from a specific position:

```python
term.refresh()

# Read 8 characters starting at row 2, column 12
user_id = term.read(2, 12, 8)
print(f"User ID field: '{user_id}'")

# Read the password prompt
passwd_label = term.read(3, 1, 9)
print(f"Label: '{passwd_label}'")
```

Arguments:

| Parameter | Type | Description |
|-----------|------|-------------|
| `row` | `int` | Row number (1-indexed) |
| `col` | `int` | Column number (1-indexed) |
| `length` | `int` | Number of characters to read |
| `trim` | `bool` | Remove trailing whitespace (default: `True`) |

By default, `read()` trims trailing whitespace. Use `trim=False` to preserve spacing:

```python
# With trim=True (default)
term.read(2, 12, 8)     # Returns "user123" if field is "user123  "

# With trim=False
term.read(2, 12, 8, trim=False)  # Returns "user123  "
```

## Check for Text

Use `check(text, row, col)` to test if a specific string appears at a given position:

```python
term.refresh()

# Check if "OK" appears at row 24, column 1
if term.check("OK", 24, 1):
    print("Operation successful")
else:
    print("Check failed")
```

This is equivalent to:

```python
if term.read(24, 1, 2) == "OK":
    print("Operation successful")
```

## Read Multiple Fields at Once

When you need to extract many fields, use `read_many()` with a list of `FieldDefinition` objects:

```python
from py3270 import FieldDefinition

term.refresh()

fields = [
    FieldDefinition(row=2, col=12, length=8, type="string"),
    FieldDefinition(row=3, col=12, length=15, type="string"),
    FieldDefinition(row=5, col=20, length=10, type="number"),
]

values = term.read_many(fields)
print(values)
```

Output:

```python
{
    "2,12": "user123",
    "3,12": "john.doe@example.c",
    "5,20": 12345.0
}
```

Each field is defined by:

| Field | Type | Description |
|-------|------|-------------|
| `row` | `int` | Row number (1-indexed) |
| `col` | `int` | Column number (1-indexed) |
| `length` | `int` | Number of characters to read |
| `type` | `str` | `"string"` or `"number"` |
| `trim` | `bool` | Remove trailing whitespace for strings (default: `True`) |

Results are stored in a dictionary with key `"{row},{col}"`. For `type="number"`, the value is converted to `float` or `None` if unparseable.

## Search for Text on Screen

To find text anywhere on the screen, use string operations:

```python
term.refresh()

if "ERROR" in term.screen():
    print("Error message detected")
    # Find the line containing ERROR
    for line in term.get_screen_buffer():
        if "ERROR" in line:
            print(f"Error: {line}")
```

Or use `wait_for()` which does this polling (see [Waiting for Changes](06_waiting_for_changes.md)).

## Common Mistakes

| Mistake | Issue | Fix |
|---------|-------|-----|
| Forgetting `refresh()` | Screen buffer is empty/stale | Always call `term.refresh()` before reading |
| Wrong coordinates | Off-by-one errors | Remember: 1-indexed, not 0-indexed |
| No trim | Extra spaces in results | Use `trim=True` (the default) for clean text |
| Assuming immediate updates | Data not ready after input | Call `term.wait_for()` before `refresh()` |

## Next Steps

- [Send input](05_sending_input.md) to populate fields and interact with forms
- [Wait for changes](06_waiting_for_changes.md) to synchronize with the host
