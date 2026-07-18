import socket
import threading
from datetime import datetime
import csv
import os
import hashlib
import json
import time

HOST = '10.0.0.1'
PORT = 5000

clients_lock = threading.RLock()
client_data = {} 
server_stats = {'processed': 0, 'broadcasts': 0, 'privates': 0}

CHAT_FILE = 'chat_history.csv'
USERS_FILE = 'users.json'
SECURITY_LOG = 'security_log.txt'

# Security variables
MAX_ATTEMPTS = 5
LOCKOUT_TIME = 60 # seconds
failed_attempts = {} # {username: {'count': int, 'lockout_until': float}}

def init_files():
    """Initializes necessary databases and logs."""
    if not os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, 'w', newline='') as f:
            csv.writer(f).writerow(['timestamp', 'sender', 'receiver', 'message_type', 'message'])
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
    if not os.path.exists(SECURITY_LOG):
        open(SECURITY_LOG, 'w').close()

def sec_log(event):
    """Logs security events without exposing passwords."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with clients_lock:
        with open(SECURITY_LOG, 'a') as f:
            f.write(f"[{timestamp}] {event}\n")
    print(f"[SECURITY] {event}")

def hash_password(password):
    """Converts a plaintext password into a secure SHA-256 hash."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def authenticate_user(username, password, ip):
    """Handles Registration, Login, and Brute Force Protection."""
    with clients_lock:
        # Check lockout status
        if username in failed_attempts:
            if time.time() < failed_attempts[username]['lockout_until']:
                sec_log(f"Blocked login for locked user '{username}' from {ip}")
                return False, "Account temporarily locked. Try again later."

        with open(USERS_FILE, 'r') as f:
            users_db = json.load(f)

        hashed_pw = hash_password(password)

        if username not in users_db:
            # Auto-register new users
            users_db[username] = hashed_pw
            with open(USERS_FILE, 'w') as f:
                json.dump(users_db, f)
            sec_log(f"New user registered: '{username}' from {ip}")
            return True, "Registration successful."
        
        else:
            # Verify existing user
            if users_db[username] == hashed_pw:
                # Reset failed attempts on success
                if username in failed_attempts:
                    del failed_attempts[username]
                sec_log(f"Successful login for '{username}' from {ip}")
                return True, "Login successful."
            else:
                # Track failed attempts
                if username not in failed_attempts:
                    failed_attempts[username] = {'count': 0, 'lockout_until': 0}
                
                failed_attempts[username]['count'] += 1
                attempts_left = MAX_ATTEMPTS - failed_attempts[username]['count']
                
                sec_log(f"Failed login for '{username}' from {ip}. Attempts left: {attempts_left}")
                
                if failed_attempts[username]['count'] >= MAX_ATTEMPTS:
                    failed_attempts[username]['lockout_until'] = time.time() + LOCKOUT_TIME
                    failed_attempts[username]['count'] = 0 # Reset count for next lockout cycle
                    sec_log(f"User '{username}' locked out for {LOCKOUT_TIME} seconds.")
                    return False, f"Too many failed attempts. Account locked for {LOCKOUT_TIME} seconds."
                
                return False, f"Invalid password. {attempts_left} attempts remaining."

def log_message(sender, receiver, msg_type, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with clients_lock:
        with open(CHAT_FILE, 'a', newline='') as f:
            csv.writer(f).writerow([timestamp, sender, receiver, msg_type, message])

def broadcast(message, sender="Server"):
    with clients_lock:
        server_stats['broadcasts'] += 1
        for user, data in client_data.items():
            if data['status'] == 'online' and user != sender:
                try:
                    data['socket'].send(message.encode('utf-8'))
                except:
                    pass

def broadcast_user_list():
    with clients_lock:
        online_users = [u for u, d in client_data.items() if d['status'] == 'online']
    list_str = "/USERLIST " + ",".join(online_users)
    broadcast(list_str + "\n")

def handle_client(client_socket, client_address):
    ip, port = client_address
    username = ""
    
    # Task 6: Session Management (Timeout after 120 seconds of inactivity)
    client_socket.settimeout(120.0) 
    
    try:
        # Auth Loop
        authenticated = False
        while not authenticated:
            client_socket.send("AUTH_REQ".encode('utf-8'))
            auth_data = client_socket.recv(1024).decode('utf-8').strip()
            
            if not auth_data.startswith("/auth "):
                client_socket.send("Invalid authentication format.\n".encode('utf-8'))
                continue
                
            parts = auth_data.split(' ', 2)
            if len(parts) != 3:
                client_socket.send("Missing credentials.\n".encode('utf-8'))
                continue
                
            req_user, req_pass = parts[1], parts[2]
            
            # Task 4: Input Validation
            if len(req_user) < 3 or not req_user.isalnum():
                client_socket.send("Username must be at least 3 alphanumeric characters.\n".encode('utf-8'))
                continue
            if len(req_pass) < 4:
                client_socket.send("Password must be at least 4 characters.\n".encode('utf-8'))
                continue

            # Task 3: Duplicate Login Prevention
            with clients_lock:
                if req_user in client_data and client_data[req_user]['status'] == 'online':
                    client_socket.send("DUPLICATE_ERROR".encode('utf-8'))
                    sec_log(f"Duplicate login attempt for '{req_user}' from {ip}")
                    continue

            # Verify credentials
            success, msg = authenticate_user(req_user, req_pass, ip)
            if success:
                username = req_user
                authenticated = True
                client_socket.send("AUTH_SUCCESS".encode('utf-8'))
            else:
                client_socket.send(f"AUTH_FAIL|{msg}".encode('utf-8'))

        # Register session
        with clients_lock:
            client_data[username] = {
                'socket': client_socket, 'ip': ip, 'port': port,
                'login_time': datetime.now().strftime('%H:%M:%S'), 'status': 'online'
            }
            
        broadcast(f"[SERVER] {username} has joined the secure chat.\n")
        broadcast_user_list()
        
        # Chat Loop
        while True:
            try:
                message = client_socket.recv(1024).decode('utf-8').strip()
                if not message:
                    break
                
                # Input Validation: Message size limit
                if len(message) > 500:
                    client_socket.send("[SERVER] Message too long (max 500 chars).\n".encode('utf-8'))
                    continue
                    
                with clients_lock:
                    server_stats['processed'] += 1

                if message == '/list':
                    broadcast_user_list()
                elif message.startswith('/msg '):
                    parts = message.split(' ', 2)
                    if len(parts) >= 3:
                        target_user, private_msg = parts[1], parts[2]
                        with clients_lock:
                            if target_user in client_data and client_data[target_user]['status'] == 'online':
                                server_stats['privates'] += 1
                                log_message(username, target_user, 'private', private_msg)
                                client_data[target_user]['socket'].send(f"[PRIVATE from {username}]: {private_msg}\n".encode('utf-8'))
                                client_socket.send(f"[PRIVATE to {target_user}]: {private_msg}\n".encode('utf-8'))
                            else:
                                client_socket.send(f"[SERVER] Error: User '{target_user}' offline.\n".encode('utf-8'))
                else:
                    log_message(username, 'ALL', 'broadcast', message)
                    broadcast(f"[{username}]: {message}\n", sender=username)
                    
            except socket.timeout:
                client_socket.send("[SERVER] Disconnected due to inactivity (2 mins).\n".encode('utf-8'))
                sec_log(f"Session timeout for '{username}'")
                break

    except Exception as e:
        pass
    finally:
        if username:
            with clients_lock:
                if username in client_data:
                    client_data[username]['status'] = 'offline'
            sec_log(f"User '{username}' logged out.")
            broadcast(f"[SERVER] {username} has left.\n")
            broadcast_user_list()
        client_socket.close()

def start_server():
    init_files()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"[*] Secure Chat Server listening on {HOST}:{PORT}")
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down secure server.")
    finally:
        server_socket.close()

if __name__ == '__main__':
    start_server()
