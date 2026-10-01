import pygame

from .attack import Projectile, Slash


# Classe base de uma arma
######################################################################################################################################
class Weapon:
    def __init__(self, damage, cooldown,):
        if damage <= 0:
            raise ValueError(
                "damage must be greater than zero."
            )

        if cooldown < 0.0:
            raise ValueError(
                "cooldown must be greater than or equal to zero."
            )

        self.damage = damage
        self.cooldown = cooldown
        self.cooldown_remaining = 0.0
        self.wave_use_time = 0.0
        self.total_use_time = 0.0

    def can_attack(self):
        return (self.cooldown_remaining <= 0.0)

    def update(self, dt):
        if dt < 0.0:
            raise ValueError(
                "dt must be greater than "
                "or equal to zero."
            )

        if self.cooldown_remaining > 0.0:
            self.cooldown_remaining -= dt

            if self.cooldown_remaining < 0.0:
                self.cooldown_remaining = 0.0

    def record_use_time(self, dt):
        if dt < 0.0:
            raise ValueError(
                "dt must be greater than or equal to zero."
            )

        self.wave_use_time += dt
        self.total_use_time += dt

    def reset_wave_usage(self):
        self.wave_use_time = 0.0

    def reset_run_usage(self):
        self.wave_use_time = 0.0
        self.total_use_time = 0.0

    def attack(self, position, direction, radius):
        if not self.can_attack():
            return []

        attacks = self._create_attacks(position, direction, radius)

        if attacks:
            self.cooldown_remaining = (self.cooldown)

        return attacks

    def _create_attacks(self, position, direction, radius):
        raise NotImplementedError(
            "Each weapon must implement "
            "_create_attacks()."
        )


# Tipo de arma: Pistola inicial
######################################################################################################################################
class Pistol(Weapon):
    def __init__(self):
        super().__init__(
            damage=1,
            cooldown=0.5,
        )

        self.projectile_speed = 1000.0
        self.projectile_radius = 3

    def _create_attacks(self, position, direction, radius):
        direction = pygame.Vector2(direction).normalize()

        spawn_position = (position + direction * radius)

        projectile = Projectile(
            position=spawn_position,
            direction=direction,
            speed=self.projectile_speed,
            damage=self.damage,
            radius=self.projectile_radius,
        )

        return [projectile]


# Tipo de arma: Espingarda
######################################################################################################################################
class Shotgun(Weapon):
    def __init__(self):
        super().__init__(damage=1, cooldown=1)

        self.projectile_speed = 1000.0
        self.projectile_count = 5
        self.spread_angle = 60.0
        self.projectile_radius = 3

    def _create_attacks(self, position, direction, radius):
        attacks = []

        direction = pygame.Vector2(direction).normalize()

        if self.projectile_count == 1:
            angle_offsets = [0.0]

        else:
            half_spread = (self.spread_angle / 2.0)

            angle_step = (self.spread_angle / (self.projectile_count - 1))

            angle_offsets = [(-half_spread + angle_step * index) for index in range(self.projectile_count)]

        for angle_offset in angle_offsets:
            projectile_direction = (direction.rotate(angle_offset))

            spawn_position = (position + projectile_direction * radius)

            projectile = Projectile(
                position=spawn_position,
                direction=projectile_direction,
                speed=self.projectile_speed,
                damage=self.damage,
                radius=self.projectile_radius,
            )

            attacks.append(projectile)

        return attacks


# Tipo de arma: Sabre de luz
######################################################################################################################################
class Lightsaber(Weapon):
    def __init__(self, reach):
        super().__init__(damage=3, cooldown=0.75)

        self.reach = reach
        self.arc_angle = 180.0
        self.slash_duration = 1.0

    def _create_attacks(self, position, direction, radius):
        slash = Slash(
            position=position,
            direction=direction,
            reach=self.reach,
            arc=self.arc_angle,
            damage=self.damage,
            lifetime=self.slash_duration,
        )

        return [slash]