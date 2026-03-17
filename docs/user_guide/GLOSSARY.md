# Glossary

This document defines key terms used throughout the py3270 user guide.

## 3270 Terminal

A text-based terminal interface that communicates using the 3270 protocol. Unlike modern graphical terminals, 3270 terminals use a structured field-based screen model where data is organized in rows and columns.

## Mainframe

A large, centralized computing system typically used by enterprises for mission-critical business operations. Mainframes can serve thousands of users simultaneously and are known for reliability and data processing power.

## TN3270

An Internet protocol that allows 3270 terminals to communicate with mainframe systems over TCP/IP networks instead of direct terminal cables. TN3270 stands for "Telnet 3270".

## TN3270E

An extended version of TN3270 that adds support for additional features like screen resizing and improved data negotiation between client and server.

## s3270

A command-line 3270 terminal emulator developed by Paul Mattes. It implements the 3270 protocol and can connect to mainframe systems. The `s3270` program is scriptable, making it ideal for automation. py3270 drives s3270 from Python.

## x3270 Suite

A collection of 3270 terminal emulators including:
- `x3270`: an interactive X11 graphical terminal
- `s3270`: a scriptable terminal emulator
- `c3270`: a curses-based terminal

py3270 specifically automates `s3270`.

## Screen Buffer

The in-memory representation of the 3270 screen as displayed to the user. The screen is typically 24 rows by 80 columns of text. After each command, py3270 caches the screen buffer locally so you can read it without sending additional queries to the host.

## Refresh

The action of retrieving the current screen display from the terminal emulator and updating the cached screen buffer. You must call `refresh()` before reading screen data in py3270.

## Keyboard Lock

A terminal mode where keyboard input is disabled (locked) until the host processes a previous command and indicates readiness. When the keyboard is unlocked, the terminal is ready to accept new input.

## Row and Column Coordinates

Positions on the screen grid, both 1-indexed. For example, row 1, column 1 is the top-left corner of the screen. This convention is consistent with 3270 terminal standards.

## AID Key

An Attention Identifier key—a special key that sends a command and current screen data to the host. Common AID keys include PF (Program Function) keys and PA (Program Attention) keys.

## PF Key

Program Function keys (PF1 through PF24) that send commands to the host application. Each key typically has a defined meaning in the application (for example, PF3 often means "Exit").

## PA Key

Program Attention keys (PA1, PA2, PA3) that interrupt the current operation and send a signal to the host. Often used for operations like "Attention" or "Reset".

## LU Name

Logical Unit name—an identifier for a specific terminal session on the mainframe. Some mainframe applications require an LU name to establish a connection. If not specified, the host assigns a default.

## Connection State

The current connectivity status of the Terminal:
- **Initial**: Terminal has not been started yet.
- **Started**: Terminal process is running, but not connected to a host.
- **Connected**: Terminal is connected to a mainframe host.
- **Disconnected**: Terminal process is running but has disconnected from the host.
- **Stopped**: Terminal process has been shut down.
- **Failed**: Terminal process encountered an error.

## EBCDIC

Extended Binary Coded Decimal Interchange Code—the character encoding used by IBM mainframes. py3270 and s3270 handle EBCDIC translation automatically.

## Escape Sequence

A special text sequence used to send non-printable characters or control codes to the terminal. For example, `\u001b[H` might represent the Home key. py3270 validates escape sequences before sending them.

## Formatted Screen

A screen layout defined by the host application using protected and unprotected fields. Protected fields are for display only; unprotected fields accept input.

## Query

A request for status or configuration information from the terminal emulator (not the host). For example, querying the connection state, current model number, or encoding.
