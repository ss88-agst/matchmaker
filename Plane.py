import pygame


class Plane(pygame.sprite.Sprite):
    def __init__(self, speed, controller, position):
        self.speed = speed  # int, controls the speed at which the plane moves (could also probably be used for rendering size in graphics)
        self.trajectory = None  # list of 2-tuples dictating the path the plane is moving on in line segments
        self.controller = controller  # int, represents who controls which plane.  -1 means the AI controller controls the plane
        self.position = position  # tuple descriping position of the plane
