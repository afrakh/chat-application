import socket
import threading

# Server settings
HOST = '127.0.0.1'  # Localhost
PORT = 55000        # Port number

# Create socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []
nicknames = []

def broadcast(message, exclude_client=None):
    """Send message to all clients except the excluded one (if any)."""
    for client in clients:
        if client != exclude_client:
            try:
                client.send(message)
            except:
                if client in clients:
                    index = clients.index(client)
                    client.close()
                    clients.remove(client)
                    nickname = nicknames[index]
                    nicknames.remove(nickname)
                    print(f"{nickname} disconnected.")

def handle(client):
    """Handle messages from each client."""
    while True:
        try:
            message = client.recv(1024).decode('utf-8')
            if not message:
                break

            # Handle typing indicator
            if message.startswith("TYPING:"):
                name = message.split(":", 1)[1]
                broadcast(f"TYPING_EVENT:{name}".encode('utf-8'), client)
                continue

            # Broadcast regular chat messages
            broadcast(message.encode("utf-8"))

        except:
            if client in clients:
                index = clients.index(client)
                clients.remove(client)
                nickname = nicknames[index]
                nicknames.remove(nickname)
                broadcast(f"{nickname} left the chat!".encode('utf-8'))
                print(f"{nickname} disconnected.")
            break

def server_send_messages():
    """Allow server admin to send messages manually via console."""
    while True:
        msg = input("")  # type message in terminal
        if msg.lower() == "/exit":
            print("Shutting down server...")
            for c in clients:
                c.close()
            server.close()
            break
        elif msg.strip():
            broadcast(f"SERVER: {msg}".encode('utf-8'))
            print(f"[Server sent]: {msg}")

def receive():
    """Accept new connections."""
    print("Server is running and waiting for connections...")
    while True:
        try:
            client, address = server.accept()
            print(f"Connected with {str(address)}")

            client.send("NICK".encode('utf-8'))
            nickname = client.recv(1024).decode('utf-8')
            nicknames.append(nickname)
            clients.append(client)

            print(f"Nickname of the client is {nickname}")

            broadcast(f"{nickname} joined the chat!".encode('utf-8'))
            client.send("Connected to the server!".encode('utf-8'))

            thread = threading.Thread(target=handle, args=(client,))
            thread.start()
        except OSError:
            break

# Start both threads
threading.Thread(target=receive, daemon=True).start()
server_send_messages()
