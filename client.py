import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import sys

SERVER_IP = '10.0.0.1'
SERVER_PORT = 5000

class SecureChatClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure TCP Chat Application")
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
        """Creates the Login Window UI with Password Protection"""
        self.login_frame = tk.Frame(self.root, pady=80)
        
        lbl_title = tk.Label(self.login_frame, text="Secure Chat Login", font=("Arial", 18, "bold"))
        lbl_title.pack(pady=10)
        
        lbl_user = tk.Label(self.login_frame, text="Username:")
        lbl_user.pack()
        self.entry_username = tk.Entry(self.login_frame, font=("Arial", 12))
        self.entry_username.pack(pady=5)
        
        lbl_pass = tk.Label(self.login_frame, text="Password:")
        lbl_pass.pack()
        # show="*" masks the password input
        self.entry_password = tk.Entry(self.login_frame, font=("Arial", 12), show="*") 
        self.entry_password.pack(pady=5)
        
        btn_connect = tk.Button(self.login_frame, text="Secure Login", command=self.connect_server, bg="#4CAF50", fg="white", width=15)
        btn_connect.pack(pady=20)

    def build_chat_frame(self):
        """Creates the Main Chat Window UI"""
        self.chat_frame = tk.Frame(self.root)
        
        self.lbl_status = tk.Label(self.chat_frame, text="Not Connected", fg="red", font=("Arial", 10, "italic"))
        self.lbl_status.pack(side=tk.TOP, fill=tk.X)
        
        main_pane = tk.PanedWindow(self.chat_frame, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        left_frame = tk.Frame(main_pane)
        self.text_area = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        main_pane.add(left_frame, width=420)
        
        right_frame = tk.Frame(main_pane)
        lbl_users = tk.Label(right_frame, text="Online Users:")
        lbl_users.pack()
        self.listbox_users = tk.Listbox(right_frame)
        self.listbox_users.pack(fill=tk.BOTH, expand=True)
        
        btn_disconnect = tk.Button(right_frame, text="Logout", command=self.disconnect, bg="#f44336", fg="white")
        btn_disconnect.pack(fill=tk.X, pady=5)
        main_pane.add(right_frame)
        
        bottom_frame = tk.Frame(self.chat_frame)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        
        lbl_msg = tk.Label(bottom_frame, text="Message:")
        lbl_msg.pack(side=tk.LEFT)
        
        self.entry_msg = tk.Entry(bottom_frame, font=("Arial", 12))
        self.entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.entry_msg.bind("<Return>", lambda event: self.send_message()) 
        
        btn_send = tk.Button(bottom_frame, text="Send", command=self.send_message, bg="#2196F3", fg="white")
        btn_send.pack(side=tk.LEFT)
        
        btn_private = tk.Button(bottom_frame, text="Private Msg", command=self.prepare_private_msg)
        btn_private.pack(side=tk.LEFT, padx=5)

    def display_message(self, message):
        """Safely inserts text into the chat history"""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.see(tk.END)
        self.text_area.config(state=tk.DISABLED)

    def connect_server(self):
        """Handles the Secure Authentication Handshake"""
        user = self.entry_username.get().strip()
        password = self.entry_password.get().strip()
        
        # Client-side input validation
        if not user or not password:
            messagebox.showerror("Validation Error", "Username and Password cannot be empty!")
            return
            
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((SERVER_IP, SERVER_PORT))
            
            # Wait for server to request authentication
            req = self.client_socket.recv(1024).decode('utf-8')
            if req == "AUTH_REQ":
                # Send credentials
                auth_payload = f"/auth {user} {password}"
                self.client_socket.send(auth_payload.encode('utf-8'))
                
                # Await server judgment
                resp = self.client_socket.recv(1024).decode('utf-8')
                
                if resp == "AUTH_SUCCESS":
                    self.username = user
                    self.running = True
                    
                    self.login_frame.pack_forget()
                    self.chat_frame.pack(fill=tk.BOTH, expand=True)
                    self.lbl_status.config(text=f"Securely Connected as '{self.username}'", fg="green")
                    
                    receive_thread = threading.Thread(target=self.receive_messages)
                    receive_thread.daemon = True
                    receive_thread.start()
                    
                elif resp == "DUPLICATE_ERROR":
                    messagebox.showerror("Security Alert", "This user is already logged in!")
                    self.client_socket.close()
                elif resp.startswith("AUTH_FAIL|"):
                    msg = resp.split('|')[1]
                    messagebox.showerror("Authentication Failed", msg)
                    self.client_socket.close()
                else:
                    messagebox.showerror("Validation Error", resp)
                    self.client_socket.close()
                    
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server.\n{e}")

    def receive_messages(self):
        """Listens for incoming data or forced timeouts."""
        while self.running:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                
                if message.startswith("/USERLIST"):
                    users_str = message.split(" ", 1)[1].strip()
                    user_list = users_str.split(",") if users_str else []
                    self.root.after(0, self.update_user_list, user_list)
                else:
                    self.root.after(0, self.display_message, message.strip())
                    
            except Exception as e:
                break
        
        if self.running:
            self.root.after(0, self.handle_server_disconnect)

    def update_user_list(self, user_list):
        self.listbox_users.delete(0, tk.END)
        for user in user_list:
            if user == self.username:
                self.listbox_users.insert(tk.END, f"{user} (You)")
            else:
                self.listbox_users.insert(tk.END, user)

    def handle_server_disconnect(self):
        self.display_message("[!] Secure session terminated.")
        self.lbl_status.config(text="Disconnected", fg="red")
        self.running = False
        self.listbox_users.delete(0, tk.END) # Clear users list

    def prepare_private_msg(self):
        selected = self.listbox_users.curselection()
        if not selected:
            messagebox.showinfo("Private Message", "Select a user from the Online Users list first!")
            return
        
        target = self.listbox_users.get(selected[0]).replace(" (You)", "")
        if target == self.username:
            messagebox.showwarning("Warning", "You cannot private message yourself.")
            return
            
        self.entry_msg.delete(0, tk.END)
        self.entry_msg.insert(0, f"/msg {target} ")
        self.entry_msg.focus()

    def send_message(self):
        msg = self.entry_msg.get().strip()
        if msg and self.running:
            if len(msg) > 500:
                messagebox.showwarning("Warning", "Message exceeds 500 character limit.")
                return

            try:
                self.client_socket.send(msg.encode('utf-8'))
                self.entry_msg.delete(0, tk.END)
                
                if not msg.startswith("/msg ") and not msg == "/list":
                    self.display_message(f"[You]: {msg}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send message: {e}")

    def disconnect(self):
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = SecureChatClientGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.disconnect)
    root.mainloop()
