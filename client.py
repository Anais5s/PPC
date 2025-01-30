import socket
import pickle
from multiprocessing import Process
import sysv_ipc
import time

# '0.0.0.0' pour accepter les connexions de toutes les interfaces
HOST = "127.0.0.1"  # Adresse du serveur
PORT = 6666         # Doit être le même que le serveur

def reception(client_socket):
    while True:
        try:
            data = client_socket.recv(1024)  # Taille maximale des données reçues
            
            if not data:
                break  # Si aucune donnée, on arrête la boucle
            
            message = pickle.loads(data)  # Désérialisation du message reçu
            print(f"Message reçu du serveur: {message}")
            mq.send(data)

        except Exception as e:
            print(f"Erreur de réception : {e}")
            break  # Sortir en cas d'erreu

    print("Connexion fermée par le serveur.")
    client_socket.close() # Ferme la connexion après l'envoi

if __name__ == "__main__":
    # Création du socket client
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((HOST, PORT))
        print("Client connecté")
    except Exception as e:
        print(f"Connexion au serveur échouée : {e}")
        client_socket.close()

    mqs=[]
    base_cle = 128
    mq = sysv_ipc.MessageQueue(base_cle, sysv_ipc.IPC_CREAT)
    #mq.remove()

    p_reception = Process(target=reception, args=(client_socket,))
    p_reception.start()

    # Affichage
    while True:
        try:
            # Appel non-bloquant avec blocking=False
            message, t = mq.receive(block=False)
            print(pickle.loads(message))
        except sysv_ipc.BusyError:
            # Si aucune donnée n'est disponible, continuer la boucle sans bloquer
            pass
        print("-" * 8)
        time.sleep(1)

    p_reception.join()