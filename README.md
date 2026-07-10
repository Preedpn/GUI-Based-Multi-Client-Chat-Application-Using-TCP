# ISEA Phase 3 - TCP GUI Chat Application

**Name:** [Your Name]
**Roll Number:** [Your Roll Number]
**Institution:** Assam down town University / Tezpur University (ISEA Phase 3)

## Objective
To convert a terminal-based TCP chat application into a graphical desktop application using Python's Tkinter. The project demonstrates event-driven programming, multithreading (separating GUI from blocking network calls), and user-friendly network application development using Mininet.

## Software Requirements
* OS: Ubuntu Linux
* Network Emulator: Mininet
* Packet Analyzer: Wireshark
* Language: Python 3.x
* Libraries: `socket`, `threading`, `tkinter`, `csv`

## Network Topology
The experiment utilizes a Mininet single-switch topology with 1 Server and 4 Clients.
Command: `sudo mn --topo single,5`
* h1: Chat Server (10.0.0.1)
* h2: Client A 
* h3: Client B
* h4: Client C
* h5: Client D

## Brief Description of Implementation
This application builds upon a standard TCP socket architecture. The server (`server.py`) handles routing, maintains a thread-safe dictionary of connected users, logs chat history to a CSV, and automatically broadcasts an updated user list. The client (`client_gui.py`) utilizes `tkinter` for the interface and runs a daemon background thread to continuously receive network payloads without freezing the main UI thread. 

## Execution Steps
1. Start the Mininet topology: `sudo mn --topo single,5`
2. Open host terminals: `xterm h1 h2 h3 h4 h5`
3. On h1, start the server: `python3 server.py`
4. On h2-h5, launch the GUI clients: `python3 client_gui.py`
5. Enter a username to connect and begin chatting.

## Sample Screenshots
*(Note: Screenshots are available in the `screenshots/` directory of this repository)*
* Login Window
* Main Chat Interface
* Wireshark Packet Captures (Broadcast & Private)
