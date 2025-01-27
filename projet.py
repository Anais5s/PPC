import multiprocessing
import random
import time
import signal
import sysv_ipc
import os

class State:
    Green = 1
    Red = 2


feux = multiprocessing.Array('i', [State.Red for _ in range(4)])
priority_queue = multiprocessing.Value("i", -1)

mqs=[]
base_cle=1000 #pour tomber sur une cle libre
for i in range (4):
    mq = sysv_ipc.MessageQueue(base_cle+i, sysv_ipc.IPC_CREAT)
    mqs.append(mq)

def normal_traffic_gen(simul):#simulates the generation of normal traffic. For each generated vehicle, it chooses 
#source and destination road sections randomly or according to some predefined criteria.
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
        print(f"voiture allant de {source} a {dest}")

def priority_traffic_gen(simul,lights_pid, priority_queue): 
#simulates the generation of high-priority traffic. For each generated vehicle, it chooses source and destination
#road sections randomly or according to some predefined criteria.
    while simul.value:
        time.sleep(random.uniform(5,15))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        try:
            mq = sysv_ipc.MessageQueue(base_cle+source)
            mq.send(str(dest).encode())
            print(f"vehicule prioritaire allant de {source} a {dest}")
            priority_queue.value = source
            os.kill(lights_pid, signal.SIGUSR1)
            print(f"Signal envoyé à lights pour la file {source}")
        except ExistentialError:
            print("Cannot connect to message queue terminating.")
            sys.exit(1)
        

def handle_priority_signal(signum, frame):
    # Cette fonction sera appelée quand le signal SIGUSR1 est reçu
    # On ne met rien dedans car on veut juste interrompre le sleep
    raise InterruptedError

def lights(simul, feux):
    # Enregistrement du gestionnaire de signal
    signal.signal(signal.SIGUSR1, handle_priority_signal)
    
    while simul.value:
        try:
            feux[0] = State.Green
            feux[2] = State.Green
            feux[1] = State.Red
            feux[3] = State.Red
            print("lumiere 0 et 2 vertes")
            time.sleep(5)
        except InterruptedError:
            priority_road = priority_queue.value
            for i in range(4):
                if i == priority_road:
                    feux[i] = State.Green
                else:
                    feux[i] = State.Red
            
            print(f"Mode priorité activé pour la voie {priority_road}")
            time.sleep(5)
            print("Retour au cycle normal")
            continue
            
        try:
            feux[0] = State.Red
            feux[2] = State.Red
            feux[1] = State.Green
            feux[3] = State.Green
            print("lumieres 1 et 3 vertes")
            time.sleep(5)
        except InterruptedError:
            priority_road = priority_queue.value
            for i in range(4):
                if i == priority_road:
                    feux[i] = State.Green
                else:
                    feux[i] = State.Red 
            print(f"Mode priorité activé pour la voie {priority_road}")
            time.sleep(5)
            print("Retour au cycle normal")

def coordinator(simul,feux):
    try:
        queues = [sysv_ipc.MessageQueue(base_cle + i) for i in range(4)]
    except ExistentialError:
        print("Cannot connect to message queues, terminating.")
        sys.exit(1)
    while simul.value:
        while feux[0]==State.Green and feux[2]==State.Green :
            try:
                voiture1, _ = queues[0].receive(block=False)
                voiture2, _ = queues[2].receive(block=False)
                voiture = random.choice([voiture1.decode(),voiture2.decode()])
                print(f"Message reçu sur la file 0 ou 2: {voiture}")
            except sysv_ipc.BusyError:
                time.sleep(0.1)
        while feux[1]==State.Green and feux[3]==State.Green :
            try:
                voiture1, _ = queues[1].receive(block=False)
                voiture2, _ = queues[3].receive(block=False)
                voiture = random.choice([voiture1.decode(),voiture2.decode()])
                print(f"Message reçu sur la file 1 ou 3: {voiture}")
            except sysv_ipc.BusyError:
                time.sleep(0.1)
        for i in range (4):
            while feux[i]==State.Green and (feux[(i+1)%4]==State.Red and feux[(i+2)%4]==State.Red and feux[(i-1)%4]==State.Red) :
                try:
                    voiture, _ = queues[i].receive(block=False)
                    print(f"Message reçu sur la file {i} en mode prioritaire: {voiture.decode()}")
                except sysv_ipc.BusyError:
                    time.sleep(0.1)

  
if __name__ == "__main__":
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