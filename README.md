# Copa EA FC 26 - FIFA World Cup 2026 Edition

Sistema de gerenciamento de campeonato EA FC 26 para 8 participantes, com site hospedado no GitHub Pages.

**Site ao vivo:** https://joaomolina.github.io/fifa-championship/

## Participantes

| Selecao | Tecnico | 
|---|---|
| Mexico | Joao Victor Molina |
| Argentina | Joao Victor Pires |
| Alemanha | Vinicius Lista |
| Franca | Igor Vereda |
| USA | Guilherme Rissi |
| Espanha | Kaiki Aguiar |
| Portugal | Felipe Aguiar |
| Inglaterra | Reinaldo Urbano |

## Quick Start

```bash
make setup            # Cria venv e instala dependencias
make load-csv CSV=data/ea_fc26_players.csv   # Carrega jogadores do dataset FC 26
make draft            # Executa o sorteio balanceado
```

O site estatico e gerado em `docs/` e servido via GitHub Pages.

## Funcionalidades do Site

- **Painel** — visao geral do torneio (classificacao, artilharia, proximos jogos)
- **Classificacao** — tabela do grupo com pontos, saldo de gols, posicao
- **Jogos** — lista de todas as partidas por rodada com resultados
- **Chaveamento** — bracket visual da fase eliminatoria (upper/lower)
- **Selecoes** — cards dos 8 times com foto do tecnico, elenco e stats por posicao
- **Formacao** — quadro tatico interativo com campo, drag & drop de jogadores e 7 formacoes
- **Transferencias** — janelas de transferencia e historico de trocas
- **Estatisticas** — artilharia, assistencias e graficos

## Arquitetura

- **Frontend**: site estatico (HTML/CSS/JS) hospedado no GitHub Pages (`docs/`)
- **Estilizacao**: Tailwind CSS (CDN) + CSS customizado com tema Copa do Mundo 2026
- **Dados**: arquivos JSON em `docs/data/` gerados pelos scripts Python
- **Backend (scripts)**: Python com Pydantic para modelos e logica de torneio
- **Dataset**: EA Sports FC 26 Player Ratings (Kaggle, marco/2026 — 16k+ jogadores)

## Dataset de Jogadores

Fonte: [EA Sports FC 26 Player Ratings](https://www.kaggle.com/datasets/justdhia/ea-sports-fc-26-player-ratings/data)

1. Baixe o ZIP do Kaggle
2. Extraia `ea_fc26_players.csv` na pasta `data/`
3. Execute: `make load-csv CSV=data/ea_fc26_players.csv`

## Formato do Torneio

### Fase de Grupos
- 8 selecoes, grupo unico, todos contra todos (28 jogos, 7 rodadas)
- Vitoria = 3pts | Empate = 1pt | Derrota = 0pts
- Top 4 classificados direto, 5o e 6o disputam repescagem

### Fase Eliminatoria (Double Elimination)
- **Quartas**: 1o vs 4o, 2o vs 3o (upper) + 5o vs 6o (lower entry)
- **Semifinal Upper**: Vencedor(1v4) vs Vencedor(2v3)
- **Lower R1**: Vencedor(5v6) vs Perdedor(1v4)
- **Lower R2**: Vencedor(Lower R1) vs Perdedor(2v3)
- **Final Lower**: Perdedor(Upper Semi) vs Vencedor(Lower R2)
- **Grande Final**: Vencedor(Upper Semi) vs Vencedor(Final Lower)
- Criterio de desempate: posicao na fase de grupos

### Composicao do Elenco (26 jogadores por selecao)
- GK: 3 | DEF: 8 | MID: 8 | FWD: 7
- Garantia de diversidade: cada time tem pelo menos 1 jogador de cada sub-posicao (CB, LB, RB, CDM, CM, CAM, LM, RM, ST, LW, RW)

### Janelas de Transferencia
- Antes do torneio comecar
- A cada 4 rodadas na fase de grupos
- Ultima janela antes da fase eliminatoria
- Maximo 3 trocas por janela, mesma posicao

## Sorteio Balanceado

O draft utiliza um algoritmo em duas fases:

1. **Fase obrigatoria**: snake draft por sub-posicao, garantindo diversidade tatica
2. **Fase de preenchimento**: vagas restantes com os melhores disponiveis do grupo de posicao
3. **Otimizacao**: trocas entre times (mesma sub-posicao) para minimizar variancia de overall

Resultado: spread de ~0.04 no overall medio entre os 8 times.

## Estrutura do Projeto

```
docs/                   # Site estatico (GitHub Pages)
  index.html            # Painel principal
  standings.html        # Classificacao
  matches.html          # Lista de jogos
  match.html            # Detalhe da partida
  bracket.html          # Chaveamento eliminatorio
  teams.html            # Lista de selecoes
  team.html             # Detalhe da selecao
  formacao.html         # Montagem tatica (drag & drop)
  transfers.html        # Janelas de transferencia
  stats.html            # Estatisticas e graficos
  js/app.js             # Logica compartilhada (dados, nav, utilitarios)
  css/style.css         # Tema Copa do Mundo 2026
  data/                 # JSONs do torneio (players, teams, matches, etc.)
  photos/               # Fotos dos participantes
src/
  models.py             # Modelos Pydantic (Player, Team, Match, etc.)
  database.py           # Persistencia JSON (leitura/escrita em docs/data/)
  draft.py              # Algoritmo de sorteio balanceado
  tournament.py         # Logica de torneio (grupos, bracket, artilharia)
  app.py                # FastAPI (uso local/dev)
scripts/
  load_players.py       # Carrega jogadores do CSV do FC 26
  run_draft.py          # Executa o sorteio e gera calendario
data/                   # CSVs brutos do Kaggle
photos/                 # Fotos originais dos participantes
```
