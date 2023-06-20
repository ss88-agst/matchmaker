# the AI.

import game_main  # contains the MainGame class
import datatypes
import game_main
import math

toMainQueue = None  # the queue sent to the main loop


MAX_PLAYER_COUNT = 4 # So that the AI can take control exclusively of the planes that aren't controlled by a player

# takes queues to write events to:
#    a queue to the main game, and
#    a queue to the network manager
def init(mainQueue):
    global toMainQueue
    toMainQueue = mainQueue


# send an event (all events should be sent over both queues)
def sendEvent(event):
    toMainQueue.put(event)


# Iterate through list of planes (all not players), and if a plane's partner is not moving, direct it towards its partner
def redirectPlanes(planeList):
    for plane in planeList:
        # This was me messing around.
        # I discourage using this model as the final AI;
        # I wasn't really trying to make it particularily smart.
        if not datatypes.Plane.moving(plane) or True:
            partnerPlane = plane.partner
            
            # only move 100 units toward the goal.
            x = plane.x
            y = plane.y
            dx = partnerPlane.x - x
            dy = partnerPlane.y - y
            r = math.sqrt(dx**2+dy**2)
            maxDist = 200
            if r > maxDist:
                dx,dy = ((dx*maxDist)//r,(dy*maxDist)//r)
            
            e = datatypes.Event(
                    "addPoint",
                    {"target_pos": [x+dx, y+dy],
                        "plane": plane},
                )
            sendEvent(e)



# performs whatever actions need to be performed.
# Access myGame.whatever, put events on the queues as needed.
# This will be called by game_main.
# THIS CODE IS RUNNING AS PART OF THE MAIN LOOP. THIS FUNCTION SHOULD FINISH QUICKLY!!!
def runAI():
    # if a player is offline, redirect their planes
    for i in range(len(game_main.playerList)):
        if not game_main.playerList[i]:
            redirectPlanes(game_main.planes[i])
    
    return
