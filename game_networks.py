# The network handler.

import game_main # for checking when the game is over, mostly.
from threading import Thread,Lock
import game_networks_socketutil as gns
import json
import time
import datatypes
import socket

incomingQueue = None # the queue of events from the main game.
mainQueue = None # the queue of events to send to the main game.
from game_main import isUserServer # share the global variable with game_main
from game_main import playerNum # share the global variable with game_main
clientSock = None
serverSock = None
players = []
expectedEvent = ""

# a flag which says that a user should not become user-server.
# set when a client re-joins a game after crashing.
skipSelf = False

# tracks who the current server is.
currentServer = -1 # initialized to -1 so that item 0 gets checked first.
# tracks users by IP:port pairing.
# used for IDing disconnects.
users = dict()


ip = None
port = None

def init(theMainQueue, theNetworkQueue):
    global mainQueue, incomingQueue
    mainQueue = theMainQueue
    incomingQueue = theNetworkQueue

# MARK: - Connection Handlers

def handleIncomingMessageP2P(sock, addr, msgRaw):
    if msgRaw == "":
        # TODO make this work.
        # connection is severed. Handle accordingly
        
        # Code for severed connection:
        if game_main.isUserServer:
            # then a client was disconnected.
            try:
                num = users[addr]
            except:
                # Not a client we know.
                return
            del users[addr] # remove entry
            incomingQueue.put(datatypes.Event("playerChange",(num,False)))
            return
        # we need to know if it was the user-server, or not.
        try:
            num = users[addr]
        except:
            return # not the user-server
        # the user-server designation.
        if num == -1:
            del users[addr] # remove entry.
            # lost connection with the user-server, 
            # establish connection with new server.
            incomingQueue.put(datatypes.Event("serverDown", None))
        return
    
    
    # print("got", msgRaw)
    msg = json.loads(msgRaw)
    if game_main.isUserServer:
        # don't directly rebroadcast, since this causes race conditions.
        # (Two sends can overlap, resulting in a garbled message)
        # Instead, put it on the queue, so it can be dealt with by the
        # queue handler.
        t = msg["type"]
        if t != "redirect" and t != "intro":
            incomingQueue.put(datatypes.Event("Broadcast",msgRaw))
    
    # events from network to main.
    if msg["source"] == game_main.playerNum:
        return # this message came from us in the first place.
    if msg["type"] == "goodbye":
        e = datatypes.Event("exit", [])  # send an 'exit' event.
        sendEvent(e)
    elif msg["type"] == "redirect":
        to = msg["to"]
        game_main.playerList[to] = True
        print(f"recieved redirect to {to}")
        del users[addr] # prevent player from being marked as gone.
        incomingQueue.put(datatypes.Event("redirect", to))
    elif msg["type"] == "intro":
        # used to define which client just connected.
        num = msg["num"]
        if num >= len(game_main.playerList):
            # Not actually part of this game.
            sock.close()
            return
        if not game_main.isUserServer:
            # you got the wrong guy.
            # help him find the actual server
            incomingQueue.put(datatypes.Event("helpFindServer", sock))
            return
        users[addr] = num # track their player ID.
        incomingQueue.put(datatypes.Event("playerChange",(num,True)))
        sendEvent(datatypes.Event("initialize",sock)) # request full game state.
    elif msg["type"] == "pause":
        tm = msg["time"] # the moment to pause.
        e = datatypes.Event("toPause", [tm])
        sendEvent(e)
    elif msg["type"] == "resume":
        # resume immediately.
        e = datatypes.Event("toResume", [])
        sendEvent(e)
    elif msg["type"] == "restart":
        # restart immediately.
        e = datatypes.Event("restartRequest", [])
        sendEvent(e)
    elif msg["type"] == "planePair":
        # new planes spawned.
        count = msg["count"]
        id1 = msg["id1"]
        id2 = msg["id2"]
        coord1 = msg["coord1"]
        coord2 = msg["coord2"]
        e = datatypes.Event("newPlanes", (count,id1,id2,coord1,coord2))
        sendEvent(e)
    elif msg["type"] == "exactPoint":
        # add exact point to plane path.
        x = msg["x"]
        y = msg["y"]
        t = msg["time"]
        pair = msg["pId"]
        owner = msg["owner"]
        e = datatypes.Event("exactPoint", (x,y,t,pair,owner))
        sendEvent(e)
    elif msg["type"] == "planeDie":
        tm = msg["time"]
        owner = msg["owner"]
        pId = msg["pId"]
        data = (tm,owner,pId)
        e = datatypes.Event("planeDie",data)
        sendEvent(e)
    elif msg["type"] == "planeWin":
        tm = msg["time"]
        owner = msg["owner"]
        pId = msg["pId"]
        data = (tm,owner,pId)
        e = datatypes.Event("planeWin",data)
        sendEvent(e)
    elif msg["type"] == "playerChange":
        # update the active player list.
        nw = msg["val"]
        for i in range(len(nw)):
            game_main.playerList[i] = nw[i]
    elif msg["type"] == "snapshot":
        data = msg["val"] # so much data, wow.
        e = datatypes.Event("load",data)
        sendEvent(e)
    else:
        print(msgRaw, "ignored")
        

# send event to main.
def sendEvent(event):
    mainQueue.put(event)

# MARK: - Main Function

# the main function. This runs as a loop in the background.
# It handles sockets, and sends events to the main game when needed.
# It takes a list of players (each as a dict with 'ip' and 'port')
# it takes its own identity, as seen from outside
def main(playersInit, sock, me):
    global clientSock
    global serverSock
    global players
    global currentServer
    players = playersInit # assign to global var.
    
    
    for i in range(len(players)):
        if sameId(players[i],me):
            game_main.playerNum = i
            game_main.playerList[i] = True
            break
    # determine if you are the user server.
    # playerNum says which player you are.
    game_main.isUserServer = False # updated automatically almost instantly
    
    
    tryClose(sock)
    # start a server.
    serverSock,_ = gns.openServerSocket(handleIncomingMessageP2P,socket.gethostname(),me[1])
    clientSock = None
    
    if game_main.playerNum != 0:
        time.sleep(3) # give the server a moment to start.
    
    findServer() # identifies the server.
    
    
    # events from main, to network
    while game_main.isRunning():
        while True:
            e = incomingQueue.get()
            if e == None:
                break
            elif e.getType() == "Broadcast":
                # a message was recieved and must be rebroadcast.
                # do this now, to avoid race conditions.
                gns.broadcast(e.getData()) # rebroadcast as-is.
            elif e.getType() == "pause":
                msg = {"type":"pause","time":e.getData()[0]}
                tell(msg)
            elif e.getType() == "resume":
                msg = {"type":"resume",}
                tell(msg)
            elif e.getType() == "exactPoint":
                # r = [x,y,time,self.pairId,self.owner]
                r = e.getData()
                msg = dict()
                msg["type"] = "exactPoint"
                msg["x"] = r[0]
                msg["y"] = r[1]
                msg["time"] = r[2]
                msg["pId"] = r[3]
                msg["owner"] = r[4]
                tell(msg)
            elif e.getType() == "spawnPair":
                count,id1,id2,coord1,coord2 = e.getData()
                msg = dict()
                msg["type"] = "planePair"
                msg["count"] = count
                msg["id1"] = id1
                msg["id2"] = id2
                msg["coord1"] = coord1
                msg["coord2"] = coord2
                tell(msg)
            elif e.getType() == "planeDie":
                tm,owner,pId = e.getData()
                msg = dict()
                msg["type"] = "planeDie"
                msg["time"] = tm
                msg["owner"] = owner
                msg["pId"] = pId
                tell(msg)
            elif e.getType() == "planeWin":
                tm,owner,pId = e.getData()
                msg = dict()
                msg["type"] = "planeWin"
                msg["time"] = tm
                msg["owner"] = owner
                msg["pId"] = pId
                tell(msg)
            elif e.getType() == "restart":
                msg = dict()
                msg["type"] = "restart"
                tell(msg)
            elif e.getType() == "serverDown":
                print("server died, finding new server.")
                game_main.playerList[currentServer] = False
                findServer()
            elif e.getType() == "redirect":
                currentServer = e.getData() - 1
                findServer()
            elif e.getType() == "playerChange":
                num,val = e.getData()
                game_main.playerList[num] = val
                tell({"type":"playerChange","val":game_main.playerList})
            elif e.getType() == "helpFindServer":
                try:
                    s = e.getData() # get the socket.
                    cS = currentServer
                    if (currentServer < 0):
                        cS = 0 # for safety
                    print(f"Redirected user to {cS}")
                    tellOne(s,{"type":"redirect","to":cS,"source":game_main.playerNum})
                    tryClose(s)
                except:
                    # failed to send info; so be it.
                    print("Failed redirect")
                    tryClose(s)
            elif e.getType() == "initialize":
                s,data = e.getData()
                msg = dict()
                msg["type"] = "snapshot"
                msg["val"] = data # so much data, wow.
                tellOne(s,msg)
            else:
                print("network got (and ignored) local event:")
                print(e.getType(),e.getData())
        # do socket stuff
        
    print("network thread shutting down")
    if game_main.isUserServer:
        # send a message saying the server is closing down.
        # tell({"type":"goodbye"})
        # Actually, do nothing.
        pass
    print("network thread done")
    return

# sends an event, depending on if user or user-server
def tell(e):
    # add a 'source' directive, so we can ignore it if it sent back.
    e["source"] = game_main.playerNum
    if game_main.isUserServer:
        broadcast(e)
    else:
        sendEventC(e)

def tellOne(s,e):
    e["source"] = game_main.playerNum
    e2 = json.dumps(e)
    gns.send(s, e2)

# send event (as client)
def sendEventC(e):
    e2 = json.dumps(e)
    gns.send(clientSock, e2)

# broadcast an event
def broadcast(e):
    gns.broadcast(json.dumps(e))

# Connects to the first availible server.
def findServer():
    global currentServer # the server num that just crashed.
    global clientSock
    global skipSelf
    # handles connection, however necessary.
    pCount = len(game_main.playerList)
    
    # loop until a server connection is established.
    while True:
        # handle when we are rejoining an old game but no-one is there.
        if skipSelf and currentServer >= pCount - 1:
            print("Existing game has no living members.\nRoom cache deleted.")
            game_main.running = False # not thread-safe, but there isn't a game anyway.
            return None # also not great, but we are about to exit anyway.
        currentServer = cycleForward(currentServer,pCount)
        if currentServer == game_main.playerNum:
            if skipSelf:
                continue
            # YOU are the new user-server.
            game_main.isUserServer = True
            # Don't make a client socket.
            clientSock = None
            print("I'm the server now.")
            
            # no-one is connected. Mostly used for graphical purposes.
            for i in range(len(game_main.playerList)):
                if i != game_main.playerNum:
                    game_main.playerList[i] = False
            
            return # I'm the user-server.
        if not game_main.playerList[currentServer]:
            # The given player is not currently connected,
            # so don't even check.
            print(f"Ignored server {currentServer}")
            continue
        # try and open connection
        print(f"trying to connect to new server {currentServer}... ",end="",flush=True)
        res = gns.openClientSocket(handleIncomingMessageP2P,players[currentServer][0],players[currentServer][1])
        if res == None:
            # player is no longer online.
            game_main.playerList[currentServer] = False
            print("failed.")
        else:
            sAddr = (players[currentServer][0],players[currentServer][1])
            clientSock,_ = res # unwrap tuple.
            tell({"type":"intro","num":game_main.playerNum})
            print("found.")
            users[sAddr] = -1 # establish as user-server.
            skipSelf = False # we are now a leader candidate again.
            return # connection established.
    
    

# add 1, reset to 0 if it hits the max.
def cycleForward(val,m):
    val += 1
    val = val % m
    return val

# checks if two ID tuples are equivalent.
def sameId(a,b):
    return a[0] == b[0] and a[1] == b[1]

# try and close socket
def tryClose(s):
    try:
        s.close()
    except:
        pass