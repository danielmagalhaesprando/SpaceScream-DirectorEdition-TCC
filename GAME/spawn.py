import math
import pygame

from .enemy import Enemy


# Formação de um grupo de inimigos
######################################################################################################################################
class Formation:
    LINE = "LINE"
    COLUMN = "COLUMN"
    BLOCK = "BLOCK"
    ARC = "ARC"
    DIAMOND = "DIAMOND"
    MAX_COUNT = 7
    DEFAULT_SPACING = 40.0
    DEFAULT_SEGMENT_WIDTH = 240.0
    ARC_ANGLE = 120.0
    SUPPORTED_COUNTS = {
        LINE: range(1, 8),
        COLUMN: range(1, 8),
        BLOCK: (4, 6),
        ARC: range(3, 8),
        DIAMOND: (4, 5, 7),
    }

    _BLOCK_TEMPLATES = {
        4: [
            (-0.5, -0.5),
            (0.5, -0.5),
            (-0.5, 0.5),
            (0.5, 0.5),
        ],
        6: [
            (-1.0, -0.5),
            (0.0, -0.5),
            (1.0, -0.5),
            (-1.0, 0.5),
            (0.0, 0.5),
            (1.0, 0.5),
        ],
    }

    _DIAMOND_TEMPLATES = {
        4: [
            (0.0, -1.0),
            (-1.0, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
        ],
        5: [
            (0.0, -1.0),
            (-1.0, 0.0),
            (0.0, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
        ],
        7: [
            (0.0, -1.0),
            (-1.0, -0.5),
            (1.0, -0.5),
            (0.0, 0.0),
            (-1.0, 0.5),
            (1.0, 0.5),
            (0.0, 1.0),
        ],
    }

    @classmethod
    def calculate_positions(cls, formation, radii, spacing=DEFAULT_SPACING):
        radii = list(radii)

        cls._validate_inputs(formation, radii, spacing)

        base_positions = cls._create_base_positions(formation, len(radii))

        base_positions = cls._center_positions(base_positions)

        scale = cls._calculate_scale(base_positions, radii, spacing)

        return [position * scale for position in base_positions]

    @classmethod
    def calculate_footprint(cls, formation, radii, spacing=DEFAULT_SPACING,):
        radii = list(radii)

        positions = cls.calculate_positions(formation=formation, radii=radii, spacing=spacing,)

        if not positions:
            return {
                "width": 0.0,
                "height": 0.0
            }

        min_x = math.inf
        max_x = -math.inf
        min_y = math.inf
        max_y = -math.inf

        for position, radius in zip(positions, radii):
            min_x = min(min_x, position.x - radius)

            max_x = max(max_x, position.x + radius)

            min_y = min(min_y, position.y - radius)

            max_y = max(max_y, position.y + radius)

        return {
            "width": max_x - min_x,
            "height": max_y - min_y
        }

    @classmethod
    def can_fit(cls, formation, radii, segment_width=DEFAULT_SEGMENT_WIDTH, segment_axis="x", spacing=DEFAULT_SPACING):
        if segment_width <= 0:
            raise ValueError(
                "segment_width must be greater than zero."
            )

        if segment_axis not in ("x", "y"):
            raise ValueError(
                "segment_axis must be 'x' or 'y'."
            )

        footprint = cls.calculate_footprint(formation=formation, radii=radii, spacing=spacing)

        if segment_axis == "x":
            return footprint["width"] <= segment_width

        return footprint["height"] <= segment_width

    @classmethod
    def _validate_inputs(cls, formation, radii, spacing):
        if formation not in cls.SUPPORTED_COUNTS:
            raise ValueError(
                f"Invalid formation: {formation}"
            )

        count = len(radii)

        if count not in cls.SUPPORTED_COUNTS[formation]:
            supported = ", ".join(str(value) for value in cls.SUPPORTED_COUNTS[formation])

            raise ValueError(
                f"{formation} does not support "
                f"{count} enemies. "
                f"Supported counts: {supported}."
            )

        if count > cls.MAX_COUNT:
            raise ValueError(
                f"A formation cannot contain more than "
                f"{cls.MAX_COUNT} enemies."
            )

        if spacing < 0:
            raise ValueError(
                "spacing must be greater than or equal to zero."
            )

        for radius in radii:
            if radius <= 0:
                raise ValueError(
                    "All enemy radii must be greater than zero."
                )

    @classmethod
    def _create_base_positions(cls, formation, count):
        if formation == cls.LINE:
            return cls._create_line_positions(count)

        if formation == cls.COLUMN:
            return cls._create_column_positions(count)

        if formation == cls.BLOCK:
            return cls._create_template_positions(cls._BLOCK_TEMPLATES, count)

        if formation == cls.ARC:
            return cls._create_arc_positions(count)

        if formation == cls.DIAMOND:
            return cls._create_template_positions(cls._DIAMOND_TEMPLATES, count)

        raise ValueError(
            f"Unsupported formation: {formation}"
        )

    @staticmethod
    def _create_line_positions(count):
        center = (count - 1) / 2.0

        return [pygame.Vector2(index - center, 0.0) for index in range(count)]

    @staticmethod
    def _create_column_positions(count):
        center = (count - 1) / 2.0

        return [pygame.Vector2(0.0, index - center) for index in range(count)]

    @staticmethod
    def _create_template_positions(templates, count):
        if count not in templates:
            raise ValueError(
                f"No template exists for count {count}."
            )

        return [pygame.Vector2(x, y) for x, y in templates[count]]

    @classmethod
    def _create_arc_positions(cls, count):
        arc_radians = math.radians(cls.ARC_ANGLE)

        start_angle = -arc_radians / 2.0

        angle_step = (arc_radians / (count - 1))

        positions = []

        for index in range(count):
            angle = (start_angle + index * angle_step)

            positions.append(pygame.Vector2(math.cos(angle), math.sin(angle)))

        return positions

    @staticmethod
    def _center_positions(positions):
        if not positions:
            return []

        min_x = min(position.x for position in positions)

        max_x = max(position.x for position in positions)

        min_y = min(position.y for position in positions)

        max_y = max(position.y for position in positions)

        center = pygame.Vector2((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

        return [position - center for position in positions]

    @staticmethod
    def _calculate_scale(positions, radii, spacing):
        if len(positions) <= 1:
            return 1.0

        scale = 0.0

        for first_index in range(len(positions)):
            for second_index in range(first_index + 1, len(positions)):
                base_distance = (positions[first_index]- positions[second_index]).length()

                if base_distance <= 0.0:
                    raise ValueError(
                        "Formation contains overlapping "
                        "base positions."
                    )

                required_distance = (radii[first_index] + radii[second_index] + spacing)

                required_scale = (required_distance / base_distance)

                scale = max(scale, required_scale)

        return scale


# Grupo de inimigos
######################################################################################################################################
class Group:
    def __init__(self, enemy_specs, spawn_region, formation, delay=0.0):
        if not enemy_specs:
            raise ValueError(
                "enemy_specs cannot be empty."
            )

        if formation is None:
            raise ValueError(
                "formation cannot be None."
            )

        if not isinstance(delay, (int, float)):
            raise TypeError(
                "delay must be a number."
            )

        if delay < 0:
            raise ValueError(
                "delay must be greater than or equal to zero."
            )

        self.enemy_specs = [dict(spec) for spec in enemy_specs]

        self.spawn_region = dict(spawn_region)
        self.formation = formation
        self.delay = float(delay)

        self._validate_spawn_region()
        self._validate_enemy_specs()

    def _validate_spawn_region(self):
        if not isinstance(self.spawn_region, dict):
            raise TypeError(
                "spawn_region must be a dictionary."
            )

        if "border" not in self.spawn_region:
            raise ValueError(
                "spawn_region must contain 'border'."
            )

        if "segment" not in self.spawn_region:
            raise ValueError(
                "spawn_region must contain 'segment'."
            )

        border = self.spawn_region["border"]
        segment = self.spawn_region["segment"]

        if border not in ("TOP", "BOTTOM", "LEFT", "RIGHT"):
            raise ValueError(
                f"Invalid spawn border: {border}"
            )

        if not isinstance(segment, int):
            raise TypeError(
                "spawn segment must be an integer."
            )

        max_segment = (4 if border in ("TOP", "BOTTOM") else 2)

        if not 0 <= segment <= max_segment:
            raise ValueError(
                f"Invalid spawn segment for "
                f"{border}: {segment}"
            )

    def _validate_enemy_specs(self):
        for spec in self.enemy_specs:
            if "tier" not in spec:
                raise ValueError(
                    "Each enemy spec must contain 'tier'."
                )

            tier = spec["tier"]

            if tier not in (1, 2, 3):
                raise ValueError(
                    f"Invalid enemy tier: {tier}"
                )

            if "speed" in spec:
                if spec["speed"] <= 0:
                    raise ValueError(
                        "Enemy speed must be greater than zero."
                    )

            if "max_health" in spec:
                if spec["max_health"] <= 0:
                    raise ValueError(
                        "Enemy max_health must be greater than zero."
                    )

    def get_enemy_count(self):
        return len(self.enemy_specs)

    def get_enemy_specs(self):
        return [dict(spec) for spec in self.enemy_specs]

    def get_state(self):
        return {
            "enemy_specs": [dict(spec) for spec in self.enemy_specs],
            "spawn_region": dict(self.spawn_region),
            "formation": self.formation,
            "delay": self.delay
        }


# "Agendador do spawn dos grupos"
######################################################################################################################################
class SpawnScheduler:
    def __init__(self):
        self.groups = []
        self.next_group_index = 0
        self.delay_remaining = 0.0

    def set_groups(self, groups):
        if groups is None:
            raise TypeError(
                "groups cannot be None."
            )

        self.groups = list(groups)

        self.next_group_index = 0

        self.delay_remaining = 0.0

    def replace_future_groups(self, groups):
        if groups is None:
            raise TypeError(
                "groups cannot be None."
            )

        executed_groups = (self.groups[:self.next_group_index])

        self.groups = (executed_groups + list(groups))

    def update(self, dt):
        if dt < 0.0:
            raise ValueError(
                "dt must be greater than or equal to zero."
            )

        if self.delay_remaining > 0.0:
            self.delay_remaining -= dt

            if self.delay_remaining < 0.0:
                self.delay_remaining = 0.0

        return self.is_ready()

    def is_ready(self):
        return (self.delay_remaining <= 0.0 and self.has_pending_groups())

    def peek_next_group(self):
        if not self.is_ready():
            return None

        return self.groups[self.next_group_index]

    def consume_next_group(self):
        if not self.is_ready():
            return None

        group = self.groups[self.next_group_index]

        self.next_group_index += 1

        self.delay_remaining = (group.delay)

        return group

    def has_pending_groups(self):
        return (self.next_group_index < len(self.groups))

    def is_waiting(self):
        return (self.delay_remaining > 0.0)

    def get_delay_remaining(self):
        return self.delay_remaining

    def get_pending_group_count(self):
        return (len(self.groups) - self.next_group_index)

    def get_next_group_index(self):
        return self.next_group_index

    def get_groups(self):
        return list(self.groups)

    def get_state(self):
        return {
            "groups": [group.get_state() for group in self.groups],

            "next_group_index": (self.next_group_index),

            "delay_remaining": (self.delay_remaining),

            "waiting": (self.is_waiting()),

            "ready": (self.is_ready())
        }


# Classe dos spawn dos grupos dos inimigos
######################################################################################################################################
class Spawn:
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    SEGMENT_LENGTH = 240.0
    TOP_BOTTOM_MARGIN = 40.0

    def __init__(self, arena_width, arena_height, spacing=Formation.DEFAULT_SPACING):
        if arena_width <= 0:
            raise ValueError(
                "arena_width must be greater than zero."
            )

        if arena_height <= 0:
            raise ValueError(
                "arena_height must be greater than zero."
            )

        if spacing < 0:
            raise ValueError(
                "spacing must be greater than or equal to zero."
            )

        self.arena_width = float(arena_width)
        self.arena_height = float(arena_height)
        self.spacing = float(spacing)

    def spawn(self, group):
        if not isinstance(group, Group):
            raise TypeError(
                "group must be an instance of Group."
            )

        enemy_specs = group.get_enemy_specs()

        radii = [Enemy.get_radius_by_tier(spec["tier"]) for spec in enemy_specs]

        self._validate_formation_fit(group.formation, radii, group.spawn_region)

        formation_positions = (Formation.calculate_positions(formation=group.formation, radii=radii, spacing=self.spacing))

        footprint = Formation.calculate_footprint(formation=group.formation, radii=radii, spacing=self.spacing)

        center = self._calculate_spawn_center(group.spawn_region, footprint)

        enemies = []

        for spec, relative_position in zip(enemy_specs, formation_positions):
            position = (center + relative_position)

            enemy = Enemy(position=position, tier=spec["tier"])

            if "speed" in spec:
                enemy.speed = spec["speed"]

            if "max_health" in spec:
                enemy.max_health = spec["max_health"]
                enemy.health = spec["max_health"]

            enemies.append(enemy)

        return enemies

    def _validate_formation_fit(self, formation, radii, spawn_region):
        border = spawn_region["border"]

        segment_axis = ("x" if border in (self.TOP, self.BOTTOM) else "y")

        if not Formation.can_fit(
            formation=formation,
            radii=radii,
            segment_width=self.SEGMENT_LENGTH,
            segment_axis=segment_axis,
            spacing=self.spacing,
        ):
            raise ValueError(
                "Formation does not fit inside "
                "the selected spawn segment."
            )

    def _calculate_spawn_center(self, spawn_region, footprint):
        border = spawn_region["border"]
        segment = spawn_region["segment"]

        if border in (self.TOP, self.BOTTOM):
            segment_start = (self.TOP_BOTTOM_MARGIN + segment * self.SEGMENT_LENGTH)

            segment_center = (segment_start + self.SEGMENT_LENGTH / 2.0)

            if border == self.TOP:
                return pygame.Vector2(segment_center, -footprint["height"] / 2.0)

            return pygame.Vector2(segment_center, self.arena_height + footprint["height"] / 2.0)

        segment_start = (segment * self.SEGMENT_LENGTH)

        segment_center = (segment_start + self.SEGMENT_LENGTH / 2.0)

        if border == self.LEFT:
            return pygame.Vector2(-footprint["width"] / 2.0, segment_center)

        return pygame.Vector2(self.arena_width + footprint["width"] / 2.0, segment_center)