import curses

def intersection(stdscr):
    curses.curs_set(0)  # Cacher le curseur
    stdscr.clear()  # Effacer l'écran initialement
    stdscr.addstr(0, 0, "Bonjour, le terminal est prêt!")
    stdscr.refresh()  # Rafraîchir l'écran
    stdscr.getkey()  # Attendre une touche avant de fermer

if __name__ == "__main__":
    # Appel correct de la fonction via curses.wrapper
    curses.wrapper(intersection)