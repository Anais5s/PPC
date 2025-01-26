import multiprocessing
import random
import time

def normal_traffic_gen(simul):#simulates the generation of normal traffic. For each generated vehicle, it chooses 
#source and destination road sections randomly or according to some predefined criteria.
    while simul.value:
        time.sleep(random.uniform(0.1,3))
        source=random.randint(1,4)
        dest=random.choice([x for x in range(1, 5) if x != source])
        print(f"voiture allant de {source} a {dest}")

def priority_traffic_gen(simul): 
#simulates the generation of high-priority traffic. For each generated vehicle, it chooses source and destination
#road sections randomly or according to some predefined criteria.
    while simul.value:
        time.sleep(random.uniform(1,15))
        source=random.randint(1,4)
        dest=random.choice([x for x in range(1, 5) if x != source])
        print(f"vehicule prioritaire allant de {source} a {dest}")

  
if __name__ == "__main__":
    simul=multiprocessing.Value("b",True)
    processes=[]
    pn = multiprocessing.Process(target=normal_traffic_gen, args=(simul,))
    processes.append(pn)
    pp = multiprocessing.Process(target=priority_traffic_gen, args=(simul,))
    processes.append(pp)
    for p in processes:
        p.start()
    time.sleep(30)
    simul.value=False
    for p in processes:
        p.join()