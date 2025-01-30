import pygame
import sys
import socket
import pickle
from multiprocessing import Process
import sysv_ipc

pygame.init() # Initialisation de Pygame

HOST = "127.0.0.1"  # Adresse du serveur
PORT = 6674         # Doit être le même que le serveur

# Création de la fenêtre
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 600 # Dimensions de la fenêtre
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Projet PPC")

class Color: # Couleurs
    whith = (255, 255, 255)
    black = (0, 0, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    gray = (200, 200, 200)


# Classes
class TrafficLight:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.state = Color.red  # Feu au rouge par défaut
        self.width = 20
        self.height = 50

    def toggle(self):
        """Changer l'état du feu."""
        self.state = Color.green if self.state == Color.red else Color.red

    def draw(self, screen):
        """Dessiner le feu de circulation."""
        # pygame.draw.rect(screen, Color.black, (self.x, self.y, self.width, self.height))
        pygame.draw.circle(screen, self.state, (self.x + self.width // 2, self.y + self.height // 2), self.width // 2)


class Car:
    def __init__(self, x, y, speed, direction):
        self.x = x
        self.y = y
        self.speed = speed
        self.direction = direction  # "horizontal" ou "vertical"
        self.width = 40 if direction == "horizontal" else 20
        self.height = 20 if direction == "horizontal" else 40

    def move(self):
        """Déplacer la voiture."""
        if self.direction == "horizontal":
            self.x += self.speed
        elif self.direction == "vertical":
            self.y += self.speed

        # Réapparaît de l'autre côté si elle sort de l'écran
        if self.x > SCREEN_WIDTH:
            self.x = -self.width
        if self.y > SCREEN_HEIGHT:
            self.y = -self.height

    def draw(self, screen):
        """Dessiner la voiture."""
        pygame.draw.rect(screen, Color.black, (self.x, self.y, self.width, self.height))

# Fonctions
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
    #---------------------------------------------
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
    # -----------------------------------------------

    # Création des objets
    Feux = [
        TrafficLight(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 140),  # Feu en haut
        TrafficLight(SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT // 2 - 100), # Feu à droite
        TrafficLight(SCREEN_WIDTH // 2 + 60, SCREEN_HEIGHT // 2 + 90),   # Feu en bas
        TrafficLight(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 50)   # Feu à gauche
    ]

    Roads = [
        [],
        [],
        [],
        []
    ]

    clock = pygame.time.Clock() # Gérer les FPS
    while True: # Boucle principale de l'affichage
        data = (None, None, None) # Réinitialisation de data
        try:
            # Appel non-bloquant avec blocking=False
            message, t = mq.receive(block=False)
            data = pickle.loads(message)
            print(data)
        except sysv_ipc.BusyError:
            pass             # Si aucune donnée n'est disponible, continuer la boucle sans bloquer

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                break

            # if event.type == pygame.KEYDOWN:
            #     if event.key == pygame.K_SPACE:
            #         # Changer l'état de tous les feux
            #         for feu in Feux:
            #             feu.toggle()

        # Mise à jour des objets
        if data[0]=='feu':
            position_feu = data[1]
            if data[2]==1:
                Feux[position_feu].state=Color.green
            else:
                Feux[position_feu].state=Color.red
        
        Roads[0].append(Car(100, SCREEN_HEIGHT // 2 - 10, 4, "horizontal"))
        Roads[1].append(Car(SCREEN_WIDTH // 2 + 10, 200, 2, "vertical"))

        # for car in Cars:
        #     car.move()

        SCREEN.fill(Color.whith) # Background

        # Dessiner les routes
        pygame.draw.rect(SCREEN, Color.gray, (SCREEN_WIDTH//2 - 50, 0, 100, SCREEN_HEIGHT))  # Route verticale
        pygame.draw.rect(SCREEN, Color.gray, (0, SCREEN_HEIGHT//2 - 50, SCREEN_WIDTH, 100))  # Route horizontale

        # Dessiner les feux de circulation
        for feu in Feux:
            feu.draw(SCREEN)

        # Dessiner les voitures
        for road in Roads:
            for car in road:
                car.draw(SCREEN)

        pygame.display.flip() # Mettre à jour le display
        clock.tick(60) # 60 FPS

    p_reception.join()
    client_socket.close()
    sys.exit()