import socket
import select
import pickle
import time

# '0.0.0.0' pour accepter les connexions de toutes les interfaces
HOST = "127.0.0.1"  # Adresse du serveur
PORT = 6666         # Doit être le même que le serveur

if __name__ == "__main__":
    # Création du socket client
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect((HOST, PORT))
            client_socket.setblocking(False) # Mode non bloquant
            print("Client connecté")
        except Exception as e:
            print(f"Connexion au serveur échouée : {e}")
            client_socket.close()

        # Affichage
        while True:
            try:
                # Vérifie si des données sont disponibles
                readable, _, _ = select.select([client_socket], [], [], 0.1)  # Timeout de 100 ms

                if readable:
                    data = client_socket.recv(1024)  # Taille maximale des données reçues

                    if not data:
                        print("Le serveur a fermé la connexion.")
                        break

                    message = pickle.loads(data)  # Désérialisation du message reçu
                    print(f"Message reçu: {message}")
                    print("-" * 8)

                print("Draw")
                time.sleep(1)  # Réduction de la charge CPU (facultatif)

            except BlockingIOError:
                # Aucune donnée disponible pour l'instant, on continue la boucle
                pass

            except Exception as e:
                print(f"Erreur de réception : {e}")
                break  # Sortir en cas d'erreur critique

    print("Connexion fermée par le serveur.")
    client_socket.close() # Inutile avec le gestionnaire de contexte