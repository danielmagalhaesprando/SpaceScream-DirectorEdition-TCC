import pygame

from .weapon import Weapon

# Espaçonave principal controlada pelo jogador
######################################################################################################################################
class Player:
    def __init__(self, position):
        self.position = pygame.Vector2(position)

        self.movement_velocity = pygame.Vector2(0, 0)

        self.knockback_velocity = pygame.Vector2(0, 0)

        self.radius = 12
        self.move_speed = 400

        self.health = 3
        self.max_health = 3
        self.alive = True

        self.aim_direction = pygame.Vector2(1, 0)

        self.invulnerability_duration = 1.0
        self.invulnerability_remaining = 0.0

        self.knockback_strength = 400
        self.knockback_decay = 400

        self.weapons = []
        self.current_weapon = None

    def update(self, dt, input_state):
        if not self.alive:
            return []

        self._update_movement(input_state)

        self._update_aim(input_state)

        self._update_invulnerability(dt)

        self._update_knockback(dt)

        self._update_weapons(dt)

        self._update_current_weapon_usage(dt)

        velocity = (self.movement_velocity + self.knockback_velocity)

        self.position += (velocity * dt)

        if input_state.fire:
            return self.attack()

        return []

    def _update_movement(self, input_state):
        movement = pygame.Vector2(input_state.movement)

        if movement.length_squared() > 0:
            movement = movement.normalize()

            self.movement_velocity = (movement * self.move_speed)

        else:
            self.movement_velocity = (pygame.Vector2(0, 0))

    def _update_aim(self, input_state):
        aim_vector = (pygame.Vector2(input_state.aim_position) - self.position)

        if aim_vector.length_squared() > 0:
            self.aim_direction = (aim_vector.normalize())

    def _update_invulnerability(self, dt):
        if(self.invulnerability_remaining > 0.0):
            self.invulnerability_remaining -= dt

            if(self.invulnerability_remaining < 0.0):
                self.invulnerability_remaining = 0.0

    def _update_knockback(self, dt):
        if(self.knockback_velocity.length_squared() == 0):
            return

        reduction = (self.knockback_decay * dt)

        current_speed = (self.knockback_velocity.length())

        if current_speed <= reduction:
            self.knockback_velocity = (pygame.Vector2(0, 0))

        else:
            self.knockback_velocity.scale_to_length(current_speed - reduction)

    def _update_weapons(self, dt):
        for weapon in self.weapons:
            weapon.update(dt)

    def _update_current_weapon_usage(self, dt):
        if self.current_weapon is None:
            return

        self.current_weapon.record_use_time(dt)

    def attack(self):
        if self.current_weapon is None:
            return []

        return self.current_weapon.attack(self.position, self.aim_direction, self.radius)

    def take_damage(self, damage):
        if(not self.alive or self.is_invulnerable()):
            return False

        if damage <= 0:
            raise ValueError(
                "damage must be greater than zero."
            )

        self.health -= damage

        if self.health <= 0:
            self.health = 0
            self.alive = False

        self.invulnerability_remaining = (self.invulnerability_duration)

        return True

    def heal(self, amount):
        if not self.alive:
            return

        if amount <= 0:
            raise ValueError(
                "amount must be greater than zero."
            )

        self.health = min(self.health + amount, self.max_health)

    def apply_knockback(self, direction):
        if not self.alive:
            return

        direction = pygame.Vector2(direction)

        if direction.length_squared() == 0:
            return

        self.knockback_velocity = (direction.normalize() * self.knockback_strength)

    def add_weapon(self, weapon):
        if not isinstance(weapon, Weapon):
            raise TypeError(
                "weapon must be an instance of Weapon."
            )

        self.weapons.append(weapon)

        if self.current_weapon is None:
            self.current_weapon = weapon

    def select_weapon(self, slot):
        if(slot is not None and 0 <= slot < len(self.weapons)):
            self.current_weapon = (self.weapons[slot])

    def reset_wave_weapon_usage(self):
        for weapon in self.weapons:
            weapon.reset_wave_usage()

    def reset_run_weapon_usage(self):
        for weapon in self.weapons:
            weapon.reset_run_usage()

    def is_invulnerable(self):
        return (self.invulnerability_remaining > 0.0)

    def is_alive(self):
        return self.alive

    def get_state(self):
        current_weapon_index = None

        if self.current_weapon is not None:
            current_weapon_index = (self.weapons.index(self.current_weapon))

        return {
            "position": self.position.copy(),
            "movement_velocity": (self.movement_velocity.copy()),
            "knockback_velocity": (self.knockback_velocity.copy()),
            "radius": self.radius,
            "move_speed": self.move_speed,
            "health": self.health,
            "max_health": self.max_health,
            "alive": self.alive,
            "aim_direction": (self.aim_direction.copy()),
            "invulnerability_remaining": (self.invulnerability_remaining),
            "weapon_count": len(self.weapons),
            "current_weapon": (current_weapon_index)
        }

    def get_context_state(self):
        return {
            "health": self.health,
            "max_health": self.max_health,
            "position": self.position.copy(),
            "weapons_usage": [
                {
                    "weapon_index": index,
                    "wave_use_time": (weapon.wave_use_time),
                    "total_use_time": (weapon.total_use_time)
                }
                for index, weapon in enumerate(self.weapons)
            ]
        }

    def draw(self, surface):
        if not self.alive:
            return

        pygame.draw.circle(surface, (80, 160, 255), (round(self.position.x), round(self.position.y)), self.radius)