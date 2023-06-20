# the event handler (for system events, like clicks.)

import datatypes
import pygame
import game_main
import time

toMainQueue = None  # the queue sent to the main loop

kEscape = pygame.key.key_code("escape")
kR = pygame.key.key_code("r")
kEnter = pygame.key.key_code("return")
kSpace = pygame.key.key_code("space")

# sets up needed info.
def init(theMainQueue):
    global toMainQueue
    toMainQueue = theMainQueue


def sendEvent(event):
    """Send an event (all events should be sent over both queues)"""
    toMainQueue.put(event)


def main():
    """The event-handling loop. Runs in the background."""
    
    planeSelected = None # tracks the plane object currently selected.
    mostRecentCoord = (0,0) # tracks the most recent coordinate of the path.
    
    while game_main.isRunning():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_main.running = False
                import sys
                sys.exit(1) # force shut-down. Safe exit happens through the 'exit' button.
                # e = datatypes.Event("exit", [])  # send an 'exit' event.
                # sendEvent(e)
                # game_main.current_scene = 1
                # game_main.running = False # to force shut down.
            
            elif event.type == pygame.KEYDOWN:
                if event.key == kEscape:
                    e = datatypes.Event("pause",[])
                    sendEvent(e)
                elif event.key == kR:
                    e = datatypes.Event("restart",[])
                    sendEvent(e)
                else:
                    print("Key:", event.key)
                
                # elif event.key == kEscape:
                
            
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Initial left click
                pos = pygame.mouse.get_pos()
                
                # a datatype for response handling. (shared memory with the main thread)
                # Used so that main can tell the event handler which plane was clicked on.
                # the first item is a flag, set to true once a response is recieved.
                # the second item is the plane that was clicked on. If no plane was hit, it remains 'None'
                # the third item is the coordinates of the plane, at the moment the click registered.
                response = [False,None,(0,0)]
                
                # note: if the click hit a controllable plane, then the plane will be immediately instructed
                # to stop. As a result, its path will consist of a single point, namely the current point, and the current time.
                
                # event
                e = datatypes.Event(
                    "click",
                    {"target_pos": pos, "response": response},
                )
                sendEvent(e)
                
                # wait for a reply.
                # if the main thread closes, though, then this one should exit too.
                # hopefully, this shouldn't wait too long.
                while not response[0] and game_main.isRunning():
                    time.sleep(0.01) # a small wait, to prevent busy-waiting.
                
                planeSelected = response[1]
                mostRecentCoord = response[2]
                
            elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                # While dragging mouse to draw plane trajectory
                pos = pygame.mouse.get_pos()
                
                # skip event if no plane selected.
                if planeSelected == None:
                    continue
                
                dx = mostRecentCoord[0] - pos[0]
                dy = mostRecentCoord[1] - pos[1]
                
                # we don't bother to square-root, since we are just comparing it
                # with a constant
                distSquared = dx**2 + dy**2
                
                # if distance since last point is less than 20 pixels
                if distSquared <= 400:
                    continue
                
                e = datatypes.Event(
                    "addPoint",
                    {"target_pos": pos,
                        "plane": planeSelected},
                    # TODO: add target expected reach time to plane trajectory events
                )
                
                sendEvent(e)
                mostRecentCoord = pos # update most recent coordinate sent.
            elif event.type == pygame.MOUSEBUTTONUP:
                # skip event if no plane selected.
                if planeSelected == None:
                    continue
                
                pos = pygame.mouse.get_pos()
                
                e = datatypes.Event(
                    "addPoint",
                    {"target_pos": pos,
                        "plane": planeSelected},
                )
                sendEvent(e)
            else:
                pass  # you have to decide what events need to be sent, if any.

    print("event thread shutting down")
    return
