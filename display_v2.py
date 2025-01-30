import pygame
import sys
import socket
import pickle
from multiprocessing import Process
import sysv_ipc

HOST = "127.0.0.1"  # Adresse du serveur
PORT = 6666         # Doit être le même que le serveur

# ---------- Settings ----------
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 600 # Dimensions de la fenêtre
CAR_SPEED = 1
CAR_WIDTH = 40
CAR_HEIGHT = 20
SPACE_BETWEEN_CAR = 10

class Color: # Couleurs
    whith = (255, 255, 255)
    black = (0, 0, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    gray = (200, 200, 200)
# ------------------------------

NORTH = 0
EAST = 1
SOUTH = 2
WEST = 3

class north_points:
    x_in = SCREEN_WIDTH//2-25
    y_in = 50
    speed = CAR_SPEED
    stop_y_in = SCREEN_HEIGHT//2-100 # Point d'entrée du carrefour
    y_out = stop_y_in # Point de sortie du carrefour (considéré comme égal au point d'entrée)
    stop_y_out = y_in # Point de sortie du dessin (considéré comme égal au point d'entrée)

class east_points:
    x_in = SCREEN_WIDTH-50
    y_in = SCREEN_HEIGHT//2-25
    speed = CAR_SPEED
    stop_x_in = SCREEN_WIDTH//2+100
    x_out = stop_x_in
    stop_x_out = x_in

class south_points:
    x_in = SCREEN_WIDTH//2+25
    y_in = SCREEN_HEIGHT-50
    speed = CAR_SPEED
    stop_y_in = SCREEN_HEIGHT//2+100
    y_out = stop_y_in
    stop_y_out = y_in

class west_points:
    x_in = 50
    y_in = SCREEN_HEIGHT//2+25
    speed = CAR_SPEED
    stop_x_in = SCREEN_WIDTH//2-100
    x_out = stop_x_in
    stop_x_out = x_in

class center_points:
    x = SCREEN_WIDTH//2
    y = SCREEN_HEIGHT//2

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
    def __init__(self, x, y, speed, width, height, source):
        self.x = x
        self.y = y
        self.speed = speed
        # Initialiser selon le point de départ
        self.width = width
        self.height = height
        self.source = source
        self.destination = -1

    def move_up(self):
        """Déplacer la voiture en haut"""
        self.y -= self.speed
        self.width = CAR_HEIGHT
        self.height = CAR_WIDTH

    def move_down(self):
        self.y += self.speed
        """Déplacer la voiture en bas"""
        self.width = CAR_HEIGHT
        self.height = CAR_WIDTH
    
    def move_right(self):
        self.x += self.speed
        """Déplacer la voiture à droite"""
        self.width = CAR_WIDTH
        self.height = CAR_HEIGHT

    def move_left(self):
        """Déplacer la voiture à gauche"""
        self.x -= self.speed
        self.width = CAR_WIDTH
        self.height = CAR_HEIGHT
    def draw(self, screen):
        """Dessiner la voiture."""
        pygame.draw.rect(screen, Color.black, (self.x-self.width//2, self.y-self.height//2, self.width, self.height))

class Road:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = Color.gray
        self.cars_in = []
        self.cars_out = []
    
    def add_in(self, car):
        self.cars_in.append(car)

    def add_out(self, car):
        self.cars_out.append(car)

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x-self.width//2, self.y-self.height//2, self.width, self.height))

def reception(client_socket):
    while True:
        try:
            data = client_socket.recv(1024)  # Taille maximale des données reçues
            if not data: break  # Si aucune donnée, on arrête la boucle
            
            message = pickle.loads(data)  # Désérialisation du message reçu
            print(f"Message reçu du serveur: {message}")
            mq.send(data)

        except Exception as e:
            print(f"Erreur de réception : {e}")
            break  # Sortir en cas d'erreu

    print("Connexion fermée par le serveur.")
    client_socket.close() # Ferme la connexion après l'envoi

# TESTS DISPLAY
# data = ('feu', 1, 1)
# data = ('création', 0)
# data = ('passage', 1, 2)

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

    p_reception = Process(target=reception, args=(client_socket,))
    p_reception.start()

    # Initialisation de Pygame
    pygame.init() 
    SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)) # Création de la fenêtre
    pygame.display.set_caption("Projet PPC") # Titre de la fenêtre
    clock = pygame.time.Clock() # Gérer les FPS

    # Création des objets
    Feux = [
        TrafficLight(SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2 - 140),  # Feu en haut
        TrafficLight(SCREEN_WIDTH // 2 + 100, SCREEN_HEIGHT // 2 - 100), # Feu à droite
        TrafficLight(SCREEN_WIDTH // 2 + 60, SCREEN_HEIGHT // 2 + 90),   # Feu en bas
        TrafficLight(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 50)   # Feu à gauche
    ]
    road_north = Road(SCREEN_WIDTH//2, SCREEN_HEIGHT//4, 100, SCREEN_HEIGHT//2)
    road_east = Road(3*SCREEN_WIDTH//4, SCREEN_HEIGHT//2, SCREEN_WIDTH//2, 100)
    road_south = Road(SCREEN_WIDTH//2, 3*SCREEN_HEIGHT//4, 100, SCREEN_HEIGHT//2)
    road_west = Road(SCREEN_WIDTH//4, SCREEN_HEIGHT//2, SCREEN_WIDTH//2, 100)
    Crossroad = []

    # Boucle principale pour l'affichage
    running = True
    while running: 
        # Récupération des données TCP (message passing)
        data = (None, None, None) # Réinitialisation de data
        try:
            # Appel non-bloquant avec blocking=False
            message, t = mq.receive(block=False)
            data = pickle.loads(message)
            print(f"Étape en cours à afficher : {data}")
        except sysv_ipc.BusyError:
            pass # Si aucune donnée n'est disponible, continuer la boucle sans bloquer

        # Si l'utilisateur quitte l'interface
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Initialise les voitures sur les routes
        if data[0]=='création': 
            if data[1]==NORTH: # Route au nord
                space = len(road_north.cars_in)*(CAR_WIDTH+SPACE_BETWEEN_CAR)
                road_north.add_in(Car(north_points.x_in, north_points.y_in-space, north_points.speed, CAR_HEIGHT, CAR_WIDTH, NORTH))
            elif data[1]==EAST: # Route au nord
                space = len(road_east.cars_in)*(CAR_WIDTH+SPACE_BETWEEN_CAR)
                road_east.add_in(Car(east_points.x_in+space, east_points.y_in, east_points.speed, CAR_WIDTH, CAR_HEIGHT, EAST))
            elif data[1]==SOUTH: # Route au nord
                space = len(road_south.cars_in)*(CAR_WIDTH+SPACE_BETWEEN_CAR)
                road_south.add_in(Car(south_points.x_in, south_points.y_in+space, south_points.speed, CAR_HEIGHT, CAR_WIDTH, SOUTH))
            elif data[1]==WEST: # Route au nord
                space = len(road_west.cars_in)*(CAR_WIDTH+SPACE_BETWEEN_CAR)
                road_west.add_in(Car(west_points.x_in-space, west_points.y_in, west_points.speed, CAR_WIDTH, CAR_HEIGHT, WEST))

        # Affichage
        SCREEN.fill(Color.whith) # Mise à jour du background

        for feu in Feux: feu.draw(SCREEN)

        road_north.draw(SCREEN)
        road_east.draw(SCREEN)
        road_south.draw(SCREEN)
        road_west.draw(SCREEN)

        for cars in road_north.cars_in: cars.draw(SCREEN)
        for cars in road_east.cars_in: cars.draw(SCREEN)
        for cars in road_south.cars_in: cars.draw(SCREEN)
        for cars in road_west.cars_in: cars.draw(SCREEN)

        for cars in road_north.cars_out: cars.draw(SCREEN)
        for cars in road_east.cars_out: cars.draw(SCREEN)
        for cars in road_south.cars_out: cars.draw(SCREEN)
        for cars in road_west.cars_out: cars.draw(SCREEN)

        for cars in Crossroad: cars.draw(SCREEN)

        pygame.display.flip() # Mettre à jour le display
        clock.tick(120) # 120 FPS

        # Mise à jour des feux
        if data[0]=='feu':
            position_feu = data[1]
            if data[2]==1:
                Feux[position_feu].state=Color.green
            else:
                Feux[position_feu].state=Color.red

        # Mise à jour des voitures
        for i in range(len(road_north.cars_in)):
            cars = road_north.cars_in[i]
            space = i*(CAR_WIDTH+SPACE_BETWEEN_CAR)
            if cars.y < north_points.stop_y_in-space-1:
                cars.move_down()

        for i in range(len(road_east.cars_in)):
            cars = road_east.cars_in[i]
            space = i*(CAR_WIDTH+SPACE_BETWEEN_CAR)
            if cars.x > east_points.stop_x_in+space:
                cars.move_left()

        for i in range(len(road_south.cars_in)):
            cars = road_south.cars_in[i]
            space = i*(CAR_WIDTH+SPACE_BETWEEN_CAR)
            if cars.y > south_points.stop_y_in+space:
                cars.move_up()

        for i in range(len(road_west.cars_in)):
            cars = road_west.cars_in[i]
            space = i*(CAR_WIDTH+SPACE_BETWEEN_CAR)
            if cars.x < west_points.stop_x_in-space:
                cars.move_right()

        for cars in road_north.cars_out:
            cars.move_up()
            if cars.y < north_points.stop_y_out:
                road_north.cars_out.remove(cars)
        
        for cars in road_east.cars_out:
            cars.move_right()
            if cars.x > east_points.stop_x_out:
                road_east.cars_out.remove(cars)

        for cars in road_south.cars_out:
            cars.move_down()
            if cars.y > south_points.stop_y_out:
                road_south.cars_out.remove(cars)

        for cars in road_west.cars_out:
            cars.move_left()
            if cars.x < west_points.stop_x_out:
                road_west.cars_out.remove(cars)

        if data[0]=='passage': # !!! Ne pas oublier de retirer "and len(Crossroad)<1" (uniquement pour les tests) !!!
            if data[1]==NORTH and len(road_north.cars_in)!=0:  # La dernière condition est inutile car ce n'est pas censé arriver
                cars = road_north.cars_in.pop(0) # Sélectionne la première voiture de la file
                cars.destination = data[2]
                Crossroad.append(cars) # Récupère la voiture qui s'apprête à traverser
            if data[1]==EAST and len(road_east.cars_in)!=0:
                cars = road_east.cars_in.pop(0)
                cars.destination = data[2]
                Crossroad.append(cars)
            if data[1]==SOUTH and len(road_south.cars_in)!=0:
                cars = road_south.cars_in.pop(0)
                cars.destination = data[2]
                Crossroad.append(cars)
            if data[1]==WEST and len(road_west.cars_in)!=0:
                cars = road_west.cars_in.pop(0)
                cars.destination = data[2]
                Crossroad.append(cars)

        for cars in Crossroad:
            # Source = NORTH
            if cars.source==NORTH:
                if cars.destination==WEST:
                    if cars.y < center_points.y-25:
                        cars.move_down()
                    else:
                        cars.move_left()
                        if cars.x < west_points.x_out:
                            road_west.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==SOUTH:
                    cars.move_down()
                    if cars.y > south_points.y_out:
                        road_south.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==EAST:
                    if cars.y < center_points.y+25:
                        cars.move_down()
                    else:
                        cars.move_right()
                        if cars.x > east_points.x_out:
                            road_east.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
            # Source = EAST
            if cars.source==EAST:
                if cars.destination==NORTH:
                    if cars.x > center_points.x+25:
                        cars.move_left()
                    else:
                        cars.move_up()
                        if cars.y < north_points.y_out:
                            road_north.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==WEST:
                    cars.move_left()
                    if cars.x < west_points.x_out:
                        road_west.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==SOUTH:
                    if cars.x > center_points.x-25:
                        cars.move_left()
                    else:
                        cars.move_down()
                        if cars.y > south_points.y_out:
                            road_south.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
            # Source = SOUTH
            if cars.source==SOUTH:
                if cars.destination==EAST:
                    if cars.y > center_points.y+25:
                        cars.move_up()
                    else:
                        cars.move_right()
                        if cars.x > east_points.x_out:
                            road_east.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==NORTH:
                    cars.move_up()
                    if cars.y < north_points.y_out:
                        road_north.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==WEST:
                    if cars.y > center_points.y-25:
                        cars.move_up()
                    else:
                        cars.move_left()
                        if cars.x < west_points.x_out:
                            road_west.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
            # Source = WEST
            if cars.source==WEST:
                if cars.destination==SOUTH:
                    if cars.x < center_points.x-25:
                        cars.move_right()
                    else:
                        cars.move_down()
                        if cars.y > south_points.y_out:
                            road_south.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==EAST:
                    cars.move_right()
                    if cars.x > east_points.x_out:
                        road_east.cars_out.append(Crossroad.pop(Crossroad.index(cars)))
                if cars.destination==NORTH:
                    if cars.x < center_points.x+25:
                        cars.move_right()
                    else:
                        cars.move_up()
                        if cars.y < north_points.y_out:
                            road_north.cars_out.append(Crossroad.pop(Crossroad.index(cars)))

pygame.quit()
p_reception.join()
client_socket.close()
sys.exit()