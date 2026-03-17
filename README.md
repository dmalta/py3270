# py3270

Python wrapper for the s3270 IBM 3270 terminal emulator.

`py3270` provides a synchronous, testable API for automating TN3270 terminal workflows from Python.

## Features

- Simple synchronous API built around the `Terminal` class
- Screen reading helpers (`screen()`, `read()`, coordinate-based access)
- Input helpers (`string()`, `enter()`, `pf()`)
- Wait and synchronization helpers (`wait_for()`, unlock/state waits)
- Structured errors for predictable exception handling
- Unit and integration test suite

## Requirements

- Python 3.11+
- `s3270` installed and available on your PATH (or configured via `TerminalOptions`)

## What Is s3270?

`s3270` is the scriptable command-line emulator from the x3270 suite. It implements the TN3270/TN3270E protocol and exposes terminal operations (connect, read screen, send keys) in a way automation tools can drive. `py3270` uses `s3270` as its execution engine and provides a clean Python API on top.

## Installation

### Install from source

```bash
git clone https://github.com/dmalta/py3270.git
cd py3270
pip install .
```

### Install for development

```bash
pip install -e .
pip install pytest pytest-cov pytest-timeout
```

See the full platform-specific setup guide in [docs/user_guide/01_installation.md](docs/user_guide/01_installation.md).

## Quickstart

```python
from py3270 import Terminal


def main() -> None:
    term = Terminal()
    term.start()
    try:
        term.connect("example.mainframe.com", 23)
        if term.wait_for("READY", timeout=5_000):
            term.refresh()
            print(term.screen())
        term.disconnect()
    finally:
        term.stop()


if __name__ == "__main__":
    main()
```

## User Guide TOC

- [Introduction](docs/user_guide/00_introduction.md)
- [Installation](docs/user_guide/01_installation.md)
- [Quickstart](docs/user_guide/02_quickstart.md)
- [Connecting](docs/user_guide/03_connecting.md)
- [Reading the Screen](docs/user_guide/04_reading_the_screen.md)
- [Sending Input](docs/user_guide/05_sending_input.md)
- [Waiting for Changes](docs/user_guide/06_waiting_for_changes.md)
- [Advanced Usage](docs/user_guide/07_advanced_usage.md)
- [Troubleshooting](docs/user_guide/08_troubleshooting.md)
- [Glossary](docs/user_guide/GLOSSARY.md)
- [API Reference](../api_reference/py3270.html)

## Additional Documentation

- [Full API and architecture notes](docs/S3270_WRAPPER_FULL_DOCUMENTATION.md)
- [s3270 manual page](docs/s3270_Manual_Page.md)
- [Technical design document](docs/tdd_py3270.md)

## References

- [The x3270 Wiki](https://x3270.miraheze.org/wiki/Main_Page)
- [x3270 repository](https://github.com/pmattes/x3270)

## Running Tests

```bash
pytest
```

Run integration tests separately (requires a working `s3270` + live host setup):

```bash
pytest -m integration
```

## Packaging

Build source and wheel distributions:

```bash
python -m build
```

The project uses `hatchling` as its PEP 517 build backend.
