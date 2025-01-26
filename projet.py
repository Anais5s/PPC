import multiprocessing
import random
import time
import sysv_ipc


class State:
    Green = 1
    Red = 2

feux = feux = multiprocessing.Array('i', [State.Red for _ in range(4)])
mqs=[]

base_cle=1000
for i in range (4):
    mq = sysv_ipc.MessageQueue(base_cle+i, sysv_ipc.IPC_CREAT)
    mqs.append(mq)


def normal_traffic_gen(simul):#simulates the generation of normal traffic. For each generated vehicle, it chooses 
#source and destination road sections randomly or according to some predefined criteria.
    while simul.value:
        time.sleep(random.uniform(0.1,3))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        mq = mqs[source]
        mq.send(str(dest).encode())
        print(f"voiture allant de {source} a {dest}")

def priority_traffic_gen(simul): 
#simulates the generation of high-priority traffic. For each generated vehicle, it chooses source and destination
#road sections randomly or according to some predefined criteria.
    while simul.value:
        time.sleep(random.uniform(1,15))
        source=random.randint(0,3)
        dest=random.choice([x for x in range(0, 4) if x != source])
        mq = mqs[source]
        mq.send(str(dest).encode())
        print(f"vehicule prioritaire allant de {source} a {dest}")

def lights(simul,feux):
    while simul.value:
        feux[0]=State.Green
        feux[2]=State.Green
        feux[1]=State.Red
        feux[3]=State.Red
        print("lumiere 0 et 2 vertes")
        time.sleep(5)
        feux[0]=State.Red
        feux[2]=State.Red
        feux[1]=State.Green
        feux[3]=State.Green
        print("lumieres 1 et 3 vertes")

def coordinator(simul,feux):
    while simul.value:
        while feux[0]==State.Green and feux[2]==State.Green :
            try:
                voiture1, _ = mqs[0].receive(block=False)
                voiture2, _ = mqs[2].receive(block=False)
                voiture1 = voiture1.decode()
                voiture2 = voiture2.decode()
                voiture = random.choice([voiture1,voiture2])
                print(f"Message reçu sur la file 0 ou 2: {voiture}")
            except sysv_ipc.BusyError:
                continue
        while feux[1]==State.Green and feux[3]==State.Green :
            try:
                voiture1, _ = mqs[1].receive(block=False)
                voiture2, _ = mqs[3].receive(block=False)
                voiture = random.choice([voiture1,voiture2])
                print(f"Message reçu sur la file 1 ou 3: {voiture.decode()}")
            except sysv_ipc.BusyError:
                time.sleep(0.1)
  
if __name__ == "__main__":
    simul=multiprocessing.Value("b",True)
    processes=[]
    pn = multiprocessing.Process(target=normal_traffic_gen, args=(simul,))
    processes.append(pn)
    pp = multiprocessing.Process(target=priority_traffic_gen, args=(simul,))
    processes.append(pp)
    pl = multiprocessing.Process(target=lights, args=(simul,feux))
    processes.append(pl)
    pc = multiprocessing.Process(target=coordinator, args=(simul,feux))
    processes.append(pc)
    for p in processes:
        p.start()
    time.sleep(30)
    simul.value=False
    for p in processes:
        p.join()