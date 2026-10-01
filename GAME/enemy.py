import pygame


# Inimigos, de 3 tiers diferentes com suas características
######################################################################################################################################
class Enemy:
    def __init__(self, position, tier):
        self.position = pygame.Vector2(position)
        self.tier = tier
        self.radius = 10
        self.speed = 90.0
        self.health = 1
        self.max_health = 1
        self.damage = 1
        self.alive = True
        self._configure_by_tier()

    def _configure_by_tier(self):
        if self.tier == 1:
            self.radius = 10
            self.speed = 90.0
            self.health = 1
            self.max_health = 1
            self.damage = 1

        elif self.tier == 2:
            self.radius = 15
            self.speed = 65.0
            self.health = 2
            self.max_health = 2
            self.damage = 1

        elif self.tier == 3:
            self.radius = 20
            self.speed = 45.0
            self.health = 3
            self.max_health = 3
            self.damage = 1

        else:
            raise ValueError(
                f"Invalid enemy tier: {self.tier}"
            )

    @staticmethod
    def get_radius_by_tier(tier):
        if tier == 1:
            return 10.0

        if tier == 2:
            return 15.0

        if tier == 3:
            return 20.0

        raise ValueError(
            f"Invalid enemy tier: {tier}"
        )

    def update(self, dt, player_position):
        if not self.alive:
            return

        direction = (pygame.Vector2(player_position) - self.position)

        if direction.length_squared() == 0:
            return

        direction = direction.normalize()

        self.position += (direction * self.speed * dt)

    def take_damage(self, amount):
        if amount <= 0:
            raise ValueError(
                "amount must be greater than zero."
            )

        if not self.alive:
            return False

        self.health -= amount

        if self.health <= 0:
            self.health = 0
            self.alive = False

        return True

    def is_alive(self):
        return self.alive

    def get_state(self):
        return {
            "position": self.position.copy(),
            "tier": self.tier,
            "radius": self.radius,
            "speed": self.speed,
            "health": self.health,
            "max_health": self.max_health,
            "damage": self.damage,
            "alive": self.alive,
        }

    def draw(self, surface):
        if not self.alive:
            return

        pygame.draw.circle(surface, (255, 80, 80), (round(self.position.x), round(self.position.y)), self.radius)