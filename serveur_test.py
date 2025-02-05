# serveur
import socket
import pickle
import time

HOST = "127.0.0.1"  # Adresse locale
PORT = 6666         # Port d'écoute

# Liste des messages à envoyer au fil du temps
messages = [
    ('feu', 0, 1),
    ('creation_normal', 0),
    ('passage', 0, 1),
    ('creation_normal', 0),
    ('creation_normal', 0),
    ('creation_priorite', 0),
    ('creation_normal', 0),
    ('creation_priorite', 0),
    ('passage', 0, 3),
    ('passage', 0, 2),
    ('fin')
]

# Création du socket serveur
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen(1) # On accepte un seul client pour l'instant
    print(f"Serveur en attente de connexion sur {HOST}:{PORT}...")
    conn, address = server_socket.accept() # Accepter une connexion unique
    print(f"Client connecté : {address}")
    conn.setblocking(True)

    # Envoi des messages à intervalle régulier
    for message in messages:
        data = pickle.dumps(message)  # Sérialisation du message
        conn.sendall(data)  # Envoi au client
        print(f"Message envoyé: {message}")

        time.sleep(2)  # Pause de 2 secondes entre chaque envoi

    server_socket.close()  # Fermer la connexion après avoir envoyé tous les messages
    print("Connexion fermée.")