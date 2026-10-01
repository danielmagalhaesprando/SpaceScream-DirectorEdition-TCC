<h1 align="center"> SpaceScream </h1>

Protótipo de jogo *twin-stick shooter* integrado a um * **AI Director** *  para adaptação dinâmica em tempo real.

Projeto acadêmico desenvolvido como Trabalho de Conclusão de Curso em Engenharia de Computação na UTFPR.

<br>

## Sobre o projeto

O SpaceScream é um jogo de ação do gênero *twin-stick shooter*, no qual o jogador se movimenta por uma arena bidimensional aberta enquanto enfrenta grupos de inimigos que o perseguem.

A jogabilidade combina movimentação, posicionamento e combate em tempo real. Os inimigos são organizados em grupos e formações distintas, enquanto
a partida é estruturada em *waves*.

Sobre essa base, o projeto incorpora um **AI Director**, responsável por observar o estado da partida e do jogador e produzir intervenções adaptativas durante a execução.

## Principais características

- *Twin-stick shooter* com movimentação e direção de ataque independentes
- Arena bidimensional aberta
- Sistema de armas e ataques
- Combate contra inimigos que perseguem o jogador
- Organização dos inimigos em grupos e formações
- Sistema de *waves* e períodos de *wave rest*
- Sistema de *health drops* para recuperação de vida
- AI Director para adaptação dinâmica em tempo real
- Representação estruturada do estado da partida e do jogador
- Sistema de intervenções aplicadas à *wave* atual e à próxima *wave*
- Instrumentação e depuração do AI Director
- Decisões lógicas do jogo e do AI Director sem uso de aleatoriedade

## Demonstração

![Gameplay](screenshots/gameplay.png)

## Estado atual

### Implementado:

- Jogo base funcional
- Controle e movimentação do jogador
- Mira e disparo por mouse
- Inimigos e sistema de perseguição
- Grupos e formações de *spawn*
- Organização das *waves*
- Sistema de *health drops*
- Estados de menu, partida, pausa, *wave rest* e *game over*
- AI Director
- Representação estruturada do contexto da partida para o AI Director
- Sistema de adaptações e aplicação das intervenções ao jogo
- Instrumentação e depuração do AI Director

### Em desenvolvimento:

- EmotionSystem
- Reconhecimento de expressões faciais por meio de FER
- Integração entre FER, EmotionSystem, AI Director e Game
- Sistema de progressão baseado em seleção de habilidades durante o *wave rest*

## Controles

| Entrada | Ação |
|---|---|
| **W** | Movimentar para cima |
| **A** | Movimentar para a esquerda |
| **S** | Movimentar para baixo |
| **D** | Movimentar para a direita |
| **Mouse** | Direcionar o ataque |
| **Botão esquerdo do mouse** | Atacar |
| **Enter / Espaço** | Confirmar ações de menu |
| **Esc** | Pausar a partida |
| **F3** | Alternar o modo de depuração |

## Tecnologias

- Python
- Pygame Community Edition

## Dependências

A execução do protótipo atual requer:

- Python 3.14.7 (64 bits)
- Pygame CE 2.5.8

As dependências Python estão especificadas em [`requirements.txt`](requirements.txt).

> **Observação:** os componentes FER e EmotionSystem ainda estão em desenvolvimento. As dependências necessárias para o reconhecimento de expressões faciais serão incorporadas ao projeto quando essa integração for implementada.

## Execução

Instale as dependências especificadas em `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

Execute a aplicação a partir da raiz do projeto:

```bash
python main.py
```

## Arquitetura

O projeto foi desenvolvido iterativamente, e organizado de forma modular, separando as responsabilidades relacionadas à execução do jogo, à adaptação dinâmica e à detecção e inferência emocional.

O arquivo `main.py` constitui o ponto de entrada da aplicação e coordena a execução e a comunicação entre os principais componentes. O diretório `GAME` concentra a implementação da jogabilidade, enquanto `AI_DIRECTOR` contém o mecanismo de tomada de decisão adaptativa.

> **Observação:** os diretórios `EMOTION_SYSTEM` e `FER` estão reservados aos componentes responsáveis pelo processamento emocional e pelo reconhecimento de expressões faciais.

```text
SpaceScream/
├── AI_DIRECTOR/
│   └── ai_director.py
├── EMOTION_SYSTEM/
├── FER/
├── GAME/
│   ├── attack.py
│   ├── drop.py
│   ├── enemy.py
│   ├── game.py
│   ├── particle.py
│   ├── player.py
│   ├── spawn.py
│   ├── wave.py
│   └── weapon.py
├── icon.png
├── main.py
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Relação com o projeto original

Este projeto foi inspirado pelo SpaceScream original desenvolvido por **Daniel Cavalcanti Jeronymo**, disponível em:

https://github.com/prof-danielc/SpaceScream

A implementação presente neste repositório possui código, organização estrutural e arquitetura próprios. O repositório original é referenciado como fonte de inspiração para a concepção inicial do projeto.

## Licença

Este projeto está licenciado sob a **MIT License**. Consulte o arquivo [`LICENSE`](LICENSE) para obter os termos completos da licença.
