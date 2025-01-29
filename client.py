import socket
import pickle

HOST = "192.168.221.33"  # Adresse du serveur
PORT = 6666         # Doit être le même que le serveur

# Création du socket client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client_socket.connect((HOST, PORT))
    print("Client connecté")
except Exception as e:
    print(f"Connexion au serveur échouée : {e}")
finally:
    client_socket.close()

while True:
    try:
        data = client_socket.recv(1024)  # Taille maximale des données reçues
        
        if not data:
            break  # Si aucune donnée, on arrête la boucle
        
        message = pickle.loads(data)  # Désérialisation du message reçu
        print(f"Message reçu du serveur: {message}")

    except Exception as e:
        print(f"Erreur de réception : {e}")
        break  # Sortir en cas d'erreur

print("Connexion fermée par le serveur.")
client_socket.close() # Ferme la connexion après l'envoi