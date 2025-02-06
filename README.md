# PPC
## Bibliothèques
- import multiprocessing
- from multiprocessing.managers import SyncManager
- import random
- import time
- import signal
- import psutil
- import sysv_ipc
- import sys
- import os
- import socket
- import pickle
- import pygame
- import threading
- import ctypes

## Exécution
Deux fichiers à lancer un fichier où se tient le programme principal qui fait office de serveur pour la connexion TCP (le fichier backend.py) et un fichier client pour le display (display.py). 

Pour mettre fin au programme il faut faire « ctrl+c » dans le terminal qui a lancé le programme principal, ce qui arrêtera automatiquement tous les processus et fermera la connexion TCP.