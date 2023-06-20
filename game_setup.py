
import os.path # for file management.
import os
import socket
import game_networks_socketutil as gns
import json
import time
from threading import Thread

cache = "last_server.tmp"
roomCache = "roomCache.tmp"

# returns a socket to the root server, otherwise exits.
def setup():
    ip,port = tryCache(False)
    
    # if cache was not used, get manual input:
    if ip == None:
        # get input
        idPair = input("Please enter server ID, as 'ip:port':\n")
        # 
        ip,port = parseToServer(idPair,True)
        if ip == None:
            exit(1)
    
    # ip and port have both been chosen.
    # return them, and cache the result.
    
    return (ip,port)

# same as setup and handleServer,
# but does everything automatically without user intervention.
def expedite():
    ip,port = tryCache(True)
    if ip == None:
        ip,port = parseToServer(input("enter new ip:port\n"),False)
        if ip == None:
            print("Bad input")
            exit(1)
    
    # we now have ip and port.
    try:
        s = socket.socket()
        s.connect((ip,port))
        makeCache(ip,port)
    except:
        print("can't connect")
        exit(1)
    s = gns.send(s,"hi")
    myName = gns.recv(s)
    myPort = int(gns.recv(s))

    gns.fallback_ip = gns.recv(s)
    gns.fallback_port = int(gns.recv(s))
    
    # get list
    s = gns.send(s,"LIST")
    res = gns.recv(s)
    ls = json.loads(res)
    if len(ls) == 0:
        s = gns.send(s,"NEW")
        gns.recv(s)
        input("you are leader, enter to start")
        s = gns.send(s,"START")
        res = json.loads(gns.recv(s))
        res = fixUp(res)
        return (s,res,(myName,myPort))
    else:
        # join first room.
        s = gns.send(s,"JOIN " + str(ls[0]["id"]))
        print("you are guest, wait for leader to start.")
        gns.recv(s) # ignore int result.
        res = json.loads(gns.recv(s))
        res = fixUp(res)
        return (s,res,(myName,myPort))


# handles interface with server to get needed room.
# gets server ip and port
# returns the socket to use for subsequent actions, as well as
# the list of players and their sockets.
def handleServer(ip, port):
    s = socket.socket()
    try:
        s.connect((ip,port))
        makeCache(ip,port)
    except:
        print("Could not establish connection with server.")
        print("Please make sure the ip and port are correct,")
        print("and that there are no NAT routers between you and the server")
        print("NAT (network address translation) routers stop the server from correctly identifying")
        print("it's own IP address, which can cause issues.")
        print("If the server IP address is 127.whatever, there's probably a NAT router in the network.")
        print("In this case, you will need to be on the same local network in order to communicate with the server.")
        exit(1)
    
    # establish friendly relations
    s = gns.send(s,"hi")
    myName = gns.recv(s)
    myPort = int(gns.recv(s))

    gns.fallback_ip = gns.recv(s)
    gns.fallback_port = int(gns.recv(s))
    
    print("Connected to the server.")
    print("----------------------------------------")
    printHelp()

    roomnum = -1

    while True:
        command = input("$ ").lower()
        if command == "help":
            printHelp()
        if command == "exit":
            print("connection closed")
            import sys
            sys.exit(0)
        elif command == "list":
            s = gns.send(s,"LIST", True)
            res = gns.recv(s)
            ls = json.loads(res)
            if ls == []:
                print("no rooms open, type 'new' to make a room")
            for l in ls:
                num = l["id"]
                ply = l["player_count"]
                print(f"room {num}\t({ply} players)")
        elif command == "new":
            s = gns.send(s,"NEW")
            roomnum = int(gns.recv(s))
            print(f"Room number: {roomnum}")
            print("You are the leader.")
            print("press enter to start the game.")
            input()
            s = gns.send(s,"START", True, roomnum, True)
            res = gns.recv(s)
            if (res == "You are not the leader."):
                print(res)
                continue
            else:
                res = json.loads(gns.recv(s))
                res = fixUp(res)
                # print(res)

                # make sure every player has reconnected to master server
                time.sleep(5)

                return (s,res,(myName,myPort))
        elif len(command) >= 4 and command[:4] == "join":
            try:
                param = command[5:]
            except:
                print("please include room number as parameter!")
                continue
            try:
                roomnum = int(param)
            except:
                print("room number must be integer!")
                continue
            if roomnum < 0:
                print("room number must be a positive integer!")
                continue
            s = gns.send(s,"JOIN " + str(roomnum), True, roomnum)
            res = gns.recv(s)
            if res[0] == 'I':
                print("That room is not open.")
                print("To make a new room, type 'new'.")
                print("To see existing rooms, type 'list'.")
                continue # nothing more to do here.
            print("Room joined. Please wait for the leader to start the game.")
            
            # Ping server until game starts
            while True:
                s = gns.send(s, "PING", True, roomnum)
                res = gns.recv(s)
                if (res != "PONG" and res != ""):
                    break
                time.sleep(4)
            print(f"Actual response was: '{res}'")
            res = json.loads(res)
            res = fixUp(res)
            return (s,res,(myName,myPort))
        elif command == "":
            continue
        else:
            print("Command not recognized. type 'help' for a list of commands")
        

# turns a list of dicts into a list of tuples.
# much nicer
def fixUp(ds):
    res = []
    for d in ds:
        res.append((d["ip"],d["port"]))
    return res


def printHelp():
    print("Please select a room. Use the following commands:")
    print()
    print("list                Returns a list of valid room numbers")
    print("join <room number>  joins a room that has already been created")
    print("new                 Makes a new room, and become the leader.")
    print("                    You will be automatically assigned a number")
    print("exit                Exits game setup")
    print("help                Shows this message again")
    # note: START is handled as an automatic thing.

# returns (ip,port) or (None,None),
# depending on if the cache was used
# if 'fast' is True, then attempt the cache first always.
def tryCache(fast):
    global cache
    # if no file, then ignore.
    if not os.path.isfile(cache):
        return (None,None)
    
    # read file
    fCont = ""
    with open(cache) as file:
        fCont = file.read() # read entire file to string.
    
    # parse file
    ip,port = parseToServer(fCont,False)
    if ip == None:
        print("Cached server name is corrupt, cache cleared...")
        delCache()
        return (None, None)
    
    # test if server is still open.
    print("Checking if cached server is up-to-date...",end='',flush=True)
    if not testExists(ip,port):
        print("\nCached server name is no longer running, cache cleared.")
        delCache()
        return (None, None)
    print(" done.")
    
    # ask user if they want to use the cache
    print(f"Cached server ID: ({ip}:{port})")
    if fast:
        res = "y"
        print("Use the cached server? (y/n)\ny\n")
    else:
        res = input("Use the cached server? (y/n)\n")
    if res != "y" and res != "Y" and res != "Yes" and res != "yes":
        # cache is only deleted if it becomes obsolete, or if it is overwritten.
        return (None,None)
    
    # result is yes, return the desired server
    return (ip,port)
        

# tries the room cache.
def tryRoomCache():
    try:
        with open(roomCache) as file:
            f = file.read()
        import json
        res = json.loads(f)
        r = input("Continue existing game? (y/n)\n")
        if r != "y":
            return None
        else:
            return res
    except:
        try:
            os.remove(roomCache)
        except:
            pass
        return None # fail
    
    

def makeRoomCache(players,me):
    try:
        p = json.dumps((players,me))
        with open(roomCache,"w") as file:
            file.write(p)
    except:
        print("could not cache room info")

def delRoomCache():
    try:
        os.remove(roomCache)
    except:
        pass

# makes a cache file from the IP and Port number
def makeCache(ip,port):
    global cache
    try:
        with open(cache,"w") as file:
            file.write(ip + ":" + str(port))
    except:
        print("could not cache server name")


# delete cache
def delCache():
    global cache
    try:
        os.remove(cache)
    except:
        print("failed to remove", cache)

# takes a string and a flag on if to print errors,
# returns an IP and port number
# returns (None,None) if there was an issue
def parseToServer(s, showErrors):
    ids = s.split(":") # auto-split on spaces
    # remove unneded spaces before and after ip and port number
    if len(ids) != 2:
        if showErrors:
            print("Input should be entered as <ip>:<port number>")
            print("You should be able to copy this from the server log")
        return (None,None)
    
    ids[0] = ids[0].strip()
    ids[1] = ids[1].strip()
    
    port = 0
    try:
        port = int(ids[1])
    except:
        if showErrors:
            print("could not resolve port number.")
        return (None,None)
    
    return (ids[0],port) # return desired result.

# tests if a server can be connected to.
def testExists(ip,port):
    try:
        with socket.socket() as s:
            s.connect((ip,port))
        return True
    except:
        return False

# sets the main game player list
def setupPlayerCount(players):
    # yup, imports inside functions are totally good practice.
    from game_main import playerList
    for p in players:
        playerList.append(True)
    
    
    # the game must have at least 2 players.
    # This is because of how plane IDs are stored;
    # a single player would produce spawning conflicts.
    if len(playerList) == 1:
        playerList.append(False)