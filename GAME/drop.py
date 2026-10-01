import pygame


# Drops de inimigos
######################################################################################################################################
class Drop:
    def __init__(self, position):
        self.position = pygame.Vector2(position)
        self.radius = 8
        self.alive = True

    def collect(self, player):
        if not self.alive:
            return False

        collected = self._apply_effect(player)

        if collected:
            self.alive = False

        return collected

    def _apply_effect(self, player):
        raise NotImplementedError(
            "Each drop must implement _apply_effect()."
        )

    def is_alive(self):
        return self.alive

    def get_state(self):
        return {
            "position": self.position.copy(),
            "radius": self.radius,
            "alive": self.alive,
        }

    def draw(self, surface):
        if not self.alive:
            return

        pygame.draw.circle(
            surface, (255, 255, 255), (round(self.position.x), round(self.position.y)), self.radius)


# Drop do tipo: +HP
######################################################################################################################################
class HealthDrop(Drop):
    def __init__(self, position):
        super().__init__(position)
        self.heal_amount = 1

    def _apply_effect(self, player):
        if player.health >= player.max_health:
            return False

        player.heal(self.heal_amount)

        return True