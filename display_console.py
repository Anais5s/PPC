import curses
import random
import time

# Fonction principale
def intersection(stdscr):
    # Paramètres de configuration
    curses.curs_set(0)  # Cacher le curseur
    stdscr.nodelay(1)   # Mode non-bloquant pour la lecture des entrées
    stdscr.timeout(1000) # Rafraîchir l'écran toutes les secondes

    # Feux de signalisation : 0 = rouge, 1 = vert
    feux = {'N': 0, 'S': 0, 'E': 0, 'O': 0}
    vehicules = {'N': [], 'S': [], 'E': [], 'O': []}  # Liste des véhicules en attente
    directions = ['N', 'S', 'E', 'O']
    
    # Dessiner l'intersection
    def dessiner_intersection():
        stdscr.clear()  # Effacer l'écran avant de redessiner
        # Routes
        for i in range(5):
            stdscr.addstr(5, i + 5, "-")  # Route horizontale
            stdscr.addstr(i + 5, 5, "|")  # Route verticale
        # Feux de signalisation
        stdscr.addstr(2, 2, "Feu N: " + ("Vert" if feux['N'] else "Rouge"))
        stdscr.addstr(2, 15, "Feu S: " + ("Vert" if feux['S'] else "Rouge"))
        stdscr.addstr(7, 2, "Feu E: " + ("Vert" if feux['E'] else "Rouge"))
        stdscr.addstr(7, 15, "Feu O: " + ("Vert" if feux['O'] else "Rouge"))
        
        # Affichage des véhicules
        for dir, veh in vehicules.items():
            for i, v in enumerate(veh):
                if dir == 'N':
                    stdscr.addstr(5 - i, 7, "V")
                elif dir == 'S':
                    stdscr.addstr(5 + i, 7, "V")
                elif dir == 'E':
                    stdscr.addstr(7, 15 + i, "V")
                elif dir == 'O':
                    stdscr.addstr(7, 1 - i, "V")
        
        stdscr.refresh()

    # Simulation
    while True:
        dessiner_intersection()

        # Ajout de véhicules aléatoires
        if random.random() < 0.1:
            direction = random.choice(directions)
            vehicules[direction].append('V')

        # Passage des véhicules si le feu est vert
        for dir in directions:
            if feux[dir] == 1 and vehicules[dir]:
                vehicules[dir].pop(0)  # Faire passer un véhicule
        
        # Changer les feux
        feux['N'] = 1 - feux['N']
        feux['S'] = 1 - feux['S']
        feux['E'] = 1 - feux['E']
        feux['O'] = 1 - feux['O']

        # Attente non-bloquante avec lecture des touches
        key = stdscr.getch()  # Attendre un input ou un délai
        if key == 27:  # Si l'utilisateur appuie sur 'ESC', on quitte
            break

if __name__ == "__main__":
    # Appel correct de la fonction via curses.wrapper
    curses.wrapper(intersection)
