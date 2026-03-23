# Introduction

Welcome to ibm3270! This guide will teach you how to automate IBM mainframe interactions from Python.

## What Is a 3270 Terminal?

Think of a 3270 terminal as an old text-only browser. Instead of a graphical web interface, it displays information in a structured, grid-based format--typically 24 rows by 80 columns. Users interact with these screens by typing text, pressing function keys, and moving a cursor.

The 3270 protocol has been used for decades and remains common in enterprise mainframe environments. While modern systems use graphical interfaces, many mission-critical financial, insurance, and government applications still run on mainframes and communicate through 3270 terminals.

## What Is a Mainframe?

A mainframe is a large, powerful computing system typically owned and operated by enterprises. Unlike a personal computer, a mainframe can serve thousands of users simultaneously and is designed for reliability, security, and processing high volumes of transactions.

Mainframes excel at:

- Processing structured business data (financial transactions, insurance claims, personnel records)
- Running 24/7 without interruption
- Securely managing sensitive information
- Scaling to enormous workloads

## How Communication Works

Communication between a 3270 terminal and a mainframe happens through a protocol called **TN3270** (or its extended version, **TN3270E**). This protocol was originally designed for dedicated terminal hardware but has been adapted to work over standard TCP/IP networks.

The flow is:

```
Your Python Code
    ↓
ibm3270 library
    ↓
s3270 terminal emulator
    ↓
TN3270/TN3270E protocol
    ↓
Mainframe Host
```

Here's what happens at each layer:

1. **Your Python code** calls ibm3270 methods like `connect()`, `string()`, and `refresh()`
2. **ibm3270** translates your commands into s3270 control commands and sends them to the local `s3270` process
3. **s3270** speaks the TN3270 protocol fluently and sends commands to the mainframe host over the network
4. **s3270** receives responses from the mainframe, parses them, and presents screen data back to ibm3270
5. **ibm3270** caches the screen and makes it available to your code

This layered approach means ibm3270 doesn't need to implement the TN3270 protocol itself--it delegates that work to the well-maintained s3270 emulator.

## Why Python Matters Here

Automating 3270 terminal interactions is useful for:

- **System testing**: Validate mainframe functionality without manual QA labor
- **Data migration**: Read and write data to legacy systems programmatically
- **Integration**: Connect modern applications to mission-critical mainframe systems
- **Scripting**: Run repetitive terminal-based tasks on a schedule

Python makes this automation accessible. Instead of writing shell scripts or VBScript macros, you write clear, readable Python code that interacts with the mainframe just as a human operator would--but faster and without errors.

## The ibm3270 Synchronous API

ibm3270 exposes a **synchronous** session API. All operations block until complete:

```python
from ibm3270 import Terminal

term = Terminal()
term.start()
term.connect("host.example.com", 23)
# This line blocks until the connection completes
term.refresh()
print(term.screen())
term.disconnect()
term.stop()
```

There is no `await`, no async/await complexity. Code runs line by line, making it easy to reason about sequencing and error handling.

## What You Will Learn

This guide covers:

1. **Installation**: Get s3270 and ibm3270 running on your system
2. **Quickstart**: Run your first automation script
3. **Connecting**: Establish and manage connections to mainframe hosts
4. **Reading screens**: Extract data and find text on the screen
5. **Sending input**: Type text, press keys, and interact with forms
6. **Waiting for changes**: Coordinate with the host's asynchronous responses
7. **Advanced usage**: Use multiple sessions, custom configuration, and diagnostic queries
8. **Troubleshooting**: Solve common problems and understand error messages

After completing this guide, you will be able to write Python scripts that navigate 3270 screens, extract data, and automate repetitive mainframe tasks.

> **Next step**: See [Installation](01_installation.md) to get started.
