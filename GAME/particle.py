import math
import random
import pygame


class Particle:
    def __init__(self, position, color=(255, 255, 255), speed=100.0, lifetime=0.5):
        if lifetime < 0.0:
            raise ValueError(
                "lifetime must be greater than or equal to zero."
            )

        self.position = pygame.Vector2(position)

        angle = random.uniform(0.0, math.tau)

        direction = pygame.Vector2(math.cos(angle), math.sin(angle))

        self.velocity = (direction * random.uniform(speed * 0.3, speed))

        self.lifetime = float(lifetime)
        self.initial_lifetime = float(lifetime)

        self.color = color

        self.alive = True

    def update(self, dt):
        if not self.alive:
            return

        self.position += (self.velocity * dt)

        self.lifetime -= dt

        if self.lifetime <= 0.0:
            self.lifetime = 0.0
            self.alive = False

    def is_alive(self):
        return self.alive

    def draw(self, surface):
        if not self.alive:
            return

        if self.initial_lifetime > 0.0:
            alpha = (self.lifetime / self.initial_lifetime)

        else:
            alpha = 0.0

        alpha = max(0.0, min(1.0, alpha))

        color = tuple(int(channel * alpha) for channel in self.color)

        pygame.draw.circle(surface, color, (round(self.position.x), round(self.position.y)), 2)