######################################################################################################################################
# TCC - MAIN
# JOGO | AI DIRECTOR | FER | EmotionSystem
######################################################################################################################################

from dataclasses import dataclass

import pygame

from AI_DIRECTOR.ai_director import AIDirector
from GAME.game import Game


# CONFIGURAÇÕES
######################################################################################################################################
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

FPS = 60


# INPUT
######################################################################################################################################
@dataclass
class InputState:
    movement: pygame.Vector2
    aim_position: tuple[int, int]
    fire: bool

    confirm: bool = False
    pause: bool = False
    debug_toggle: bool = False


def collect_input():
    running = True

    confirm = False
    pause = False
    debug_toggle = False


    # Eventos
    ##################################################################################################################################
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                confirm = True

        elif event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                confirm = True

            elif event.key == pygame.K_ESCAPE:
                pause = True

            elif event.key == pygame.K_F3:
                debug_toggle = True

    # Movimento do jogador
    ##################################################################################################################################
    movement = pygame.Vector2(0, 0)

    keys = pygame.key.get_pressed()

    if keys[pygame.K_w]:
        movement.y -= 1

    if keys[pygame.K_s]:
        movement.y += 1

    if keys[pygame.K_a]:
        movement.x -= 1

    if keys[pygame.K_d]:
        movement.x += 1

    if movement.length_squared() > 0.0:
        movement = movement.normalize()

    # Mira
    ##################################################################################################################################
    aim_position = pygame.mouse.get_pos()

    # Disparo
    ##################################################################################################################################
    fire = pygame.mouse.get_pressed()[0]

    # Estado de input atual do jogo
    ##################################################################################################################################
    input_state = InputState(
        movement=movement,
        aim_position=aim_position,
        fire=fire,
        confirm=confirm,
        pause=pause,
        debug_toggle=debug_toggle,
    )

    return running, input_state


# SISTEMA DE EMOÇÃO PROVISÓRIO
######################################################################################################################################
class ProvisionalEmotionSystem:

    def __init__(self, tendency="DOWN"):
        self.tendency = tendency

    def update(self):
        return {"tendency": self.tendency}


######################################################################################################################################
# FUNÇÃO PRINCIPAL
######################################################################################################################################

def main():

    # Inicialização
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("SpaceScream")
    clock = pygame.time.Clock()
    # Ícone
    icon = pygame.image.load("icon.png")
    pygame.display.set_icon(icon)

    # Instanciação dos 4 módulos
    ##################################################################################################################################
    # fer = FER()
    
    emotion_system = (ProvisionalEmotionSystem(tendency="DOWN"))

    ai_director = AIDirector()

    game = Game()

    # Loop principal
    ##################################################################################################################################
    running = True

    while running:
        # Delta Time
        dt = clock.tick(FPS) / 1000.0

        # Input
        running, input_state = (collect_input())

        if not running:
            break

        # Debug
        if input_state.debug_toggle:
            game.toggle_debug()

        # Menu / Estados
        previous_state = game.state

        menu_handled = (game.handle_menu_input(input_state))

        if not game.running:
            break

        # Nova run
        if(previous_state in(Game.INITIAL_SCREEN, Game.GAME_OVER) and game.state == Game.PLAYING):
            ai_director.reset()

        # Ação de menu consume o input
        if menu_handled:
            game.render(screen)

            pygame.display.flip()

            continue

        # Pause
        if input_state.pause:
            if game.state in (Game.PLAYING, Game.WAVE_REST):
                game.toggle_pause()

        ##############################################################################################################################
        # 1 - FER
        ##############################################################################################################################

        # fer = Fer.fer()

        ##############################################################################################################################
        # 2 - EMOTION SYSTEM
        ##############################################################################################################################

        emotion_trend = (emotion_system.update())

        # A observação precisa ser registrada antes do update do Game,
        # pois esse update pode concluir a Wave e mudar PLAYING -> WAVE_REST.
        game.record_playing_emotion(emotion_trend)

        ##############################################################################################################################
        # 3 - AI DIRECTOR
        ##############################################################################################################################

        game_context = (game.get_director_context())

        adaptation = (
            ai_director.update(
                context=game_context,
                emotion=emotion_trend,
                dt=dt,
            )
        )

        game.record_director_debug(
            director_state=ai_director.get_state(),
            adaptation=adaptation,
        )

        ##############################################################################################################################
        # 4 - JOGO
        ##############################################################################################################################

        if adaptation is not None:
            game.apply_adaptation(adaptation)

        game.update(dt=dt, input_state=input_state)

        game.render(screen)

        pygame.display.flip()

    # Finalização
    pygame.quit()


if __name__ == "__main__":
    main()
