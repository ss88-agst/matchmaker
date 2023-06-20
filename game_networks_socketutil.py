import socket
import select
from threading import Thread

clients = []
debug = 0 # used for debug messages.

fallback_ip = "0.0.0.0"
fallback_port = 0

LOG_MSGS = debug
LOG_MSGS = True

def clientReconnectToFallbackServer(s, roomnum, leader):
    global fallback_ip, fallback_port
    try:
        port = s.getsockname()[1]
        s.close()
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))  
        s.connect((fallback_ip,fallback_port))
        print(f"Connected to {fallback_ip}:{fallback_port}")
    except Exception as e:
        print(f"can't connect to {fallback_ip}:{fallback_port}: {e}")
        exit(1)
    send(s, "hi")

    # Ignore ip/port
    recv(s)
    recv(s)

    fallback_ip = recv(s)
    fallback_port = int(recv(s))
    #recv(s)
    #int(recv(s))

    # send room num
    if (roomnum > -1):
        send(s, f"JOIN {roomnum} {leader}")
        int(recv(s))
    return s

def socketWaitReady(sock):
    if (sock == None):
        raise Exception("Socket does not exist.")
    if (sock.fileno()) < 0:
        return False
    _, ready, _ = select.select([],[sock.fileno()], [])
    if (len(ready) == 0):
        raise Exception("Socket failed.")
    return True

# socket can read at this moment
def socketCanRead(sock):
    if (sock == None):
        raise Exception("Socket does not exist.")
    if (sock.fileno()) < 0:
        return False
    ready, _, _ = select.select([sock.fileno()],[], [], 0)
    return len(ready) != 0

# socket can write at this moment
def socketCanWrite(sock):
    if (sock == None):
        raise Exception("Socket does not exist.")
    if (sock.fileno()) < 0:
        return False
    _, ready, _ = select.select([sock.fileno()],[], [], 0)
    return len(ready) != 0

def openServerSocket(handler, ip, port, fb_ip=None, fb_port=None):
    global fallback_ip, fallback_port
    if (fb_ip != None and fb_port != None):
        fallback_ip = fb_ip
        fallback_port = fb_port 
    serverSock = socket.socket()
    serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSock.bind((ip, port))
    serverSock.listen(5)
    serverSock.settimeout(10)
    print(f"URL-based ID:\n    {socket.gethostname()}:{serverSock.getsockname()[1]}\n")
    print(f"All-purpose ID:\n    {serverSock.getsockname()[0]}:{serverSock.getsockname()[1]}\n\n")
    t = Thread(target=serverListen, args=(serverSock,handler,))
    t.daemon = True
    t.start()
    # returns a triple: server socket, server thread, a list containing a bool used to close the server.
    return (serverSock,t)

# on fail, returns 'None'
def openClientSocket(handler, ip, port):
    global fallback_ip, fallback_port
    try:
        # print(F"Client connecting to {ip}:{port}")
        clientSock = socket.socket() # this can fail, if ip or port number are bad.
        clientSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        clientSock.connect((ip, port))
        
        # Establish friendly relations before we return the valid socket.
        send(clientSock,"hi") # to establish friendly relations.
        # ignore client/server name.
        recv(clientSock)
        recv(clientSock)

        # get fallback name
        fallback_ip = recv(clientSock)
        fallback_port = recv(clientSock)
        
        
        t = Thread(target=clientListen, args=(clientSock,(ip, port),handler))
        t.daemon = True
        t.start()
        return (clientSock,t)
    except:
        return None

def handleConnection(conn, addr, handler):
    # determine if it is a ping or a genuine connection
    firstMsg = recv(conn)
    if firstMsg == "":
        print(f"Ping from {addr[0]}:{addr[1]}")
        return
    elif firstMsg != "hi":
        print(f"Bouncers refused admission to {addr[0]}:{addr[1]}")
        print(f"Message recieved was: \"{firstMsg}\"")
        try:
            conn.close()
        except:
            pass
        return
    print(f"Client {addr[0]}:{addr[1]} connected.")
    # send the connector's own info to it. (because of NAT and such.)
    send(conn,addr[0])
    send(conn,str(addr[1]))

    # Send fallback infos
    send(conn, fallback_ip)
    send(conn, f"{fallback_port}")
    
    # only append genuine connections.
    clients.append(conn)
    try:
        while True:
            msg = recv(conn)
            handler(conn, addr, msg)
            if msg == "": # end of communication
                break
    finally:
        # always remove connections from list when closed.
        print(f"Client {addr[0]}:{addr[1]} closed.")
        clients.remove(conn)

def clientListen(s, addr, handler):
    # handleConnection(s, addr, handler) # old implementation
    while True:
        msg = recv(s)
        handler(s, addr, msg)
        if msg == "": # end of communication
            break

def serverListen(s, handler):
    while True:
        try:
            (conn, addr) = s.accept()
            t = Thread(target=handleConnection, args=(conn, addr, handler,))
            t.daemon = True
            t.start()
        except TimeoutError:
            pass
        except socket.timeout:
            pass
    print("server thread closed")

# send a dictionary over a socket.
def send(sock, msg, toMasterServer=False, roomnum=-1, leader=False) -> socket.socket:
    socketWaitReady(sock)
    if LOG_MSGS:
        print(f"{sock.getsockname()[1]}: Sending {msg}")
    
    bMsg = msg.encode()
    size = len(bMsg)
    bSize = size.to_bytes(length=3,byteorder="big")
    try:
        sock.sendall(bSize)
        sock.sendall(bMsg)
    except ConnectionResetError:
        if(toMasterServer):
            sock = clientReconnectToFallbackServer(sock, roomnum, leader)
            sock.sendall(bSize)
            sock.sendall(bMsg)
    except:
        if debug:
            print("Msg send failed.")
    return sock

def broadcast(msg):
    for client in clients:
        send(client, msg)

# close all connections. Used never, right now.
def closeAll():
    for client in clients:
        client.close()

def recv(sock) -> str:
    try:
        bSize = sock.recv(3)
        size = int.from_bytes(bSize,byteorder="big")
        
        bMsg = sock.recv(size)
        # validate msg size.
        if len(bMsg) != size:
            if debug:
                print("recv interrupted mid-action")
            return ""
        msg = bMsg.decode()
        if LOG_MSGS:
            print(f"{sock.getsockname()[1]}: Recving {msg}")
        return msg
    except:
        if debug:
            print("Could not recv from socket.")
        return ""

# sends a dict over a socket.
# send dicts with primitives only, please!
# no pointers, classes, or such.
def sendDict(sock,d):
    msg = json.dumps(d)
    send(sock,msg)

# gets a dict from a socket.
def recvDict(sock) -> dict:
    msg = recv(sock)
    return json.loads(msg)

def closeall(socks):
    for client in clients:
        client.close()
    for sock in socks:
        sock.close()