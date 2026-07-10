import socket
import threading
from datetime import datetime
import csv
import os

HOST = '10.0.0.1'
PORT = 5000

clients_lock = threading.RLock()
client_data = {} 
server_stats = {'processed': 0, 'broadcasts': 0, 'privates': 0}
CHAT_FILE = 'chat_history.csv'

def init_csv():
    if not os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'sender', 'receiver', 'message_type', 'message'])

def log_message(sender, receiver, msg_type, message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with clients_lock:
        with open(CHAT_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, sender, receiver, msg_type, message])

def get_last_five_messages(username):
    history = []
    try:
        with open(CHAT_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['sender'] == username or row['receiver'] == username or row['receiver'] == 'ALL':
                    msg_format = f"[{row['timestamp']}] {row['sender']} -> {row['receiver']}: {row['message']}"
                    history.append(msg_format)
    except FileNotFoundError:
        pass
    return history[-5:]

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
    """New function for GUI: Sends the updated user list to everyone automatically"""
    with clients_lock:
        online_users = [u for u, d in client_data.items() if d['status'] == 'online']
    
    # Send a formatted string that the GUI can intercept and parse
    list_str = "/USERLIST " + ",".join(online_users)
    broadcast(list_str + "\n")

def handle_client(client_socket, client_address):
    ip, port = client_address
    username = ""
    
    try:
        client_socket.send("Enter Username: ".encode('utf-8'))
        username = client_socket.recv(1024).decode('utf-8').strip()
        
        with clients_lock:
            client_data[username] = {
                'socket': client_socket, 'ip': ip, 'port': port,
                'login_time': datetime.now().strftime('%H:%M:%S'), 'status': 'online'
            }
            
        print(f"[*] {username} connected from {ip}:{port}")
        broadcast(f"[SERVER] {username} has joined the chat.\n")
        
        # Trigger the automatic GUI list update for everyone
        broadcast_user_list()
        
        last_msgs = get_last_five_messages(username)
        if last_msgs:
            client_socket.send("--- Last 5 Messages ---\n".encode('utf-8'))
            for m in last_msgs:
                client_socket.send((m + "\n").encode('utf-8'))
            client_socket.send("-----------------------\n".encode('utf-8'))

        while True:
            message = client_socket.recv(1024).decode('utf-8').strip()
            if not message:
                break
                
            with clients_lock:
                server_stats['processed'] += 1

            if message == '/list':
                with clients_lock:
                    online_users = [u for u, d in client_data.items() if d['status'] == 'online']
                user_list = "/USERLIST " + ",".join(online_users)
                client_socket.send((user_list + "\n").encode('utf-8'))
                
            elif message.startswith('/msg '):
                parts = message.split(' ', 2)
                if len(parts) >= 3:
                    target_user = parts[1]
                    private_msg = parts[2]
                    
                    with clients_lock:
                        if target_user in client_data and client_data[target_user]['status'] == 'online':
                            server_stats['privates'] += 1
                            log_message(username, target_user, 'private', private_msg)
                            
                            formatted_msg = f"[PRIVATE from {username}]: {private_msg}"
                            client_data[target_user]['socket'].send((formatted_msg + "\n").encode('utf-8'))
                            client_socket.send(f"[PRIVATE to {target_user}]: {private_msg}\n".encode('utf-8'))
                        else:
                            client_socket.send(f"[SERVER] Error: User '{target_user}' not found or offline.\n".encode('utf-8'))
                else:
                    client_socket.send("[SERVER] Usage: /msg <username> <message>\n".encode('utf-8'))
            
            else:
                log_message(username, 'ALL', 'broadcast', message)
                formatted_msg = f"[{username}]: {message}"
                broadcast(formatted_msg + "\n", sender=username)

    except Exception as e:
        pass
    finally:
        if username:
            with clients_lock:
                if username in client_data:
                    client_data[username]['status'] = 'offline'
            
            print(f"[-] {username} disconnected.")
            broadcast(f"[SERVER] {username} has left the chat.\n")
            
            # Update everyone's GUI listbox when someone leaves
            broadcast_user_list()
            
        client_socket.close()

def start_server():
    init_csv()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)
    print(f"[*] GUI-Ready Chat Server listening on {HOST}:{PORT}")
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\n[*] Shutting down server.")
    finally:
        server_socket.close()

if __name__ == '__main__':
    start_server()
