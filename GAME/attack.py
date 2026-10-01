import math
import pygame


# Projéteis de disparos de armas de fogo
######################################################################################################################################
class Projectile:
    def __init__(self, position, direction, speed, damage, radius):
        if speed <= 0.0:
            raise ValueError(
                "speed must be greater than zero."
            )

        if damage <= 0:
            raise ValueError(
                "damage must be greater than zero."
            )

        if radius <= 0.0:
            raise ValueError(
                "radius must be greater than zero."
            )

        self.position = pygame.Vector2(position)

        direction = pygame.Vector2(direction)

        if direction.length_squared() == 0.0:
            raise ValueError(
                "direction cannot be a zero vector."
            )

        self.direction = direction.normalize()
        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.alive = True

    def update(self, dt):
        if dt < 0.0:
            raise ValueError(
                "dt must be greater than or equal to zero."
            )

        self.position += self.direction * self.speed * dt

    def kill(self):
        self.alive = False

    def get_state(self):
        return {
            "position": self.position.copy(),
            "direction": self.direction.copy(),
            "speed": self.speed,
            "damage": self.damage,
            "radius": self.radius,
            "alive": self.alive,
        }


# Espadada de arma branca
######################################################################################################################################
class Slash:
    def __init__(self, position, direction, reach, arc, damage, lifetime):
        if reach <= 0.0:
            raise ValueError(
                "reach must be greater than zero."
            )

        if arc <= 0.0:
            raise ValueError(
                "arc must be greater than zero."
            )

        if damage <= 0:
            raise ValueError(
                "damage must be greater than zero."
            )

        if lifetime < 0.0:
            raise ValueError(
                "lifetime must be greater than or equal to zero."
            )

        self.position = pygame.Vector2(position)

        direction = pygame.Vector2(direction)

        if direction.length_squared() == 0.0:
            raise ValueError(
                "direction cannot be a zero vector."
            )

        self.direction = direction.normalize()

        self.reach = reach
        self.arc = arc
        self.damage = damage
        self.lifetime = lifetime
        self.alive = True

        self._hit_targets = set()

    def update(self, dt):
        if dt < 0.0:
            raise ValueError(
                "dt must be greater than or equal to zero."
            )

        self.lifetime -= dt

        if self.lifetime <= 0.0:
            self.lifetime = 0.0
            self.alive = False

    def can_hit(self, target):
        return id(target) not in self._hit_targets

    def register_hit(self, target):
        self._hit_targets.add(id(target))

    def kill(self):
        self.alive = False

    def get_state(self):
        return {
            "position": self.position.copy(),
            "direction": self.direction.copy(),
            "reach": self.reach,
            "arc": self.arc,
            "damage": self.damage,
            "lifetime": self.lifetime,
            "alive": self.alive,
        }