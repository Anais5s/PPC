# client
import socket
import pickle
 
HOST = "localhost"
PORT = 6666
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    client_socket.connect((HOST, PORT))
    while True:
        data = client_socket.recv(1024)  # Taille du buffer
        message = pickle.loads(data)  # Désérialisation correcte
        print(message)
