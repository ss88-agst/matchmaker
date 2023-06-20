#! /usr/bin/python

# The executable.

from sys import argv

debug = False # auto-runs the setup process
silent = False # don't touch the room cache
newGame = False # force a new game.
if len(argv) > 1:
    for param in argv[1:]:
        if param == "-d":
            debug = True
        elif param == "-s":
            silent = True
        elif param == "-n":
            newGame = True

# main imports
import pygame
pygame.init() # set up the environment.
import datatypes # common datatypes
import threading # multithreading
import game_main # the main loop and data object
import game_draw # the graphics handler
import game_AI # the AI handler
import game_events # the system event handler.
import game_networks # the socket/connection handler.
import game_setup
print()

# removes the room cache.
if newGame:
    game_setup.delRoomCache()

res = None
if not silent:
    res = game_setup.tryRoomCache()
    if res != None:
        import socket
        pls,me = res
        # make the blank socket, to conform to the rest of the protocol.
        s = socket.socket()
        s.bind((me[0],me[1]))
        res = (s,pls,me)
        game_networks.skipSelf = True # join whoever is active, even lower-priority games.


if res != None:
    pass # continue the game from where we left off.
elif debug:
    res = game_setup.expedite()
else:
    ip,port = game_setup.setup()
    res = game_setup.handleServer(ip,port)
sock,players,me = res
game_setup.setupPlayerCount(players)

if len(players) > 1:
    # a multi-player game.
    game_setup.makeRoomCache(players,me)

print("")
print("Press esc to pause, and enter or spacebar to resume.")
print("To restart, press 'r'.")
print("Enjoy!\n\n")





screen = pygame.display.set_mode([800,800]) # make GUI

# define the queues
mainQueue = datatypes.EventQueue() # the queue from events, networks, and AI to main
netQueue = datatypes.EventQueue() # The queue from events, networks, and AI to the network manager

# create the needed objects
game_draw.init(screen,mainQueue) # the draw manager
game_events.init(mainQueue) # the system event manager
game_networks.init(mainQueue,netQueue) # the network manager
game_AI.init(mainQueue) # the AI
game_main.init(mainQueue,netQueue,game_draw,game_AI,players) # the main game

# define the threads
tMain = threading.Thread(target=game_main.main)
tNet = threading.Thread(target=game_networks.main,args=(players,sock,me,))

# start all the threads
tMain.start()
tNet.start()
game_events.main() # main thread handles game events.
# the main thread is the event thread.
# 'Event.get' can only be called from the thread which defined pygame.display (meaning this one)


# stop all the threads.
tMain.join()
tNet.join()

if not silent:
    print("deleting room cache...")
    game_setup.delRoomCache()

print("All threads closed, shutting down pygame.")
pygame.quit()