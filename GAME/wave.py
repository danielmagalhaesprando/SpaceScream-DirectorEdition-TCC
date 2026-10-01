from .spawn import Group


# Wave completa
class Wave:
    """
    A Wave possui:
    - orçamento total de inimigos;
    - plano COMPLETO de Spawn;
    - progresso de Spawn;
    - quantidade de inimigos materializados;
    - quantidade de inimigos restantes para Spawn;
    - quantidade de eliminações;
    - orçamento total de Drops;
    - plano COMPLETO de Drops;
    - progresso dos Drops acionados.
    """

    def __init__(self, wave_number, total_enemies, health_drop_budget, spawn_plan, drop_schedule):
        if wave_number <= 0:
            raise ValueError(
                "wave_number must be greater than zero."
            )

        if total_enemies <= 0:
            raise ValueError(
                "total_enemies must be greater than zero."
            )

        if health_drop_budget < 0:
            raise ValueError(
                "health_drop_budget must be greater than or equal to zero."
            )

        if spawn_plan is None:
            raise TypeError(
                "spawn_plan cannot be None."
            )

        if drop_schedule is None:
            raise TypeError(
                "drop_schedule cannot be None."
            )


        # Identificação / orçamento da Wave
        self.wave_number = int(wave_number)
        self.total_enemies = int(total_enemies)


        # SPAWN
        self.spawn_plan = []

        # Índice do próximo Group que ainda não foi executado.
        self.next_spawn_group_index = 0

        self.set_spawn_plan(spawn_plan)

        # Quantidade de inimigos que já foi efetivamente materializada.
        self.spawned_enemy_count = 0

        # Quantidade de inimigos que ainda precisam ser materializados.
        self.remaining_to_spawn = (self.total_enemies)


        # KILLS
        self.kills_this_wave = 0


        # DROPS
        self.health_drop_budget = int(health_drop_budget)

        self.drop_schedule = []

        # Índice do próximo Drop do cronograma.
        self.next_drop_index = 0

        self.set_drop_schedule(drop_schedule)


    # PLANO DE SPAWN
    def set_spawn_plan(self, spawn_plan):
        if spawn_plan is None:
            raise TypeError(
                "spawn_plan cannot be None."
            )

        spawn_plan = list(spawn_plan)

        # Todos os elementos são Grupos
        for group in spawn_plan:
            if not isinstance(group, Group):
                raise TypeError(
                    "spawn_plan must contain only Group instances."
                )

        # Soma do orçamento
        planned_enemy_count = sum(group.get_enemy_count() for group in spawn_plan)

        if planned_enemy_count != (self.total_enemies):
            raise ValueError(
                "The complete spawn plan must contain exactly the total enemy budget of the wave."
            )

        # Armazena plano completo
        self.spawn_plan = list(spawn_plan)

        # Reinicia cursor
        self.next_spawn_group_index = 0


    # SUBSTITUIÇÃO DO FUTURO DE SPAWN
    def replace_future_spawn_plan(self, spawn_plan,):
        if spawn_plan is None:
            raise TypeError(
                "spawn_plan cannot be None."
            )

        spawn_plan = list(spawn_plan)

        for group in spawn_plan:
            if not isinstance(group, Group):
                raise TypeError(
                    "spawn_plan must contain only Group instances."
                )

        # Preserva prefixo executado
        executed_groups = (self.spawn_plan[:self.next_spawn_group_index])

        # Calcula novo orçamento futuro
        future_enemy_count = sum(group.get_enemy_count() for group in spawn_plan)

        # O novo futuro precisa consumir exatamente o restante
        if future_enemy_count != (self.remaining_to_spawn):
            raise ValueError(
                "The replacement future spawn plan must contain exactly the remaining enemy budget of the wave.")

        # Novo plano completo
        self.spawn_plan = (executed_groups + spawn_plan)

        # Verificação de consistência
        planned_enemy_count = sum(group.get_enemy_count() for group in self.spawn_plan)

        if planned_enemy_count != (self.total_enemies):
            raise RuntimeError(
                "Wave spawn plan lost consistency after future replacement."
            )


    # REGISTRO DE GROUP EXECUTADO
    def register_group_spawned(self, group):
        # Tipo
        if not isinstance(group, Group):
            raise TypeError(
                "group must be an instance of Group."
            )

        # Verifica se existe Group pendente
        if self.next_spawn_group_index >= len(self.spawn_plan):
            raise ValueError(
                "There is no pending Group in the wave spawn plan."
            )

        # Group esperado
        expected_group = (self.spawn_plan[self.next_spawn_group_index])

        # O mesmo objeto precisa ser executado
        if group is not expected_group:
            raise ValueError(
                "The spawned Group does not match the next Group in the wave spawn plan."
            )

        # Quantidade de inimigos
        enemy_count = (group.get_enemy_count())

        if enemy_count > (self.remaining_to_spawn):
            raise ValueError(
                "Cannot spawn more enemies than remain in the wave."
            )

        # Avança o cursor
        self.next_spawn_group_index += 1

        # Atualiza quantidade materializada
        self.spawned_enemy_count += (enemy_count)

        # Atualiza restante
        self.remaining_to_spawn -= (enemy_count)

        # Invariante
        if(self.spawned_enemy_count + self.remaining_to_spawn != self.total_enemies):
            raise RuntimeError(
                "Wave enemy spawn accounting became inconsistent."
            )


    # STATUS DO SPAWN
    def is_spawn_complete(self):
        return (self.remaining_to_spawn == 0)

    def has_pending_spawn_groups(self):
        return (self.next_spawn_group_index < len(self.spawn_plan))

    def get_spawn_plan(self):
        return list(self.spawn_plan)

    def get_pending_spawn_groups(self):
        return list(self.spawn_plan[self.next_spawn_group_index:])

    def get_executed_spawn_groups(self):
        return list(self.spawn_plan[:self.next_spawn_group_index])

    def get_spawn_group_count(self):
        return len(self.spawn_plan)

    def get_pending_spawn_group_count(self):
        return (len(self.spawn_plan) - self.next_spawn_group_index)

    def get_executed_spawn_group_count(self):
        return (self.next_spawn_group_index)

    def get_next_spawn_group_index(self):
        return (self.next_spawn_group_index)

    def get_spawned_enemy_count(self):
        return (self.spawned_enemy_count)


    # KILLS
    def register_kill(self):
        # Registra uma eliminação ocorrida durante esta Wave.
        if self.kills_this_wave >= (self.total_enemies):
            raise ValueError(
                "Cannot register more kills than total enemies in the wave."
            )

        self.kills_this_wave += 1


    # PLANO DE DROPS COMPLETO
    def set_drop_schedule(self, schedule):
        if schedule is None:
            raise TypeError(
                "schedule cannot be None."
            )

        schedule = list(schedule)

        # O cronograma precisa consumir todo o budget
        if len(schedule) != (self.health_drop_budget):
            raise ValueError(
                "The complete drop schedule must contain exactly the health drop budget number of entries."
            )

        # Ordem
        previous = 0

        for kill_count in schedule:
            if not isinstance(kill_count, int):
                raise TypeError(
                    "Drop schedule kill counts must be integers."
                )

            if kill_count <= previous:
                raise ValueError(
                    "Drop schedule must contain strictly increasing kill counts."
                )

            if kill_count <= 0:
                raise ValueError(
                    "Drop schedule kill counts must be greater than zero."
                )

            if kill_count > (self.total_enemies):
                raise ValueError(
                    "Drop schedule cannot exceed the total enemies in the wave."
                )

            # Ao definir um plano completo para uma Wave nova, nenhuma eliminação deveria ter ocorrido ainda.
            if kill_count <= (self.kills_this_wave):
                raise ValueError(
                    "Drop schedule cannot contain kill counts that have already occurred."
                )

            previous = (kill_count)

        # Armazena cronograma completo
        self.drop_schedule = list(schedule)

        # Reinicia cursor
        self.next_drop_index = 0


    # SUBSTITUIÇÃO DO FUTURO DE DROPS
    def replace_future_drop_schedule(self, schedule):
        if schedule is None:
            raise TypeError(
                "schedule cannot be None."
            )

        schedule = list(schedule)

        # Prefixo irrevogável
        triggered_schedule = (self.drop_schedule[:self.next_drop_index])

        # O novo futuro precisa completar exatamente o budget
        expected_future_count = (self.health_drop_budget - len(triggered_schedule))

        if len(schedule) != (expected_future_count):
            raise ValueError(
                "The replacement future drop schedule must contain the number of untriggered Drops required to complete the budget."
            )

        # Validação da ordem
        previous = (triggered_schedule[-1] if triggered_schedule else 0)

        for kill_count in schedule:
            if not isinstance(kill_count, int):
                raise TypeError(
                    "Drop schedule kill counts must be integers."
                )

            if kill_count <= previous:
                raise ValueError(
                    "Future drop schedule must contain strictly increasing kill counts."
                )

            if kill_count > (self.total_enemies):
                raise ValueError(
                    "Drop schedule cannot exceed the total enemies in the wave."
                )

            # O novo futuro não pode apontar para uma morte que já ocorreu.
            if kill_count <= (self.kills_this_wave):
                raise ValueError(
                    "Future drop schedule cannot contain kill counts that have already occurred."
                )

            previous = (kill_count)

        # Novo cronograma completo
        self.drop_schedule = (triggered_schedule + schedule)

        # Invariante
        if len(self.drop_schedule) != self.health_drop_budget:
            raise RuntimeError(
                "Wave drop schedule lost consistency after future replacement."
            )


    # EXECUÇÃO DOS DROPS
    def has_pending_drop(self):
        return (self.next_drop_index < len(self.drop_schedule) and self.kills_this_wave >= self.drop_schedule[self.next_drop_index])

    # Consome o próximo Drop elegível
    def consume_next_drop(self):
        if not self.has_pending_drop():
            return False

        self.next_drop_index += 1

        return True


    # GETTERS DOS DROPS
    def get_triggered_drop_count(self):
        return (self.next_drop_index)

    def get_scheduled_future_drop_count(self):
        return (len(self.drop_schedule) - self.next_drop_index)

    def get_unscheduled_drop_count(self):
        return (self.health_drop_budget - len(self.drop_schedule))

    def get_remaining_drop_budget(self):
        return (self.health_drop_budget - self.next_drop_index)

    def get_drop_schedule(self):
        return list(self.drop_schedule)

    def get_next_drop_index(self):
        return (self.next_drop_index)


    # COMPLETION
    def is_complete(self,alive_enemies):
        """
        A Wave só está completa quando:

        1. todos os inimigos planejados foram materializados;
        2. não existem inimigos vivos no mundo.
        """

        if alive_enemies < 0:
            raise ValueError(
                "alive_enemies must be greater than or equal to zero."
            )

        return (self.is_spawn_complete() and alive_enemies == 0)


    # STATE
    def get_state(self):
        # Plano completo de Spawn
        planned_enemy_count = sum(group.get_enemy_count() for group in self.spawn_plan)

        # Invariante do Spawn
        if planned_enemy_count != (self.total_enemies):
            raise RuntimeError(
                "Wave spawn plan is inconsistent with the total enemy budget."
            )

        # Retorno
        return {
            # Identificação
            "wave_number": (self.wave_number),

            "total_enemies": (self.total_enemies),

            # Spawn
            "spawn_state": {
                "planned_enemy_count": (planned_enemy_count),

                "spawned_enemy_count": (self.spawned_enemy_count),

                "remaining_to_spawn": (self.remaining_to_spawn),

                "group_count": (self.get_spawn_group_count()),

                "next_group_index": (self.next_spawn_group_index),

                "executed_group_count": (self.get_executed_spawn_group_count()),

                "pending_group_count": (self.get_pending_spawn_group_count()),

                "groups": [group.get_state() for group in self.spawn_plan]
            },

            # Kills
            "kills_this_wave": (self.kills_this_wave),

            # Drops
            "drop_state": {
                "health_drop_budget": (self.health_drop_budget),

                "schedule": (self.get_drop_schedule()),

                "next_drop_index": (self.next_drop_index),

                "triggered_count": (self.get_triggered_drop_count()),

                "scheduled_future_count": (self.get_scheduled_future_drop_count()),

                "unscheduled_count": (self.get_unscheduled_drop_count()),

                "remaining_count": (self.get_remaining_drop_budget())
            }
        }