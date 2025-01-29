import multiprocessing
import random
import time
import signal
import sysv_ipc
import sys
import os

class State:
    Green = 1
    Red = 2

PRIORITY_RULES = {
    # Pour la source 0
    (0, 1): [1],     
    (0, 2): [1, 3],        
    (0, 3): [1, 2, 3],    

    # Pour la source 1
    (1, 2): [2],           
    (1, 3): [2, 0],        
    (1, 0): [2, 3, 0],     

    # Pour la source 2
    (2, 3): [3],           
    (2, 0): [3, 1],       
    (2, 1): [3, 0, 1],     

    # Pour la source 3
    (3, 0): [0],           
    (3, 1): [0, 2],        
    (3, 2): [0, 1, 2],
}

feux = multiprocessing.Array('i', [State.Red for _ in range(4)])
priority_queue = multiprocessing.Value("i", -1)

lock = multiprocessing.Lock()

mqs=[]
base_cle=1000 # Pour tomber sur une clé libre
for i in range (4):
    mq = sysv_ipc.MessageQueue(base_cle+i, sysv_ipc.IPC_CREAT)
    mqs.append(mq)

def normal_traffic_gen(simul):
    '''Simulates the generation of normal traffic.
    For each generated vehicle, it chooses source and destination road sections randomly or according to some predefined criteria.'''
    while simul.value:
        time.sleep(random.uniform(0.1,3))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        try:
            mq = sysv_ipc.MessageQueue(base_cle+source)
        except sysv_ipc.ExistentialError:
            print("Cannot connect to message queue terminating.")
            sys.exit(1)
        mq.send(str(dest).encode())
        #envoie tcp Mathis
        print(f"Voiture allant de {source} à {dest}")

def priority_traffic_gen(simul,lights_pid, priority_queue): 
    '''Simulates the generation of high-priority traffic.
    For each generated vehicle, it chooses source and destination road sections randomly or according to some predefined criteria.'''
    while simul.value:
        time.sleep(random.uniform(5,15))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        try:
            mq = sysv_ipc.MessageQueue(base_cle+source)
            mq.send(str(dest).encode())
            #envoie tcp Mathis
            print(f"Vehicule prioritaire allant de {source} à {dest}")
            priority_queue.value = source
            os.kill(lights_pid, signal.SIGUSR1)
            print(f"Signal envoyé à lights pour la file {source}")
        except sysv_ipc.ExistentialError:
            print("Cannot connect to message queue terminating.")
            sys.exit(1)
        
def handle_priority_signal(signum, frame):
    '''Cette fonction sera appelée quand le signal SIGUSR1 est reçu
    On ne met rien dedans car on veut juste interrompre le sleep'''
    raise InterruptedError

def set_lights(states):
    with lock:
        for i, state in enumerate(states):
            feux[i] = state
        #envoi tcp Mathis

def handle_priority():
    priority_road = priority_queue.value
    with lock:
        for i in range(4):
            feux[i] = State.Green if i == priority_road else State.Red
        #envoi tcp Mathis
    print(f"Mode priorité activé pour la voie {priority_road}")
    time.sleep(5)
    priority_queue.value = -1
    print("Retour au cycle normal")

def lights(simul, feux):
    '''Enregistrement du gestionnaire de signal'''
    signal.signal(signal.SIGUSR1, handle_priority_signal)
        # Définition des états normaux des feux
    NORMAL_STATES = [
        ([State.Green, State.Red, State.Green, State.Red], "lumiere 0 et 2 vertes"),
        ([State.Red, State.Green, State.Red, State.Green], "lumieres 1 et 3 vertes")
    ]
    while simul.value:
        for states, message in NORMAL_STATES:
            try:
                set_lights(states)
                print(message)
                time.sleep(5)
            except InterruptedError:
                handle_priority()
                break


def coordinator(simul, feux):
    try:
        queues = [sysv_ipc.MessageQueue(base_cle + i) for i in range(4)]
    except sysv_ipc.ExistentialError:
        print("Cannot connect to message queues, terminating.")
        sys.exit(1)
    
    def process_messages(active_feux):
        messages = []
        msg0=None
        msg1=None
        if msg0==None:
            try:
                msg0, _ = queues[active_feux[0]].receive(block=False)
                messages.append((active_feux[0], int(msg0.decode())))
            except sysv_ipc.BusyError:
                pass
        if msg1==None:
            try:
                msg1, _ = queues[active_feux[1]].receive(block=False)
                messages.append((active_feux[1], int(msg1.decode())))
            except sysv_ipc.BusyError:
                pass
                  
        if len(messages) >= 2:
            source1, dest1 = messages[0]
            source2, dest2 = messages[1]
                   
            if source2 in PRIORITY_RULES.get((source1, dest1), []):
                print(f"Message reçu sur la file {source2}: {dest2}")
                msg1=None
                #envoi tcp Mathis
                time.sleep(1)
            elif source1 in PRIORITY_RULES.get((source2, dest2), []):
                # La première voiture a priorité
                print(f"Message reçu sur la file {source1}: {dest1}")
                msg0=None
                #envoi tcp Mathis
                time.sleep(1)
            else:
                print(f"Les deux voitures ont pu passer")
                print(f"Message reçu sur la file {source1}: {dest1} et sur la file {source2}: {dest2}")
                msg0=None
                msg1=None
                #envoi tcp Mathis
                time.sleep(1)

        elif messages:
            # S'il n'y a qu'un seul message, le traiter
            print(f"Message reçu sur la file {messages[0][0]}: {messages[0][1]}")
            msg0=None
            #envoi tcp Mathis
            time.sleep(1)
                
        time.sleep(0.1)  

    while simul.value:
        if feux[0] == State.Green and feux[2] == State.Green:
            process_messages([0, 2])
        elif feux[1] == State.Green and feux[3] == State.Green:
            process_messages([1, 3])
        
        while priority_queue.value >= 0:
            try:
                mess, _ = queues[priority_queue.value].receive(block=False)
                print(f"Message reçu sur la file {priority_queue.value}: {mess.decode()}")
                #envoi tcp Mathis
                time.sleep(1)
            except sysv_ipc.BusyError:
                pass

        time.sleep(0.1)


  
if __name__ == "__main__": # Faire des threads pour certaines tâches au lieu de process (peut-être trop overkill ?)
    simul=multiprocessing.Value("b",True)
    processes=[]
    pn = multiprocessing.Process(target=normal_traffic_gen, args=(simul,))
    processes.append(pn)
    pl = multiprocessing.Process(target=lights, args=(simul,feux))
    pl.start()
    lights_pid = pl.pid
    pp = multiprocessing.Process(target=priority_traffic_gen, args=(simul,lights_pid,priority_queue))
    processes.append(pp)
    pc = multiprocessing.Process(target=coordinator, args=(simul,feux))
    processes.append(pc)
    for p in processes:
        p.start()
    time.sleep(40)
    simul.value=False
    for p in processes:
        p.join()
    for mq in mqs:
        mq.remove()