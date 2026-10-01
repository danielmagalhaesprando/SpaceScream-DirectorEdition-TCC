import math
import pygame

from .attack import Projectile, Slash
from .drop import HealthDrop
from .enemy import Enemy
from .player import Player
from .spawn import Formation, Group, Spawn, SpawnScheduler
from .wave import Wave
from .weapon import Pistol, Shotgun, Lightsaber


######################################################################################################################################
# GAME
######################################################################################################################################
class Game:
    # ESTADOS
    INITIAL_SCREEN = "INITIAL_SCREEN"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    WAVE_REST = "WAVE_REST"
    GAME_OVER = "GAME_OVER"


    # CONFIGURAÇÕES
    ARENA_WIDTH = 1280
    ARENA_HEIGHT = 720

    MAX_ALIVE_ENEMIES = 30

    PLAYER_START_POSITION = (ARENA_WIDTH / 2, ARENA_HEIGHT / 2)

    MENU_BUTTON_WIDTH = 280
    MENU_BUTTON_HEIGHT = 60
    MENU_BUTTON_GAP = 20


    # INICIALIZAÇÃO
    def __init__(self):
        # Estado geral
        self.running = True

        self.state = self.INITIAL_SCREEN

        self.previous_state = self.INITIAL_SCREEN

        # Tempo
        self.game_time = 0.0

        self.wave_start_game_time = 0.0

        # Entidades
        self.player = None

        self.enemies = []

        self.projectiles = []

        self.slashes = []

        self.drops = []

        # Sistemas
        self.spawn_system = Spawn(arena_width=self.ARENA_WIDTH, arena_height=self.ARENA_HEIGHT)

        self.spawn_scheduler = SpawnScheduler()

        # Wave
        self.wave = None

        self.wave_enemy_composition = {}

        # Histórico
        self.previous_wave = None

        # Emoção
        self.last_playing_emotion = None

        # Planejamento da próxima Wave
        self.next_wave_plan = None


        # DEBUG
        self.debug_enabled = False

        self.debug_adaptation_history = []

        self.debug_director_state = None

        self.debug_last_adaptation = None

        self.debug_last_before_spawn = None

        self.debug_last_after_spawn = None

        self.debug_last_before_drop_schedule = None

        self.debug_last_after_drop_schedule = None

        self.DEBUG_MAX_ADAPTATIONS = 5

        # Inicialização
        self._reset_run_state()


    # RESET DA EXECUÇÃO
    def _reset_run_state(self):
        # Tempo
        self.game_time = 0.0

        self.wave_start_game_time = 0.0

        # Entidades
        self.enemies.clear()

        self.projectiles.clear()

        self.slashes.clear()

        self.drops.clear()

        # Histórico
        self.previous_wave = None

        # Emoção
        self.last_playing_emotion = None

        # Próxima Wave
        self.next_wave_plan = None


        # DEBUG
        self.debug_adaptation_history.clear()

        self.debug_director_state = None

        self.debug_last_adaptation = None

        self.debug_last_before_spawn = None

        self.debug_last_after_spawn = None

        self.debug_last_before_drop_schedule = None

        self.debug_last_after_drop_schedule = None

        # Composição
        self.wave_enemy_composition = {}

        # Jogador
        self.player = Player(position=pygame.Vector2(self.PLAYER_START_POSITION))

        self.player.add_weapon(Pistol())

        # Wave inicial
        self._create_initial_wave()


    # NOVA PARTIDA
    def start_new_game(self):
        self.running = True

        self.state = self.PLAYING

        self.previous_state = self.INITIAL_SCREEN

        self._reset_run_state()


    # CRIAÇÃO DA WAVE INICIAL
    def _create_initial_wave(self):
        initial_groups = (self._get_initial_wave_groups())

        self._create_wave(wave_number=1, groups=initial_groups, health_drop_budget=3)


    # CRIAÇÃO DE UMA WAVE
    def _create_wave(self, wave_number, groups, health_drop_budget, drop_schedule=None):
        # Limpa entidades transitórias da Wave anterior (Drops, projectiles e slashes não atravessam a transição de Wave)
        self.drops.clear()
        self.projectiles.clear()
        self.slashes.clear()

        if groups is None:
            raise TypeError(
                "groups cannot be None."
            )

        if health_drop_budget < 0:
            raise ValueError(
                "health_drop_budget must be greater than or equal to zero."
            )

        groups = list(groups)

        # Verifica Groups
        for group in groups:
            if not isinstance(group, Group):
                raise TypeError(
                    "groups must contain only Group instances."
                )

        # Orçamento total da Wave
        total_enemies = sum(group.get_enemy_count() for group in groups)

        if total_enemies <= 0:
            raise ValueError(
                "A wave must contain at least one enemy."
            )

        # O número de Drops não pode exceder o número de kills possíveis, pois cada Drop é associado a um kill ordinal distinto.
        if health_drop_budget > total_enemies:
            raise ValueError(
                "health_drop_budget cannot exceed total_enemies."
            )

        # Plano completo de Drops
        if drop_schedule is None:
            drop_schedule = (self._build_default_drop_schedule(total_enemies=total_enemies, health_drop_budget=health_drop_budget))

        # Validação defensiva do Drop Schedule
        drop_schedule = list(drop_schedule)

        if len(drop_schedule) != (health_drop_budget):
            raise ValueError(
                "drop_schedule must contain exactly health_drop_budget entries."
            )

        # Criação da Wave
        self.wave = Wave(
            wave_number=wave_number,
            total_enemies=total_enemies,
            health_drop_budget=health_drop_budget,
            spawn_plan=groups,
            drop_schedule=drop_schedule,
        )

        # Scheduler executa o MESMO plano
        self.spawn_scheduler.set_groups(groups)

        # Tempo inicial da Wave
        self.wave_start_game_time = (self.game_time)

        # Composição da Wave
        self.wave_enemy_composition = {}


    # CRIAÇÃO DO DROP SCHEDULE PADRÃO
    @staticmethod
    def _build_default_drop_schedule(total_enemies, health_drop_budget):
        # Nenhum Drop
        if health_drop_budget == 0:
            return []

        # Validação
        if total_enemies <= 0:
            raise ValueError(
                "total_enemies must be greater than zero."
            )

        if health_drop_budget > total_enemies:
            raise ValueError(
                "health_drop_budget cannot exceed total_enemies."
            )

        # Distribui os Drops pela Wave
        schedule = []

        for index in range(1, health_drop_budget + 1):
            ordinal = math.ceil(index * total_enemies / health_drop_budget)

            # Garante ordem estritamente crescente
            if schedule and ordinal <= schedule[-1]:
                ordinal = (schedule[-1] + 1)

            # Não pode ultrapassar o último inimigo
            if ordinal > total_enemies:
                ordinal = (total_enemies)

            # Garante entrada válida
            if(not schedule or ordinal > schedule[-1]):
                schedule.append(ordinal)

        # A construção deve produzir exatamente o budget solicitado.
        if len(schedule) != (health_drop_budget):
            raise RuntimeError(
                "Failed to build a complete drop schedule."
            )

        return schedule


    # GRUPOS INICIAIS
    def _get_initial_wave_groups(self):
        """
        Wave inicial:
        5 Groups
        6 inimigos por Group
        """

        group_specs = [
            {
                "border": "TOP",
                "segment": 0,
                "formation": Formation.BLOCK,
                "count": 6,
                "tier": 1,
                "delay": 2.0,
            },

            {
                "border": "RIGHT",
                "segment": 1,
                "formation": Formation.BLOCK,
                "count": 6,
                "tier": 1,
                "delay": 2.0,
            },

            {
                "border": "BOTTOM",
                "segment": 2,
                "formation": Formation.BLOCK,
                "count": 6,
                "tier": 1,
                "delay": 2.0,
            },

            {
                "border": "LEFT",
                "segment": 1,
                "formation": Formation.BLOCK,
                "count": 6,
                "tier": 1,
                "delay": 2.0,
            },

            {
                "border": "TOP",
                "segment": 4,
                "formation": Formation.BLOCK,
                "count": 6,
                "tier": 1,
                "delay": 2.0,
            },
        ]

        return self._build_groups_from_specs(group_specs)


    # CONSTRUÇÃO DOS GROUPS
    def _build_groups_from_specs(self, specs):
        if specs is None:
            raise TypeError(
                "specs cannot be None."
            )

        groups = []

        for spec in specs:
            # Enemy specs
            enemy_specs = []

            count = int(spec["count"])

            tier = int(spec["tier"])

            for _ in range(count):
                enemy_spec = {"tier": tier}

                if "speed" in spec:
                    enemy_spec["speed"] = (spec["speed"])

                if "max_health" in spec:
                    enemy_spec["max_health"] = (spec["max_health"])

                enemy_specs.append(enemy_spec)

            # Group
            group = Group(
                enemy_specs=enemy_specs,

                spawn_region={
                    "border": spec["border"],
                    "segment": int(spec["segment"])
                },

                formation=spec["formation"],

                delay=float(spec.get("delay", 0.0))
            )

            groups.append(group)

        return groups


    # UPDATE
    def update(self, dt, input_state):
        # Delta time
        if dt < 0.0:
            raise ValueError(
                "dt must be greater than or equal to zero."
            )


        # PAUSED
        if self.state == self.PAUSED:
            return


        # INITIAL SCREEN
        if self.state == self.INITIAL_SCREEN:
            return


        # GAME OVER
        if self.state == self.GAME_OVER:
            return


        # WAVE REST
        if self.state == self.WAVE_REST:
            self.game_time += dt

            return

        # Somente PLAYING executa o mundo
        if self.state != self.PLAYING:
            return

        # Tempo
        self.game_time += dt

        # Jogador
        if self.player is not None:
            attacks = (self.player.update(dt=dt, input_state=input_state))

            self._register_player_attacks(attacks)

        # Spawn
        self._spawn_enemies(dt)

        # Inimigos
        if self.player is not None:
            player_position = (self.player.position)

            for enemy in self.enemies:
                enemy.update(dt=dt, player_position=player_position)

        # Projectiles
        for projectile in self.projectiles:
            if projectile.alive:
                projectile.update(dt)

        # Slashes
        for slash in self.slashes:
            if slash.alive:
                slash.update(dt)

        # Projectiles fora da arena
        self._remove_projectiles_outside_arena()

        # Colisões
        self._resolve_enemy_enemy_collisions()

        self._resolve_player_enemy_collisions()

        self._resolve_projectile_enemy_collisions()

        self._resolve_slash_enemy_collisions()

        self._resolve_player_drop_collisions()

        # Mantém o Player inteiramente dentro da arena, inclusive após knockback.
        self._clamp_player_to_arena()

        # Limpeza
        self._cleanup_entities()

        # Game Over
        if (self.player is not None and not self.player.is_alive()):
            self._enter_game_over()

            return

        # Conclusão da Wave
        self._check_wave_completion()


    # REGISTRO DOS ATAQUES DO JOGADOR
    def _register_player_attacks(self, attacks):
        if attacks is None:
            return

        for attack in attacks:
            if isinstance(attack, Projectile):
                self.projectiles.append(attack)

            elif isinstance(attack, Slash):
                self.slashes.append(attack)

            else:
                raise TypeError(
                    "Player attacks must be Projectile or Slash instances."
                )


    # SPAWN DOS GROUPS
    def _spawn_enemies(self, dt):
        # Atualiza somente o relógio do Scheduler.
        self.spawn_scheduler.update(dt)

        # Consulta o próximo Group sem consumi-lo.
        group = (self.spawn_scheduler.peek_next_group())

        if group is None:
            return

        # Verifica se existe capacidade para materializar o Group (caso não, o Group permanece pendente)
        if(len(self.enemies) + group.get_enemy_count() > self.MAX_ALIVE_ENEMIES):
            return

        # Agora o Group pode realmente ser consumido.
        group = (self.spawn_scheduler.consume_next_group())

        if group is None:
            return

        # Materializa o Group.
        spawned_enemies = (self.spawn_system.spawn(group))

        # Adiciona ao mundo.
        self.enemies.extend(spawned_enemies)

        # Registra a execução na Wave.
        self.wave.register_group_spawned(group)

        # Verificação de sincronização.
        if(self.spawn_scheduler.get_next_group_index() != self.wave.get_next_spawn_group_index()):
            raise RuntimeError(
                "SpawnScheduler and Wave are out of sync after group spawn."
            )

        # Atualiza composição da Wave.
        for enemy in spawned_enemies:
            tier = enemy.tier

            self.wave_enemy_composition[tier] = (self.wave_enemy_composition.get(tier, 0) + 1)


    # COLISÃO PLAYER x ENEMY
    def _resolve_player_enemy_collisions(self):
        if self.player is None:
            return

        for enemy in self.enemies:
            if not enemy.alive:
                continue

            if not self._circles_overlap(self.player.position, self.player.radius, enemy.position, enemy.radius):
                continue

            # Direção da separação
            delta = (self.player.position - enemy.position)

            distance_squared = (delta.length_squared())

            if distance_squared == 0.0:
                normal = pygame.Vector2(1.0, 0.0)

                distance = 1.0

            else:
                distance = math.sqrt(distance_squared)

                normal = (delta / distance)

            # Correção de penetração
            penetration = (self.player.radius + enemy.radius - distance)

            if penetration > 0.0:
                correction = (normal * (penetration / 2.0))

                self.player.position += (correction)

                enemy.position -= (correction)

            # Dano
            if not self.player.is_invulnerable():
                damaged = (self.player.take_damage(enemy.damage))

                if damaged:
                    self.player.apply_knockback(normal)


    # COLISÃO ENEMY x ENEMY
    def _resolve_enemy_enemy_collisions(self):
        for index_a in range(len(self.enemies)):
            enemy_a = self.enemies[index_a]

            if not enemy_a.alive:
                continue

            for index_b in range(index_a + 1, len(self.enemies),):
                enemy_b = self.enemies[index_b]

                if not enemy_b.alive:
                    continue

                if not self._circles_overlap(enemy_a.position, enemy_a.radius, enemy_b.position, enemy_b.radius):
                    continue

                # Separação
                delta = (enemy_a.position - enemy_b.position)

                distance_squared = (delta.length_squared())

                if distance_squared == 0.0:
                    normal = pygame.Vector2(1.0, 0.0)

                    distance = 1.0

                else:
                    distance = math.sqrt(distance_squared)

                    normal = (delta / distance)

                penetration = (enemy_a.radius + enemy_b.radius - distance)

                if penetration <= 0.0:
                    continue

                correction = (normal * (penetration / 2.0))

                enemy_a.position += (correction)

                enemy_b.position -= (correction)


    # COLISÃO PROJECTILE x ENEMY
    def _resolve_projectile_enemy_collisions(self):
        for projectile in self.projectiles:
            if not projectile.alive:
                continue

            for enemy in self.enemies:
                if not enemy.alive:
                    continue

                if not self._circles_overlap(projectile.position, projectile.radius, enemy.position, enemy.radius):
                    continue

                enemy.take_damage(projectile.damage)

                projectile.kill()

                break


    # COLISÃO SLASH x ENEMY
    def _resolve_slash_enemy_collisions(self):
        for slash in self.slashes:
            if not slash.alive:
                continue

            for enemy in self.enemies:
                if not enemy.alive:
                    continue

                if not slash.can_hit(enemy):
                    continue

                if self._slash_collides_with_enemy(slash, enemy):
                    enemy.take_damage(slash.damage)

                    slash.register_hit(enemy)


    # COLISÃO PLAYER x DROP
    def _resolve_player_drop_collisions(self):
        if self.player is None:
            return

        for drop in self.drops:
            if not drop.alive:
                continue

            if not self._circles_overlap(self.player.position, self.player.radius, drop.position, drop.radius):
                continue

            drop.collect(self.player)


    # TESTE DE SOBREPOSIÇÃO DE CÍRCULOS
    @staticmethod
    def _circles_overlap(position_a, radius_a, position_b, radius_b):
        return (position_a.distance_to(position_b) <= radius_a + radius_b)


    # REMOÇÃO DOS PROJECTILES FORA DA ARENA
    def _remove_projectiles_outside_arena(self):
        for projectile in self.projectiles:
            if not projectile.alive:
                continue

            if(
                projectile.position.x < 0.0
                or projectile.position.x > self.ARENA_WIDTH
                or projectile.position.y < 0.0
                or projectile.position.y > self.ARENA_HEIGHT
            ):
                projectile.kill()


    # COLISÃO DO SLASH
    @staticmethod
    def _slash_collides_with_enemy(slash, enemy):
        offset = (enemy.position - slash.position)

        distance = offset.length()

        # Fora do alcance
        if distance > (slash.reach + enemy.radius):
            return False

        # Enemy sobre a origem do Slash
        if distance == 0.0:
            return True

        # Direção normalizada até o Enemy
        direction = (offset / distance)

        slash_direction = (slash.direction.normalize())

        # Ângulo entre o Slash e o Enemy
        dot = max(-1.0, min(1.0, slash_direction.dot(direction)))

        angle = math.degrees(math.acos(dot))

        # Expansão angular devido ao raio do Enemy
        angular_expansion = math.degrees(math.asin(min(1.0, enemy.radius / distance)))

        # Colisão final
        return (angle <= (slash.arc / 2.0 + angular_expansion))

    # REGISTRO DE MORTE | LIMITES DO PLAYER
    def _clamp_player_to_arena(self):
        if self.player is None:
            return

        radius = self.player.radius

        self.player.position.x = max(radius, min(self.ARENA_WIDTH - radius, self.player.position.x))

        self.player.position.y = max(radius, min(self.ARENA_HEIGHT - radius, self.player.position.y))


    def _register_enemy_death(self, enemy):
        # Kill ordinal
        self.wave.register_kill()

        # Verifica o Drop programado para este ordinal
        if self.wave.has_pending_drop():
            self.wave.consume_next_drop()

            self._create_health_drop(enemy.position)


    # CRIA HEALTH DROP
    def _create_health_drop(self, position):
        drop = HealthDrop(position=pygame.Vector2(position))

        self.drops.append(drop)


    # LIMPEZA DAS ENTIDADES
    def _cleanup_entities(self):
        # Drops
        self.drops = [drop for drop in self.drops if drop.alive]

        # Projectiles
        self.projectiles = [projectile for projectile in self.projectiles if projectile.alive]

        # Slashes
        self.slashes = [slash for slash in self.slashes if slash.alive]

        # Inimigos mortos
        dead_enemies = [enemy for enemy in self.enemies if not enemy.alive]

        for enemy in dead_enemies:
            self._register_enemy_death(enemy)

        self.enemies = [enemy for enemy in self.enemies if enemy.alive]


    # VERIFICAÇÃO DE GAME OVER
    def _enter_game_over(self):
        self.previous_state = (self.state)

        self.state = self.GAME_OVER


    # VERIFICAÇÃO DA CONCLUSÃO DA WAVE
    def _check_wave_completion(self):
        if self.wave is None:
            return

        if not self.wave.is_complete(alive_enemies=len(self.enemies)):
            return

        self._enter_wave_rest()


    # ENTRADA NO WAVE REST
    def _enter_wave_rest(self):
        self.previous_wave = (self._build_previous_wave_summary())

        self.state = self.WAVE_REST


    # RESUMO DA WAVE ANTERIOR
    def _build_previous_wave_summary(self):
        duration = (self.game_time - self.wave_start_game_time)

        return {
            "wave_number": (self.wave.wave_number),

            "total_enemies": (self.wave.total_enemies),

            "kills": (self.wave.kills_this_wave),

            "duration": duration,

            "enemy_composition": dict(self.wave_enemy_composition)
        }


    # REGISTRO DA EMOÇÃO DE PLAYING
    def record_playing_emotion(self, emotion):
        if self.state != self.PLAYING:
            return

        if emotion is None:
            return

        self.last_playing_emotion = emotion


    # CONTEXTO DO DIRECTOR
    def get_director_context(self):
        return self.get_game_context()


    # CONTEXTO COMPLETO
    def get_game_context(self):
        return {
            "game": self._build_game_context(),

            "player": self.get_player_context(),
        }


    # GAME CONTEXT
    def _build_game_context(self):
        if self.wave is None:
            return {
                "state": self.state,

                "game_time": self.game_time,

                "wave_number": 0,

                "total_enemies": 0,

                "remaining_to_spawn": 0,

                "alive_enemies": len(self.enemies),

                "enemy_composition": {},

                "spawn_state": {},

                "drop_state": {},

                "allowed_spawn_borders": [],

                "arena_width": (self.ARENA_WIDTH),

                "arena_height": (self.ARENA_HEIGHT),

                "kill_rate": 0.0,

                "previous_wave": (self.previous_wave),

                "max_alive_enemies": (self.MAX_ALIVE_ENEMIES)
            }

        return {
            "state": self.state,

            "game_time": self.game_time,

            "wave_number": (self.wave.wave_number),

            "total_enemies": (self.wave.total_enemies),

            "remaining_to_spawn": (self.wave.remaining_to_spawn),

            "alive_enemies": len(self.enemies),

            "enemy_composition": (self._get_alive_enemy_composition()),

            "spawn_state": (self._get_spawn_context()),

            "drop_state": (self._get_drop_context()),

            "allowed_spawn_borders": (self._get_allowed_spawn_borders()),

            "arena_width": (self.ARENA_WIDTH),

            "arena_height": (self.ARENA_HEIGHT),

            "kill_rate": (self._get_kill_rate()),

            "previous_wave": (self.previous_wave),

            "max_alive_enemies": (self.MAX_ALIVE_ENEMIES),
        }


    # PLAYER CONTEXT
    def get_player_context(self):
        if self.player is None:
            return None

        state = (self.player.get_context_state())

        logical_position = (self._world_to_logical_position(state["position"]))

        return {
            "health": (state["health"]),

            "max_health": (state["max_health"]),

            "position": (logical_position),

            "weapons_usage": (state["weapons_usage"])
        }


    # COMPOSIÇÃO DE INIMIGOS VIVOS
    def _get_alive_enemy_composition(self):
        composition = {}

        for enemy in self.enemies:
            if not enemy.alive:
                continue

            tier = enemy.tier

            composition[tier] = (composition.get(tier, 0) + 1)

        return composition


    # POSIÇÃO DO PLAYER NO GRID LÓGICO
    def _world_to_logical_position(self, position):
        column = int(max(0, min(4, position.x / self.ARENA_WIDTH * 5)))

        row = int(max(0, min(2, position.y / self.ARENA_HEIGHT * 3)))

        return [column, row]


    # CONTEXTO DO SPAWN
    def _get_spawn_context(self):
        groups = (self.wave.get_spawn_plan())

        next_group_index = (self.wave.get_next_spawn_group_index())

        return {
            "groups": [group.get_state() for group in groups],

            "next_group_index": (next_group_index),

            "delay_remaining": (self.spawn_scheduler.get_delay_remaining()),

            "waiting": (self.spawn_scheduler.is_waiting()),

            "pending_group_count": (self.spawn_scheduler.get_pending_group_count())
        }


    # CONTEXTO DOS DROPS
    def _get_drop_context(self):
        return {
            "health_drop_budget": (self.wave.health_drop_budget),

            "triggered_drop_count": (self.wave.get_triggered_drop_count()),

            "scheduled_drop_count": (len(self.wave.get_drop_schedule())),

            "pending_drop_count": (self.wave.get_scheduled_future_drop_count()),

            "remaining_drop_budget": (self.wave.get_remaining_drop_budget()),

            "unscheduled_drop_count": (self.wave.get_unscheduled_drop_count()),

            "drop_schedule": (self.wave.get_drop_schedule()),

            "next_drop_index": (self.wave.get_next_drop_index())
        }


    # TAXA DE ABATES
    def _get_kill_rate(self):
        if self.wave is None:
            return 0.0

        duration = (self.game_time - self.wave_start_game_time)

        if duration <= 0.0:
            return 0.0

        return (self.wave.kills_this_wave / duration)


    # BORDAS PERMITIDAS
    def _get_allowed_spawn_borders(self):
        if self.player is None:
            return []

        logical_position = (self.get_player_context()["position"])

        column = logical_position[0]

        row = logical_position[1]

        # Matriz de regiões permitidas
        if column in (0, 1) and row == 0:
            return ["BOTTOM", "RIGHT"]

        if column in (3, 4) and row == 0:
            return ["BOTTOM", "LEFT"]

        if column in (0, 1) and row == 2:
            return ["TOP", "RIGHT"]

        if column in (3, 4) and row == 2:
            return ["TOP", "LEFT"]

        if column in (0, 1) and row == 1:
            return ["TOP", "BOTTOM", "RIGHT"]

        if column in (3, 4) and row == 1:
            return ["TOP", "BOTTOM", "LEFT"]

        if column == 2 and row == 0:
            return ["LEFT", "BOTTOM", "RIGHT"]

        if column == 2 and row == 2:
            return ["LEFT", "TOP", "RIGHT"]

        if column == 2 and row == 1:
            return ["LEFT", "TOP", "BOTTOM", "RIGHT"]

        return ["TOP", "BOTTOM", "LEFT", "RIGHT"]


    # APLICAÇÃO DE ADAPTAÇÃO
    def apply_adaptation(self, adaptation):
        if adaptation is None:
            return

        # O Director só pode adaptar enquanto estamos em PLAYING.
        if self.state != self.PLAYING:
            return

        # Wave atual
        if adaptation.current_wave is not None:
            self._apply_current_wave_adaptation(adaptation.current_wave)


    # APLICA ADAPTAÇÃO NA WAVE ATUAL
    def _apply_current_wave_adaptation(self, current_wave):
        if current_wave is None:
            return

        # Spawn
        spawn_data = (current_wave.get("spawn") or {})

        if spawn_data.get("action") == "replace_future_groups":
            future_specs = (spawn_data.get("groups", []))

            future_groups = (self._build_groups_from_adaptation(future_specs))

            # A Wave é atualizada primeiro.
            self.wave.replace_future_spawn_plan(future_groups)

            # O Scheduler passa a executar exatamente o mesmo futuro.
            self.spawn_scheduler.replace_future_groups(future_groups)

        # Drops
        drops_data = (current_wave.get("drops") or {})

        if drops_data.get("action") == "replace_future_schedule":
            future_schedule = (drops_data.get("schedule", []))

            self.wave.replace_future_drop_schedule(future_schedule)

        # Verificação final de sincronização
        if(self.spawn_scheduler.get_next_group_index() != self.wave.get_next_spawn_group_index()):
            raise RuntimeError(
                "Wave and SpawnScheduler are out of sync after adaptation."
            )


        # DEBUG: registra o estado efetivamente aplicado.
        self.debug_last_after_spawn = [group.get_state() for group in self.wave.get_spawn_plan()]

        self.debug_last_after_drop_schedule = (self.wave.get_drop_schedule())


    # CONVERSÃO DAS ESPECIFICAÇÕES DE GROUP
    def _build_groups_from_adaptation(self, specs):
        if specs is None:
            raise TypeError(
                "future group specifications cannot be None."
            )

        groups = []

        for spec in specs:
            if isinstance(spec, Group):
                groups.append(spec)

                continue

            # Deve ser dictionary na fronteira Director -> Game
            if not isinstance(spec, dict):
                raise TypeError(
                    "Each adapted future group must be a Group or dict."
                )

            # Enemy specs
            enemy_specs = (spec.get("enemy_specs", []))

            spawn_region = (spec.get("spawn_region"))

            formation = (spec.get("formation"))

            delay = float(spec.get("delay", 0.0))

            # Criação do Group
            groups.append(
                Group(
                    enemy_specs=[dict(enemy_spec) for enemy_spec in enemy_specs],

                    spawn_region=dict(spawn_region),

                    formation=formation,

                    delay=delay
                )
            )

        return groups


    # PRÓXIMA WAVE
    def _start_next_wave_from_plan(self):
        if self.next_wave_plan is None:
            return False

        # O plano da próxima Wave já deve ser completo.
        next_wave_plan = (self.next_wave_plan)

        self.next_wave_plan = None

        next_wave_number = (self.wave.wave_number + 1)

        if isinstance(next_wave_plan, dict):
            groups = (next_wave_plan.get("groups", []))

            drop_schedule = (next_wave_plan.get("drop_schedule"))

            health_drop_budget = (next_wave_plan.get("health_drop_budget", 3))

        else:
            groups = (next_wave_plan)

            drop_schedule = None

            health_drop_budget = 3

        groups = (self._build_groups_from_adaptation(groups))

        self._create_wave(
            wave_number=next_wave_number,
            groups=groups,
            health_drop_budget=health_drop_budget,
            drop_schedule=drop_schedule,
        )

        return True


    # DEBUG
    def record_director_debug(self, director_state, adaptation):
        if director_state is not None:
            self.debug_director_state = director_state

        if adaptation is None:
            return

        self.debug_last_adaptation = adaptation.get_state()

        self.debug_adaptation_history.append(self.debug_last_adaptation)

        if len(self.debug_adaptation_history) > self.DEBUG_MAX_ADAPTATIONS:
            self.debug_adaptation_history.pop(0)

        # Snapshot do plano antes da aplicação.
        self.debug_last_before_spawn = [group.get_state() for group in self.wave.get_spawn_plan()] if self.wave is not None else []

        self.debug_last_before_drop_schedule = (self.wave.get_drop_schedule() if self.wave is not None else [])

    def toggle_debug(self):
        self.debug_enabled = not self.debug_enabled


    # MENU
    def handle_menu_input(self, input_state):
        if not input_state.confirm:
            return False

        mouse_position = input_state.aim_position

        if self.state == self.INITIAL_SCREEN:
            buttons = self._get_initial_screen_buttons()

            if buttons["start"].collidepoint(mouse_position):
                self.start_new_game()
                return True

            if buttons["options"].collidepoint(mouse_position):
                # Botão/entrada preservado; conteúdo de Options será implementado quando as configurações forem adicionadas.
                return True

            if buttons["exit"].collidepoint(mouse_position):
                self.quit()
                return True

            return False

        if self.state == self.PAUSED:
            buttons = self._get_pause_buttons()

            if buttons["resume"].collidepoint(mouse_position):
                self.toggle_pause()
                return True

            if buttons["initial_screen"].collidepoint(mouse_position):
                self.return_to_initial_screen()
                return True

            if buttons["exit"].collidepoint(mouse_position):
                self.quit()
                return True

            return False

        if self.state == self.GAME_OVER:
            buttons = self._get_game_over_buttons()

            if buttons["restart"].collidepoint(mouse_position):
                self.start_new_game()
                return True

            if buttons["initial_screen"].collidepoint(mouse_position):
                self.return_to_initial_screen()
                return True

            if buttons["exit"].collidepoint(mouse_position):
                self.quit()
                return True

            return False

        if self.state == self.WAVE_REST:
            self._continue_from_wave_rest()
            return True

        return False


    # BOUNDING BOXES DOS MENUS
    def _get_initial_screen_buttons(self):
        start, options, exit_button = (self._get_vertical_menu_buttons(3))

        return {"start": start, "options": options, "exit": exit_button}

    def _get_vertical_menu_buttons(self, labels_count):

        total_height = (self.MENU_BUTTON_HEIGHT * labels_count + self.MENU_BUTTON_GAP * (labels_count - 1))

        start_y = int((self.ARENA_HEIGHT - total_height) / 2)

        x = int((self.ARENA_WIDTH - self.MENU_BUTTON_WIDTH) / 2)

        return [
            pygame.Rect(
                x,
                start_y + index * (self.MENU_BUTTON_HEIGHT + self.MENU_BUTTON_GAP),
                self.MENU_BUTTON_WIDTH,
                self.MENU_BUTTON_HEIGHT,
            )
            for index in range(labels_count)
        ]

    def _get_pause_buttons(self):
        resume, initial_screen, exit_button = (self._get_vertical_menu_buttons(3))

        return {"resume": resume, "initial_screen": initial_screen, "exit": exit_button,}

    def _get_game_over_buttons(self):
        restart, initial_screen, exit_button = (self._get_vertical_menu_buttons(3))

        return {"restart": restart, "initial_screen": initial_screen, "exit": exit_button}


    # CONTINUAÇÃO DA WAVE REST
    def _continue_from_wave_rest(self):
        started = (self._start_next_wave_from_plan())

        if not started:
            self._create_wave(
                wave_number = (self.wave.wave_number + 1),

                groups = (self._get_initial_wave_groups()),

                health_drop_budget=3,
            )

        if self.player is not None:
            self.player.reset_wave_weapon_usage()

        self.state = self.PLAYING


    # PAUSE
    def toggle_pause(self):
        if self.state in (self.PLAYING, self.WAVE_REST,):
            self.previous_state = (self.state)

            self.state = self.PAUSED

            return

        if self.state == self.PAUSED:
            self.state = (self.previous_state)


    # RETORNA PARA A TELA INICIAL
    def return_to_initial_screen(self):
        self._reset_run_state()

        self.state = (self.INITIAL_SCREEN)

        self.previous_state = (self.INITIAL_SCREEN)


    # QUIT
    def quit(self):
        self.running = False


    # RENDER
    def render(self, screen):
        # Fundo
        screen.fill((12, 12, 18))

        # Arena
        pygame.draw.rect(screen, (40, 40, 55), pygame.Rect(0, 0, self.ARENA_WIDTH, self.ARENA_HEIGHT), 2)

        # Drops
        for drop in self.drops:
            drop.draw(screen)

        # Inimigos
        for enemy in self.enemies:
            enemy.draw(screen)

        # Projectiles
        for projectile in self.projectiles:
            if not projectile.alive:
                continue

            pygame.draw.circle(
                screen,
                (255, 230, 100),
                (round(projectile.position.x), round(projectile.position.y)),
                round(projectile.radius)
            )

        # Slashes
        for slash in self.slashes:
            if not slash.alive:
                continue

            self._draw_slash(screen, slash)

        # Player
        if self.player is not None:
            self.player.draw(screen)

        # Overlays
        if self.state == self.INITIAL_SCREEN:
            self._render_initial_screen(screen)

        elif self.state == self.PAUSED:
            self._render_pause_overlay(screen)

        elif self.state == self.WAVE_REST:
            self._render_wave_rest_overlay(screen)

        elif self.state == self.GAME_OVER:
            self._render_game_over_overlay(screen)


        # DEBUG
        if self.debug_enabled:
            self._render_debug_overlay(screen)


    # DEBUG OVERLAY
    def _render_debug_overlay(self, screen):
        panel_width = 720
        panel_height = 700

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)

        panel.fill((8, 8, 12, 225))

        screen.blit(panel, (10, 10))

        title_font = pygame.font.Font(None, 24)

        font = pygame.font.Font(None, 18)

        small_font = pygame.font.Font(None, 16)

        x = 25
        y = 25
        line_height = 19

        title = title_font.render("AI DIRECTOR DEBUG", True, (235, 235, 245))

        screen.blit(title, (x, y))

        y += 32

        self._render_debug_line(screen, font, f"State:{self.state}", x, y)

        y += line_height

        if self.wave is not None:
            self._render_debug_line(screen, font, f"Wave:{self.wave.wave_number}", x, y)

            y += line_height

            self._render_debug_line(screen, font, f"Alive:{len(self.enemies)} / {self.MAX_ALIVE_ENEMIES}", x, y)

            y += line_height

            self._render_debug_line(screen, font, f"Kills:{self.wave.kills_this_wave}", x, y)

            y += line_height

        y += 4


        # DECISÃO DO DIRECTOR
        self._render_debug_line(screen, font, "DIRECTOR DECISION", x, y)

        y += line_height

        director_state = (self.debug_director_state or {})

        decision = (director_state.get("last_decision") or {})

        pressure = decision.get("pressure") or {}
        performance = decision.get("performance") or {}
        survivability = decision.get("survivability") or {}
        wave_progress = decision.get("wave_progress") or {}

        self._render_debug_line(
            screen,
            small_font,
            f"Pressure: {pressure.get('category', '?')}  score={pressure.get('score', 0.0):.2f}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Performance: {performance.get('category', '?')}  kill={performance.get('kill_rate', 0.0):.2f}/s  expected={performance.get('expected_kill_rate', 0.0):.2f}  ratio={performance.get('ratio', 0.0):.2f}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Survivability: {survivability.get('category', '?')}  health={survivability.get('health_ratio', 0.0):.2f}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Wave progress: {wave_progress.get('category', '?')}  progress={wave_progress.get('progress', 0.0):.2f}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Emotion: {decision.get('emotional_tendency', '?')}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Action: {decision.get('action', '?')}  Strength: {decision.get('strength', '?')}  Reason: {decision.get('reason', '?')}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Evaluating: {director_state.get('is_evaluating', False)}  elapsed={director_state.get('evaluation_elapsed', 0.0):.2f}s  observations={director_state.get('observation_count', 0)}",
            x + 10,
            y,
        )

        y += line_height

        self._render_debug_line(
            screen,
            small_font,
            f"Window: {director_state.get('minimum_evaluation_time', 0.0):.2f}s - {director_state.get('maximum_evaluation_time', 0.0):.2f}s",
            x + 10,
            y,
        )

        y += line_height + 4


        # ÚLTIMA ADAPTAÇÃO
        
        self._render_debug_line(
            screen,
            font,
            "LAST ADAPTATION",
            x,
            y,
        )

        y += line_height

        adaptation = self.debug_last_adaptation

        if adaptation is None:
            self._render_debug_line(screen, small_font, "No adaptation applied yet.", x + 10, y)

            y += line_height

        else:
            current_wave = (adaptation.get("current_wave") or {})

            self._render_debug_line(
                screen,
                small_font,
                f"ID: {adaptation.get('intervention_id', '?')}  Evaluation: {adaptation.get('evaluation_time', 0.0):.2f}s",
                x + 10,
                y,
            )
            
            y += line_height

            self._render_debug_line(
                screen,
                small_font,
                f"Action: {current_wave.get('action', '?')}  Strength: {current_wave.get('decision_strength', '?')}  Reason: {current_wave.get('reason', '?')}",
                x + 10,
                y,
            )

            y += line_height

            changes = current_wave.get("changes") or []

            self._render_debug_line(
                screen,
                small_font,
                "Changes:",
                x + 10,
                y,
            )

            y += line_height

            if changes:
                for change in changes:
                    if not isinstance(change, dict):
                        text = str(change)

                    else:
                        text = (f"{change.get('type', '?')}: " f"{change.get('magnitude', 0.0):.2f}")

                    self._render_debug_line(screen, small_font, f"- {text}", x + 20, y)

                    y += line_height

            else:
                self._render_debug_line(screen, small_font, "- none", x + 20, y)

                y += line_height

        y += 4


        # SPAWN PLAN
        self._render_debug_line(screen, font, "SPAWN PLAN: BEFORE -> AFTER", x, y)

        y += line_height

        before = self.debug_last_before_spawn or []
        after = self.debug_last_after_spawn or []

        max_groups = max(len(before), len(after))

        if max_groups == 0:
            self._render_debug_line(screen, small_font, "No applied spawn plan yet.", x + 10, y)

            y += line_height

        else:
            for index in range(max_groups):
                before_group = (before[index] if index < len(before) else None)

                after_group = (after[index] if index < len(after) else None)

                self._render_debug_line(screen, small_font, f"G{index + 1} BEFORE: {self._format_debug_group(before_group)}", x+10, y)

                y += line_height

                self._render_debug_line(screen, small_font, f"   AFTER:  {self._format_debug_group(after_group)}", x+10, y)

                y += line_height

                if y > panel_height - 105:
                    break


        # DROPS
        if y <= panel_height - 65:
            y += 3

            self._render_debug_line(screen, font, "DROPS: BEFORE -> AFTER", x, y)
            
            y += line_height

            self._render_debug_line(
                screen,
                small_font,
                f"{self.debug_last_before_drop_schedule or []}  ->  {self.debug_last_after_drop_schedule or []}",
                x + 10,
                y,
            )

            y += line_height


        # HISTÓRICO
        if y <= panel_height - 45:
            y += 3

            self._render_debug_line(screen, font, "RECENT ADAPTATIONS", x, y)

            y += line_height

            if not self.debug_adaptation_history:
                self._render_debug_line(screen, small_font, "None", x+10, y)

                y += line_height

            else:
                for adaptation in reversed(self.debug_adaptation_history):
                    current_wave = (adaptation.get("current_wave") or {})

                    line = (
                        f"#{adaptation.get('intervention_id', '?')} "
                        f"{current_wave.get('action', 'NONE')} "
                        f"{current_wave.get('decision_strength', '')}"
                    )

                    self._render_debug_line(screen, small_font, line, x + 10, y)

                    y += line_height

                    if y > panel_height - 20:
                        break

        hint = small_font.render("F3: toggle debug", True, (180, 180, 190))

        screen.blit(hint, (x, panel_height - 25))

    @staticmethod
    def _render_debug_line(screen, font, text, x, y):
        surface = font.render(text, True, (235, 235, 245))

        screen.blit(surface, (x, y))

    @staticmethod
    def _format_debug_group(group_state,):
        if group_state is None:
            return "NONE"

        enemy_specs = group_state.get("enemy_specs", [])

        counts = {}

        for enemy_spec in enemy_specs:
            tier = enemy_spec.get("tier", "?")

            counts[tier] = (counts.get(tier, 0) + 1)

        composition = ",".join(f"T{tier}x{count}" for tier, count in sorted(counts.items()))

        spawn_region = group_state.get("spawn_region", {})

        border = spawn_region.get("border", "?")

        segment = spawn_region.get("segment", "?")

        formation = group_state.get("formation", "?")

        delay = group_state.get("delay", 0.0)

        return (f"[{composition}] " f"{formation} " f"{border}/{segment} " f"d={delay:.1f}")


    # INITIAL SCREEN
    def _render_initial_screen(self, screen):
        self._render_text_center(screen, "SpaceScream", 100, 64)

        buttons = self._get_initial_screen_buttons()

        self._draw_menu_button(screen, buttons["start"], "START")
        self._draw_menu_button(screen, buttons["options"], "OPTIONS")
        self._draw_menu_button(screen, buttons["exit"], "EXIT")


    # PAUSE
    def _render_pause_overlay(self, screen):
        self._draw_overlay(screen, 150)
        self._render_text_center(screen, "PAUSED", 260, 64)

        buttons = self._get_pause_buttons()

        self._draw_menu_button(screen, buttons["resume"], "RESUME")
        self._draw_menu_button(screen, buttons["initial_screen"], "RETURN TO MENU")
        self._draw_menu_button(screen, buttons["exit"], "EXIT")


    # WAVE REST
    def _render_wave_rest_overlay(self, screen):
        self._render_text_center(screen, "WAVE COMPLETE", 250, 48)
        self._render_text_center(screen, "Press ENTER to continue", 400, 28)


    # GAME OVER
    def _render_game_over_overlay(self, screen):
        self._draw_overlay(screen, 170)
        self._render_text_center(screen, "GAME OVER", 260, 64)

        buttons = self._get_game_over_buttons()

        self._draw_menu_button(screen, buttons["restart"], "RESTART")
        self._draw_menu_button(screen, buttons["initial_screen"], "RETURN TO MENU")
        self._draw_menu_button(screen, buttons["exit"], "EXIT")


    # BOTÕES / OVERLAY
    @staticmethod
    def _draw_menu_button(screen, rect, text):
        pygame.draw.rect(screen, (235, 235, 245), rect, 2)

        font = pygame.font.Font(None, 28)
        surface = font.render(text, True, (235, 235, 245))

        text_rect = surface.get_rect(center=rect.center)

        screen.blit(surface, text_rect)

    @staticmethod
    def _draw_overlay(screen, alpha):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        overlay.fill((0, 0, 0, alpha))

        screen.blit(overlay, (0, 0))


    # DESENHO DO SLASH
    @staticmethod
    def _draw_slash(screen, slash):

        center = (round(slash.position.x), round(slash.position.y))

        start_angle = (math.atan2(-slash.direction.y, slash.direction.x) - math.radians(slash.arc / 2.0))

        end_angle = start_angle + math.radians(slash.arc)

        rect = pygame.Rect(
            round(slash.position.x - slash.reach),
            round(slash.position.y - slash.reach),
            round(slash.reach * 2.0),
            round(slash.reach * 2.0),
        )

        pygame.draw.arc(screen, (220, 240, 255), rect, start_angle, end_angle, 64)


    # TEXTO CENTRALIZADO
    @staticmethod
    def _render_text_center(screen, text, y, size):
        font = pygame.font.Font(None, size)
        surface = font.render(text, True, (235, 235, 245))

        rect = surface.get_rect(center=(Game.ARENA_WIDTH / 2, y))

        screen.blit(surface, rect)
