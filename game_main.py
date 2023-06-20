# the main loop. handles movement of planes, calls other functions.
# the main game. Tracks any data about the game state.

import math

import pygame
import datatypes
import random



# psuedo-imports
game_draw = (
    None  # the draw manager module. imported later, to prevent circular imports.
)
game_AI = None  # the AI module. Imported later, to prevent circular imports.
current_scene = None
running = True  # whether the game should terminate
queue = None  # the event queue coming from game_events and game_networks.
netQueue = None # the queue to send events to the network.
# the queue of events which are future events.
selfQueue = None
winLoss = 0 # becomes 1 on win, -1 on loss.
paused = 1 # tracks paused state.
planeCount = 0 # tracks the ID of the next plane pair to spawn
nextSpawn = 5000 # tracks the game time to initiate the next spawn.
spawnInterval = 5000
nextAI = 500 # tracks when the AI should run (twice a second only)
startMenu = 1
# decides if to initiate events, like spawning, or collisions.
isUserServer = False
# decides which characters you control
playerNum = 0
# a list of booleans, saying who is online.
# its length corresponds to the number of players playing.
playerList = []

# Plane speed constant.
PLANE_SPEED_FACTOR = datatypes.PLANE_SPEED_FACTOR

# a list of planes. (plane objects)
# four sub-lists, each for players 0-3.
planes = [[], [], [], []]

# resets everything
def restart():
    global planes
    global paused
    global winLoss
    global planeCount
    global nextSpawn
    global current_time
    global time_offset
    global current_scene
    global startMenu
    
    current_scene = 1
    planes = [[],[],[],[]]
    paused = False
    winLoss = 0
    planeCount = 0
    nextSpawn = 5000
    current_time = 0
    time_offset = pygame.time.get_ticks() # sets offset for get_ticks to game time.
    while selfQueue.get() != None:
        pass # clear the self queue

# sets up queues and imports.
def init(q, netQ, drawManager, ai, players):
    global game_draw
    global game_AI
    global queue
    global startMenu

    global current_scene
    current_scene = 1
    global netQueue
    global current_time
    global time_offset
    global selfQueue
    startMenu = True
    netQueue = netQ
    queue = q
    game_draw = drawManager
    game_AI = ai
    selfQueue = datatypes.EventQueue()
    

# the main loop
def main():
    
    global current_time
    global planes # list of planes
    global running
    global nextSpawn # when to spawn a plane next.
    global isUserServer
    global nextAI
    
    newTime = current_time
    while isRunning():
        if timePassing():
            newTime,time_delta = get_time_delta()
            
            if isUserServer:
                # run AI on a half-second interval.
                if nextAI <= newTime:
                    game_AI.runAI()  # run the AI
                    nextAI = newTime + 500 # half a second.
                    # note: this isn't half a second after the previous run,
                    # but rather half a second after now.
                # spawn stuff if needed.
                if nextSpawn <= newTime:
                    nextSpawn += spawnInterval
                    spawnPair(newTime)
        else:
            time_delta = 0
        newTime,time_delta = handleEvents(newTime,time_delta)
        updateGameState(newTime, time_delta)  # update the game state
        game_draw.drawAll(current_scene,planes, newTime)  # draw the new game state
    print("game_main thread shutting down.")


current_time = 0
time_offset = 0

# returns the new game time and time delta as a pair.
def get_time_delta():
    """
    Get the difference between the current time and the previous current time.
    This is used to stabilise the pace of the game. This also resets the previous
    time delta.
    """
    global current_time
    new_time = get_offset_time()
    time_delta = new_time - current_time
    current_time = new_time
    return (new_time,time_delta)

# gets the time with only an offset
def get_offset_time():
    return pygame.time.get_ticks() - time_offset

# resumes the game, handling side effects.
def resume(newTime):
    global paused
    global time_offset
    global startMenu
    paused = False
    startMenu = False
    # adjust time offset, so that game time stays the same.
    time_offset = pygame.time.get_ticks() - newTime


def handleEvents(newTime,time_delta):
    global paused
    global time_offset
    global running
    global winLoss
    
    while True:
        nextEvent = queue.get()
        if nextEvent == None:
            break
        if nextEvent.getType() == "exit":
            running = False
        elif nextEvent.getType() == "pause":
            if winLoss != 0: # so you can see the game board
                paused = not paused
            elif not paused:
                e = datatypes.Event("pause",[newTime])
                selfQueue.put(e)
                sendEvent(e)
        elif nextEvent.getType() == "resume":
            if paused:
                sendEvent(datatypes.Event("resume",[]))
                resume(newTime)
        elif nextEvent.getType() == "toResume":
            resume(newTime)
        elif nextEvent.getType() == "toPause":
            # instructs when to pause.
            # adds to delay queue
            selfQueue.put(datatypes.Event("pause",nextEvent.getData()))
        elif nextEvent.getType() == "restart":
            restart()
            netQueue.put(nextEvent) # tell your friends
            return (0,0) # reset timer.
        elif nextEvent.getType() == "restartRequest":
            restart()
            return (0,0) # reset timer.
        elif nextEvent.getType() == "click":
            x,y = nextEvent.getData()["target_pos"]
            response = nextEvent.getData()["response"]
            
            if paused:
                # nope, no planes here.
                response[0] = True
                continue
            
            for plane in planes[playerNum]:
                if plane.contains(x,y):
                    response[1] = plane
                    response[2] = (plane.x,plane.y)
                    break
            
            if response[1] != None:
                # tell the selected plane to stop.
                plane = response[1]
                x = plane.x
                y = plane.y
                plane.newPointExact(x,y,newTime,netQueue)
                
            
            response[0] = True # message processed successfuly.
        elif nextEvent.getType() == "addPoint":
            # add point to end of path.
            # triggered by local event.
            if paused: # ignore local events while paused.
                continue
            x,y = nextEvent.getData()["target_pos"]
            plane = nextEvent.getData()["plane"]
            plane.newPointSafe(x,y,newTime,netQueue)
        elif nextEvent.getType() == "exactPoint":
            x,y,t,pair,owner = nextEvent.getData()
            plane = getPlane(pair,owner)
            if plane == None:
                print(f"Failed to handle event on plane: pairId:{pair},owner:{owner}")
                continue
            # add exact point to the plane path
            plane.newPointExact(x,y,t)
        elif nextEvent.getType() == "newPlanes":
            count,id1,id2,coord1,coord2 = nextEvent.getData()
            # make planes.
            p1 = datatypes.Plane(id1,count,coord1)
            p2 = datatypes.Plane(id2,count,coord2)
            p1.link(p2)
            addPlane(p1)
            addPlane(p2)
            global planeCount
            planeCount = count + 1 # try to keep variable consistent.
            global nextSpawn
            nextSpawn = newTime + 5000 # to keep it synced, give or take.
        elif nextEvent.getType() == "planeDie":
            selfQueue.put(nextEvent) # because it must occur at a specific time.
        elif nextEvent.getType() == "planeWin":
            selfQueue.put(nextEvent) # because it must occur at a specific time.
        elif nextEvent.getType() == "initialize":
            # initialize a new game on the current state.
            s = nextEvent.getData()
            e = datatypes.Event("initialize",(s,snapshot(newTime)))
            netQueue.put(e)
        elif nextEvent.getType() == "load":
            d = nextEvent.getData()
            newTime = loadSnapshot(d)
            time_delta = 0
            global time_offset
            time_offset = pygame.time.get_ticks() - newTime
        else:
            # event 'someType' ignored.
            print(f"Event: '{nextEvent.getType()}' ignored.")
    
    # handle self queue events.
    selfQueue.put(None) # adds an 'end-of-queue' message
    # this message ensures that the queue does not cycle indefinitely.
    # Yes, this is not good practice.
    while True:
        nextEvent = selfQueue.get()
        if nextEvent == None:
            break
        if nextEvent.getData()[0] > newTime:
            selfQueue.put(nextEvent) # put the event back.
        elif nextEvent.getType() == "pause":
            newTime = nextEvent.getData()[0] # yup, time travel. Oof.
            paused = True
        elif nextEvent.getType() == "planeDie":
            winLoss = -1
            paused = True
            _,owner,pId = nextEvent.getData()
            plane = getPlane(pId,owner)
            if plane == None:
                print(f"Failed to handle event on plane: pairId:{pair},owner:{owner}")
                continue
            plane.doLose() # plane has lost
        elif nextEvent.getType() == "planeWin":
            t,owner,pId = nextEvent.getData()
            plane = getPlane(pId,owner)
            if plane == None:
                print(f"Failed to handle event on plane: pairId:{pair},owner:{owner}")
                continue
            plane.doWin(t) # plane has won
    
    
    # in case the event handler tampered with time progression.
    return newTime,time_delta

# returns a plane, or None if not found.
def getPlane(pair,owner):
    for p in planes[owner]:
        if p.pairId == pair:
            return p
    return None

# a full state of the game. ALL details included.
def snapshot(gameTime):
    # contains game time, win/loss state, pause state,
    # plane count, and a list of planes with their coordinates.
    return (gameTime,startMenu,winLoss,paused,planeCount,planeSnapshot())

# loads a full snapshot, as made by 'snapshot(time)'
def loadSnapshot(data):
    global gameTime
    global startMenu
    global winLoss
    global paused
    global planeCount
    gameTime,startMenu,winLoss,paused,planeCount,ps = data
    loadPlaneSnapshot(ps)
    return gameTime

# a full state of the planes.
def planeSnapshot():
    # get a single list
    ps = []
    for pls in planes:
        for p in pls:
            ps.append(p)
    
    # remove pair duplicates
    rs = []
    for p in ps:
        if p.partner not in rs:
            rs.append(p)
    
    # turn to a nicer format.
    fs = []
    for r in rs:
        fs.append(r.storePairAsList())
    
    return fs

# loads a plane snapshot
def loadPlaneSnapshot(ps):
    global planes
    planes = [[],[],[],[]]
    for p in ps:
        p1 = datatypes.Plane(0,0,(0,0))
        p2 = datatypes.Plane(0,0,(0,0))
        p1.link(p2)
        p1.loadPairFromList(p)
        addPlane(p1)
        addPlane(p2)

# processes events from queue, updates plane positions
# takes the game time to update the game state for.
def updateGameState(newTime, time_delta):
    global running
    global mainMenuActive
    # TODO make this work.
    
    
    # update the plane positions.
    # iterate across entire matrix of planes.
    # (Interestingly enough, since updatePos only takes a game time,
    #  we don't actually have to worry about time deltas.)
    toRemove = [] # planes to remove.
    for planeList in planes:
        for plane in planeList:
            if plane.win > 0:
                # if it has won, don't move it.
                if plane.win < newTime:
                    toRemove.append(plane)
                    # remove it after a few moments of victory.
            else:
                plane.updatePos(newTime, time_delta)
    
    detectCollisions(newTime)
    
    # remove each plane in the 'toRemove' list.
    for plane in toRemove:
        planes[plane.owner].remove(plane)
    
    return

# detects and handles collisions
def detectCollisions(newTime):
    global winLoss
    global current_scene
    global paused
    
    
    # don't run if it isn't the user server.
    # don't run if the game is already over.
    global isUserServer
    global winLoss
    if not isUserServer:
        return
    if winLoss != 0:
        return
    
    
    newList = []
    # make list of planes.
    for planeList in planes:
        for plane in planeList:
            if not plane.win and not plane.lose:
                newList.append(plane)
            if plane.lose:
                winLoss = -1
                paused = True
                e = datatypes.Event("planeDie",(newTime,plane.owner,plane.pairId))
                netQueue.put(e)
    
    # traverse list of planes.
    for i in range(len(newList)):
        for j in range(len(newList)):
            if i <= j:
                continue
            plane = newList[i]
            plane2 = newList[j]
            
            if plane.isColliding(plane2):
                if plane.partner == plane2:
                    plane.doWin(newTime)
                    plane2.doWin(newTime)
                    e1 = datatypes.Event("planeWin",(newTime,plane.owner,plane.pairId))
                    e2 = datatypes.Event("planeWin",(newTime,plane2.owner,plane2.pairId))
                    netQueue.put(e1)
                    netQueue.put(e2)
                else:
                    plane.doLose()
                    plane2.doLose()
                    e1 = datatypes.Event("planeDie",(newTime,plane.owner,plane.pairId))
                    e2 = datatypes.Event("planeDie",(newTime,plane2.owner,plane2.pairId))
                    
                    netQueue.put(e1)
                    netQueue.put(e2)
                    
                    print("game over")
                    winLoss = -1
                    paused = True
                    # add it to be checked for collisions against next planes.
            


def spawnPair(time):
    global planes
    global planeCount
    # owners
    n = len(playerList)
    o1 = random.randint(0,n-1)
    o2 = random.randint(0,n-2)
    if o2 >= o1: # to prevent identical plane IDs
        o2 = o2 + 1
    
    # spawn positions (range 1-3100)
    # keeping them far apart.
    pos1 = random.randint(1,2800)
    pos2 = ((pos1 + random.randint(200,2600)) % 2800) + 1
    
    
    p1,x1,y1 = makePlane(planeCount, o1, pos1)
    p2,x2,y2 = makePlane(planeCount, o2, pos2)
    
    # send 'make planes' event
    data = (planeCount,o1,o2,(p1.x,p1.y),(p2.x,p2.y))
    e = datatypes.Event("spawnPair",data)
    sendEvent(e)
    
    p1.newPointSafe(x1,y1,time,netQueue)
    p2.newPointSafe(x2,y2,time,netQueue)
    planeCount += 1
    p1.link(p2)
    addPlane(p1)
    addPlane(p2)

# makes a plane from 3 attributes:
# pair id,
# owner id,
# position around the edge of the arena to spawn the plane.
# the current time
def makePlane(pairId,ownerId,position):
    xIn = 0
    xOut = 0
    yIn = 0
    yOut = 0
    
    if position < 700:
        xIn = 50 + position
        xOut = xIn
        yIn = 50
        yOut = -50
    elif position < 1400:
        xIn = 750
        xOut = 850
        yIn = 50 + position - 700
        yOut = yIn
    elif position < 2100:
        xIn = 50 + position - 1400
        xOut = xIn
        yIn = 750
        yOut = 850
    else:
        xIn = 50
        xOut = -50
        yIn = 50 + position - 2100
        yOut = yIn
    
    
    res = datatypes.Plane(ownerId,pairId,(xOut,yOut))
    return res,xIn,yIn


# checks if the game is still running
def isRunning():
    return running

def changeRunning(bool):
    running = bool

# determines if the game is playing or paused (or gameover)
def timePassing():
    return not paused and winLoss == 0

# adds a plane to the list of planes.
def addPlane(p):
    global planes
    planes[p.owner].append(p)


# checks if the game state is main menu
def isMainMenu():
    return mainMenuActive

# send an event to the network
def sendEvent(event):
    netQueue.put(event)
