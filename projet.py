import multiprocessing
import random
import time
import signal
import sysv_ipc
import sys
import os
import socket
import pickle  # Pour sérialiser les tuples avant envoi

HOST = "localhost"
PORT = 6665

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

def normal_traffic_gen(simul,sock):
    '''Simulates the generation of normal traffic.
    For each generated vehicle, it chooses source and destination road sections randomly or according to some predefined criteria.'''
    while simul.value:
        time.sleep(random.uniform(0.1,3))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        try:
            mq = sysv_ipc.MessageQueue(base_cle+source)
            message=(dest,0)
            mq.send(pickle.dumps(message))
            msg_creation = ('creation_normal', source)
            sock.sendall(pickle.dumps(msg_creation))
            print(f"Voiture allant de {source} à {dest}")
        except sysv_ipc.ExistentialError:
            print("Cannot connect to message queue terminating.")
            sys.exit(1)

def priority_traffic_gen(simul,lights_pid, priority_queue, sock): 
    '''Simulates the generation of high-priority traffic.
    For each generated vehicle, it chooses source and destination road sections randomly or according to some predefined criteria.'''
    while simul.value:
        time.sleep(random.uniform(10,20))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        try:
            mq = sysv_ipc.MessageQueue(base_cle+source)
            message=(dest,1)
            mq.send(pickle.dumps(message))
            msg_creation = ('creation_priorite', source)
            sock.sendall(pickle.dumps(msg_creation))
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

def set_lights(states,feux,sock):
    with lock:
        for i, state in enumerate(states):
            feux[i] = state
            msg_feu = ('feu', i, state)
            sock.sendall(pickle.dumps(msg_feu))
            print(f"On envoie un feu {i} avec la state {feux[i]}")


def handle_priority(feux,sock):
    priority_road = priority_queue.value
    with lock:
        for i in range(4):
            feux[i] = State.Green if i == priority_road else State.Red
            msg_feu = ('feu', i, feux[i])
            sock.sendall(pickle.dumps(msg_feu))
            print(f"On envoie un feu {i} avec la state {feux[i]}")
    print(f"Mode priorité activé pour la voie {priority_road}")
    queue = sysv_ipc.MessageQueue(base_cle + priority_road)
    while True:
        try:
            mess, _ = queue.receive(block=False)
            data = pickle.loads(mess)
            print(f"Message reçu sur la file {priority_queue.value}: {data[0]}")
            msg_passage = ('passage', priority_queue.value, data[0])
            sock.sendall(pickle.dumps(msg_passage))
            if data[1] == 1:  # Vérifier si la voiture prioritaire est passée
                break
        except sysv_ipc.BusyError:
            print("En attente du passage du véhicule prioritaire...")
            time.sleep(0.5)
    time.sleep(3)
    priority_queue.value = -1
    print("Retour au cycle normal")

def lights(simul, feux,sock):
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
                set_lights(states,feux,sock)
                print(message)
                time.sleep(15)
            except InterruptedError:
                handle_priority(feux,sock)
                break


def coordinator(simul, feux, sock):
    try:
        queues = [sysv_ipc.MessageQueue(base_cle + i) for i in range(4)]
    except sysv_ipc.ExistentialError:
        print("Cannot connect to message queues, terminating.")
        sys.exit(1)
    
    def process_messages(active_feux,sock):
        messages = []
        msg0=None
        msg1=None
        if msg0==None:
            try:
                msg0, _ = queues[active_feux[0]].receive(block=False)
                data0=pickle.loads(msg0)
                messages.append((active_feux[0], data0[0]))
            except sysv_ipc.BusyError:
                pass
        if msg1==None:
            try:
                msg1, _ = queues[active_feux[1]].receive(block=False)
                data1=pickle.loads(msg1)
                messages.append((active_feux[1], data1[0]))
            except sysv_ipc.BusyError:
                pass
                  
        if len(messages) >= 2:
            source1, dest1 = messages[0]
            source2, dest2 = messages[1]
                   
            if source2 in PRIORITY_RULES.get((source1, dest1), []):
                print(f"Message reçu sur la file {source2}: {dest2}")
                msg_passage = ('passage', source2, dest2)
                sock.sendall(pickle.dumps(msg_passage))
                msg1=None
                time.sleep(1)
            elif source1 in PRIORITY_RULES.get((source2, dest2), []):
                # La première voiture a priorité
                print(f"Message reçu sur la file {source1}: {dest1}")
                msg_passage = ('passage', source1, dest1)
                sock.sendall(pickle.dumps(msg_passage))
                msg0=None
                time.sleep(1)
            else:
                print(f"Les deux voitures ont pu passer")
                print(f"Message reçu sur la file {source1}: {dest1} et sur la file {source2}: {dest2}")
                msg_passage = ('passage', source1, dest1)
                sock.sendall(pickle.dumps(msg_passage))
                msg_passage = ('passage', source2, dest2)
                sock.sendall(pickle.dumps(msg_passage))
                msg0=None
                msg1=None
                time.sleep(1)

        elif messages:
            # S'il n'y a qu'un seul message, le traiter 
            source, dest = messages[0]
            print(f"Message reçu sur la file {source}: {dest}")
            msg_passage = ('passage', source, dest)
            sock.sendall(pickle.dumps(msg_passage))
            msg0=None
            time.sleep(1)
                
        time.sleep(0.1)  

    while simul.value:
        if feux[0] == State.Green and feux[2] == State.Green:
            process_messages([0, 2], sock)
        elif feux[1] == State.Green and feux[3] == State.Green:
            process_messages([1, 3], sock)
        time.sleep(0.1)


  
if __name__ == "__main__": # Faire des threads pour certaines tâches au lieu de process (peut-être trop overkill ?)
    simul=multiprocessing.Value("b",True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(2)
        print("En attente d'une connexion client...")
        client_socket, address = server_socket.accept() 
        print(f"Client connecté : {address}")
        client_socket.setblocking(True)
    processes=[]
    pn = multiprocessing.Process(target=normal_traffic_gen, args=(simul,client_socket))
    processes.append(pn)
    pl = multiprocessing.Process(target=lights, args=(simul,feux,client_socket))
    pl.start()
    lights_pid = pl.pid
    pp = multiprocessing.Process(target=priority_traffic_gen, args=(simul,lights_pid,priority_queue,client_socket))
    processes.append(pp)
    pc = multiprocessing.Process(target=coordinator, args=(simul,feux, client_socket))
    processes.append(pc)
    for p in processes:
        p.start()
    time.sleep(40)
    simul.value=False
    for p in processes:
        p.join()
    for mq in mqs:
        mq.remove()
    client_socket.close()