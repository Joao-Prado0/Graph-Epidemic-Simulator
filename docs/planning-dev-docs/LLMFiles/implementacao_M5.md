# Implementação do M5: Interface, mapa e saída

Documento para aprovação antes de qualquer código. Base: zip atual do repositório, `responsabilidades_modulos.md` (v0.3), `arquitetura_simulador_epidemias.md` (v0.6), `documento_apoio` e wireframes em `docs/wireframes/`.

Escopo: exatamente a lista de funcionalidades do M5 enviada pelo responsável. Itens citados nas docs e não listados ficam de fora, salvo onde indicado na seção 4 como dúvida.

---

## 1. Estado atual do repositório

| Item | Situação |
|---|---|
| `src/epidemia/ui/` | Só `__init__.py`, vazio. Nenhuma tela existe. |
| `src/epidemia/main.py` | Prova de conceito (estados aleatórios, sem `SimulationSession`). Precisa ser substituído. |
| `src/epidemia/config.py` | Vazio. |
| `app/playback.py`, `app/panel_metrics.py`, `app/config_io.py`, `app/export.py` | Não existem. |
| `src/epidemia/datasets/` | Vazio (M4). |
| `data/processed/` | Só `.gitkeep`. Não há `countries.csv`, `edges.csv` nem `countries.geojson` (M4). |
| `scripts/build_exe.ps1` | Existe, sem `--add-data` para `data/processed` (comentado). |
| `tests/architecture/test_camadas.py` | Existe e cobre as regras de dependência. |

Já disponível de M1, M2 e M3, e utilizável pelo M5:

- `SimulationSession` (`app/simulation_session.py`): configurar, calibrar β, iniciar, `run_day()`, `timeline()`, `reset()`.
- `SimulationConfig` imutável (`core/epidemic/parameters.py`), com `exit_rate_gamma`, `mortality`, `incubation_days`, `intervention_level`, `r0`, `seed`, `patient_zero`.
- Protocolo `Timeline` e `StateBuffer` (`core/timeline/`), com `vertex_states(day)` e `country_counts(day)`.
- `estimate_effective_r0_from_series` e `summarize_epidemic_series` (`core/analysis/epidemic_metrics.py`) para o painel.
- `label_propagation_communities` e `contract_graph_by_country` (M2) para a seção de comunidades.
- Exceções próprias em `core/errors.py` (`EpidemiaError` e subclasses) para a caixa de diálogo.

Suíte atual: 201 testes passam. Um falha só porque PySide6 não estava instalado no ambiente de análise (`tests/test_smoke.py`). Não é defeito do código.

---

## 2. Escopo do M5 (lista aprovada)

| # | Funcionalidade | Arquivo(s) | Requisitos |
|---|---|---|---|
| 2.1 | Janela principal em PySide6 e tela de configuração: parâmetros da doença, seleção de pandemia, cenário, R0 informado, níveis de isolamento e vacinação, paciente zero | `ui/main_window.py`, `ui/config_panel.py`, `main.py` | RF01, RF03, RF09, RF23 |
| 2.2 | Player com play, pausa, voltar e avançar, lendo o buffer gravado. Reiniciar descarta o buffer | `app/playback.py`, `ui/player_bar.py` | RF04, RF11, E2 |
| 2.3 | Mapa de polígonos pela cor de status dominante do dia. Vértices aparecem a partir de 40 px de largura do país e somem abaixo de 36 px. Regra do fluxo real em validação | `ui/map_view.py`, `ui/styles.py` | RF12, RF22 |
| 2.4 | Painel de resultados: métricas de comparação, centralidades, comunidades, R0 efetivo e indicação de pico | `app/panel_metrics.py`, `ui/main_window.py` | RF14, RF18, RF19, RF21, RF24 |
| 2.5 | Gráficos S, E, I, R, D com exportação de imagem | `ui/charts_view.py` | RF24, RF08 |
| 2.6 | Salvar e carregar configuração em JSON (biblioteca padrão) | `app/config_io.py` | RF07 |
| 2.7 | Exportação de CSV a partir do `Timeline` | `app/export.py` | RF08 |
| 2.8 | Tratamento de erros com exceções próprias, exibidas em caixa de diálogo | `ui/main_window.py` (diálogo), `core/errors.py` (já existe) | RNF08 |
| 2.9 | Empacotamento com PyInstaller para Windows | `scripts/build_exe.ps1` | RNF04 |

Regra de dependência, respeitada em todos os arquivos: `ui` pode importar `app` e `core`; `app` não importa `ui`, `PySide6` nem `pyqtgraph`; `core` não importa nada de Qt. O teste `tests/architecture/test_camadas.py` garante isso.

### 2.1 Fora do escopo (não será feito, salvo aprovação)

- Análise de rede como aba própria (wireframe Tela 10): caminho mínimo, pontes e articulações, desempenho.
- Tema claro (wireframe Tela 1, variante clara).
- Inspeção de vértice por clique (wireframe Tela 14, RF26).
- Calibração com tela própria (wireframe Tela 3).
- Créditos e fontes (wireframe Tela 16).
- Erros e avisos em painel separado (wireframe Tela 15). Só a caixa de diálogo de 2.8.
- Comparação simulado × real como tela (wireframe Tela 11). A métrica RF14 entra no painel de 2.4.

---

## 3. Viabilidade dos wireframes

Resposta curta: dá para implementar a tela de configuração e a de simulação em PySide6 com QSS, parecidas com o wireframe. O mapa precisa ser feito com QPainter, não com pyqtgraph. Se algum detalhe fino ficar fora, a versão simples é aceitável, como você indicou.

| Elemento do wireframe | Viável | Como |
|---|---|---|
| Layout em 3 colunas, cards, cabeçalho, rodapé | Sim | `QGridLayout`, `QFrame` com QSS |
| Sliders com valor ao lado (R0, γ, incubação) | Sim | `QSlider` + `QDoubleSpinBox` sincronizados |
| Botões segmentados (Baixo, Médio, Alto; Global, Regional) | Sim | `QButtonGroup` com botões checáveis |
| Tabela de níveis (somente leitura) | Sim | Labels na coluna central |
| Mapa com polígonos, vértices e zoom | Sim, com QPainter | `QPainterPath` por país, pré-calculado; vértices em lote com `drawPoints`. A prova de conceito já validou 8.000 pontos |
| Tooltip de país ao passar o mouse | Sim | `mouseMoveEvent` + hit test por polígono |
| Zoom (+/−), "Ajustar mapa", arrastar | Sim | Transformação do `QPainter` |
| Hachura em países sem rota | Sim | `QBrush` com padrão |
| Player com ×1 ×2 ×5 ×10 e barra de dias | Sim | Botões e `QSlider`. Ver dúvida 4 |
| Painel de resumo (infectados, pico, duração, mortes, R0 efetivo) | Sim | Labels e `summarize_epidemic_series` |
| Gráfico com linhas S, E, I, R, D e marcador de dia | Sim | pyqtgraph (`charts_view.py`) |
| Chips de série com percentual e contagem | Sim | Widgets simples |
| Tela de seleção de pandemia com cards e mini-mapas | Parcial | Cards em QSS são simples. Mini-mapas exigem geometria real (depende do M4). Ver dúvida 6 |
| Tema escuro | Sim | QSS |
| Fontes e espaçamento finos do mockup | Parcial | Aproximação com fonte padrão do sistema |
| Indicador "Calculando..." e FPS | Sim | Label atualizado por timer |

Valores de exemplo do wireframe (10.000 indivíduos, β = 0,32, Brasil com vértice #0421) são ilustrativos. A própria tela diz "Dados ilustrativos". O número de vértices real é N_total provisório de 8.000, definido pelo M1 e pelo benchmark do M2.

---

## 4. Dúvidas que bloqueiam a implementação

Respostas curtas bastam. Em cada uma deixei a recomendação. Se você aprovar as recomendações, eu sigo com elas.

1. **Mapa: pyqtgraph ou QPainter?** Sua lista diz pyqtgraph. A arquitetura (4.1 e 8), a modelagem (RF22, RNF02) e a prova de conceito usam QPainter em lote. pyqtgraph é para gráficos. **Recomendo QPainter para o mapa e pyqtgraph para os gráficos.**

2. **Dados do M4.** `data/processed/` está vazio. Sem `countries.geojson` não há polígonos reais, e sem `countries.csv` e `edges.csv` o `World` não é montado. **Recomendo** começar com um fixture sintético pequeno, por exemplo 5 países retangulares com rotas entre eles, em `tests/`. O código real entra quando o M4 entregar. O caminho crítico continua sendo o M4.

3. **Thread de simulação.** Não está na sua lista. Sem ela, a simulação roda na thread da interface e a janela trava (RNF03, essencial). Como o player só lê dias já gravados, alguém precisa gravar esses dias. **Recomendo incluir** `ui/simulation_thread.py` (`QThread`, sinal `day_ready`), que só chama `session.run_day()`. Não é código de domínio.

4. **Velocidade do player (×1, ×2, ×5, ×10).** RF04 é essencial e pede ajuste de velocidade. Sua lista cita só play, pausa, voltar e avançar. **Recomendo incluir** os quatro botões. É um valor de timer, sem impacto no buffer.

5. **Zoom e pan no mapa.** O critério de 40 px e 36 px depende de largura em pixels na tela, ou seja, depende do zoom. Sem zoom, o limiar só mostra vértices no zoom inicial. RF26 é desejável. **Recomendo incluir** zoom (+/−, roda) e arrastar, sem inspeção de vértice.

6. **Seleção de pandemia e navegação.** Sua lista coloca a seleção de pandemia na tela de configuração. O wireframe (Telas 1 e 8) põe em abas: Início, Simulação, Pandemias reais. A tela inicial é RF25, essencial. **Recomendo** duas abas (Simulação e Pandemias reais) com a configuração na aba Simulação, e a seleção de pandemia como uma lista na mesma tela de configuração do fluxo real. Sem Análise de rede, sem tela inicial separada.

7. **Regra de cor do fluxo real.** Sua lista diz "em validação". A decisão já registrada na arquitetura (A12, de 03/11) é: simulação por status dominante; fluxo real por intensidade de casos acumulados por 100 mil habitantes, a partir de 10 por 100 mil. **Recomendo implementar a decisão registrada**, deixando o limiar em `styles.py` como parâmetro, e marcar a validação como pendente no relatório.

8. **Painel de resultados.** Sua lista cita centralidades e comunidades. A Tela 10 mostra cinco abas. **Recomendo** incluir só centralidades (grau e intermediação aproximada, M2) e comunidades (propagação de rótulos, M2) como seções do painel, sem pontes, caminho mínimo nem desempenho.

Se você não quiser que eu espere, respondo com as recomendações acima. Pontos 1, 2 e 3 são os que mudam o que eu escrevo no prompt.

---

## 5. Premissas (valem se não houver resposta contrária)

- Tema escuro único, via QSS.
- Idioma da interface em português, nomes de código em inglês (decisão C2).
- Configuração salva em JSON com as mesmas chaves de `SimulationConfig`.
- Exportação de CSV com uma linha por dia e colunas por país e compartimento, a partir de `country_counts(day)`.
- Exportação de imagem dos gráficos em PNG, pelo `pyqtgraph.exporters`.
- Exceções de domínio são exibidas em `QMessageBox`, sem lógica de negócio na interface.
- O calibrador de β roda antes do início, chamado por `SimulationSession.start()`. O botão "Calibrar β" da tela só chama `calibrate_beta()` e mostra o valor.
- Valores do limiar de vértices (40 px e 36 px) em `styles.py`, como parâmetros.
- Teste automático de interface com `QT_QPA_PLATFORM=offscreen`, sem `pytest-qt`, para não aumentar dependências.

---

## 6. Plano de implementação

Ordem pensada para ficar testável a cada etapa, e para não depender do M4 antes da hora.

**Etapa A: domínio da interface (sem Qt)**

1. `app/config_io.py`: `save_config(path, config)` e `load_config(path)` com `json` da biblioteca padrão. Valida pela `SimulationConfig` e levanta `ParameterOutOfRangeError` em JSON inválido.
2. `app/export.py`: `export_timeline_csv(timeline, path)` por dia, com colunas S, E, I, R natural, R vacinado, D, isolados e total.
3. `app/playback.py`: `Playback` com dia atual, velocidade, estado de pausa e limite `days_available`. Não toca no motor e não grava nada. Reiniciar chama `session.reset()`.
4. `app/panel_metrics.py`: monta o resumo do painel (pico, dia do pico, duração, mortes e percentual, R0 efetivo) a partir de `country_counts`, usando `estimate_effective_r0_from_series`. Não duplica a fórmula.

Testes em `tests/app/`: round-trip de configuração (salvar e carregar produz `SimulationConfig` igual), JSON inválido, CSV com total de colunas esperado, playback que não avança além de `days_available`, painel com série conhecida.

**Etapa B: janela e configuração (com fixture)**

5. `ui/styles.py`: cores dos estados, escala do fluxo real, limiares 40 px e 36 px, QSS do tema escuro.
6. `ui/config_panel.py`: campos e sliders (R0, γ, mortalidade, incubação, nível de intervenção, cenário, semente, paciente zero). Ao salvar ou carregar, usa `config_io`.
7. `ui/main_window.py`: janela com abas, cria `SimulationSession` a partir do mundo (fixture por enquanto), diálogo de erro para `EpidemiaError`.
8. `main.py` substituído. Continua sendo o ponto de entrada `python -m epidemia.main`.

**Etapa C: mapa, player e gráficos**

9. `ui/map_view.py`: polígonos pré-calculados em `QPainterPath`, cor por status dominante (simulação) ou por intensidade (real), vértices em lote com regra de 40/36 px, zoom, arrastar, tooltip.
10. `ui/player_bar.py`: play, pausa, voltar, avançar, velocidade, barra de dias.
11. `ui/simulation_thread.py`: `QThread` que chama `run_day()` e emite `day_ready`, com interrupção ao reiniciar.
12. `ui/charts_view.py`: curvas S, E, I, R, D com pyqtgraph, marcador de dia e exportação PNG.
13. Ligação do painel de resultados (2.4) e das seções de centralidade e comunidades.

**Etapa D: executável e fechamento**

14. `scripts/build_exe.ps1`: incluir `--add-data` para `data/processed` quando o M4 entregar os arquivos.
15. Ruff (`check` e `format --check`) e pytest passando no CI (Windows).
16. Validação manual do player e do mapa no protótipo, na máquina mais fraca do grupo. Medir FPS e confirmar 40/36 px.
17. Build do executável e teste em máquina sem o ambiente de desenvolvimento.

---

## 7. Critérios de aceitação (os da sua lista, com teste)

| Critério | Como será verificado |
|---|---|
| O player reproduz o buffer sem recalcular a simulação | Teste: `Playback` lê `timeline()`; teste de arquitetura mostra que `app/playback.py` não importa `core/epidemic` |
| Pausa e retorno não alteram o histórico | Teste: `days_available` e `vertex_states(d)` iguais antes e depois de pausar e voltar |
| Configuração salva e carregada produz o mesmo buffer | Teste: salvar, carregar, rodar as mesmas N etapas e comparar hash do buffer (mesma semente) |
| Executável roda em Windows sem o ambiente de desenvolvimento | Teste manual na máquina Windows sem Python instalado |

Testes adicionais: CSV com número de linhas igual a dias gravados; painel consistente com `summarize_epidemic_series`; `ParameterOutOfRangeError` mostrado sem fechar a janela.

---

## 8. Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| M4 não entrega `countries.geojson` a tempo | Mapa sem países reais, executável sem dados | Fixture sintético e troca no fim, com `datasets/loaders.py` |
| Mapa com QPainter não atinge 20 FPS com 8.000 vértices | Animação travando | Vértices em lote, polígonos pré-calculados, ocultar vértices abaixo de 36 px |
| Limiares de 40 px e 36 px inadequados na máquina fraca | Vértices demais ou de menos | Parâmetros em `styles.py`; teste visual no protótipo (pendência do grupo) |
| PyInstaller sem os dados | Executável sem mapa | `--add-data` em `build_exe.ps1` |
| Não é possível testar o `.exe` aqui (ambiente Linux) | Falha só aparece no Windows | Validação manual na máquina Windows do grupo, antes da entrega |
| Escopo de visual crescer além do wireframe | Atraso | Versão simples aceita, conforme sua orientação |

---

## 9. Entregáveis do M5

- Código em `src/epidemia/ui/`, `src/epidemia/app/` (quatro arquivos novos) e `src/epidemia/main.py`.
- Testes em `tests/app/` e `tests/architecture/` (regras de dependência do M5).
- Ajuste em `scripts/build_exe.ps1`.
- Documentação de docstrings e do README da pasta `ui/`, sob responsabilidade do M5.
- Commits individuais no Git (RNF07).
