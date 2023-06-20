# some useful datatypes.

import queue # a threadsafe queue object
import math # for sqrt().

 # the plane speed factor.
 # Measured in pixels per milliseconds (I think)
PLANE_SPEED_FACTOR = 0.1

# a single plane. Contains all sorts of useful info.
class Plane:
    radius = 25 # a global constant. Do not change.
    
    
    owner = 0 # the player who can control it. 0-3
    pairId = 0 # which pair ID it is part of. Partners share a pairId
    partner = None # the plane it wants to collide with
    x = 0 # the x coordinate the plane is currently at.
    y = 0 # the y coordinate the plane is currently at.
    sad = 0 # Grows when not moving, shrinks when moving.
    maxSad = 10000 # 10 seconds stationary
    
    # a variable tracking if it has found its partner. If 0, it hasn't won.
    # otherwise, it contains a timestamp of when it should disappear.
    win = 0
    # Tracks if the plane has hit a bad target.
    lose = 0
    
    # the previous coordinate and timestamp.
    # Used to interpolate current position.
    oldP = (0,0,0)
    
    # DO NOT MODIFY PATHS DIRECTLY. USE THE GIVEN FUNCTIONS!
    # invariant: paths must never be empty!
    path = None # A list of coordinate pairs, each also timestamped with ETAs
    pathAsLine = None # A list of coordinate pairs without timestamps. Used for drawing the path line.
    
    # initializer. See above attributes to see what is being initialized.
    def __init__(self, owner, pairNum, startingCoord):
        self.owner = owner
        self.pairId = pairNum
        self.x,self.y = startingCoord # expect startingCoord = (x,y)
        
        # add starting coordinate to path.
        self.path = [(self.x,self.y,0)]
        self.pathAsLine = [startingCoord]
    
    # link a plane and its partner. Links both ways
    def link(self, other):
        self.partner = other
        other.partner = self
    
    # checks if two planes are colliding
    def isColliding(self, other):
        return self.dist(other.x,other.y) <= self.radius * 2
    
    # when it wins
    def doWin(self,time):
        self.win = time + 1000
        self.stop()
    
    # when it loses
    def doLose(self):
        self.lose = 1
        self.stop()
    
    # stop moving
    def stop(self):
        self.path = [(self.x,self.y,0)]
        self.pathAsLine = [(self.x,self.y)]
    
    # checks the cartesian distance between a plane's center and a point.
    def dist(self,x,y):
        return math.sqrt((self.x-x)**2 + (self.y-y)**2)
    
    # checks if a point is inside the plane's hitbox.
    # Used for processing 'click' events
    def contains(self,x,y):
        return self.dist(x,y) <= self.radius
    
    # add a new point to the path.
    # Requires an exact x,y, and arrive-time
    def newPointExact(self,x,y,time,netQueue=None):
        if netQueue != None:
            # add event to queue.
            r = [x,y,time,self.pairId,self.owner]
            e = Event("exactPoint",r)
            netQueue.put(e)
        
        if self.path[0][2] >= time:
            # the entire path, for some reason, is obsolete.
            # Remove it all.
            self.path = []
            self.pathAsLine = []
        elif time <= self.path[-1][2]:
            # overwrite any points which need to be overwritten.
            r = -1 # how many points to remove
            while time <= self.path[r][2]:
                r -= 1 # remove another point
            # removes overwritten points
            self.path = self.path[:r]
            self.pathAsLine = self.pathAsLine[:r]
        # add the new point to each path.
        self.path.append((x,y,time))
        self.pathAsLine.append((x,y))
    
    # adds a new point to the end of the path.
    # calculates the timestamp based on the previous point.
    # be careful with this function, since there might be rounding errors, so
    # don't input values close to existing points.
    def newPointLazy(self,x,y,netQueue=None):
        (lx,ly,lt) = self.path[-1]
        d = math.sqrt((lx-x)**2+(ly-y)**2)
        tDelta = d / PLANE_SPEED_FACTOR # time to reach destination
        t = lt + tDelta # the time the destination is reached.
        self.newPointExact(x,y,t,netQueue) # add the point the conventional way.
    
    # like newPointLazy, but also takes the current game time.
    # If adding the point would cause the plane to teleport,
    # then a second point is added at the current position to prevent that.
    # Use this function only for click-and-drag events on the local machine.
    # finally, optionally takes a netQueue to notify of the new point.
    def newPointSafe(self,x,y,t,netQueue=None):
        if self.path[-1][2] <= t:
            self.newPointExact(self.x,self.y,t,netQueue)
        self.newPointLazy(x,y,netQueue)
        
    
    # calculates the plane position based on the game time.
    def updatePos(self, time, time_delta):
        while self.pathLen() > 1 and self.nextPoint()[2] <= time:
            self.oldP = self.popNextPoint()
        
        # handle the 'reached destination' case
        if self.pathLen() == 1 and self.nextPoint()[2] <= time:
            self.x,self.y,_ = self.nextPoint() # go to the end of the path
            self.sad += time_delta
            if self.sad >= self.maxSad:
                from game_main import isUserServer # yup, a conditional import.
                if isUserServer:
                    self.doLose()
                else:
                    self.sad = self.maxSad
            return
        elif self.sad == 0:
            pass # already happy
        else:
            self.sad = max(self.sad - time_delta, 0) # reduce anger.
        
        # otherwise, we are somewhere between oldP and nextPoint
        p1 = self.oldP
        p2 = self.nextPoint()
        
        # if the points are the same, we need to handle this separately.
        # otherwise, we get divide by zero.
        if p1[2] == p2[2]:
            self.x,self.y,_ = p1
            return
        
        # current time is between the two. Interpolate position based on this.
        t1 = p1[2]
        t2 = time
        t3 = p2[2]
        
        # offset the times so that t1=0
        t2 -= t1
        t3 -= t1
        # solve for how close t2 is to t3.
        r = t2 / t3
        # 'r' contains a number from 0-1, saying how far along the line segment we are.
        # use 'r' to get a weighted average of the two points.
        # this is our result.
        self.x = (p2[0] * r) + (p1[0] * (1-r))
        self.y = (p2[1] * r) + (p1[1] * (1-r))
        return # nothing more to do.
        
    
    # return the next point and the time it should arrive at.
    def nextPoint(self):
        return self.path[0]
    
    # return next point (with timestamp).
    # removes points from both paths.
    # will not pop the last point.
    def popNextPoint(self):
        res = self.path[0]
        if self.pathLen() == 1:
            return res # cannot pop last point off
        self.path = self.path[1:]
        self.pathAsLine = self.pathAsLine[1:]
        return res
    
    # says how many points are remaining.
    def pathLen(self):
        return len(self.path)
    
    # returns a path in a format compatible with PyGame line drawing.
    def getDrawablePath(self):
        return [(self.x,self.y)] + self.pathAsLine
    
    def moving(self):
        return self.x != self.path[-1][0] or self.y != self.path[-1][1]
    
    # turns a plane pair to a single list
    def storeAsList(self):
        return (self.oldP,
            self.owner,
            self.pairId,
            self.sad,
            self.win,
            self.lose,
            self.path)
    
    # turns a plane pair to a single list
    def storePairAsList(self):
        return (self.partner.storeAsList(),
            self.oldP,
            self.owner,
            self.pairId,
            self.sad,
            self.win,
            self.lose,
            self.path)
    
    # load data into plane
    def loadFromList(self,data):
        self.oldP,self.owner,self.pairId,self.sad,self.win,self.lose,self.path = data
        self.pathAsLine = []
        for coord in self.path:
            x,y,t = coord
            self.pathAsLine.append((x,y))
    
    # load data into plane pair
    def loadPairFromList(self,data):
        x,self.oldP,self.owner,self.pairId,self.sad,self.win,self.lose,self.path = data
        self.partner.loadFromList(x)
        self.pathAsLine = []
        for coord in self.path:
            x,y,t = coord
            self.pathAsLine.append((x,y))
    

# a threadsafe queue. Put or get items on it. If you can't get an item, then it returns None
class EventQueue:
    myQueue = None
    
    def __init__(self):
        self.myQueue = queue.Queue(1000) # a threadsafe queue with a thousand elements.
    
    # get an event from the queue.
    # returns 'None' if no element remains.
    def get(self):
        try:
            # get an element, or throw an exception if no element is found
            res = self.myQueue.get(False) # the 'False' means "don't block"
            return res
        except:
            return None
    
    # put an item on the queue.
    # thread-safe.
    def put(self,item):
        self.myQueue.put(item) # Hello there.

# an event for the EventQueue
class Event:
    _tType = None # the type (can be a string if you want)
    _tData = None # the data (whatever makes sense; you decide)
    
    # make an event. Takes type of the event and any needed data.
    def __init__(self,theType,theData):
        self._tType = theType
        self._tData = theData
    
    # returns the type of the event.
    def getType(self):
        return self._tType
    
    # returns the data linked to the event.
    def getData(self):
        return self._tData
    
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Event):
            return False
        return self._tType == __o._tType and self._tData == __o._tData
    
    def toString(self):
        return f"{self._tType}: {self._tData}"
    
class Room:
    
    players = []

    def addPlayer(self, player):
        self.players.append(player)
    
    def removePlayer(self, player):
        self.players.remove(player)
    
    def leader(self):
        if (len(self.players) == 0):
            raise ValueError() 
        return self.players[0]

    def __init__(self, id):
        self.players = []
        self.id = id

    def __dict__(self) -> dict:
        #return {'id':self.id, 'players':len(self.players)}
        return {'id':self.id, 'players':[x.__dict__() for x in self.players], 'player_count':len(self.players)}

class Player:
    def __init__(self, ip, port, sock) -> None:
        self.ip = ip
        self.port = port
        self.sock = sock
    
    def inList(self,l):
        for other in l:
            if self.same(other):
                return True
        return False
    
    @classmethod
    def fromDict(self, dict):
        return self(dict['ip'], dict['port'], None)
    
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Player):
            return False
        return self.ip == __o.ip and self.port == __o.port
    
    def __dict__(self) -> dict:
        return {'ip':self.ip, 'port':self.port}