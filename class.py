class Color:
    green = 'chemin_vert'
    red = 'chemin_rouge'

class Traffic_lights:
    def __init__(self):
        self.state = Color.red # Feu au rouge par défaut
    def vert(self):
        self.state=Color.green
    def rouge(self):
        self.state=Color.red
    def changement(self):
        self.state = Color.green if self.state == Color.red else Color.red

feu1 = Traffic_lights()
feu1.changement()
print(feu1.state)