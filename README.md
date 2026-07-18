1. Objective
To enhance a GUI-based multi-client TCP application by implementing practical
backend security mechanisms. The project focuses on application-level
security, introducing authentication, cryptographic password hashing (SHA-
256), brute-force protection, duplicate login prevention, and secure session
management.
2. Security Features Implemented
• User Authentication: Custom /auth handshake protocol implemented
before any chat data is accepted.
• Secure Password Storage: Plaintext passwords are mathematically
transformed using Python's hashlib.sha256() and stored in a
local users.json database.
• Duplicate Login Prevention: The server validates incoming authentication
requests against the active thread dictionary, rejecting concurrent
sessions for the same username.
• Input Validation: Both client-side and server-side validation reject empty
fields, short passwords, non-alphanumeric usernames, and oversized
message payloads (>500 characters).
• Failed Login Protection: An in-memory tracking dictionary logs failed
attempts per username. Five consecutive failures trigger a 60-second
temporal IP/account lockout.
• Session Management & Logging: Sockets enforce a 120-second inactivity
timeout. All security events are logged to security_log.txt without
exposing credential data.
3. System Architecture
The application runs over a Mininet single-switch topology (single,5). It
maintains the multithreaded client-server architecture from Assignment 6 but
introduces a strict state-machine on the server side. A client socket is placed in
an "unauthenticated" state upon connection and is restricted from joining the
broadcast loop until the authentication handshake is fully verified by the
server.
4. Implementation Details
The server acts as a centralized identity provider. threading.RLock() is utilized
heavily to prevent race conditions during rapid authentication requests or
concurrent security logging. The client GUI was updated to include a masked
password entry field and logic to
parse AUTH_FAIL and DUPLICATE_ERROR server codes into user-
friendly tkinter.messagebox popups.
