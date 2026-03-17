# Installation

This chapter guides you through installing both s3270 and py3270.

## Install s3270

py3270 requires `s3270`—the scriptable terminal emulator. Choose your platform below.

### macOS

Install via Homebrew:

```bash
brew install x3270
```

This installs the entire x3270 suite, including `s3270`.

### Linux

#### Debian / Ubuntu

```bash
sudo apt-get update
sudo apt-get install x3270
```

#### RHEL / CentOS / Fedora

```bash
sudo yum install x3270
```

or

```bash
sudo dnf install x3270
```

#### Arch Linux

```bash
sudo pacman -S x3270
```

### Windows

Download the x3270 installer from [Paul Mattes' x3270 page](http://x3270.bgp.nu/):

1. Visit the download page
2. Download the Windows installer (e.g., `x3270-*-setup.exe`)
3. Run the installer
4. Accept the defaults or choose your preferred installation directory
5. The installer places `s3270.exe` in the installation directory

If you installed to the default location (`C:\Program Files\x3270`), the full path is:

```
C:\Program Files\x3270\s3270.exe
```

If you installed to another location, adjust the path accordingly. You will tell py3270 where to find `s3270` when creating a Terminal.

## Verify s3270

Once installed, verify s3270 works from the command line:

```bash
s3270 -h
```

You should see help output. This confirms s3270 is correctly installed and in your system PATH.

If you installed s3270 to a non-standard location on Windows, use the full path:

```bash
"C:\Program Files\x3270\s3270.exe" -h
```

## Install py3270

Install py3270 from PyPI using pip:

```bash
pip install py3270
```

Or, if you are using a virtual environment (recommended):

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
pip install py3270
```

## Verify py3270

Create a test file called `test_install.py`:

```python
from py3270 import Terminal

print(f"py3270 imported successfully!")
print(f"Terminal class: {Terminal}")
```

Run it:

```bash
python test_install.py
```

You should see:

```
py3270 imported successfully!
Terminal class: <class 'py3270.terminal.Terminal'>
```

If you encounter import errors, make sure py3270 is installed in your active Python environment.

## Troubleshooting

### s3270 not found

If you see an error like "s3270: command not found" or "executable not found: s3270", the binary is not in your system PATH.

**Solutions:**

1. **Ensure it is installed**: Re-run the platform-specific install command above.
2. **Add to PATH**: Add the installation directory to your system PATH environment variable.
3. **Use the full path**: When creating a py3270 Terminal, provide the full path to s3270:

   ```python
   from py3270 import Terminal, TerminalOptions

   options = TerminalOptions(executable="C:\\Program Files\\x3270\\s3270.exe")
   term = Terminal(options)
   term.start()
   ```

### Python import errors

If `import py3270` fails:

1. Confirm py3270 is installed: `pip list | grep py3270`
2. Confirm you are using the correct Python environment: `which python`
3. Reinstall if needed: `pip install --upgrade --force-reinstall py3270`

### Permission errors on Linux/macOS

If you see permission denied errors after installing via package manager:

- Try `sudo` (not ideal but can unblock you): `sudo pip install py3270`
- Or use a virtual environment to avoid permission issues

### Next Steps

Once installation is verified, proceed to the [Quickstart](02_quickstart.md) for your first automation script.
