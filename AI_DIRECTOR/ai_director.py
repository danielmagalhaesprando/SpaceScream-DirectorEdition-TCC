from dataclasses import dataclass
from typing import Any, Optional
from itertools import combinations

from GAME.enemy import Enemy
from GAME.spawn import Formation


class Pressure:
    LOW = "LOW"
    ADEQUATE = "ADEQUATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Performance:
    LOW = "LOW"
    ADEQUATE = "ADEQUATE"
    HIGH = "HIGH"


class Survivability:
    CRITICAL = "CRITICAL"
    LOW = "LOW"
    SAFE = "SAFE"


class EmotionalTendency:
    DOWN = "DOWN"
    STABLE = "STABLE"
    UP = "UP"


class WaveProgress:
    EARLY = "EARLY"
    MIDDLE = "MIDDLE"
    LATE = "LATE"


class Action:
    KEEP = "KEEP"
    INCREASE = "INCREASE"
    REDUCE = "REDUCE"


class Strength:
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"


class SpatialTarget:
    FAR = "FAR"
    MEDIUM = "MEDIUM"
    NEAR = "NEAR"


# FUNÇÃO MATEMÁTICA LOCAL
def math_hypot(x, y):
    return (x * x + y * y) ** 0.5


# ADAPTAÇÃO PRODUZIDA PELO AI DIRECTOR
######################################################################################################################################
@dataclass
class Adaptation:
    intervention_id: int

    current_wave: Optional[dict[str, Any]] = None

    next_wave: Optional[dict[str, Any]] = None

    evaluation_time: float = 0.0

    def has_current_wave_adaptation(self):
        return (self.current_wave is not None)

    def has_next_wave_adaptation(self):
        return (self.next_wave is not None)

    def is_empty(self):
        return (self.current_wave is None and self.next_wave is None)

    def get_state(self):
        return {
            "intervention_id": (self.intervention_id),
            "current_wave": (self.current_wave),
            "next_wave": (self.next_wave),
            "evaluation_time": (self.evaluation_time)
        }


######################################################################################################################################
# AI DIRECTOR
######################################################################################################################################
class AIDirector:
    """
    O Director realiza o seguinte pipeline:
    - observa o contexto do jogo;
    - infere pressão;
    - infere performance;
    - infere sobrevivência;
    - considera tendência emocional;
    - considera progresso da Wave;
    - consulta uma matriz de decisão;
    - cria uma intervenção;
    - aguarda sua avaliação.

    O Director pode adaptar as seguintes partes do jogo:
    | Dimensão  | Parâmetro                         |   Mínimo |                     Máximo |                    Tipo |
    | --------- | --------------------------------- | -------- | -------------------------- | ----------------------- |
    | Spawn     | tamanho dos grupos                |        1 |                          7 |                discreto |
    | Spawn     | tiers dos inimigos dos grupos     |        1 |                          3 |                discreto |
    | Spawn     | delays entre grupos               |   5.0s ? |                    10.0s ? |                contínuo |
    | Spawn     | formação dos grupos               |        — |                          — |   categórico (5 opções) |
    | Spawn     | segmentos das bordas disponíveis  |        — |                          — |      categórico (no 5x3)|
    | Enemy     | speed                             |  0.75% ? |                     150% ? |                contínuo |
    | Enemy     | HP                                |        1 |                        5 ? |                discreto |
    | Drops     | distribuição (qual inimigo dropa) |        — |                          — |                discreto |
    | Next wave | orçamento inimigos da wave        |       35 |                         45 |                discreto |
    | Next wave | orçamento drops da wave           |        1 |    5 por wave, no máximo ? |                discreto |
    | Next wave | parâmetros iniciais da horda      |        — |                          — |              categórico |
    """

    # Limites de spawn
    MIN_GROUP_DELAY = 2.0
    MAX_GROUP_DELAY = 6.0

    MIN_GROUP_COUNT = 1
    MAX_GROUP_COUNT = 7

    MAX_ENEMIES_PER_GROUP = 7

    # Limites dos inimigos
    MIN_SPEED_MULTIPLIER = 0.75
    MAX_SPEED_MULTIPLIER = 1.50

    MIN_ENEMY_HP = 1
    MAX_ENEMY_HP = 5

    # Limites de drop
    MIN_HEALTH_DROP_BUDGET = 0
    MAX_HEALTH_DROP_BUDGET = 5

    # Sobrevivência
    CRITICAL_HEALTH_RATIO = 0.15
    LOW_HEALTH_RATIO = 0.30

    # Progresso
    EARLY_PROGRESS_THRESHOLD = 0.33
    MIDDLE_PROGRESS_THRESHOLD = 0.66

    # Performance
    LOW_PERFORMANCE_THRESHOLD = 0.75
    HIGH_PERFORMANCE_THRESHOLD = 1.25

    # Velocidades base
    BASE_ENEMY_SPEED = {
        1: 250.0,
        2: 200.0,
        3: 150.0,
    }

    # Taxa esperada das mortes por segundo
    EXPECTED_KILL_RATE = {
        Pressure.LOW: 1.0,
        Pressure.ADEQUATE: 2.0,
        Pressure.HIGH: 3.0,
        Pressure.CRITICAL: 4.0,
    }

    # Pressão
    ALIVE_PRESSURE_WEIGHT = 0.70
    TIER_THREAT_WEIGHT = 0.30

    # Avaliação
    MIN_EVALUATION_TIME = 2.0
    MAX_EVALUATION_TIME = 4.0
    MAX_EVALUATION_MULTIPLIER = 1.5

    # Pesos das avaliações
    # A magnitude de uma intervenção é determinada pela soma dos pesos das dimensões modificadas simultaneamente.
    ADAPTATION_WEIGHTS = {
        "DELAY": 1,
        "SPEED": 2,
        "TIER": 2,
        "HP": 2,
        "GROUP_COUNT": 3,
        "FORMATION": 3,
    }

    SMALL_MIN_WEIGHT = 1
    SMALL_MAX_WEIGHT = 3

    MEDIUM_MIN_WEIGHT = 4
    MEDIUM_MAX_WEIGHT = 6

    LARGE_MIN_WEIGHT = 7

    MAX_ADAPTATION_WEIGHT = sum(ADAPTATION_WEIGHTS.values())

    # Histórico usado para diversificar as decisões
    RECENT_INTERVENTION_HISTORY_SIZE = 6

    # DROP_SCHEDULE como intervenção de emergência, fora das seis dimensões que determinam a magnitude normal
    IMPACT_DROP_SCHEDULE = 0.0
    IMPACT_NEXT_WAVE = 0.0

    ################################################################################################################################## 
    def __init__(self):
        self.reset()

    def reset(self):
        self.is_evaluating = False

        self.intervention_id = 0

        self.evaluation_elapsed = 0.0

        self.minimum_evaluation_time = 0.0

        self.maximum_evaluation_time = 0.0

        self.intervention_observations = []

        # Histórico recente de combinações escolhidas. Cada entrada é uma tupla ordenada de tipos de adaptação
        self._recent_interventions = []

        # Quantidade de ocorrências recentes por dimensão
        self._recent_dimension_counts = {
            adaptation_type: 0
            for adaptation_type in self.ADAPTATION_WEIGHTS
        }

        self._active_adaptation = None

        self._last_decision = None

    def update(self, context, emotion, dt):
        # Avalia o estado atual e produz uma Adaptation quando necessário.
        if context is None:
            raise TypeError("Context cannot be None.")

        if emotion is None:
            raise TypeError("Emotion cannot be None.")

        if dt < 0.0:
            raise ValueError("dt must be greater than or equal to zero.")

        game_context = (context.get("game") or {})

        if game_context.get("state") != "PLAYING":
            return None

        emotional_tendency = (self._normalize_emotional_tendency(emotion))

        # Observação de intervenção em andamento
        if self.is_evaluating:
            self.evaluation_elapsed += dt

            self._record_observation(
                context=context,
                emotion=emotional_tendency,
            )

            # Emergência
            if self._emergency_condition_detected(context):
                self._finish_intervention_evaluation()

                adaptation = (
                    self._create_emergency_adaptation(
                        context=context,
                    )
                )

                if adaptation is None:
                    return None

                self._start_intervention_evaluation(adaptation)

                return adaptation

            # Avaliação mínima
            if(self.evaluation_elapsed < self.minimum_evaluation_time):
                return None

            # Efeito suficiente
            if self._effect_is_clear(
                context=context,
                emotion=emotional_tendency,
            ):
                self._finish_intervention_evaluation()
                return None

            # Avaliação máxima
            if(self.evaluation_elapsed >= self.maximum_evaluation_time):
                self._finish_intervention_evaluation()
                return None

            return None

        # Nova decisão
        decision = (self._evaluate_decision(
                context=context,
                emotion=emotional_tendency,
            )
        )

        if decision["action"] == Action.KEEP:
            self._last_decision = decision
            return None

        adaptation = (self._create_adaptation(
                context=context,
                decision=decision,
            )
        )

        if(adaptation is None or adaptation.is_empty()):
            return None

        self._start_intervention_evaluation(adaptation)

        return adaptation


    # Entrada I : EMOÇÃO
    ##################################################################################################################################
    def _normalize_emotional_tendency(self, emotion):

        if isinstance(emotion, str):
            tendency = emotion.upper()

        elif isinstance(emotion, dict):
            tendency = emotion.get("tendency", emotion.get("emotional_tendency"))

            if tendency is None:
                raise ValueError("Emotion context must contain 'tendency'.")

            tendency = str(tendency).upper()

        else:
            raise TypeError("Emotion must be a string or dictionary.")

        if tendency not in {
            EmotionalTendency.DOWN,
            EmotionalTendency.STABLE,
            EmotionalTendency.UP,
        }:

            raise ValueError(f"Invalid emotional tendency: {tendency}")

        return tendency


    # PRESSÃO
    def _infer_pressure(self, context):
        game_context = (context.get("game") or {})

        alive_enemies = int(game_context.get("alive_enemies", 0))

        max_alive_enemies = int(game_context.get("max_alive_enemies", 0))

        composition = (game_context.get("enemy_composition", {}) or {})

        if alive_enemies <= 0:
            alive_pressure = 0.0
            tier_threat = 0.0

        else:
            if max_alive_enemies <= 0:
                raise ValueError("max_alive_enemies must be greater than zero.")

            alive_pressure = (alive_enemies / max_alive_enemies)

            tier1 = int(composition.get(1, 0))

            tier2 = int(composition.get(2, 0))

            tier3 = int(composition.get(3, 0))

            weighted_tier_count = (tier1 + tier2 * 2 + tier3 * 3)

            tier_threat = (weighted_tier_count / (alive_enemies * 3.0))

        score = (self.ALIVE_PRESSURE_WEIGHT * alive_pressure + self.TIER_THREAT_WEIGHT * tier_threat)

        score = max(0.0, min(1.0, score))

        if score < 0.30:
            category = Pressure.LOW

        elif score < 0.60:
            category = Pressure.ADEQUATE

        elif score < 0.80:
            category = Pressure.HIGH

        else:
            category = Pressure.CRITICAL

        return {
            "category": category,
            "score": score,
            "alive_pressure": alive_pressure,
            "tier_threat": tier_threat,
        }


    # SOBREVIVÊNCIA
    def _infer_survivability(self, context):
        player_context = (context.get("player") or {})

        health = float(player_context.get("health", 0))

        max_health = float(player_context.get("max_health", 0))

        if max_health <= 0.0:
            return {
                "category": Survivability.CRITICAL,
                "health_ratio": 0.0,
            }

        ratio = (health / max_health)

        ratio = max(0.0, min(1.0, ratio))

        if ratio <= self.CRITICAL_HEALTH_RATIO:
            category = Survivability.CRITICAL

        elif ratio <= self.LOW_HEALTH_RATIO:
            category = Survivability.LOW

        else:
            category = Survivability.SAFE

        return {
            "category": category,
            "health_ratio": ratio,
        }


    # PROGRESSO
    def _infer_wave_progress(self, context):
        game_context = (context.get("game") or {})

        total_enemies = int(game_context.get("total_enemies", 0))

        remaining_to_spawn = int(game_context.get("remaining_to_spawn", 0))

        alive_enemies = int(game_context.get("alive_enemies", 0))

        if total_enemies <= 0:

            return {
                "category": WaveProgress.LATE,
                "progress": 1.0,
                "kills_this_wave": 0,
            }

        kills_this_wave = (total_enemies - remaining_to_spawn - alive_enemies)

        kills_this_wave = max(0, min(total_enemies, kills_this_wave))

        progress = (kills_this_wave / total_enemies)

        if progress < self.EARLY_PROGRESS_THRESHOLD:
            category = WaveProgress.EARLY

        elif progress < self.MIDDLE_PROGRESS_THRESHOLD:
            category = WaveProgress.MIDDLE

        else:
            category = WaveProgress.LATE

        return {
            "category": category,
            "progress": progress,
            "kills_this_wave": kills_this_wave,
        }


    # DESEMPENHO DO JOGADOR
    def _infer_performance(self, context, pressure):
        game_context = (context.get("game") or {})

        kill_rate = float(game_context.get("kill_rate", 0.0))

        expected_rate = (self.EXPECTED_KILL_RATE[pressure["category"]])

        if expected_rate <= 0.0:
            ratio = 0.0
        else:
            ratio = (kill_rate / expected_rate)

        if ratio < self.LOW_PERFORMANCE_THRESHOLD:
            category = Performance.LOW

        elif ratio < self.HIGH_PERFORMANCE_THRESHOLD:
            category = Performance.ADEQUATE

        else:
            category = Performance.HIGH

        return {
            "category": category,
            "kill_rate": kill_rate,
            "expected_kill_rate": expected_rate,
            "ratio": ratio,
        }


    # DECISÕES
    def _evaluate_decision(self, context, emotion):
        pressure = (self._infer_pressure(context))

        survivability = (self._infer_survivability(context))

        wave_progress = (self._infer_wave_progress(context))

        performance = (self._infer_performance(
                context=context,
                pressure=pressure,
            )
        )

        if (survivability["category"] == Survivability.CRITICAL):
            decision = {
                "action": Action.REDUCE,
                "strength": Strength.LARGE,
                "reason": "EMERGENCY",
            }

        else:
            decision = (
                self._get_matrix_decision(
                    pressure=pressure["category"],
                    performance=performance["category"],
                    emotional_tendency=emotion,
                )
            )

        decision.update({
            "pressure": pressure,
            "performance": performance,
            "survivability": survivability,
            "wave_progress": wave_progress,
            "emotional_tendency": emotion,
        })

        decision = (self._apply_wave_progress_policy(decision, wave_progress))

        self._last_decision = decision

        return decision


    def _get_matrix_decision(self, pressure, performance, emotional_tendency):
        matrix = {
            Pressure.LOW: {
                Performance.LOW: {
                    EmotionalTendency.DOWN:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                },

                Performance.ADEQUATE: {
                    EmotionalTendency.DOWN:
                        (Action.INCREASE, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                },

                Performance.HIGH: {
                    EmotionalTendency.DOWN:
                        (Action.INCREASE, Strength.MEDIUM),
                    EmotionalTendency.STABLE:
                        (Action.INCREASE, Strength.MEDIUM),
                    EmotionalTendency.UP:
                        (Action.INCREASE, Strength.MEDIUM)
                }
            },

            Pressure.ADEQUATE: {
                Performance.LOW: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                },

                Performance.ADEQUATE: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                },

                Performance.HIGH: {
                    EmotionalTendency.DOWN:
                        (Action.INCREASE, Strength.MEDIUM),
                    EmotionalTendency.STABLE:
                        (Action.INCREASE, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                }
            },

            Pressure.HIGH: {
                Performance.LOW: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.LARGE),
                    EmotionalTendency.STABLE:
                        (Action.REDUCE, Strength.MEDIUM),
                    EmotionalTendency.UP:
                        (Action.REDUCE, Strength.SMALL)
                },

                Performance.ADEQUATE: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                },

                Performance.HIGH: {
                    EmotionalTendency.DOWN:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.KEEP, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                }
            },

            Pressure.CRITICAL: {
                Performance.LOW: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.LARGE),
                    EmotionalTendency.STABLE:
                        (Action.REDUCE, Strength.LARGE),
                    EmotionalTendency.UP:
                        (Action.REDUCE, Strength.LARGE)
                },

                Performance.ADEQUATE: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.MEDIUM),
                    EmotionalTendency.STABLE:
                        (Action.REDUCE, Strength.MEDIUM,),
                    EmotionalTendency.UP:
                        (Action.REDUCE, Strength.MEDIUM)
                },

                Performance.HIGH: {
                    EmotionalTendency.DOWN:
                        (Action.REDUCE, Strength.SMALL),
                    EmotionalTendency.STABLE:
                        (Action.REDUCE, Strength.SMALL),
                    EmotionalTendency.UP:
                        (Action.KEEP, Strength.SMALL)
                }
            }
        }

        action, strength = (matrix[pressure][performance][emotional_tendency])

        return {
            "action": action,
            "strength": strength,
            "reason": "DECISION_MATRIX",
        }


    # MODERAÇÃO PELO PROGRESSO
    @staticmethod
    def _apply_wave_progress_policy(decision, wave_progress):
        if(wave_progress["category"] == WaveProgress.EARLY and decision["strength"] == Strength.LARGE):
            decision["strength"] = (Strength.MEDIUM)

        return decision


    # CRIAÇÃO DE ADAPTAÇÃO
    def _create_adaptation(self, context, decision):
        future_groups = self._get_future_groups(context)

        if not future_groups:
            return None

        if decision["action"] == Action.INCREASE:
            return self._build_adaptation_from_candidates(
                context=context,
                decision=decision,
                future_groups=future_groups,
                direction=1,
            )

        if decision["action"] == Action.REDUCE:
            return self._build_adaptation_from_candidates(
                context=context,
                decision=decision,
                future_groups=future_groups,
                direction=-1,
            )

        return None

    # SELEÇÃO DA COMPOSIÇÃO
    def _build_adaptation_from_candidates(self, context, decision, future_groups, direction):
        strength = decision["strength"]

        candidate = self._select_adaptation_combination(
            context=context,
            future_groups=future_groups,
            strength=strength,
            direction=direction,
        )

        if candidate is None:
            return None

        groups = self._copy_groups(future_groups)
        changes = []

        # Ordem de aplicação não participa da seleção dos candidatos.
        application_order = ("GROUP_COUNT", "TIER", "HP", "SPEED", "DELAY", "FORMATION")

        for adaptation_type in application_order:
            if adaptation_type not in candidate["types"]:
                continue

            change_result = self._apply_adaptation_type(
                adaptation_type=adaptation_type,
                groups=groups,
                direction=direction,
            )

            if change_result is None:
                return None

            if adaptation_type == "GROUP_COUNT":
                changed, groups = change_result

            else:
                changed = change_result

            if not changed:
                return None

            weight = self.ADAPTATION_WEIGHTS[adaptation_type]

            changes.append({
                "type": adaptation_type,
                "weight": weight,
                "magnitude": float(weight),
            })

        if not changes:
            return None

        total_weight = sum(change["weight"] for change in changes)

        calculated_strength = self._classify_strength(total_weight)

        # O plano produzido deve ser >= ao mínimo.
        if not self._strength_accepts_weight(
            strength=strength,
            weight=total_weight,
        ):
            return None

        self._validate_future_spawn_plan(
            context=context,
            groups=groups,
        )

        self.intervention_id += 1

        current_wave = {
            "action": decision["action"],
            "reason": decision["reason"],
            "decision_strength": strength,
            "calculated_strength": calculated_strength,
            "intervention_weight": total_weight,
            "selected_adaptations": list(candidate["types"]),
            "selection": {
                "minimum_required_weight": candidate["minimum_required_weight"],
                "candidate_count": candidate["candidate_count"],
                "combination_repeat_count": candidate["combination_repeat_count"],
                "dimension_usage_score": candidate["dimension_usage_score"],
            },
            "spawn": {
                "action": "replace_future_groups",
                "groups": groups,
            },
            "drops": None,
            "changes": changes,
        }

        evaluation_time = self._calculate_evaluation_time(total_weight)

        adaptation = Adaptation(
            intervention_id=self.intervention_id,
            current_wave=current_wave,
            next_wave=None,
            evaluation_time=evaluation_time,
        )

        self._record_intervention_history(candidate["types"])

        return adaptation

    def _select_adaptation_combination(self, context, future_groups, strength, direction):

        minimum_required_weight = self._get_strength_min_weight(strength)

        maximum_weight = self._get_strength_max_weight(strength)

        candidates = []

        adaptation_types = tuple(self.ADAPTATION_WEIGHTS.keys())

        for size in range(1, len(adaptation_types) + 1):
            for combination in combinations(adaptation_types, size):
                total_weight = sum(self.ADAPTATION_WEIGHTS[item] for item in combination)

                if total_weight < minimum_required_weight:
                    continue

                if(maximum_weight is not None and total_weight > maximum_weight):
                    continue

                if not self._combination_is_applicable(
                    future_groups=future_groups,
                    combination=combination,
                    direction=direction,
                ):
                    continue

                recent_exact_count = self._get_recent_combination_count(combination)

                dimension_usage_score = self._get_dimension_usage_score(combination)

                candidates.append({
                    "types": tuple(combination),
                    "weight": total_weight,
                    "combination_repeat_count": recent_exact_count,
                    "dimension_usage_score": dimension_usage_score,
                })

        if not candidates:
            # Qualquer combinação com o menor peso possível acima do mínimo é aceitável. Para LARGE, não há teto
            if strength == Strength.LARGE:
                fallback = []

                for size in range(1, len(adaptation_types) + 1):
                    for combination in combinations(adaptation_types, size):
                        total_weight = sum(self.ADAPTATION_WEIGHTS[item] for item in combination)

                        if total_weight < minimum_required_weight:
                            continue

                        if self._combination_is_applicable(
                            future_groups=future_groups,
                            combination=combination,
                            direction=direction,
                        ):
                            fallback.append({
                                "types": tuple(combination),
                                "weight": total_weight,
                                "combination_repeat_count": self._get_recent_combination_count(combination),
                                "dimension_usage_score": self._get_dimension_usage_score(combination),
                            })

                candidates = fallback

        if not candidates:
            return None

        # Regra determinística:
        # 1) menor número de dimensões alteradas;
        # 2) menor repetição da combinação inteira;
        # 3) menor uso recente das dimensões;
        # 4) menor peso dentro das alternativas restantes;
        # 5) desempate por ordem canônica da tupla.
        selected = min(
            candidates,
            key=lambda candidate: (
                len(candidate["types"]),
                candidate["combination_repeat_count"],
                candidate["dimension_usage_score"],
                candidate["weight"],
                candidate["types"],
            ),
        )

        selected = dict(selected)
        selected["minimum_required_weight"] = minimum_required_weight
        selected["candidate_count"] = len(candidates)

        return selected

    def _combination_is_applicable(self, future_groups, combination, direction):
        groups = self._copy_groups(future_groups)

        application_order = ("GROUP_COUNT", "TIER", "HP", "SPEED", "DELAY", "FORMATION")

        for adaptation_type in application_order:
            if adaptation_type not in combination:
                continue

            result = self._apply_adaptation_type(adaptation_type=adaptation_type, groups=groups, direction=direction)

            if result is None:
                return False

            if adaptation_type == "GROUP_COUNT":
                changed, groups = result
            else:
                changed = result

            if not changed:
                return False

        return True

    def _apply_adaptation_type(self, adaptation_type, groups, direction):
        if adaptation_type == "GROUP_COUNT":
            return self._change_future_group_count(groups, direction)

        if adaptation_type == "TIER":
            return self._change_future_tier(groups, direction)

        if adaptation_type == "HP":
            return self._change_future_hp(groups, direction)

        if adaptation_type == "SPEED":
            return self._change_future_speed(groups, 0.25 * direction)

        if adaptation_type == "DELAY":
            amount = -1.0 if direction > 0 else 1.0

            if not self._can_change_group_delays(groups, amount):
                return False

            self._change_group_delays(groups, amount)

            return True

        if adaptation_type == "FORMATION":
            return self._change_future_formation(groups)

        return None


    # HISTÓRICO E DIVERSIDADE
    def _record_intervention_history(self, adaptation_types):
        combination = tuple(adaptation_types)

        self._recent_interventions.append(combination)

        for adaptation_type in combination:
            self._recent_dimension_counts[adaptation_type] += 1

        while len(self._recent_interventions) > self.RECENT_INTERVENTION_HISTORY_SIZE:
            removed = self._recent_interventions.pop(0)

            for adaptation_type in removed:self._recent_dimension_counts[adaptation_type] -= 1

    def _get_recent_combination_count(self, combination):
        normalized = tuple(combination)

        return sum(1 for previous in self._recent_interventions if previous == normalized)

    def _get_dimension_usage_score(self, combination):
        return sum(self._recent_dimension_counts.get(adaptation_type, 0) for adaptation_type in combination)


    # CLASSIFICAÇÃO DA MAGNITUDE
    @classmethod
    def _classify_strength(cls, total_weight):
        if total_weight <= cls.SMALL_MAX_WEIGHT:
            return Strength.SMALL

        if total_weight <= cls.MEDIUM_MAX_WEIGHT:
            return Strength.MEDIUM

        return Strength.LARGE

    @classmethod
    def _strength_accepts_weight(cls, strength, weight):
        minimum = cls._get_strength_min_weight(strength)

        maximum = cls._get_strength_max_weight(strength)

        if weight < minimum:
            return False

        if maximum is not None and weight > maximum:
            return False

        return True

    @classmethod
    def _get_strength_min_weight(cls, strength):
        if strength == Strength.SMALL:
            return cls.SMALL_MIN_WEIGHT

        if strength == Strength.MEDIUM:
            return cls.MEDIUM_MIN_WEIGHT

        if strength == Strength.LARGE:
            return cls.LARGE_MIN_WEIGHT

        return 1

    @classmethod
    def _get_strength_max_weight(cls, strength):
        if strength == Strength.SMALL:
            return cls.SMALL_MAX_WEIGHT

        if strength == Strength.MEDIUM:
            return cls.MEDIUM_MAX_WEIGHT

        return None

    # FUTURO DA WAVE
    def _get_future_groups(self, context):
        game_context = (context.get("game") or {})

        spawn_state = (game_context.get("spawn_state") or {})

        groups = list(spawn_state.get("groups", []))

        next_group_index = int(spawn_state.get("next_group_index", 0))

        if next_group_index < 0:
            raise ValueError(
                "next_group_index cannot be negative."
            )

        if next_group_index > len(groups):
            raise ValueError(
                "next_group_index cannot exceed the number of groups."
            )

        return [dict(group) for group in groups[next_group_index:]]

    # CÓPIA PROFUNDA DOS GROUPS
    @staticmethod
    def _copy_groups(groups):
        copied = []

        for group in groups:
            copied.append({
                "enemy_specs": [dict(spec) for spec in group.get("enemy_specs", [])],

                "spawn_region": dict(group.get("spawn_region", {})),

                "formation": group.get("formation"),

                "delay": float(group.get("delay", 0.0))
            })

        return copied

    # DELAY
    def _can_change_group_delays(self, groups, amount):
        for group in groups:
            current_delay = float(group.get("delay", self.MIN_GROUP_DELAY))

            candidate = (current_delay + amount)

            candidate = max(self.MIN_GROUP_DELAY, min(self.MAX_GROUP_DELAY, candidate))

            if abs(candidate - current_delay) > 1e-9:
                return True

        return False

    def _change_group_delays(self, groups, amount):
        for group in groups:
            current_delay = float(group.get("delay", self.MIN_GROUP_DELAY))

            new_delay = (current_delay + amount)

            new_delay = max(self.MIN_GROUP_DELAY, min(self.MAX_GROUP_DELAY, new_delay))

            group["delay"] = new_delay

        return groups


    # GROUP COUNT
    def _change_future_group_count(self, groups, amount):
        current_count = len(groups)

        target_count = (current_count + amount)

        if(target_count < self.MIN_GROUP_COUNT or target_count > self.MAX_GROUP_COUNT):
            return False, groups

        enemy_specs = []

        for group in groups:
            enemy_specs.extend([dict(spec) for spec in group.get("enemy_specs", [])])

        if not enemy_specs:
            return False, groups

        if target_count > len(enemy_specs):
            return False, groups

        rebuilt = (self._redistribute_enemy_specs(enemy_specs=enemy_specs, target_group_count=target_count, original_groups=groups))

        if rebuilt is None:
            return False, groups

        return True, rebuilt

    def _redistribute_enemy_specs(self, enemy_specs, target_group_count, original_groups):
        total = len(enemy_specs)

        if total <= 0:
            return None

        if(target_group_count <= 0 or target_group_count > total):
            return None

        # Distribuição equilibrada
        base_size = (total // target_group_count)

        remainder = (total % target_group_count)

        sizes = []

        for index in range(target_group_count):
            size = (base_size + (1 if index < remainder else 0))

            if(size <= 0 or size > self.MAX_ENEMIES_PER_GROUP):
                return None

            sizes.append(size)

        # Regiões / delays originais
        original_regions = [dict(group.get("spawn_region", {}))for group in original_groups]

        original_delays = [float(group.get("delay", self.MIN_GROUP_DELAY)) for group in original_groups]

        if not original_regions:
            return None

        # Reconstrução
        result = []

        cursor = 0

        for index, size in enumerate(sizes):
            specs = [dict(spec) for spec in enemy_specs[cursor:cursor + size]]

            cursor += size

            region = dict(original_regions[index % len(original_regions)])

            delay = (original_delays[index % len(original_delays)])

            formation = (self._select_safe_formation(enemy_specs=specs, spawn_region=region))

            if formation is None:
                return None

            result.append({
                "enemy_specs": specs,
                "spawn_region": region,
                "formation": formation,
                "delay": delay,
            })

        return result


    # FORMATION SEGURA
    def _select_safe_formation(self, enemy_specs, spawn_region,):
        # Escolhe uma formação fisicamente válida, usando como parâmetros de decisão:
        # quantidade de inimigos, raio real do Enemy, eixo do segmento, largura física, e spacing real da Formation

        if not enemy_specs:
            return None

        count = len(enemy_specs)

        if(count <= 0 or count > self.MAX_ENEMIES_PER_GROUP):
            return None

        border = (spawn_region.get("border"))

        if border in ("TOP", "BOTTOM"):
            segment_axis = "x"

        elif border in ("LEFT", "RIGHT"):
            segment_axis = "y"

        else:
            return None

        # Raios reais dos inimigos
        radii = []

        for spec in enemy_specs:
            tier = spec.get("tier")

            if tier not in (1, 2, 3):
                return None

            radii.append(Enemy.get_radius_by_tier(tier))

        # Formações preferenciais (o teste físico determina se elas realmente cabem)
        if count in (4, 6):
            candidate_formations = (Formation.BLOCK, Formation.DIAMOND, Formation.LINE, Formation.COLUMN)

        elif count in (5, 7):
            candidate_formations = (Formation.DIAMOND, Formation.ARC, Formation.LINE, Formation.COLUMN)

        else:
            candidate_formations = (Formation.LINE, Formation.COLUMN,)

        # Formação orientada ao segmento
        if segment_axis == "x":
            candidate_formations = (self._prefer_horizontal_formations(candidate_formations))

        else:
            candidate_formations = (self._prefer_vertical_formations(candidate_formations))

        # Validação geométrica
        for formation in candidate_formations:
            if count not in (Formation.SUPPORTED_COUNTS[formation]):
                continue

            if Formation.can_fit(
                formation=formation,
                radii=radii,
                segment_width=Formation.DEFAULT_SEGMENT_WIDTH,
                segment_axis=segment_axis,
                spacing=Formation.DEFAULT_SPACING,
            ):
                return formation

        return None

    @staticmethod
    def _prefer_horizontal_formations(formations):
        preferred = [Formation.LINE, Formation.BLOCK, Formation.DIAMOND, Formation.ARC, Formation.COLUMN]

        return [formation for formation in preferred if formation in formations]

    @staticmethod
    def _prefer_vertical_formations(formations):
        preferred = [Formation.COLUMN, Formation.BLOCK, Formation.DIAMOND, Formation.ARC, Formation.LINE]

        return [formation for formation in preferred if formation in formations]


    # SPEED
    def _change_future_speed(self, groups, delta_multiplier):
        changed = False

        for group in groups:
            new_specs = []

            for spec in group["enemy_specs"]:
                new_spec = dict(spec)

                tier = new_spec.get("tier")

                base_speed = (self.BASE_ENEMY_SPEED[tier])

                current_speed = float(new_spec.get("speed", base_speed))

                current_multiplier = (current_speed / base_speed)

                new_multiplier = (current_multiplier + delta_multiplier)

                new_multiplier = max(self.MIN_SPEED_MULTIPLIER, min(self.MAX_SPEED_MULTIPLIER, new_multiplier))

                if abs(new_multiplier - current_multiplier) > 1e-9:
                    changed = True

                if(abs(new_multiplier - 1.0) <= 1e-9):
                    new_spec.pop("speed", None)

                else:
                    new_spec["speed"] = (base_speed * new_multiplier)

                new_specs.append(new_spec)

            group["enemy_specs"] = (new_specs)

        return changed


    # TIER
    def _change_future_tier(self, groups, direction,):
        if direction not in (-1, 1):
            raise ValueError(
                "direction must be -1 or 1."
            )

        if direction > 0:
            source_tiers = (1, 2)

        else:
            source_tiers = (3, 2)

        for source_tier in source_tiers:
            for group in groups:
                for index, spec in enumerate(group["enemy_specs"]):
                    if spec.get("tier") != source_tier:
                        continue

                    new_tier = (source_tier + direction)

                    new_spec = dict(spec)

                    new_spec["tier"] = (new_tier)

                    # Overrides relacionados ao Tier anterior são removidos.
                    new_spec.pop("speed", None)

                    if("max_health" in new_spec):
                        old_base_hp = (source_tier)

                        if(float(new_spec["max_health"]) == float(old_base_hp)):
                            new_spec.pop("max_health", None)

                    group["enemy_specs"][index] = new_spec

                    # A formação pode ter mudado de validade física após o novo Tier, então ela será recalculada posteriormente
                    
                    return True

        return False


    # HP
    def _change_future_hp(self, groups, direction):
        if direction not in (-1, 1):
            raise ValueError(
                "direction must be -1 or 1."
            )

        for group in groups:
            for index, spec in enumerate(group["enemy_specs"]):
                tier = int(spec["tier"])

                base_hp = (tier)

                current_hp = float(spec.get("max_health", base_hp))

                new_hp = (current_hp + direction)

                new_hp = max(self.MIN_ENEMY_HP, min(self.MAX_ENEMY_HP, new_hp))

                if abs(new_hp - current_hp) <= 1e-9:
                    continue

                new_spec = dict(spec)

                new_spec["max_health"] = (int(new_hp) if new_hp.is_integer() else new_hp)

                group["enemy_specs"][index] = new_spec

                return True

        return False


    # FORMATION
    def _change_future_formation(self, groups):
        # Altera a formação futura de cada Group para outra formação válida.

        changed = False

        for group in groups:
            enemy_specs = group.get("enemy_specs", [])

            region = group.get("spawn_region", {})

            current = group.get("formation")

            alternatives = self._get_safe_formation_alternatives(
                enemy_specs=enemy_specs,
                spawn_region=region,
                current_formation=current,
            )

            if not alternatives:
                return False

            selected = alternatives[0]

            if selected != current:
                group["formation"] = selected
                changed = True

        return changed

    def _get_safe_formation_alternatives(self, enemy_specs, spawn_region, current_formation):

        if not enemy_specs:
            return []

        border = spawn_region.get("border")

        if border in ("TOP", "BOTTOM",):
            segment_axis = "x"
            preferred = [Formation.LINE, Formation.BLOCK, Formation.DIAMOND, Formation.ARC, Formation.COLUMN]

        elif border in ("LEFT", "RIGHT"):
            segment_axis = "y"
            preferred = [Formation.COLUMN, Formation.BLOCK, Formation.DIAMOND, Formation.ARC, Formation.LINE]

        else:
            return []

        count = len(enemy_specs)

        radii = []
        for spec in enemy_specs:
            tier = spec.get("tier")
            if tier not in (1, 2, 3):
                return []
            radii.append(Enemy.get_radius_by_tier(tier))

        valid = []

        # Começa depois da formação atual para garantir mudança sempre que existir pelo menos uma alternativa fisicamente válida
        if current_formation in preferred:
            start_index = preferred.index(current_formation) + 1

        else:
            start_index = 0

        ordered = (preferred[start_index:] + preferred[:start_index])

        for formation in ordered:
            if formation == current_formation:
                continue

            if count not in Formation.SUPPORTED_COUNTS[formation]:
                continue

            if Formation.can_fit(
                formation=formation,
                radii=radii,
                segment_width=Formation.DEFAULT_SEGMENT_WIDTH,
                segment_axis=segment_axis,
                spacing=Formation.DEFAULT_SPACING,
            ):
                valid.append(formation)

        return valid


    # SPATIAL TARGET
    def _apply_spatial_target(self, context, groups, target):
        if not groups:
            return False

        game_context = (context.get("game") or {})

        player_context = (context.get("player") or {})

        allowed_borders = (game_context.get("allowed_spawn_borders", []) or [])

        player_position = (player_context.get("position", [2, 1]))

        arena_width = float(game_context.get("arena_width", 1280))

        arena_height = float(game_context.get("arena_height", 720))

        if not allowed_borders:
            return False

        candidates = (
            self._get_segment_candidates(
                allowed_borders=allowed_borders,
                arena_width=arena_width,
                arena_height=arena_height,
                player_position=player_position,
            )
        )

        if not candidates:
            return False

        ordered = (self._get_ordered_spatial_candidates(candidates, target))

        changed = False

        # Cada Group recebe um candidato espacial.
        for index, group in enumerate(groups):
            selected = (ordered[index % len(ordered)])

            new_region = {
                "border": selected["border"],
                "segment": selected["segment"]
            }

            previous_region = (
                group.get("spawn_region", {})
            )

            if(previous_region.get("border") != new_region["border"] or previous_region.get("segment") != new_region["segment"]):
                changed = True

            group["spawn_region"] = (new_region)

            # Recalcula a formação porque o eixo pode ter mudado.
            formation = (self._select_safe_formation(enemy_specs=group["enemy_specs"], spawn_region=new_region))

            if formation is None:
                return False

            if formation != group.get("formation"):
                changed = True

            group["formation"] = formation

        return changed


    # CANDIDATOS ESPACIAIS
    def _get_segment_candidates(self, allowed_borders, arena_width, arena_height, player_position):
        candidates = []

        for border in allowed_borders:
            if border in ("TOP", "BOTTOM"):
                segment_count = 5

            elif border in ("LEFT", "RIGHT"):
                segment_count = 3

            else:
                continue

            for segment in range(segment_count):
                point = (self._get_segment_center(border=border, segment=segment, arena_width=arena_width, arena_height=arena_height))

                distance = (
                    self._get_distance_to_player(
                        point=point,
                        player_position=player_position,
                        arena_width=arena_width,
                        arena_height=arena_height,
                    )
                )

                candidates.append({"border": border, "segment": segment, "distance": distance,})

        return candidates


    # CENTRO DOS SEGMENTOS
    @staticmethod
    def _get_segment_center(border, segment, arena_width, arena_height):
        segment_length = 240.0
        margin = 40.0

        if border in ("TOP", "BOTTOM"):
            x = (margin + segment * segment_length + segment_length / 2.0)

            y = (0.0 if border == "TOP" else arena_height)

        else:
            y = (segment * segment_length + segment_length / 2.0)

            x = (0.0 if border == "LEFT" else arena_width)

        return (x, y)


    # DISTÂNCIA
    @staticmethod
    def _get_distance_to_player(point, player_position, arena_width, arena_height):
        column = int(player_position[0])

        row = int(player_position[1])

        cell_width = (arena_width / 5.0)

        cell_height = (arena_height / 3.0)

        player_x = (column * cell_width + cell_width / 2.0)

        player_y = (row * cell_height + cell_height / 2.0)

        dx = (point[0] - player_x)

        dy = (point[1] - player_y)

        return math_hypot(dx, dy)


    # ORDENAÇÃO ESPACIAL
    @staticmethod
    def _get_ordered_spatial_candidates(candidates, target):
        ordered = sorted(candidates, key=lambda candidate: (candidate["distance"], candidate["border"], candidate["segment"]))

        if target == SpatialTarget.NEAR:
            return ordered

        if target == SpatialTarget.FAR:
            return list(reversed(ordered))


        # MEDIUM
        if not ordered:
            return []

        middle = (len(ordered) - 1) // 2

        result = [ordered[middle]]

        left = (middle - 1)

        right = (middle + 1)

        while (left >= 0 or right < len(ordered)):

            if left >= 0:
                result.append(ordered[left])

                left -= 1

            if right < len(ordered):
                result.append(ordered[right])

                right += 1

        return result


    # RECUPERAÇÃO DOS DROPS
    def _build_advanced_recovery_plan(self, context):
        game_context = (context.get("game") or {})

        drop_state = (game_context.get("drop_state") or {})

        schedule = list(drop_state.get("drop_schedule", []))

        next_drop_index = int(drop_state.get("next_drop_index", 0))

        total_enemies = int(game_context.get("total_enemies", 0))

        remaining_to_spawn = int(game_context.get("remaining_to_spawn", 0))

        alive_enemies = int(game_context.get("alive_enemies", 0))

        kills_this_wave = (total_enemies - remaining_to_spawn - alive_enemies)

        kills_this_wave = max(0, min( total_enemies, kills_this_wave))

        future_schedule = (schedule[next_drop_index:])

        if not future_schedule:
            return None

        future_count = len(future_schedule)

        remaining_kills = (total_enemies - kills_this_wave)

        if remaining_kills < future_count:
            return None

        # Distribui os Drops futuros entre os kills restantes.
        available_first = (kills_this_wave + 1)

        available_last = (total_enemies)

        new_schedule = []

        for index in range(future_count):
            fraction = (index + 1) / (future_count + 1)

            candidate = round(available_first + (available_last - available_first) * fraction)

            candidate = max(available_first, min(available_last, candidate))

            if(new_schedule and candidate <= new_schedule[-1]):
                candidate = (new_schedule[-1] + 1)

            new_schedule.append(int(candidate))

        if new_schedule == (future_schedule):
            return None

        return {"action": "replace_future_schedule", "schedule": new_schedule}


    # VALIDAÇÃO DO FUTURO DE SPAWN
    def _validate_future_spawn_plan(self, context, groups):
        if not groups:
            return

        game_context = (context.get("game") or {})

        remaining_to_spawn = int(game_context.get("remaining_to_spawn", 0))

        # Orçamento exato
        future_enemy_count = sum(len(group.get("enemy_specs", [])) for group in groups)

        if future_enemy_count != (remaining_to_spawn):
            raise ValueError(
                "Future spawn plan must contain exactly "
                "the remaining enemy budget."
            )

        # Quantidade de Groups
        if not (self.MIN_GROUP_COUNT <= len(groups) <= self.MAX_GROUP_COUNT):
            raise ValueError(
                "Future spawn plan has an invalid Group count."
            )

        # Validação individual
        for group in groups:
            enemy_specs = (group.get("enemy_specs", []))

            count = len(enemy_specs)

            if(count <= 0 or count > self.MAX_ENEMIES_PER_GROUP):
                raise ValueError(
                    "Future spawn Group has an invalid enemy count."
                )

            region = (group.get("spawn_region", {}))

            border = region.get("border")

            segment = region.get("segment")

            if border not in ("TOP", "BOTTOM", "LEFT", "RIGHT"):
                raise ValueError(
                    "Future spawn Group has an invalid border."
                )

            max_segment = (4 if border in ("TOP", "BOTTOM") else 2)

            if(not isinstance(segment, int) or not(0 <= segment <= max_segment)):
                raise ValueError(
                    "Future spawn Group has an invalid segment."
                )

            formation = group.get("formation")

            if formation not in (Formation.LINE, Formation.COLUMN, Formation.BLOCK, Formation.ARC, Formation.DIAMOND):
                raise ValueError(
                    "Future spawn Group has an invalid formation."
                )

            delay = float(group.get("delay", 0.0))

            if not (self.MIN_GROUP_DELAY <= delay <= self.MAX_GROUP_DELAY):
                raise ValueError(
                    "Future spawn Group delay is outside Director limits."
                )

            # Raios e validade física
            radii = []

            for spec in enemy_specs:
                tier = spec.get("tier")

                if tier not in (1, 2, 3):

                    raise ValueError(
                        "Future enemy spec has an invalid tier."
                    )

                radii.append(Enemy.get_radius_by_tier(tier))

            segment_axis = ("x" if border in ("TOP", "BOTTOM") else "y")

            if not Formation.can_fit(
                formation=formation,
                radii=radii,
                segment_width=Formation.DEFAULT_SEGMENT_WIDTH,
                segment_axis=segment_axis,
                spacing=Formation.DEFAULT_SPACING,
            ):
                raise ValueError(
                    "Future spawn Group formation does not fit its spawn segment."
                )

            # Velocidade / HP
            for spec in enemy_specs:
                tier = int(spec["tier"])

                if "speed" in spec:
                    speed = float(spec["speed"])

                    base_speed = (self.BASE_ENEMY_SPEED[tier])

                    multiplier = (speed / base_speed)

                    if not (self.MIN_SPEED_MULTIPLIER <= multiplier <= self.MAX_SPEED_MULTIPLIER):
                        raise ValueError(
                            "Future enemy speed is outside Director limits."
                        )

                if "max_health" in spec:
                    hp = float(spec["max_health"])

                    if not (self.MIN_ENEMY_HP <= hp <= self.MAX_ENEMY_HP):
                        raise ValueError(
                            "Future enemy HP is outside Director limits."
                        )


    # VALIDAÇÃO DE DROPS
    def _validate_future_drop_plan(self, context, drop_action):
        if drop_action is None:
            return

        game_context = (context.get("game") or {})

        drop_state = (game_context.get("drop_state") or {})

        current_schedule = list(drop_state.get("drop_schedule", []))

        next_drop_index = int(drop_state.get("next_drop_index", 0))

        budget = int(drop_state.get("health_drop_budget", 0))

        total_enemies = int(game_context.get("total_enemies", 0))

        remaining_to_spawn = int(game_context.get("remaining_to_spawn", 0))

        alive_enemies = int(game_context.get("alive_enemies", 0))

        kills_this_wave = (total_enemies - remaining_to_spawn - alive_enemies)

        kills_this_wave = max(0, min(total_enemies, kills_this_wave))

        triggered_schedule = (current_schedule[:next_drop_index])

        future_schedule = list(drop_action.get("schedule", []))

        # O futuro precisa completar o budget total
        if(len(triggered_schedule) + len(future_schedule) != budget):
            raise ValueError(
                "Future drop schedule must complete the Wave drop budget."
            )

        # Ordem
        previous = (triggered_schedule[-1] if triggered_schedule else 0)

        for ordinal in future_schedule:
            if not isinstance(ordinal, int):
                raise TypeError(
                    "Drop schedule entries must be integers."
                )

            if ordinal <= previous:
                raise ValueError(
                    "Drop schedule must be strictly increasing."
                )

            if ordinal > (total_enemies):
                raise ValueError(
                    "Drop schedule cannot exceed total enemies."
                )

            if ordinal <= (kills_this_wave):
                raise ValueError(
                    "Future drop schedule cannot reference past kills."
                )

            previous = ordinal


    # EMERGÊNCIA
    def _emergency_condition_detected(self, context):
        survivability = self._infer_survivability(context)

        game_context = (context.get("game") or {})

        alive_enemies = int(game_context.get("alive_enemies", 0))

        return (survivability["category"] == Survivability.CRITICAL and alive_enemies >= 5)

    def _create_emergency_adaptation(self, context):
        future_groups = self._get_future_groups(context)

        if not future_groups:
            return None

        decision = {
            "action": Action.REDUCE,
            "strength": Strength.LARGE,
            "reason": "EMERGENCY",
        }

        adaptation = self._build_adaptation_from_candidates(
            context=context,
            decision=decision,
            future_groups=future_groups,
            direction=-1,
        )

        if adaptation is None:
            return None

        # Recuperação de drops continua sendo um mecanismo de segurança específico de emergência
        # Ela não participa da classificação de magnitude porque os pesos oficiais do Director são as seis dimensões de adaptação
        drops = self._build_advanced_recovery_plan(context)

        if drops is not None:
            current_wave = adaptation.current_wave
            current_wave["drops"] = drops
            current_wave["emergency_recovery"] = True

            self._validate_future_drop_plan(context=context, drop_action=drops,)

        return adaptation

    # MAGNITUDE
    def _calculate_adaptation_magnitude(self, current_wave, next_wave):
        magnitude = 0.0

        if current_wave:
            for change in ( current_wave.get( "changes", []) or []):
                weight = change.get("weight")

                if weight is None:
                    weight = self.ADAPTATION_WEIGHTS.get(change.get("type"), 0)

                magnitude += float(weight)

        return magnitude


    # TEMPO DE AVALIAÇÃO
    def _calculate_evaluation_time(self, magnitude):
        if magnitude <= 0.0:
            return self.MIN_EVALUATION_TIME

        normalized = min(magnitude / float(self.MAX_ADAPTATION_WEIGHT), 1.0)

        return (self.MIN_EVALUATION_TIME + normalized * (self.MAX_EVALUATION_TIME - self.MIN_EVALUATION_TIME))


    # EFEITO DA INTERVENÇÃO
    def _effect_is_clear(self, context, emotion,):
        if self._emergency_condition_detected(context):
            return False

        decision = (self._evaluate_decision(context=context, emotion=emotion))

        return (decision["action"] == Action.KEEP)

    # AVALIAÇÃO
    def _start_intervention_evaluation(self, adaptation):
        self.is_evaluating = True

        self.evaluation_elapsed = 0.0

        self.minimum_evaluation_time = (adaptation.evaluation_time)

        self.maximum_evaluation_time = (adaptation.evaluation_time * self.MAX_EVALUATION_MULTIPLIER)

        self._active_adaptation = (adaptation)

        self.intervention_observations = []

    def _finish_intervention_evaluation(self):
        self.is_evaluating = False

        self.evaluation_elapsed = 0.0

        self.minimum_evaluation_time = 0.0

        self.maximum_evaluation_time = 0.0

        self._active_adaptation = None

        self.intervention_observations = []


    # OBSERVAÇÕES
    def _record_observation(self, context, emotion):
        self.intervention_observations.append({ "context": context, "emotion": emotion})


    # ESTADO
    def get_state(self):
        return {
            "is_evaluating": (self.is_evaluating),

            "intervention_id": (self.intervention_id),

            "evaluation_elapsed": (self.evaluation_elapsed),

            "minimum_evaluation_time": (self.minimum_evaluation_time),

            "maximum_evaluation_time": (self.maximum_evaluation_time),

            "observation_count": (len(self.intervention_observations)),

            "last_decision": (self._last_decision),

            "recent_interventions": [list(combination) for combination in self._recent_interventions],

            "recent_dimension_counts": dict(self._recent_dimension_counts),

            "active_intervention": (self._active_adaptation.get_state() if self._active_adaptation is not None else None),
        }