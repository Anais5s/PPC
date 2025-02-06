import multiprocessing
from multiprocessing.managers import SyncManager
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

class TrafficManager(SyncManager):
    pass

TrafficManager.register("Feux", dict)

priority_queue = multiprocessing.Value("i", -1)

lock = multiprocessing.Lock()

mqs=[]
base_cle=1000 # Pour tomber sur une clé libre
for i in range (4):
    mq = sysv_ipc.MessageQueue(base_cle+i, sysv_ipc.IPC_CREAT)
    mqs.append(mq)

def normal_traffic_gen(sock):
    '''Simulates the generation of normal traffic.
    For each generated vehicle, it chooses source and destination road sections randomly or according to some predefined criteria.'''
    while True:
        try:
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
        except:
            print(f"Process normal_traffic_gen arrêté par KeyboardInterrupt.")
            break

def priority_traffic_gen(lights_pid, priority_queue, sock): 
    '''Simulates the generation of high-priority traffic.
    For each generated vehicle, it chooses source and destination road sections randomly or according to some predefined criteria.'''
    while True:
        try:
            time.sleep(random.uniform(20,40))
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
        except KeyboardInterrupt:
            print(f"Process priority_traffic_gen arrêté par KeyboardInterrupt.")
            break
        
def handle_priority_signal(signum, frame):
    '''Cette fonction sera appelée quand le signal SIGUSR1 est reçu
    On ne met rien dedans car on veut juste interrompre le sleep'''
    raise InterruptedError

def set_lights(feux,states,sock):
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

def handle_priority(feux,sock):
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

def lights(feux,sock):
    '''Enregistrement du gestionnaire de signal'''
    signal.signal(signal.SIGUSR1, handle_priority_signal)
        # Définition des états normaux des feux
    NORMAL_STATES = [
        ([1, 2, 1, 2], "lumiere 0 et 2 vertes"),
        ([2, 1, 2, 1], "lumieres 1 et 3 vertes")
    ]
    while True:
        try:
            for states, message in NORMAL_STATES:
                try:
                    set_lights(feux,states,sock)
                    print(message)
                    time.sleep(15)
                except InterruptedError:
                    try:
                        handle_priority(feux,sock)
                    except InterruptedError:
                        print("Double interrupt")    
        except KeyboardInterrupt:
            print(f"Process lights arrêté par KeyboardInterrupt.")
            break

        
def coordinator(feux, sock):
    try:
        queues = [sysv_ipc.MessageQueue(base_cle + i) for i in range(4)]
    except sysv_ipc.ExistentialError:
        print("Cannot connect to message queues, terminating.")
        sys.exit(1)

    def process_messages(active_feux, sock):
        temp_queue = []
        for feu in active_feux:
            try:
                msg, msg_type = queues[feu].receive(block=False, type=2)
                temp_queue.append((feu, int(msg.decode()), msg_type))
            except sysv_ipc.BusyError:
                try:
                    msg, msg_type = queues[feu].receive(block=False, type=3)
                    temp_queue.append((feu, int(msg.decode()), msg_type))
                except sysv_ipc.BusyError:
                    try:    
                        msg, msg_type = queues[feu].receive(block=False)
                        temp_queue.append((feu, int(msg.decode()), msg_type))
                    except sysv_ipc.BusyError:
                        pass  

        # Analyser les nouveaux messages récupérés
        if len(temp_queue) >= 2:
            source1, dest1, type1 = temp_queue.pop(0)
            source2, dest2, type2 = temp_queue.pop(0)
            tourne_gauche_1 = (dest1 == (source1 + 1) % 4)
            tourne_gauche_2 = (dest2 == (source2 + 1) % 4)

            if not tourne_gauche_1 and not tourne_gauche_2:
                print(f"Les deux voitures peuvent passer")
                if feux[source1] == 1 and feux[source2] == 1:
                    sock.sendall(pickle.dumps(('passage', source1, dest1)))
                    sock.sendall(pickle.dumps(('passage', source2, dest2)))
                    time.sleep(1.5)
                    return  
            
            elif tourne_gauche_1 and not tourne_gauche_2:
                print(f"Message reçu sur la file {source2}: {dest2}")
                if feux[source2] == 1:
                    sock.sendall(pickle.dumps(('passage', source2, dest2)))
                    time.sleep(1.5)
                    queues[source1].send(str(dest1).encode(), type=3)
                    return  

            elif tourne_gauche_2 and not tourne_gauche_1:
                print(f"Message reçu sur la file {source1}: {dest1}")
                if feux[source1] == 1:
                    sock.sendall(pickle.dumps(('passage', source1, dest1)))
                    time.sleep(1.5)
                    queues[source2].send(str(dest2).encode(), type=3)
                    return  

            else:
                print("On en prend une au hasard")
                source, dest, _ = random.choice([(source1, dest1, type1), (source2, dest2, type2)])
                if feux[source] == 1:
                    sock.sendall(pickle.dumps(('passage', source, dest)))
                    time.sleep(1.5)
                    if source==source1:
                        queues[source2].send(str(dest2).encode(), type=3)
                    else:
                        queues[source1].send(str(dest1).encode(), type=3)
                    return  


        elif len(temp_queue) == 1:
            source, dest, msg_type = temp_queue.pop(0)
            print(f"Message reçu sur la file {source}: {dest}")
            sock.sendall(pickle.dumps(('passage', source, dest)))
            if msg_type==2:
                time.sleep(2)
                print("C'etait une voiture prioritaire")
            else:
                time.sleep(1.5)
        else:
            time.sleep(0.1)

    while True:
        try:
            if feux[0] == 1 and feux[2] == 1:
                process_messages([0, 2], sock)
            elif feux[1] == 1 and feux[3] == 1:
                process_messages([1, 3], sock)
            while priority_queue.value!=-1 and feux[priority_queue.value]==1:
                try:
                    process_messages([priority_queue.value], sock)
                except sysv_ipc.BusyError:
                    time.sleep(0.1)
            time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"Process coordinator arrêté par KeyboardInterrupt.")
            break


def stop_processes(signum, frame, processes):
    """ Fonction appelée quand un signal est reçu (ici ctr+c) """
    signal.signal(signal.SIGINT, signal.SIG_IGN) 
    for process in processes:
        if process is not None:
            process.terminate()  # Envoie SIGTERM
            process.join()  # Attend la fin du processus
    print("Tous les processus ont été arrêtés.")
    sys.exit(0) 

if __name__ == "__main__": # Faire des threads pour certaines tâches au lieu de process (peut-être trop overkill ?)
    signal.signal(signal.SIGINT, signal.SIG_IGN) 
    signal.signal(signal.SIGINT, lambda signum, frame: stop_processes(signum, frame, processes))
    manager = multiprocessing.Manager()
    feux = manager.list([2, 2, 2, 2])
    for i in range(4):
        feux[i] = 2  # 2 pour rouge, 1 pour vert
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #pour que le socket soit réutilisable direct apres
            server_socket.bind((HOST, PORT))
            server_socket.listen(2)
            print("En attente d'une connexion client...")
            client_socket, address = server_socket.accept() 
            print(f"Client connecté : {address}")
            client_socket.setblocking(True)
        time.sleep(3)
        processes=[]
        pl = multiprocessing.Process(target=lights, args=(feux, client_socket))
        pl.start()
        lights_pid = pl.pid
        pn = multiprocessing.Process(target=normal_traffic_gen, args=(client_socket,))
        pp = multiprocessing.Process(target=priority_traffic_gen, args=(lights_pid, priority_queue, client_socket))  # lights_pid n'est pas encore défini
        pc = multiprocessing.Process(target=coordinator, args=(feux, client_socket))
        processes.extend([pn, pp, pc])
        for p in processes:
            p.start()
        processes.append(pl)
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                stop_processes(signal.SIGINT, None, processes)
    except Exception as e:
        print(f"Il y a une erreur {e}")
    finally:
        print("liberation des ressources")
        for mq in mqs:
            mq.remove()
        try:
            client_socket.sendall(pickle.dumps(('fin', 0)))
        except Exception as e:
            print(f"Erreur lors de l'envoi du message de fin : {e}")
        try:
            client_socket.close()
        except Exception as e:
            print(f"Pas reussi a fermer la socket: {e}")
        manager.shutdown()
