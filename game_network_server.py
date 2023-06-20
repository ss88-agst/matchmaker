from game_networks_socketutil import *
from game_setup import parseToServer
from datatypes import *
import json
import random

rooms = []

# commands:
# LIST
#   lists rooms
# JOIN <roomNum>
#   joins an existing room
# NEW
#   starts a new room
# START
#   starts the game.


def leaveRoom(player):
    currentRooms = [x for x in rooms if player in x.players]
    # print(currentRooms)
    for room in currentRooms:
        # print(f"{player.port} trying to leave room {room.id} with current players {json.dumps([x.__dict__() for x in room.players])}")
        room.removePlayer(player)
        if (len(room.players) == 0):
            rooms.remove(room)

def joinRoom(sock, player, id, leader=False):
    if (id not in [x.id for x in rooms]):
        rooms.append(Room(id))
        #return f"Invalid room. Type LIST to see available rooms."
    
    # leave existing rooms
    leaveRoom(player)

    # join requested room
    requestedRoom = [x for x in rooms if x.id == id][0]
    if (leader):
        requestedRoom.players.insert(0, player)
    else:
        requestedRoom.addPlayer(player)
    #sendToFallbackServer(sock, f"UPDATE {json.dumps({'id':id, 'player':player.__dict__()})}")
    return f"{id}"

# handler for server responses, specifically
def handler(conn, addr, msg):
    global rooms
    currentPlayer = Player(addr[0], addr[1], conn)
    
    # if player already assigned to room, save socket
    for room in rooms:
        for player in [x for x in room.players if x == currentPlayer]:
            player.sock = conn
            print(f"Matched player.")

    requestData = msg.split(' ', 1)
    if (msg == ''):
        leaveRoom(currentPlayer)
        print("connection closed")
        conn.close()
        return
    if (requestData[0] == "LIST"):
        response = json.dumps([x.__dict__() for x in rooms])
    elif (requestData[0] == "JOIN"):
        if (len(requestData) < 2):
            response = f"Syntax: JOIN <code>"
        else:
            deepdata = requestData[1].split(' ')
            leader = len(deepdata) == 2 and deepdata[1] == "True"
            response = joinRoom(conn, currentPlayer, int(deepdata[0]), leader)
    elif (requestData[0] == "NEW"):
        roomnum = 0
        while True:
            #roomnum = random.randrange(100000, 1000000)
            roomnum = random.randrange(10, 99) # a more sensible range.
            if (roomnum not in rooms):
                break

        rooms.append(Room(roomnum))
        msg = joinRoom(conn, currentPlayer, roomnum, True)
        response = msg
    elif (requestData[0] == "START"):
        relevantRooms = [x for x in rooms if x.leader() == currentPlayer]
        if (len(relevantRooms) == 0):
            relevantRooms = [x for x in rooms if currentPlayer in x.players]
            response = f"You are not the leader."
        else:
            response = json.dumps([x.__dict__() for x in relevantRooms[0].players])
            for player in relevantRooms[0].players:
                #if (player != currentPlayer): # send to all players.
                send(player.sock, response)
            rooms.remove(relevantRooms[0])
    elif (requestData[0] == "UPDATE"):
        jsondata = json.loads(requestData[1])
        player = Player.fromDict(jsondata['player'])
        id = int(jsondata['id'])
        leaveRoom(player)

        # does room exist?
        if (id not in [x.id for x in rooms]):
            rooms.append(Room(id))
        
        joinRoom(conn, player, jsondata['id'])

        print(f"Updating database.")
        response = "OK"
    elif (requestData[0] == "PING"):
        response = "PONG"
    else:
        return
    send(conn, response)

def main():
    fb_addr = input("Please enter a fallback IP: ")
    (fb_ip, fb_port) = parseToServer(fb_addr, False)
    if (fb_ip == None or fb_port == None):
        print("Opting for no fallback server.")
    (sock, thread) = openServerSocket(handler, socket.gethostname(), 0, fb_ip, fb_port)
    return (sock, thread)