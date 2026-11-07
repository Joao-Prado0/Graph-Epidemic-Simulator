# Responsabilidades por módulo: Simulador de Epidemias em Redes

Versão 0.1, 03/11/2026. Proposta para discussão do grupo.

## 1. Premissas

- Um **módulo** é um conjunto de funcionalidades com um responsável. Pode ocupar mais de uma pasta e não é necessariamente um componente independente.
- A base são as decisões já fechadas: grupos 0, A a F da modelagem, decisões B1 a B9 e C1 a C8, decisões de dados e as decisões de arquitetura registradas (pasta `datasets/`, buffer de histórico, sementes por subsistema).
- A arquitetura v0.3 não estava disponível neste chat. Os nomes de módulos (M1 a M5) e pastas seguem o que está registrado nas decisões. Conferir com o documento de arquitetura antes de fechar.
- O grupo foi informado com **5 integrantes**. O histórico registra 6. Confirmar: se houver um sexto integrante, a carga do M3 e do M5 pode ser dividida.
- Os integrantes aparecem como A a E. Cada letra representa um integrante, a ser atribuído em grupo.

## 2. Visão geral

| Módulo | Responsável | Escopo resumido | Pastas prováveis | Carga estimada |
|---|---|---|---|---|
| M1 Grafo e rede | A | Construção do grafo unificado, alocação de vértices, arestas, pesos e custos | `core/graph/` | Grande |
| M3 Motor epidemiológico | B | Passo diário, isolamento, vacinação, paciente zero, histórico, calibração de β | `core/engine/` | Grande |
| M2 Análise e benchmark | C | Métricas estruturais, métricas epidemiológicas, benchmark de desempenho | `core/analysis/`, `tests/bench/` | Média |
| M4 Dados e comparação | D | Script de preparação, geometria processada, fluxo real, comparação com dados reais | `scripts/prepare_data.py`, `datasets/` | Grande |
| M5 Interface e saída | E | Janelas, player, mapa, painel, gráficos, configuração, exportação, empacotamento | `app/`, `ui/` | Grande |

Observação: a carga é relativa e precisa ser validada pelo grupo depois da primeira estimativa de cada integrante.

## 3. Contratos a fechar na primeira reunião

Antes de codar, os responsáveis por M1, M3, M4 e M5 devem concordar com estas estruturas. Sem isso, os módulos não se encaixam.

| Contrato | Dono | Conteúdo |
|---|---|---|
| `Grafo` | M1 | Vértices com país e posição, lista de adjacência, máscara de arestas ativas, pesos `w` e custos `−ln p` |
| `SimulationConfig` | M3 | Parâmetros da doença, níveis de isolamento e vacinação, paciente zero, semente global, N_total, β calibrado |
| `Timeline` | M3 | Buffer por dia (um `bytearray` por dia), com estado, flag de isolado e flag de vacinado por vértice |
| `CountriesData` / `EdgesData` | M4 | Saídas do script: `countries.csv`, `edges.csv`, `countries.geojson` e séries diárias |
| `MetricasSerie` | M2 | Séries de casos, mortes e recuperados para comparação e painel |

## 4. Detalhamento por módulo

### M1: Grafo e rede (responsável A)

**Funcionalidades**

- Alocação de vértices por país: total fixo `N_total` (provisório 8.000), `n_min = 12`, `α = 0,5`, alocação iterativa de piso e arredondamento por maior resto. Grau efetivo `d̄_ef = min(d̄, n_i − 1)`.
- Posição dos vértices sorteada dentro do polígono do país (polígonos vindos do M4).
- Raio das conexões internas por `r ≈ √(d̄ / (π · ρ))`, com `d̄` entre 6 e 10. Rede geométrica aleatória (RF02).
- Arestas entre países por `k_ij = min(k_max, ceil(routes_ij / escala))`, com vértices escolhidos ao acaso e semente fixa. Cada aresta herda `w_ij`.
- Pesos: `w = log(1 + routes) / log(1 + max routes)`, `p = 1 − exp(−β · w)`, custo `−ln(p)` com `p ≤ 0,999`.
- Estrutura de lista de adjacência com máscara de arestas ativas (E1). Versão NumPy/CSR só se o professor liberar NumPy.
- Consultas: vizinhos e caminho mínimo (Dijkstra) pelo custo de distância efetiva.
- Sinalização de países isolados (sem rota no OpenFlights), sem arestas artificiais.
- Redistribuição do orçamento de vértices no cenário regional (B3), mantendo o grafo global.

**Entradas:** `countries.csv`, `edges.csv`, polígonos (M4).
**Saídas:** `Grafo` (contrato).
**Critérios de aceitação:** soma de vértices igual a `N_total`; grafo não direcionado; custo de caminho derivado de `p`, não de `routes`; grafos pequenos com resposta conhecida (caminho, ciclo, Dijkstra calculado à mão).
**Bloqueios:** `β`, `k_max`, `escala` e `d̄` (benchmark, com C).

### M3: Motor epidemiológico (responsável B)

**Funcionalidades**

- Compartimentos S, E, I, R, D. Passo de um dia, transição com `1 − exp(−γ)` (C1, C2).
- Saída de I: vai para D com probabilidade igual à mortalidade e para R com a probabilidade complementar. γ é a taxa total de saída de I.
- Isolamento como flag e máscara de arestas, sem alterar o grafo. Isolado não é contaminado, pode morrer e volta com as mesmas arestas (C3, RF05).
- Vacinação automática: move S para R com eficácia 0,8. Início e fração diária vêm dos níveis baixo, médio e alto (C5, provisório). Vacinado é uma flag separada, e a comparação com dados reais ignora essa flag (acordo do Bloco 2, item 3).
- Paciente zero manual ou aleatório (RF03). Centralidade fica só como análise (M2).
- Sementes: uma global, e uma derivada por subsistema (rede, paciente zero, isolamento, vacinação, rótulos), de forma determinística (F2, RNF05).
- Invariante `S + E + I + R + D = N` verificado em todo passo (F1).
- Buffer de histórico gravado durante a execução, um `bytearray` por dia. A escrita é feita pela thread de simulação e a leitura pela interface (E2).
- Calibração de β por bisseção até o R0 informado pelo usuário (B2). Configuração travada após a calibração.
- Histórico no mesmo formato para o fluxo real, lido pelo mesmo player.

**Entradas:** `Grafo` (M1), `SimulationConfig`.
**Saídas:** `Timeline` (contrato), séries para o M2 e o M4.
**Critérios de aceitação:** caso de referência sem isolamento nem vacinação dentro de 5% do pico da solução do SIR (F1); mesma semente e mesmos parâmetros geram o mesmo buffer (comparação por hash); invariante em todas as simulações de teste.
**Bloqueios:** liberação de NumPy pelo professor; benchmark para N_total; níveis C5 (validar se produzem diferenças visíveis).

### M2: Análise de grafo e métricas (responsável C)

**Funcionalidades**

- Tarjan no grafo completo de vértices: pontes e pontos de articulação (E3).
- Comunidades por propagação de rótulos no grafo contraído por país (RF19, E3).
- Centralidade de grau para o painel. Intermediação aproximada por amostragem de fontes; versão exata só no benchmark (E4).
- Coeficiente de agrupamento local por vértice e média global, com custo `O(Σ k_v²)` (RF18). Média por país opcional, a partir do grafo contraído.
- Métricas epidemiológicas: R0 efetivo pelo crescimento inicial, na forma SEIR `R0 ≈ (1 + r/σ)(1 + r/γ)`, com `r = ln(I_t / I_0) / t` (B6, C8). Indicação do pico. Pico de novos casos por dia e tamanho final.
- Benchmark de desempenho (RNF02) para definir `N_total`, `β`, `k_max`, `escala` e `d̄`. Comparação de desempenho com NetworkX (F1).
- Fixtures de teste de grafos pequenos, usados também pelo M1.

**Entradas:** `Grafo` (M1), `Timeline` (M3).
**Saídas:** métricas para o painel (M5) e valores para o relatório.
**Critérios de aceitação:** resultados de Tarjan e Dijkstra iguais aos calculados à mão nos grafos de teste; benchmark documentado com tempo por passo.
**Atribuição transversal (sugestão):** o C também cuida da configuração do ambiente de testes (pytest) e de um padrão de revisão do repositório, no início.

### M4: Dados e comparação com a realidade (responsável D)

**Funcionalidades**

- Script `prepare_data.py` e pacote `datasets/` (renomeado de `dados/`, C2). Leitura de JHU, OWID, OpenFlights e Natural Earth.
- Normalização: aliases de países, descarte de não-países (D8), cummax (D10), série diária contínua (D11), recuperados só no SARS (D12), duplicata da China no SARS mantendo o acumulado crescente.
- Agregação de territórios ao país-mãe (GIB ao GBR; BES ao NLD; TKL ao NZL; GLP, GUF, MTQ, MYT e REU ao FRA). Ilhas Åland ao Finlândia e Norte do Chipre ao Chipre. Feições fora do modelo descartadas (ATA, ATF, HMD, NFK, SGS, IOT, SOL, KAS).
- Universo de 229 entidades. Kosovo como OWID_KOS.
- Rotas: não direcionadas, número bruto em `edges.csv` (D13). Exclui codeshare (D14). Rotas entre território e metrópole viram domésticas e saem.
- Regra da Libéria no Ebola: manter por data a linha de maior número de casos e descartar a série Liberia 2.
- Geometria: `countries.geojson` processado (D20), chave ISO_A3_EH com fallback em ADM0_A3, agregação de feições do mesmo país, tratamento do antimeridiano (Rússia, Fiji, EUA).
- Cenário regional (B4): países que atingem 10 casos acumulados nos primeiros 60 dias a partir do dia 0. Prazo configurável. Não há lista fixa.
- Fluxo real: séries e histórico processados, no formato do `Timeline`.
- Comparação com dados reais (RF14): dia 0 pelo limiar de 10 casos em fração da população (B5). Acumulados `I + R + D`, mortes em `D`, recuperados em `R` natural (só SARS). Métricas: erro quadrático médio, diferença de pico de novos casos por dia, diferença de tamanho final (B7, D1, D2).

**Entradas:** arquivos brutos (Kaggle, JHU, OWID, OpenFlights, Natural Earth).
**Saídas:** `countries.csv`, `edges.csv`, `countries.geojson`, séries processadas, métricas de comparação.
**Critérios de aceitação:** contagem de países com e sem rota recalculada no script e registrada; nenhuma aresta artificial; teste do script com conferência de totais de população e casos por país.
**Bloqueios:** confirmação de shapely (e pyshp, se necessário) com o professor; formato de entrada do Natural Earth (GeoJSON ou shapefile); licenças e fonte do Ebola (substituir o Kaggle pela fonte HDX, conforme análise de licenças).
**Nota:** o responsável pelo script foi listado como decisão do grupo. Esta atribuição é uma proposta.

### M5: Interface, mapa e saída (responsável E)

**Funcionalidades**

- Janela principal em PySide6 e tela de configuração: parâmetros da doença (RF01), seleção de pandemia (RF09), cenário, R0 informado, níveis de isolamento e vacinação, paciente zero.
- Player com play, pausa, voltar e avançar, lendo o buffer gravado (RF04, RF11, E2). Reiniciar descarta o buffer.
- Mapa em pyqtgraph: polígonos pintados pela cor de status dominante do dia. Vértices só aparecem em países com largura igual ou maior que 40 px e são ocultados abaixo de 36 px. Regra de status dominante do fluxo real em validação (proposta de intensidade por 100 mil habitantes).
- Painel de resultados: métricas de comparação (RF14, RF21, RF24), centralidades, comunidades, R0 efetivo e indicação de pico.
- Gráficos com exportação de imagem (`ui/charts_view.py`, RF08).
- Salvar e carregar configuração em JSON pela biblioteca padrão (`app/config_io.py`, RF07).
- Exportação em CSV a partir do `Timeline` (`app/export.py`, RF08).
- Tratamento de erros com exceções próprias, aprovado em 31/10.
- Empacotamento com PyInstaller para Windows (todos os integrantes usam Windows).

**Entradas:** `Timeline` (M3), `Grafo` (M1), métricas (M2 e M4), `countries.geojson` (M4).
**Saídas:** aplicativo executável.
**Critérios de aceitação:** o player reproduz o buffer sem recalcular a simulação; pausa e retorno não alteram o histórico; configuração salva e carregada produz o mesmo buffer; executável roda em máquina Windows sem o ambiente de desenvolvimento.
**Bloqueios:** contrato `Timeline`; regra de status dominante (proposta pendente); decisão sobre vértices em países pequenos (ainda a validar).

## 5. Atribuições transversais

- **Testes:** cada responsável escreve os testes do próprio módulo. O C configura o pytest.
- **Revisão cruzada:** cada integrante revisa um módulo de outro antes do fechamento de cada etapa.
- **Documentação técnica:** docstrings e README de cada pasta, pelo responsável do módulo.
- **Setup do ambiente e repositório:** já documentado (setup_ambiente). Manter atualizado pelo responsável do M5 (empacotamento).
- **Casos de uso, UML e relatório LaTeX:** não atribuídos aqui. A lista de casos de uso (C5) está delegada a outro integrante. Definir quem assume UML e relatório depois da primeira versão deste documento.

## 6. Ordem de execução sugerida

1. **Etapa 1:** fechar os contratos (seção 3). M1 e M4 começam o grafo base e os dados processados. C configura o ambiente de testes.
2. **Etapa 2:** M3 implementa o motor sobre o grafo do M1. M2 implementa Tarjan, comunidades e métricas sobre o grafo. M5 monta a janela, o mapa e o player com dados falsos (buffer de teste).
3. **Etapa 3:** calibração de β e benchmark (M3 e M2). Cenário regional e comparação com dados reais (M4). Painel completo (M5).
4. **Etapa 4:** testes de integração, validação do caso de referência, empacotamento, revisão cruzada e ajustes finais.

## 7. Pendências que podem mudar este plano

| Pendência | Afeta | Quem resolve |
|---|---|---|
| Liberação de NumPy pelo professor | M1, M3 | Grupo (pergunta ao professor) |
| Confirmação de shapely e pyshp | M4 | Grupo (pergunta ao professor) |
| Formato do Natural Earth (GeoJSON ou shapefile) | M4, M1 | D, alinhado com A |
| Benchmark: `N_total`, `β`, `k_max`, `escala`, `d̄` | M1, M2, M3 | C, com A e B |
| Níveis C5 (isolamento e vacinação) | M3, M5 | B, com validação do grupo |
| Revisão de σ e γ (H1N1 e SARS) após fontes de incubação | M3, M2 | B e C |
| Regra de status dominante no fluxo real | M5, M4 | E, com D |
| Licenças e fonte do Ebola | M4 | D |
| Quem assume casos de uso, UML e relatório | Documentação | Grupo |

## 8. Pontos a confirmar pelo grupo

- Número de integrantes: 5 ou 6.
- Aceite da atribuição do script de preparação de dados ao M4.
- Aceite da carga estimada. Se algum módulo estiver pesado demais, a divisão preferida é mover a interface de gráficos (M5) para o M2.
