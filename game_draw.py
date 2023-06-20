"""
The graphics controller.
Manages drawing things on the screen.
"""

import math
import datatypes
import pygame
import game_main
import math
from button import *
from text import *
import random

# Colour constants
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
RED = (255,0,0)

screen = None  # the screen to draw on.
current_scene = None
#class game_draw:

toMainQueue = None  # the queue sent to the main loop

# sets up needed info

def init(theScreen, theMainQueue):
    """Sets up needed info"""
    global screen
    global toMainQueue
    screen = theScreen
    toMainQueue = theMainQueue
    global scenes
    global font
    global display_surface
    global HEIGHT
    global WIDTH
    global maintickables
    global maindrawables
    maintickables = []
    maindrawables = []
    global pausetickables
    global pausedrawables
    pausetickables = []
    pausedrawables = []

    global overtickables
    global overdrawables
    overtickables = []
    overdrawables = []
    HEIGHT = 800
    WIDTH = 800
    current_scene = 0;
    font = pygame.font.Font("font.ttf", 32)
    display_surface = pygame.display.set_mode((800, 800))
    #scenes = [mainMenu(self)]
    create_buttonsMainMenu()
    create_ButtonsPause()
    create_ButtonsGameOver()

    
# draw the entire screen.
# This method is the only one which will be invoked externally.
# This code runs as part of the main loop. Don't put a 'while True' in this!
def changePlay(text):
    e = datatypes.Event("resume",[])
    toMainQueue.put(e)
#def changeInfo(text):
#    game_main.current_scene = 2

def exit(text):
    game_main.current_scene = 1
    game_main.running = False


def resumePlay(Text):
    # send an event to main requesting a resume.
    e = datatypes.Event("resume",[])
    toMainQueue.put(e)

def rePlay(Text):
    e = datatypes.Event("restart",[])
    toMainQueue.put(e)
    resumePlay(Text)

def addButtonMain(buttonAdd):
    maintickables.append(buttonAdd)
    maindrawables.append(buttonAdd)

def addButtonPause(buttonAdd):
    pausetickables.append(buttonAdd)
    pausedrawables.append(buttonAdd)

def addButtonOver(buttonAdd):
    overtickables.append(buttonAdd)
    overdrawables.append(buttonAdd)

def create_buttonsMainMenu():
    playButton = Button("Play", pygame.Rect(WIDTH/2-200,HEIGHT/2-150, 400, 100), (100, 150, 20),changePlay)
    exitButton = Button("Exit", pygame.Rect(WIDTH/2-200, HEIGHT/2+50, 400, 100), (230, 14, 14),exit)
    
   # infoButton = Button("Info", pygame.Rect(WIDTH/2-200, HEIGHT/2, 400, 100), (230, 230, 30),changeInfo)
    addButtonMain(playButton)
   # addButton(infoButton)
    addButtonMain(exitButton)

    fontTitle = pygame.font.Font("font.ttf",108)
    title = Text(display_surface,fontTitle,"Matchmaker",BLACK,WIDTH/2,HEIGHT/2-250,100,100)
    maindrawables.append(title)


def create_ButtonsPause():
    resumeButton = Button("Resume", pygame.Rect(WIDTH/2-200,HEIGHT/2-150, 400, 100), (100, 150, 20),resumePlay)
    exitButton = Button("Exit", pygame.Rect(WIDTH/2-200, HEIGHT/2+50, 400, 100), (230, 14, 14),exit)
    
   # infoButton = Button("Info", pygame.Rect(WIDTH/2-200, HEIGHT/2, 400, 100), (230, 230, 30),changeInfo)
    addButtonPause(resumeButton)
   # addButton(infoButton)
    addButtonPause(exitButton)

    fontTitle = pygame.font.Font("font.ttf",108)
    title = Text(display_surface,fontTitle,"Paused",BLACK,WIDTH/2,HEIGHT/2-250,100,100)
    pausedrawables.append(title)

def create_ButtonsGameOver():
    resumeButton = Button("Play Again", pygame.Rect(WIDTH/2-200,HEIGHT/2-150, 400, 100), (100, 150, 20),rePlay)
    exitButton = Button("Exit", pygame.Rect(WIDTH/2-200, HEIGHT/2+50, 400, 100), (230, 14, 14),exit)
    
   # infoButton = Button("Info", pygame.Rect(WIDTH/2-200, HEIGHT/2, 400, 100), (230, 230, 30),changeInfo)
    addButtonOver(resumeButton)
   # addButton(infoButton)
    addButtonOver(exitButton)

    fontTitle = pygame.font.Font("font.ttf",108)
    title = Text(display_surface,fontTitle,"Game Over",BLACK,WIDTH/2,HEIGHT/2-250,100,100)
    overdrawables.append(title)

def drawAll(scene,planes, newTime):
    """
    Draw the entire screen. This method is the only one which will be invoked externally.
    This code runs as part of the main loop. Don't put a 'while True' in this!
    """

    # scene 0: main menu
    # scene 1: game, and paused, and gameover
    
    
    # draw the planes regardless
    if scene == 0:
        drawBackground()
        for item in maintickables:
            item.tick()
        for item in maindrawables:
            item.draw(display_surface,font)
    elif scene == 1:
        # draw the planes and such
        drawBackground()
        # a sample of how to use the 'myGame' to get info about the state.
    
        # draw each plane
        for planeList in planes:
            for plane in planeList:
                drawPlane(plane, newTime)
        
        # draw plane paths.
        for planeList in planes:
            for plane in planeList:
                drawPlanePath(plane)
        
        # draw plane paths.
        for planeList in planes:
            for plane in planeList:
                drawPlaneBar(plane)
        
        # draw loss screen and pause on top of main screen.
        if game_main.paused:
            if game_main.startMenu == True:
                for item in maintickables:
                    item.tick()
                for item in maindrawables:
                    item.draw(display_surface,font)
            elif game_main.winLoss == -1:
                # game over screen.
                for item in overtickables:
                    item.tick()
                for item in overdrawables:
                    item.draw(display_surface,font)
            else:
                # pause screen.
                for item in pausetickables:
                    item.tick()
                for item in pausedrawables:
                    item.draw(display_surface,font)
        drawPlayers()
    
    
    pygame.display.flip() # pushes the update to the screen



def drawBackground():
    screen.fill((151, 232, 164))
    seed = random.randint(0,10000000)
    random.seed(15)
    x = 6
    y = 15
    while (x<800):
        while (y < 800):
            drawGrass(x,y)
            y = y+12*random.randrange(1,20)
        x = x+15*random.randrange(1,20)
        y = 15*random.randrange(1,5)

    x = 10
    y = 10
    while (x<800):
        while (y < 800):
            drawFlower(x,y)
            y = y+25*random.randrange(1,20)
        x = x+20*random.randrange(1,20)
        y = 10*random.randrange(1,5)

    random.seed(seed)

def drawGrass(x,y):
    grassColour = (73, 110, 79)
    pygame.draw.line(screen,grassColour,(x,y-15),(x,y),2)
    pygame.draw.line(screen,grassColour,(x-6,y-13),(x,y),2)
    pygame.draw.line(screen,grassColour,(x+6,y-13),(x,y),2)

def drawFlower(x,y):
    pygame.draw.line(screen,(73, 110, 79),(x,y),(x,y+15),2)
    pygame.draw.ellipse(screen,RED,(x,y-3,10,6))
    pygame.draw.ellipse(screen,RED,(x-10,y-3,10,6))
    pygame.draw.ellipse(screen,RED,(x-3,y-10,6,10))
    pygame.draw.ellipse(screen,RED,(x-3,y,6,10))
    pygame.draw.circle(screen,(255, 255, 0),(x,y),3)
    pygame.draw.circle(screen,BLACK,(x,y),4,1)
# takes a plane object, and draws it.
# This is a wrapper on drawSinglePlane, included for convenience.

def drawAccessories(x,y,pair):
    if pair%6 == 3:
        pygame.draw.rect(screen,BLACK,(x-25,y-25,50,5))
        pygame.draw.rect(screen,BLACK,(x-20,y-45,40,20))
    elif pair%6 ==1:
        pygame.draw.polygon(screen,BLUE,((x,y+20),(x-15,y+10),(x-15,y+30)))
        pygame.draw.polygon(screen,BLUE,((x,y+20),(x+15,y+10),(x+15,y+30)))              
    elif pair%6 == 2:
        pygame.draw.rect(screen,BLACK,(x-15,y-12,14,14),2)
        pygame.draw.rect(screen,BLACK,(x+1,y-12,14,14),2)  
        pygame.draw.line(screen, BLACK,(x-15,y-6),(x-22,y-8),2)  
        pygame.draw.line(screen, BLACK,(x+15,y-6),(x+22,y-8),2)
        pygame.draw.line(screen,BLACK,(x+1,y-6),(x-1,y-6),2)
    elif pair%6 == 4:
        pygame.draw.rect(screen,(255,192,203),(x-5,y+14,10,10))
        pygame.draw.circle(screen,(255,192,203),(x,y+24),5)    
        pygame.draw.line(screen,BLACK,(x,y+15),(x,y+24))
    elif pair%6 == 0:
        pygame.draw.circle(screen, BLACK,(x-3,y+3),3)
        pygame.draw.circle(screen,BLACK,(x+3,y+3),3)
        pygame.draw.polygon(screen,BLACK,((x-6,y+3),(x-3,y+6),(x-12,y+6)))
        pygame.draw.polygon(screen,BLACK,((x+6,y+3),(x+3,y+6),(x+12,y+6)))



def drawPlane(p, newTime):
    # the plane position
    x = p.x
    y = p.y
    rotation = None # assigned further down
    color = getColor(p.owner,p.win,p.lose)
    
    dx = p.partner.x - x
    dy = p.partner.y - y
    if dx == 0:
        # handle special cases of angles.
        if dy >= 0:
            rotation = 90
        else:
            rotation = -90
    else:
        rotation = math.degrees(math.atan(dy/dx))
        if dx < 0:
            rotation = rotation + 180
        
    
    # 'rotation' is the angle, in degrees, counterclockwise from +x
    # color range is rgb, 0-255
    
    # a circle
    pygame.draw.circle(screen, color,(x,y),25)
    #pygame.draw.circle(screen, (100,100,100), (x-8,y-5),5)
    #pygame.draw.circle(screen, (100,100,100), (x+8,y-5),5)
    #pygame.draw.circle(screen, WHITE, (x-8,y-5),4 )
    #pygame.draw.circle(screen, WHITE, (x+8,y-5),4 )
    pygame.draw.circle(screen, BLACK, (x-8,y-5),3 )
    pygame.draw.circle(screen, BLACK, (x+8,y-5),3 )
    pygame.draw.arc(screen,BLACK,(x-12.5,y,25,15),math.radians(190),math.radians(350),2)
    drawAccessories(x,y,p.pairId)
    # math for a triangle
    pointOneX = 25 * math.cos(math.radians(rotation-20)) + x
    pointOneY = 25 * math.sin(math.radians(rotation-20)) + y

    pointTwoX = 35 * math.cos(math.radians(rotation)) + x
    pointTwoY = 35 * math.sin(math.radians(rotation)) + y

    pointThreeX = 25 * math.cos(math.radians(rotation+20)) + x
    pointThreeY = 25 * math.sin(math.radians(rotation+20)) + y

    #pygame.draw.polygon(screen, (0,0,0),((pointOneX,pointOneY),(pointTwoX,pointTwoY),(pointThreeX,pointThreeY)))


# draws a bar saying how angry the plane is.
def drawPlaneBar(p):
    if p.sad == 0:
        return # no sad, no bar.
    if p.win:
        return # win, no sad
    
    x = p.x
    y = p.y
    
    # bar outline
    pygame.draw.rect(screen, (100,100,100), (x-18,y+35,36,7))
    # calculate how much life left.
    r = p.sad / p.maxSad * 34
    # draw 'anger remaining' bar
    pygame.draw.rect(screen, (255,0,0), (x-17,y+36,r,5))

# determines what color to draw the plane
def getColor(owner,win,lose):
    if win:
        return (0,250,0) # green
    elif lose:
        return (250,0,0) # red
    elif owner == 0:
        return (250,250,250) # white
    elif owner == 1:
        return (220,0,220) # purple
    elif owner == 2:
        return (252, 123, 3) # orange
    elif owner == 3:
        return (0,0,250) # blue
    

# draw a plane path.
def drawPlanePath(plane):
    
    if not plane.moving():
        return
    # get a list of coordinates.
    path = plane.getDrawablePath()
    # draw a black line on the screen, where it is no a closed object, with 
    # 'path' as the list of points, with a width of 2 pixels.
    pygame.draw.lines(screen, BLACK, False, path, 2)

# Shows which players are online
def drawPlayers():
    for i in range(len(game_main.playerList)):
        numofCOM = 0;
        c = getColor(i,0,0)
        if game_main.playerList[i]:
            pygame.draw.rect(screen, c, (150*i+100,770,100,30))
            playerNum = Text(display_surface,font,"Player " + str(i+1),BLACK,150*i+150,760,100,30)
            playerNum.draw(display_surface,font)
        else:
            numofCOM = numofCOM + 1
            pygame.draw.rect(screen, c, (150*i+100,770,100,30))
            playerNum = Text(display_surface,font,"COM " + str(numofCOM),BLACK,150*i+150,760,100,30)
            playerNum.draw(display_surface,font)
        if game_main.playerNum == i:
            # this is me
            pygame.draw.rect(screen, (50,50,50), (150*i+100,770,100,5))
            playerNum = Text(display_surface,font,"Player " + str(i+1),BLACK,30,775,100,100)
            if game_main.paused:
                pygame.draw.polygon(screen, c, ((0,0),(0,100),(100,0)))
                pygame.draw.polygon(screen, c, ((800,800),(800,700),(700,800)))
                pygame.draw.polygon(screen, c, ((800,0),(700,0),(800,100)))
                pygame.draw.polygon(screen, c, ((0,800),(0,700),(100,800)))
                pygame.draw.line(screen, BLACK, (0,100),(100,0),2)
                pygame.draw.line(screen, BLACK, (800,700),(700,800),2)
                pygame.draw.line(screen, BLACK, (700,0),(800,100),2)
                pygame.draw.line(screen, BLACK, (0,700),(100,800),2)
            else:
                pygame.draw.polygon(screen, c, ((0,0),(0,50),(50,0)))
                pygame.draw.polygon(screen, c, ((800,800),(800,750),(750,800)))
                pygame.draw.polygon(screen, c, ((800,0),(750,0),(800,50)))
                pygame.draw.polygon(screen, c, ((0,800),(0,750),(50,800)))
                pygame.draw.line(screen, BLACK, (0,50),(50,0),2)
                pygame.draw.line(screen, BLACK, (800,750),(750,800),2)
                pygame.draw.line(screen, BLACK, (750,0),(800,50),2)
                pygame.draw.line(screen, BLACK, (0,750),(50,800),2)
            playerNum.draw(display_surface,font)
            pygame.draw.rect(screen,BLACK,(0,0,800,800),2)

# draw a pause icon in the top-left.
def drawPause():
    pygame.draw.rect(screen, (10,10,10), (20,20,100,100))

    if False:
        # yellow
        c = (252, 236, 0)
    else:
        # white
        c = (230,230,230)
    
    pygame.draw.rect(screen, c, (40,30,20,80))
    pygame.draw.rect(screen, c, (80,30,20,80))
