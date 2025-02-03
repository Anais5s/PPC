import multiprocessing
from multiprocessing.shared_memory import SharedMemory
import random
import time
import signal
import psutil
import sysv_ipc
import sys
import os
import socket
import pickle  # Pour sérialiser les tuples avant envoi

HOST = "localhost"
PORT = 6666


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
            message = str(dest).encode()
            mq.send(message,type=1)
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
        time.sleep(random.uniform(20,30))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        try:
            mq = sysv_ipc.MessageQueue(base_cle+source)
            message = str(dest).encode()
            mq.send(message,type=2)
            msg_creation = ('creation_priorite', source)
            sock.sendall(pickle.dumps(msg_creation))
            print(f"Vehicule prioritaire allant de {source} à {dest}")
            priority_queue.value = source
            if lights_pid and psutil.pid_exists(lights_pid):
                os.kill(lights_pid, signal.SIGUSR1)
                print(f"Signal envoyé à lights pour la file {source}")    
            else:
                print(f"Processus {lights_pid} introuvable")
        except sysv_ipc.ExistentialError:
            print("Cannot connect to message queue terminating.")
            sys.exit(1)
        
def handle_priority_signal(signum, frame):
    '''Cette fonction sera appelée quand le signal SIGUSR1 est reçu
    On ne met rien dedans car on veut juste interrompre le sleep'''
    raise InterruptedError

def set_lights(states,sock):
    with lock:
        for i in range (4):
            feux[i] = 2
            msg_feu = ('feu', i, 2)
            sock.sendall(pickle.dumps(msg_feu))
            print(f"On envoie un feu {i} avec la state {feux[i]}")
        time.sleep(2)
        for i, state in enumerate(states):
            feux[i] = state
            msg_feu = ('feu', i, state)
            sock.sendall(pickle.dumps(msg_feu))
            print(f"On envoie un feu {i} avec la state {feux[i]}")

def handle_priority(sock):
    priority_road = priority_queue.value
    with lock:
        for i in range (4):
            feux[i] = 2
            msg_feu = ('feu', i, 2)
            sock.sendall(pickle.dumps(msg_feu))
            print(f"On envoie un feu {i} avec la state {feux[i]}")
        time.sleep(2)
        for i in range(4):
            if i == priority_road:
                feux[i] = 1
                msg_feu = ('feu', i, feux[i])
                sock.sendall(pickle.dumps(msg_feu))
                print(f"On envoie un feu {i} avec la state {feux[i]}")
            else:
                feux[i]=2
    print(f"Mode priorité activé pour la voie {priority_road}")
    time.sleep(10)
    priority_queue.value = -1
    print("Retour au cycle normal")

def lights(simul,sock):
    '''Enregistrement du gestionnaire de signal'''
    signal.signal(signal.SIGUSR1, handle_priority_signal)
        # Définition des états normaux des feux
    NORMAL_STATES = [
        ([1, 2, 1, 2], "lumiere 0 et 2 vertes"),
        ([2, 1, 2, 1], "lumieres 1 et 3 vertes")
    ]
    while simul.value:
        for states, message in NORMAL_STATES:
            try:
                set_lights(states,sock)
                print(message)
                time.sleep(15)
            except InterruptedError:
                try:
                    handle_priority(sock)
                except InterruptedError:
                    handle_priority(sock)
                break

def coordinator(simul, sock):
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
                msg=int(msg0.decode())
                messages.append((active_feux[0], msg))
            except sysv_ipc.BusyError:
                pass
        if msg1==None:
            try:
                msg1, _= queues[active_feux[1]].receive(block=False)
                msg=int(msg1.decode())
                messages.append((active_feux[1], msg))
            except sysv_ipc.BusyError:
                pass
                  
        if len(messages) >= 2:
            source1, dest1 = messages[0]
            source2, dest2 = messages[1]
                   
            if source2 in PRIORITY_RULES.get((source1, dest1), []):
                print(f"Message reçu sur la file {source2}: {dest2}")
                msg_passage = ('passage', source2, dest2)
                if feux[source2]==1:
                    sock.sendall(pickle.dumps(msg_passage))
                    msg1=None
                    time.sleep(1)
            elif source1 in PRIORITY_RULES.get((source2, dest2), []):
                # La première voiture a priorité
                print(f"Message reçu sur la file {source1}: {dest1}")
                msg_passage = ('passage', source1, dest1)
                if feux[source1]==1:
                    sock.sendall(pickle.dumps(msg_passage))
                    msg0=None
                    time.sleep(1)
            else:
                print(f"Les deux voitures ont pu passer")
                print(f"Message reçu sur la file {source1}: {dest1} et sur la file {source2}: {dest2}")
                if feux[source1]==1 and feux[source2]==1:
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
        if feux[0] == 1 and feux[2] == 1:
            process_messages([0, 2], sock)
        elif feux[1] == 1 and feux[3] == 1:
            process_messages([1, 3], sock)
        while priority_queue.value!=-1 and feux[priority_queue.value]==1:
            try:
                mess, t = queues[priority_queue.value].receive(block=False)
                print(f"Message reçu sur la file {priority_queue.value}: {mess.decode()}")
                msg_passage = ('passage', priority_queue.value, int(mess.decode()))
                if feux[priority_queue.value]!=1:
                    break
                sock.sendall(pickle.dumps(msg_passage))
                time.sleep(1)
            except sysv_ipc.BusyError:
                time.sleep(0.1)
        time.sleep(0.1)
    for mq in queues:
        try:
            mq.remove()
        except sysv_ipc.ExistentialError:
            pass
    feux_shm.close()


  
if __name__ == "__main__": # Faire des threads pour certaines tâches au lieu de process (peut-être trop overkill ?)
    simul=multiprocessing.Value("b",True)
    feux_shm = SharedMemory(create=True, size=4 * 4)
    feux = memoryview(feux_shm.buf)
    for i in range(4):
        feux[i] = 2  # 2 pour rouge, 1 pour vert
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((HOST, PORT))
            server_socket.listen(2)
            print("En attente d'une connexion client...")
            client_socket, address = server_socket.accept() 
            print(f"Client connecté : {address}")
            client_socket.setblocking(True)
        time.sleep(3)
        processes=[]
        pn = multiprocessing.Process(target=normal_traffic_gen, args=(simul,client_socket))
        processes.append(pn)
        pl = multiprocessing.Process(target=lights, args=(simul,client_socket))
        pl.start()
        lights_pid = pl.pid
        pp = multiprocessing.Process(target=priority_traffic_gen, args=(simul,lights_pid,priority_queue,client_socket))
        processes.append(pp)
        pc = multiprocessing.Process(target=coordinator, args=(simul, client_socket))
        processes.append(pc)
        for p in processes:
            p.start()
        time.sleep(40)
        simul.value=False
    except Exception as e:
        print(f"Il y a une erreur {e}")
    finally:
        client_socket.send('fin'.encode())
        print("liberation des ressources")
        for p in processes:
            p.terminate()
            p.join()
        for mq in mqs:
            mq.remove()
        try:
            client_socket.close()
        except Exception as e:
            print(f"Pas reussi a fermer la socket: {e}")
        time.sleep(1)
        del feux
        feux_shm.close()
        feux_shm.unlink()
