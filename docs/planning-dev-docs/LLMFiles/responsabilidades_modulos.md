# Responsabilidades por módulo: Simulador de Epidemias em Redes

Versão 0.3, 14/11/2026. Proposta para discussão do grupo. Atualiza a v0.2 com as decisões de 14/11 (escopo do M1 da v0.1, nomes em inglês, γ como taxa total de saída de I e dia 0 por vértices infectados).

## 1. Premissas

- A equipe tem **5 integrantes**, identificados como A a E. A atribuição de cada letra a uma pessoa é decisão do grupo e continua pendente.
- Um **módulo** é um conjunto de funcionalidades com um responsável. Pode ocupar mais de um pacote e não é necessariamente um componente independente.
- Base: modelagem (revisão 2), dados (v0.8), documento de apoio (v0.8), arquitetura (v0.6) e setup (v1.3).
- **Escopo do M1 aprovado em 14/11:** o M1 mantém a construção do grafo unificado, como na v0.1 (`world/`), além do núcleo do grafo, das sementes e das exceções.
- **Nomes em inglês** nos contratos e no código (decisão C2). Documentação em português.
- Os nomes de pacotes e arquivos seguem a seção 8 da arquitetura v0.6.

## 2. Visão geral

| Módulo | Responsável | Escopo resumido | Pacotes principais | Carga estimada |
|---|---|---|---|---|
| M1 Grafo unificado e núcleo do grafo | A | Estruturas e algoritmos de grafo, construção do grafo unificado (alocação, posições, conexões, arestas, pesos, cenários), sementes e exceções | `core/graph/`, `world/`, `core/seeds.py`, `core/errors.py` | Grande |
| M2 Análise de redes e benchmark | C | Tarjan, comunidades, grau, agrupamento, intermediação aproximada, benchmark de desempenho | `core/analysis/`, `benchmarks/` | Média |
| M3 Motor de simulação | B | Parâmetros, calibração de β, modelo SEIRD, isolamento, vacinação, buffer, sessão de simulação | `core/epidemic/`, `core/timeline/`, `app/simulation_session.py` | Grande |
| M4 Dados e comparação | D | Script de preparação, geometria processada, leitura dos dados, fluxo real e comparação com dados reais | `data/`, `datasets/`, `app/real_session.py`, `app/comparison.py` | Média |
| M5 Interface, mapa e resultados | E | Telas, player, mapa, painel, gráficos, salvar e carregar configuração, exportação, testes de arquitetura, executável | `ui/`, `app/playback.py`, `app/panel_metrics.py`, `app/config_io.py`, `app/export.py`, `scripts/build_exe.ps1` | Grande |

A carga é relativa. Deve ser validada pelo grupo depois da primeira estimativa de cada integrante.

## 3. Contratos a fechar na primeira reunião

Antes de codar, os responsáveis pelos contratos devem publicar a assinatura inicial. Sem isso, os módulos não se encaixam.

| Contrato | Dono | Conteúdo |
|---|---|---|
| `Graph` | M1 | Vértices, lista de adjacência, máscara de arestas ativas, peso `w` por aresta. Funções `transmission_probability(w, beta)` e `travel_cost(p)`, que recebem β como argumento |
| `derive_seed(global_seed, name)` | M1 | Semente de cada subsistema, por `hashlib` (F2) |
| `Timeline` (protocolo) e `StateBuffer` | M3 | Um `bytearray` por dia. Byte por vértice: bits 0 a 2 para o estado (S, E, I, R, D), bit 3 isolado, bit 4 vacinado (arquitetura, A10) |
| `SimulationConfig` | M3 | Imutável. `seed`, `scenario`, `r0`, `exit_rate_gamma` (γ, taxa total de saída de I), `mortality`, `incubation_days`, `intervention_level`, paciente zero. β não entra: é calibrado depois |
| `CountryInfo` e arquivos processados | M4 | `countries.csv`, `edges.csv`, `countries.geojson` e as séries em `data/processed/` |
| `RealTimeline` | M4 | Mesma forma de leitura do `Timeline`, alimentada pelas séries reais |
| `ComparisonResult` | M4 | Métricas de comparação com dados reais (RF14) |

Ponto de atenção: `CountryInfo` e os arquivos processados pelo M4 são o caminho crítico. M1, M3 e M5 podem começar com dados de teste, mas o grafo real só existe depois que M4 gerar os arquivos.

## 4. Detalhamento por módulo

### M1: Grafo unificado e núcleo do grafo (responsável A)

**Funcionalidades**

- `Graph` (`core/graph/graph.py`): lista de adjacência com máscara de arestas ativas. Desligar uma aresta altera a máscara, não a estrutura (C3). A versão com arrays e CSR é opcional, porque o professor liberou NumPy no núcleo do grafo (D17).
- Travessia (`core/graph/traversal.py`): BFS, DFS e componentes conexos.
- Caminho mínimo (`core/graph/shortest_path.py`): Dijkstra recebendo o custo por aresta, calculado por `travel_cost(p)`.
- Alocação de vértices por país (`world/allocation.py`): total fixo `N_total` (provisório 8.000), `n_min = 12`, `α = 0,5`, alocação iterativa de piso e arredondamento por maior resto. Grau efetivo `d̄_ef = min(d̄, n_i − 1)`.
- Posição dos vértices sorteada dentro do polígono do país, com geometria só da biblioteca padrão (`world/geometry.py`). Trata o antimeridiano e agrega feições do mesmo país.
- Conexões internas por raio `r ≈ √(d̄ / (π · ρ))` com `d̄` entre 6 e 10, usando grade espacial (`world/spatial_grid.py` e `world/builder.py`). Rede geométrica aleatória (RF02).
- Arestas entre países `k_ij = min(k_max, ceil(routes_ij / escala))`, com vértices escolhidos ao acaso e semente própria. Cada aresta herda `w_ij`.
- Pesos `w = log(1 + routes) / log(1 + max routes)`. Probabilidade `p = 1 − exp(−β · w)` e custo `−ln(p)` com `p ≤ 0,999`, implementados como funções que recebem β (`transmission_probability`, `travel_cost`). O M3 chama essas funções depois da calibração.
- Cenários (`world/scenarios.py`): global e regional. No regional, países que atingem 10 casos acumulados nos primeiros 60 dias a partir do dia 0 do surto recebem o orçamento de vértices (B3, B4). O prazo é configurável. As séries vêm do M4.
- Sinalização de países sem rota no OpenFlights, sem arestas artificiais (D16).
- Sementes (`core/seeds.py`) e exceções próprias (`core/errors.py`, RNF08). Entregues na Etapa 1, porque o M3 e o M4 dependem delas.
- Cache do grafo por (semente, cenário), porque a construção pode levar segundos.

**Entradas:** lista de países, populações, polígonos e rotas (M4).
**Saídas:** `Graph` (contrato), `derive_seed`, funções de probabilidade e custo, cenários.
**Critérios de aceitação:** soma de vértices igual a `N_total`; grafo não direcionado; máscara desliga aresta sem alterar a estrutura; custo de caminho derivado de `p`, não de `routes`; BFS, componentes e Dijkstra conferidos com grafos pequenos calculados à mão (caminho, ciclo e grafo de três países); mesma semente gera a mesma derivação de subsistema.
**Bloqueios:** arquivos processados pelo M4 para testar com o grafo real. Testes com fixtures não dependem de ninguém.

### M2: Análise de redes e benchmark (responsável C)

**Funcionalidades**

- Tarjan (`core/analysis/bridges.py`): pontes e pontos de articulação no grafo completo de vértices (E3).
- Comunidades (`core/analysis/communities.py`): propagação de rótulos no grafo contraído por país (RF19, E3).
- Métricas (`core/analysis/metrics.py`): grau para o painel; agrupamento local por vértice e média global, com custo `O(Σ k_v²)` (RF18); intermediação aproximada por amostragem de fontes, com versão exata só no benchmark (E4).
- Benchmark (`benchmarks/bench_grafo.py`): único lugar em que NetworkX é permitido (F1). Mede tempo por passo e serve para definir `N_total`, `k_max`, `escala` e `d̄`.
- Fixtures de grafos pequenos, usadas por M1 e M3.
- Configuração do pytest e do padrão de testes do repositório, no início do projeto.

**Entradas:** `Graph` (M1), `Timeline` (M3).
**Saídas:** métricas para o painel (M5) e valores para o relatório.
**Critérios de aceitação:** Tarjan dá todas as arestas como pontes em um caminho e nenhuma em um ciclo; benchmark documentado com tempo por passo na máquina mais fraca do grupo.
**Bloqueios:** `Graph` (M1) e `Timeline` (M3). O benchmark completo depende do motor (M3).
**Nota:** β não entra no benchmark. Ele é calibrado a cada início por bisseção até o R0 informado (B2 da modelagem).

### M3: Motor de simulação (responsável B)

**Funcionalidades**

- `SimulationConfig` (`core/epidemic/parameters.py`): objeto imutável. Qualquer mudança exige nova configuração e novo início (RN01). Inclui γ (`exit_rate_gamma`), taxa total de saída de I, informada pelo usuário (RF01).
- Calibração de β (`core/epidemic/calibration.py`): bisseção sobre simulações curtas até o R0 medido ficar perto do informado. A fórmula de Newman serve só de verificação (B2, A14). Chama `transmission_probability` depois de testar cada β.
- Modelo SEIRD (`core/epidemic/model.py`): passo de um dia, transição `1 − exp(−σ)` para E → I e `1 − exp(−γ)` para a saída de I (C1, C2). Cada saída de I vai para D com probabilidade igual à mortalidade e para R com a complementar.
- Isolamento (`core/epidemic/interventions.py`): flag no bit 3 e máscara de arestas. Isolado não é contaminado, pode morrer e volta com as mesmas arestas (C3, RF05).
- Vacinação automática (`core/epidemic/interventions.py`): uma fração diária dos suscetíveis é vacinada; cada vacinado vai para R com flag no bit 4, com probabilidade igual à eficácia (0,8). Início e fração diária vêm do nível baixo, médio ou alto (C4, C5). A flag não entra na comparação com dados reais (acordo do Bloco 2, item 3).
- Níveis de intervenção: valores provisórios, tratados como premissas com análise de sensibilidade (C5, C7).
- Paciente zero manual ou aleatório (RF03). Centralidade fica só como análise (M2).
- Dia 0 do país (decidido em 14/11): primeiro dia em que o número de vértices infectados atinge M. O valor de M está pendente.
- Motor (`core/epidemic/engine.py`): `EpidemicEngine.step()` avança um dia e grava no buffer. Sem Qt e sem tempo de parede.
- Buffer (`core/timeline/buffer.py`): append-only, um `bytearray` por dia, anunciado dia a dia (E2 e arquitetura seção 7).
- `Timeline` (`core/timeline/protocol.py`) e `SimulationSession` (`app/simulation_session.py`).

**Entradas:** `Graph` e funções de probabilidade (M1), `SimulationConfig`, sementes derivadas (M1).
**Saídas:** `Timeline` (contrato), `DayRecord` por dia, séries para M2 e M5.
**Critérios de aceitação:**
- Caso de referência sem isolamento nem vacinação dentro de 5% do pico da solução numérica do SIR (F1).
- Invariante `S + E + I + R + D = N` verificado em todo passo, por país e no total (F1).
- Mesma semente e mesmos parâmetros geram o mesmo buffer, comparado por hash (F2).

**Bloqueios:** `Graph` (M1); benchmark de `N_total` e demais parâmetros de tamanho (M2); validação dos níveis C5 por sensibilidade; valor de M para o dia 0 (grupo).

### M4: Dados e comparação com dados reais (responsável D)

**Funcionalidades**

*Script de preparação (`data/`, fora do aplicativo)*
- `data/prepare_data.py`: leitura de JHU, OWID, OpenFlights e Natural Earth. Gera `countries.csv`, `edges.csv`, `countries.geojson` e as séries em `data/processed/`.
- Natural Earth convertido uma vez de shapefile para GeoJSON. shapely liberado pelo professor para o script (união de polígonos e centroide), e não entra no aplicativo.
- Normalização: aliases de países, descarte de não-países (D8), cummax (D10), série diária contínua (D11), recuperados só no SARS (D12), duplicata da China no SARS mantendo o acumulado crescente, regra da Libéria no Ebola (D22).
- Agregação: territórios ao país-mãe (GIB ao GBR; BES ao NLD; TKL ao NZL; GLP, GUF, MTQ, MYT e REU ao FRA), Ilhas Åland à Finlândia, Norte do Chipre ao Chipre (D24). Feições fora do modelo descartadas (ATA, ATF, HMD, NFK, SGS, IOT, SOL, KAS).
- Universo de 229 entidades. Kosovo como OWID_KOS.
- Rotas: não direcionadas, com número bruto em `edges.csv` (D13). Codeshare excluído (D14). Rotas entre território e metrópole viram domésticas e saem.
- Países sem rota ficam isolados, com aviso na interface e sem arestas artificiais (D16).
- Geometria processada: `countries.geojson` com chave ISO_A3_EH e fallback em ADM0_A3 (D20).

*Pacote `datasets/` (`src/epidemia/datasets/`, só biblioteca padrão)*
- `loaders.py`: lê `countries.csv`, `edges.csv` e `countries.geojson`.
- `series.py`: lê as séries de covid19, ebola, h1n1 e sars.

*Fluxo real e comparação*
- `RealTimeline` e `app/real_session.py`: entrega a mesma leitura de `Timeline` a partir das séries reais.
- Comparação com dados reais (RF14), em `app/comparison.py`: dia 0 pelo mesmo M de vértices, convertido em casos pela população do país. Acumulados `I + R + D`, mortes em `D`, recuperados em `R` natural, só no SARS (D1). Métricas: erro quadrático médio para casos e mortes, diferença de pico de novos casos por dia e diferença de tamanho final para casos (B7, D2).

**Entradas:** arquivos brutos (Kaggle, JHU, OWID, OpenFlights, Natural Earth) e saídas do M1 para a comparação.
**Saídas:** `countries.csv`, `edges.csv`, `countries.geojson`, séries processadas, `RealTimeline`, `ComparisonResult`.
**Critérios de aceitação:**
- Totais de população e de casos por país conferidos com os arquivos brutos.
- Nenhuma aresta artificial.
- Contagem de países com e sem rota registrada no script, sobre as 229 entidades.

**Bloqueios:** fonte do Ebola (substituir o Kaggle pela HDX, conforme análise de licenças); recontagem de rotas e de países sem rota (ver seção 8); valor de M (grupo).

### M5: Interface, mapa e resultados (responsável E)

**Funcionalidades**

- Tela inicial para escolher entre os dois fluxos (RF25) e tela de configuração com parâmetros da doença, R0 informado, γ, níveis de intervenção, paciente zero e cenário (RF01, RF09, RF23). A seleção de pandemia é feita entre as embutidas (RF09).
- Player com play, pausa, velocidade, voltar e avançar sobre o `Timeline` (`app/playback.py`, RF04, RF11). Lê o buffer já gravado e não toca no motor. Reiniciar descarta o buffer.
- Thread de simulação (`ui/simulation_thread.py`, `QThread`): executa `run_day()` em laço, respeita pausa e parada, e emite `day_ready` a cada dia (RNF03, E2).
- Mapa (`ui/map_view.py`, QPainter em lote; RF22, RF26):
  - Simulação: polígono pintado pelo status dominante do dia.
  - Fluxo real: polígono pintado por intensidade de casos acumulados por 100 mil habitantes, em escala sequencial a partir de 10 por 100 mil (A12).
  - Vértices aparecem a partir de 40 px de largura do país na tela e somem abaixo de 36 px (valores iniciais, a validar no protótipo).
- Painel de resultados (`app/panel_metrics.py`): pico, duração, mortes, percentual e R0 efetivo pelo crescimento inicial na forma SEIR (B6, C8). Indica o pico e exibe as métricas do RF14 (RF21, RF24).
- Gráficos (`ui/charts_view.py`, pyqtgraph) das curvas S, E, I, R e D, com exportação de imagem (RF24, RF08).
- Salvar e carregar configuração em JSON pela biblioteca padrão (`app/config_io.py`, RF07).
- Exportação de CSV a partir do `Timeline` (`app/export.py`, RF08).
- Exibição das exceções próprias em caixa de diálogo (RNF08).
- Testes de arquitetura (`tests/architecture/test_camadas.py`), que verificam as regras de dependência.
- Empacotamento com PyInstaller para Windows (`scripts/build_exe.ps1`).

**Entradas:** `Timeline` (M3), `Graph` e `ComparisonResult` (M1 e M4), métricas (M2), `countries.geojson` (M4).
**Saídas:** aplicativo executável.
**Critérios de aceitação:**
- O player reproduz o buffer sem recalcular a simulação.
- Pausa e retorno não alteram o histórico.
- Configuração salva e carregada produz o mesmo buffer.
- Executável roda em máquina Windows sem o ambiente de desenvolvimento.

**Bloqueios:** contrato `Timeline` (M3); validação de 40 px e 36 px no protótipo.

## 5. Atribuições transversais

- **Testes:** cada responsável escreve os testes do próprio pacote, espelhados em `tests/<pacote>/`. O C configura o pytest. O E mantém `tests/architecture/`.
- **Revisão cruzada:** cada integrante revisa um módulo de outro antes do fechamento de cada etapa.
- **Documentação técnica:** docstrings e README de cada pasta, pelo responsável do pacote.
- **Setup e repositório:** setup v1.3 (Python 3.12 para todos, Windows, repositório público). O E mantém o setup atualizado no que toca o empacotamento.
- **Licença do código e `DATA_SOURCES.md`:** pendentes. Sugestão: D (M4), que já reuniu as fontes e as licenças.
- **Casos de uso, UML e relatório LaTeX:** fora desta divisão. Os casos de uso e os diagramas UML são de outro integrante, conforme a arquitetura. Definir quem assume o relatório LaTeX.

## 6. Ordem de execução sugerida

1. **Etapa 1, contratos e base:** publicar as assinaturas dos contratos (seção 3). A entrega `Graph`, `derive_seed`, `errors.py` e a estrutura de `world/` é do M1. M4 gera os arquivos processados, que é o caminho crítico. M3 publica `Timeline` e `StateBuffer`. M2 configura o pytest e as fixtures de grafos. M5 monta a janela e o player com buffer de teste.
2. **Etapa 2, sobre dados de teste:** M1 conclui alocação, posições, conexões e arestas com fixtures. M3 implementa o motor sobre o `Graph` de fixture. M2 implementa Tarjan, comunidades e métricas. M4 processa os dados reais e M5 implementa o mapa e o painel sobre o buffer de teste.
3. **Etapa 3, integração:** calibração de β e benchmark (M3 e M2). Cenário regional com séries reais (M1 e M4) e comparação com dados reais (M4). Painel completo, configuração e exportação (M5).
4. **Etapa 4, fechamento:** testes de integração, validação do caso de referência, teste visual do limiar de vértices no protótipo, empacotamento, revisão cruzada e ajustes finais.

## 7. Carga e balanceamento

Com o escopo do M1 da v0.1 restabelecido, o M1 concentra a construção do grafo e tem carga grande. O M4 fica com a carga média: dados, geometria processada, fluxo real e comparação. Se o M1 precisar de apoio, a parte de testes de grafo pode ser dividida com o M2, que já configura o pytest.

## 8. Pendências

### Resolvidas desde a v0.2

| Item | Decisão | Impacto |
|---|---|---|
| Escopo do M1 | Mantém a construção do grafo unificado (`world/`), sementes e exceções (14/11, escopo da v0.1) | M1 e M4 |
| Nomes no código e nos contratos | Inglês, com os nomes da seção 3 (14/11) | Todos |
| Campo de γ em RF01 | Taxa total de saída de I, informada pelo usuário; a mortalidade divide a saída (14/11) | M3, M5 |
| Custo e probabilidade | Recebem β como argumento; chamados pelo M3 depois da calibração (14/11) | M1 e M3 |
| Dia 0 | Primeiro dia em que o número de vértices infectados de um país atinge M (14/11) | M3 e M4 |
| NumPy no núcleo | Liberado pelo professor (04/11) | M1 e M3 |
| shapely | Liberado para o script, não para o aplicativo (04/11) | M4 |
| Formato do Natural Earth | GeoJSON, convertido uma vez | M4 |
| OpenFlights | Arquivo derivado versionado sob ODbL (04/11) | M4 e relatório |

### Ainda abertas

| Pendência | Afeta | Quem resolve |
|---|---|---|
| Valor de M, número mínimo de vértices infectados para o dia 0 | M3, M4 | Grupo |
| Validação de 40 px e 36 px no protótipo, na máquina mais fraca | M5 | E |
| Benchmark de `N_total` (provisório 8.000), `k_max`, `escala` e `d̄` | M1, M2, M3 | C, com A e B |
| Recontagem de rotas e de países sem rota sobre as 229 entidades | M4 | D |
| Fonte do Ebola: trocar o Kaggle pela HDX | M4 | D |
| Licença do código e `DATA_SOURCES.md` | Repositório | D, com o grupo |
| Níveis de intervenção: validar por sensibilidade | M3, M5 | B, com o grupo |
| R0 de referência e leitura direta de Lipsitch et al. (2003) | Modelagem e relatório | B, com o grupo |
| Local do cálculo de R0 efetivo (`app/panel_metrics.py` ou `core/analysis/`) | M2, M5 | C e E |
| Atribuição de responsáveis (A a E) | Todos | Grupo |
| Casos de uso, UML e relatório LaTeX | Documentação | Grupo |

## 9. Lacunas da arquitetura v0.5 e situação na v0.6

| # | Lacuna na v0.5 | Situação na v0.6 |
|---|---|---|
| 1 | `app/real_session.py` não aparecia na tabela de módulos | Resolvido: M4 |
| 2 | Comparação com dados reais (RF14) não tinha arquivo | Resolvido: `app/comparison.py`, M4 |
| 3 | R0 efetivo em `app/panel_metrics.py` (M5), enquanto a modelagem trata como análise | Em aberto (seção 8) |
| 4 | `tests/` listado como responsabilidade do M5 | Resolvido: cada pacote testa a si mesmo; M5 fica com `tests/architecture/` |
| 5 | Regra de dependência com `NUMPY_LIBERADO = False` | Resolvido: NumPy só em `core/timeline/buffer.py` e `core/epidemic/engine.py` |
| 6 | Alocação e cenários em `world/` (M4) | Resolvido: `world/` é do M1 |

## 10. Histórico de alterações

| Versão | Data | Mudanças |
|---|---|---|
| 0.1 | 03/11/2026 | Primeira proposta: cinco módulos, responsáveis A a E, contratos e etapas. |
| 0.2 | 14/11/2026 | Pacotes alinhados à arquitetura v0.5. Construção do grafo unificado movida do M1 para o M4. Testes atribuídos a cada pacote. Pendências atualizadas com as decisões de 04/11. Seções 7 e 9 novas. |
| 0.3 | 14/11/2026 | Escopo do M1 da v0.1 restabelecido (`world/`, sementes, erros e funções de probabilidade e custo); M4 com dados, comparação e fluxo real; nomes em inglês nos contratos; γ como taxa total de saída de I; β como argumento das funções de custo; dia 0 por vértices infectados (M pendente); lacunas da arquitetura atualizadas. |
