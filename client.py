import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import sys

SERVER_IP = '10.0.0.1'
SERVER_PORT = 5000

class ChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TCP Chat Application")
        self.root.geometry("600x500")
        
        self.client_socket = None
        self.username = ""
        self.running = False
        
        # Build the GUI Frames
        self.build_login_frame()
        self.build_chat_frame()
        
        # Start by showing Login, hiding Chat
        self.chat_frame.pack_forget()
        self.login_frame.pack(fill=tk.BOTH, expand=True)

    def build_login_frame(self):
        """Creates the Login Window UI"""
        self.login_frame = tk.Frame(self.root, pady=100)
        
        lbl_title = tk.Label(self.login_frame, text="Welcome to Chat", font=("Arial", 18, "bold"))
        lbl_title.pack(pady=10)
        
        lbl_user = tk.Label(self.login_frame, text="Username:")
        lbl_user.pack()
        self.entry_username = tk.Entry(self.login_frame, font=("Arial", 12))
        self.entry_username.pack(pady=5)
        
        # Connect Button triggers the network connection
        btn_connect = tk.Button(self.login_frame, text="Connect", command=self.connect_server, bg="#4CAF50", fg="white", width=15)
        btn_connect.pack(pady=20)

    def build_chat_frame(self):
        """Creates the Main Chat Window UI"""
        self.chat_frame = tk.Frame(self.root)
        
        # Top Status Bar
        self.lbl_status = tk.Label(self.chat_frame, text="Not Connected", fg="red", font=("Arial", 10, "italic"))
        self.lbl_status.pack(side=tk.TOP, fill=tk.X)
        
        # Split the screen into Left (Chat) and Right (Users)
        main_pane = tk.PanedWindow(self.chat_frame, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left side: Scrollable Chat history
        left_frame = tk.Frame(main_pane)
        self.text_area = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        main_pane.add(left_frame, width=420)
        
        # Right side: Online users listbox
        right_frame = tk.Frame(main_pane)
        lbl_users = tk.Label(right_frame, text="Online Users:")
        lbl_users.pack()
        self.listbox_users = tk.Listbox(right_frame)
        self.listbox_users.pack(fill=tk.BOTH, expand=True)
        
        btn_disconnect = tk.Button(right_frame, text="Disconnect", command=self.disconnect, bg="#f44336", fg="white")
        btn_disconnect.pack(fill=tk.X, pady=5)
        main_pane.add(right_frame)
        
        # Bottom area: Message input
        bottom_frame = tk.Frame(self.chat_frame)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        lbl_msg = tk.Label(bottom_frame, text="Message:")
        lbl_msg.pack(side=tk.LEFT)
        
        self.entry_msg = tk.Entry(bottom_frame, font=("Arial", 12))
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # Bind the 'Enter' key on keyboard to send message
        self.entry_msg.bind("<Return>", lambda event: self.send_message()) 
        
        btn_send = tk.Button(bottom_frame, text="Send", command=self.send_message, bg="#2196F3", fg="white")
        btn_send.pack(side=tk.LEFT)
        
        btn_private = tk.Button(bottom_frame, text="Private Msg", command=self.prepare_private_msg)
        btn_private.pack(side=tk.LEFT, padx=5)

    def display_message(self, message):
        """Safely inserts text into the chat history"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.see(tk.END) # Auto-scroll to bottom
        self.text_area.config(state=tk.DISABLED)

    def connect_server(self):
        """Triggered by Login button. Establishes TCP connection."""
        user = self.entry_username.get().strip()
        if not user:
            messagebox.showerror("Error", "Username cannot be empty!")
            return
            
        self.username = user
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            
            # Receive server prompt and send username
            self.client_socket.recv(1024)
            self.client_socket.send(self.username.encode('utf-8'))
            self.running = True
            
            # Switch GUI from Login to Chat
            self.login_frame.pack_forget()
            self.chat_frame.pack(fill=tk.BOTH, expand=True)
            self.lbl_status.config(text=f"Connected to Server as '{self.username}'", fg="green")
            
            # START THE BACKGROUND THREAD
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server.\n{e}")

    def receive_messages(self):
        """Background thread function that listens to the network."""
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                
                # Check if this is the hidden list command from our updated server
                if message.startswith("/USERLIST"):
                    users_str = message.split(" ", 1)[1].strip()
                    user_list = users_str.split(",") if users_str else []
                    
                    # Schedule GUI update safely in the main thread
                    self.root.after(0, self.update_user_list, user_list)
                else:
                    self.root.after(0, self.display_message, message.strip())
                    
            except Exception as e:
                break
        
        if self.running:
            self.root.after(0, self.handle_server_disconnect)

    def update_user_list(self, user_list):
        """Refreshes the online users sidebar."""
        self.listbox_users.delete(0, tk.END)
        for user in user_list:
            if user == self.username:
                self.listbox_users.insert(tk.END, f"{user} (You)")
            else:
                self.listbox_users.insert(tk.END, user)

    def handle_server_disconnect(self):
        self.display_message("[!] Lost connection to server.")
        self.lbl_status.config(text="Disconnected", fg="red")
        self.running = False

    def prepare_private_msg(self):
        """Helper to format a private message based on listbox selection."""
        selected = self.listbox_users.curselection()
        if not selected:
            messagebox.showinfo("Private Message", "Select a user from the Online Users list first!")
            return
        
        target = self.listbox_users.get(selected[0]).replace(" (You)", "")
        if target == self.username:
            messagebox.showwarning("Warning", "You cannot private message yourself.")
            return
            
        # Autofill the input box with the /msg command
        self.entry_msg.delete(0, tk.END)
        self.entry_msg.insert(0, f"/msg {target} ")
        self.entry_msg.focus()

    def send_message(self):
        """Sends data to server. Triggered by Send button or Enter key."""
        msg = self.entry_msg.get().strip()
        if msg and self.running:
            try:
                self.client_socket.send(msg.encode('utf-8'))
                self.entry_msg.delete(0, tk.END)
                
                # Because the server doesn't echo broadcasts back to the sender,
                # we must print our own broadcast locally so we can see it.
                if not msg.startswith("/msg ") and not msg == "/list":
                    self.display_message(f"[You]: {msg}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send message: {e}")

    def disconnect(self):
        """Cleans up sockets and destroys the window."""
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.root.quit()

if __name__ == "__main__":
    # Create the main Tkinter window
    root = tk.Tk()
    app = ChatClientGUI(root)
    # Ensure background threads die if the user clicks the 'X' button
    root.protocol("WM_DELETE_WINDOW", app.disconnect)
    root.mainloop()
