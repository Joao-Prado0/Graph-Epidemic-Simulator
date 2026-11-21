# Modelagem e Planejamento da Solução: Simulador de Epidemias em Redes

Trabalho Prático – Teoria dos Grafos (Tema 7)

---

## Sumário

1. [Descrição do Problema, Objetivos e Escopo](#1-descrição-do-problema-objetivos-e-escopo)
2. [Levantamento e Preparação dos Dados](#2-levantamento-e-preparação-dos-dados)
3. [Modelagem do Grafo e Justificativas](#3-modelagem-do-grafo-e-justificativas)
4. [Modelo Epidemiológico SEIRD, Intervenções e Comparação Real](#4-modelo-epidemiológico-seird-intervenções-e-comparação-real)
5. [Algoritmos em Grafos, Complexidade e Validação](#5-algoritmos-em-grafos-complexidade-e-validação)
6. [Diagramas UML do Sistema](#6-diagramas-uml-do-sistema)
7. [Estrutura do Projeto e Plano de Desenvolvimento](#7-estrutura-do-projeto-e-plano-de-desenvolvimento)
8. [Limitações do Modelo](#8-limitações-do-modelo)

---

## 1. Descrição do Problema, Objetivos e Escopo

### 1.1 Definição do Problema
A propagação de uma doença infecciosa depende tanto das características biológicas do patógeno quanto da estrutura da rede de contatos entre indivíduos e regiões. Redes com *hubs* de transporte, forte agrupamento local e pontes entre comunidades produzem dinâmicas epidêmicas muito diferentes daquelas previstas por modelos homogêneos sem topologia.

O projeto aborda o **Tema 7 — Simulador de Epidemias em Redes**, consistindo no desenvolvimento de uma ferramenta desktop em Python que modela a rede global de países e indivíduos como um grafo ponderado, simula a propagação estocástica de epidemias e analisa a estrutura da rede por meio de algoritmos clássicos de Teoria dos Grafos implementados pelo grupo.

### 1.2 Objetivos
- **Fluxo de Simulação:** Simular a propagação de uma epidemia sobre um grafo global unificado, a partir de parâmetros configurados pelo usuário antes do início ($R_0$, taxa de saída $\gamma$, mortalidade, período de incubação e nível de intervenção).
- **Fluxo de Pandemias Reais:** Reproduzir visualmente quatro surtos históricos (**COVID-19**, **Ebola 2014–2016**, **H1N1 2009** e **SARS 2003**) sobre o mesmo grafo global, permitindo comparar a curva simulada com os dados históricos.
- **Análise em Grafos:** Aplicar algoritmos de busca (BFS, DFS e componentes conexos), caminho mínimo (Dijkstra sobre distância efetiva), métricas de rede (grau, agrupamento local/global e centralidade de intermediação de Brandes), detecção de comunidades (propagação de rótulos) e identificação de arestas e vértices críticos (Tarjan).
- **Interface Visual:** Exibir a evolução diária em um mapa-múndi interativo em duas camadas (polígonos de países e vértices individuais exibidos conforme o zoom), acompanhado de player de linha do tempo, curvas em tempo real e painel de métricas.

### 1.3 Princípio de Funcionamento e Escopo
O simulador opera de forma **demonstrativa e reprodutível**:
- O usuário define os parâmetros antes da partida; após o início, a configuração fica travada e o usuário acompanha a evolução pelo player da linha do tempo sem alterar o rumo da epidemia em andamento.
- Isolamento e vacinação ocorrem apenas no fluxo de simulação e são aplicados automaticamente pelo motor de forma estocástica conforme o nível escolhido (*Baixo*, *Médio* ou *Alto*).
- O motor grava o estado de cada vértice dia a dia em um buffer de histórico, e a interface apenas reproduz essa linha do tempo, permitindo usar o mesmo player nos dois fluxos.
- **Stack tecnológica:** Python 3.12, `PySide6` (`QPainter` para renderização do mapa em lote), `pyqtgraph` (curvas em tempo real), `pytest` e `PyInstaller`. Nenhuma biblioteca pronta de grafos é utilizada no núcleo do sistema (`NetworkX` é restrito exclusivamente aos scripts de benchmark).

---

## 2. Levantamento e Preparação dos Dados

### 2.1 Fontes de Dados
Como os *datasets* epidemiológicos trazem apenas séries de casos e óbitos por país, o projeto combina quatro fontes complementares, cruzadas pelo código **ISO3** de cada país:

| Fonte | Arquivos Utilizados | Papel na Modelagem |
|---|---|---|
| **JHU CSSE / OMS (Kaggle)** | Séries de COVID-19, Ebola (2014–2016), H1N1 (2009) e SARS (2003) | Séries temporais diárias acumuladas de casos, óbitos e (no SARS) recuperados. |
| **Our World in Data (OWID)** | `owid-covid-data.csv` | Tabela mestra de países com código ISO3 e população. |
| **OpenFlights** | `airports.dat`, `routes.dat`, `countries.dat` | Rotas aéreas internacionais para construção das arestas entre países. |
| **Natural Earth (50m, v5.1.1)** | `ne_50m_admin_0_countries.json` | Polígonos geográficos dos países para sorteio dos vértices e desenho do mapa. |

### 2.2 Normalização e Universo de 229 Entidades
A preparação dos dados é realizada *offline* pelo script `data/prepare_data.py`, gerando arquivos limpos em `data/processed/` que o aplicativo lê usando apenas a biblioteca padrão:
- **Fechamento em 229 entidades:** A partir dos 237 países do OWID com continente definido, são agregados às respectivas metrópoles 8 territórios que não possuem polígono próprio na escala 50m do Natural Earth (Gibraltar ao Reino Unido; Bonaire, Saba e Santo Eustáquio aos Países Baixos; Tokelau à Nova Zelândia; Guadalupe, Guiana Francesa, Martinica, Mayotte e Reunião à França), agrega-se o Norte do Chipre ao Chipre e inclui-se o Kosovo (`KOS`), totalizando **229 entidades**.
- **Limpeza das séries temporais:** Embarcações e eventos (*Diamond Princess*, *MS Zaandam*, Olimpíadas) são descartados; datas faltantes são preenchidas por *forward-fill* para formar séries diárias contínuas; aplica-se máximo acumulado (`cummax`) em cada série para corrigir quedas retroativas de notificação antes da soma nos países-mãe.
- **Filtragem de rotas aéreas:** Rotas domésticas e voos em *codeshare* são descartados, consolidando o volume bruto de rotas internacionais por par não ordenado de países em `edges.csv` (licenciado sob ODbL 1.0).

---

## 3. Modelagem do Grafo e Justificativas

### 3.1 Grafo Global Unificado Não Direcionado
Os dois fluxos compartilham o mesmo grafo não direcionado $G = (V, E)$. Cada país é representado por um conjunto de vértices proporcional à sua população, com arestas internas por proximidade geométrica e arestas entre países pelas rotas aéreas.
- **Justificativa:** Utilizar um único grafo garante a mesma granularidade espacial na comparação entre simulação e dados reais e unifica a visualização. O grafo é não direcionado porque o contato e o transporte aéreo ocorrem nos dois sentidos (as rotas $A \to B$ e $B \to A$ são somadas no par $\{A, B\}$); o sentido da transmissão decorre do estado dos vértices ($I$ contamina $S$).

### 3.2 Alocação Iterativa de Vértices por População
Para cada país $i$ com população $p_i$, o número de vértices $n_i$ segue uma relação sublinear com piso mínimo $n_{\min} = 12$, expoente $\alpha = 0{,}5$ e orçamento total fixo $N_{\text{total}} = 8.000$:
$$n_i \propto p_i^\alpha, \quad \text{com } \sum_{i=1}^{229} n_i = N_{\text{total}} \text{ e } n_i \ge n_{\min}$$
- **Procedimento e justificativa:** Aplicar `max(n_min, ...)` diretamente faria a soma ultrapassar $N_{\text{total}}$. Por isso, a alocação é iterativa: calcula-se a divisão proporcional sobre o orçamento livre, fixam-se em $n_{\min} = 12$ os países que ficaram abaixo do piso descontando-os do orçamento, e repete-se até que todos os países livres fiquem acima de $n_{\min}$, aplicando ao final o arredondamento pelo método do maior resto.
- **Cenário Regional (Ebola):** Mantém o grafo global, mas fixa em $n_{\min} = 12$ os países fora do foco e redistribui o orçamento restante entre os países que atingem ao menos 10 casos nos primeiros 60 dias do surto (Guiné, Libéria e Serra Leoa).

### 3.3 Conexões Internas (Rede Geométrica e Grade Espacial)
Os vértices de cada país são sorteados dentro do seu polígono geográfico e conectados quando a distância entre eles é menor que o raio adaptativo $r_i$:
$$r_i \approx \sqrt{\frac{\bar{d}_{\text{ef}}}{\pi \cdot \rho_i}}, \quad \text{com } \rho_i = \frac{n_i}{\text{Área}_i} \text{ e } \bar{d}_{\text{ef}} = \min(\bar{d}, n_i - 1)$$
onde o grau médio alvo $\bar{d}$ situa-se entre 6 e 10.
- **Justificativa:** Um raio fixo faria o grau médio variar drasticamente com a densidade territorial do país. O raio ajustado pela densidade mantém a estrutura local consistente entre países grandes e pequenos, e o uso de uma **grade espacial 2D** reduz a construção das arestas internas de $O(n_i^2)$ para $O(n_i + E_i)$.

### 3.4 Arestas entre Países, Pesos e Distância Efetiva
Para cada par de países $(i, j)$ com $\text{routes}_{ij}$ rotas no OpenFlights:
1. **Multiplicidade de arestas:**
   $$k_{ij} = \min\bigl(k_{\max}, \lceil \text{routes}_{ij} / \text{escala} \rceil\bigr)$$
   São sorteadas $k_{ij}$ arestas ligando vértices escolhidos ao acaso entre os dois países, com semente fixa.
2. **Peso normalizado e probabilidade de transmissão:**
   $$w_{ij} = \frac{\ln(1 + \text{routes}_{ij})}{\ln(1 + \max \text{routes})}, \qquad p_{ij} = 1 - \exp(-\beta \cdot w_{ij})$$
3. **Custo de caminho para o Dijkstra (Distância Efetiva de Brockmann & Helbing, 2013):**
   $$\text{custo}_{ij} = -\ln\bigl(\min(p_{ij}, 0{,}999)\bigr)$$
- **Justificativa:** O logaritmo impede que rotas extremas dominem toda a rede. Transformar a probabilidade em custo por $-\ln(p_{ij})$ garante pesos estritamente positivos em que somar custos ao longo de um caminho equivale a multiplicar as probabilidades de transmissão. Países sem rota no OpenFlights permanecem isolados na malha aérea, sem arestas artificiais.

---

## 4. Modelo Epidemiológico SEIRD, Intervenções e Comparação Real

### 4.1 Estados, Flags e Transições Diárias
O modelo utiliza cinco compartimentos (**S, E, I, R, D**) e duas flags booleanas independentes empacotadas em 1 byte por vértice:
- **Flag de isolado (bit 3):** permite que um vértice esteja em $I$ e isolado ao mesmo tempo.
- **Flag de vacinado (bit 4):** vacinados passam ao estado $R$ com a flag ligada, permitindo distinguir recuperados naturais ($R$ sem flag) na comparação com dados reais.

Cada passo equivale a **1 dia**, com probabilidades na forma exponencial:
$$P(E \to I) = 1 - \exp(-\sigma), \qquad P(\text{saída de } I) = 1 - \exp(-\gamma)$$
onde $\sigma = 1/\text{incubação}$ e $\gamma$ é a taxa total de saída de $I$. Ao sair de $I$, o vértice vai para óbito ($D$) com probabilidade igual à mortalidade configurada e para recuperado natural ($R$) com a probabilidade complementar.

### 4.2 Calibração de $\beta$ por Bisseção
O usuário informa o $R_0$ desejado. Antes do início da simulação, o sistema executa simulações curtas no grafo gerado e ajusta $\beta$ por **bisseção** até que o $R_0$ empírico medido convirja para o valor informado (utilizando a fórmula analítica de Newman, $R_0 \approx T \cdot (\langle k^2 \rangle / \langle k \rangle - 1)$, como verificação). Ao final da calibração, os custos $-\ln(p_{ij})$ são atualizados nas arestas do grafo.

### 4.3 Isolamento e Vacinação Automáticos
As intervenções seguem constantes determinadas pelo nível escolhido pelo usuário:

| Nível | Isolamento Diário em $I$ (probabilidade e duração) | Vacinação Diária em $S$ (dia de início e fração) | Eficácia da Vacina |
|---|---|---|---|
| **Baixo** | $5\%\text{/dia}$, por $7\text{ dias}$ | A partir do dia $180$, $0{,}2\%\text{/dia}$ | $80\%$ (fixa) |
| **Médio** | $15\%\text{/dia}$, por $10\text{ dias}$ | A partir do dia $120$, $0{,}5\%\text{/dia}$ | $80\%$ (fixa) |
| **Alto** | $30\%\text{/dia}$, por $14\text{ dias}$ | A partir do dia $60$, $1{,}0\%\text{/dia}$ | $80\%$ (fixa) |

O isolamento desativa temporariamente a máscara de arestas do vértice sem alterar a topologia do grafo; ao término do prazo, o vértice retorna com as mesmas arestas.

### 4.4 Comparação com Dados Reais e Regra de Cor no Mapa
- **Alinhamento e comparação:** Compara-se a soma de casos acumulados simulados ($I + R_{\text{natural}} + D$, sem expostos e sem vacinados) e óbitos ($D$) com as séries históricas, alinhando o **Dia 0** de cada país pelo primeiro dia com $M = 1$ vértice infectado (convertido proporcionalmente para a população real do país). As métricas avaliadas são o Erro Quadrático Médio (EQM) entre as curvas normalizadas, a diferença do dia de pico de novos casos diários e a diferença de tamanho final da epidemia.
- **Renderização em duas camadas no mapa:** No fluxo de simulação, cada país é pintado pelo estado dominante do dia; no fluxo real, pela intensidade de casos acumulados por 100 mil habitantes (a partir de 10 casos/100 mil hab.). Os vértices individuais aparecem quando o país ocupa largura $\ge 40\text{ px}$ na tela e são ocultados abaixo de $36\text{ px}$ (histerese de $4\text{ px}$).

---

## 5. Algoritmos em Grafos, Complexidade e Validação

### 5.1 Resumo de Complexidade dos Algoritmos Implementados

| Algoritmo / Operação | Aplicação no Sistema | Complexidade de Tempo | Complexidade de Espaço |
|---|---|---|---|
| **Busca em Largura (BFS) e Profundidade (DFS iterativa)** | Componentes conexos e distância em saltos | $O(V + E)$ | $O(V)$ |
| **Dijkstra** | Caminho mais provável de transmissão com custo $-\ln(p)$ | $O((V + E) \log V)$ | $O(V)$ |
| **Tarjan (pontes e pontos de articulação)** | Identificação de conexões e vértices críticos em uma DFS | $O(V + E)$ | $O(V)$ |
| **Propagação de Rótulos (*Label Propagation*)** | Detecção de comunidades no grafo contraído por país | Quase linear $O(I_{\text{rot}} \cdot (V_c + E_c))$ | $O(V_c + E_c)$ |
| **Grau e Coeficiente de Agrupamento** | Grau médio/local e transitividade local e global | Grau: $O(V + E)$; Agrupamento: $O(\sum k_v^2)$ | $O(V)$ |
| **Centralidade de Intermediação (Brandes)** | Centralidade aproximada por $k$ fontes (e exata no benchmark) | Aproximada: $O(k \cdot (V + E))$; Exata: $O(V \cdot E)$ | $O(V + E)$ |
| **Grade Espacial 2D** | Conexão geométrica dos vértices internos de cada país | $O(V + E)$ esperado | $O(V)$ |
| **Passo Diário da Simulação (`step`)** | Atualização síncrona SEIRD sobre arestas ativas | $O(V + E_{\text{ativas}})$ | $O(V)$ |

### 5.2 Validação e Reprodutibilidade
- **Caso de referência em grafo completo:** Sem isolamento nem vacinação, o pico de infectados simulado em grafo completo deve ficar dentro de $5\%$ da solução numérica de campo médio.
- **Invariante de conservação:** Em todos os passos, $S + E + I + R + D = N$.
- **Reprodutibilidade por semente:** Uma semente global deriva sub-sementes determinísticas via `hashlib.sha256` para cada subsistema (rede, paciente zero, isolamento, vacinação, rótulos e calibração), garantindo que a mesma configuração gere exatamente o mesmo histórico.

---

## 6. Diagramas UML do Sistema

### 6.1 Diagrama de Componentes e Camadas
A arquitetura é organizada em quatro camadas com dependência em sentido único (`ui` $\to$ `app` $\to$ `world`/`datasets` $\to$ `core`), isolando o núcleo de grafos e de simulação da interface gráfica:

![Diagrama de Componentes UML](../../diagramas/diagrama_de_componente/diagrama_de_componentes.png)

### 6.2 Diagrama de Classes UML
Representa as estruturas centrais do domínio (`Graph`, `World`, `Timeline`, `StateBuffer`, `SimulationConfig`, `EpidemicEngine`), as sessões de aplicação (`SimulationSession` e `RealSession`) e os componentes da interface gráfica:

![Diagrama de Classes UML](../../diagramas/diagrama_de_classe/diagrama_de_classe_epidemia.png)

### 6.3 Diagramas de Casos de Uso
Os casos de uso dividem as interações do usuário entre os dois fluxos principais da aplicação, compartilhando o mesmo grafo global e os mesmos controles de reprodução da linha do tempo:

#### Fluxo de Simulação
Cobre a configuração dos parâmetros epidemiológicos, calibração de $\beta$, definição do paciente zero, execução com isolamento e vacinação automáticos, reprodução no player, visualização das curvas SEIRD, cálculo de métricas de rede e exportação de resultados (JSON, CSV e PNG):

![Diagrama de casos de uso do fluxo de simulação](<../../diagramas/casos de uso/diagramas/casos de uso/fluxo de simulação.png>)

#### Fluxo de Pandemias Reais
Cobre a seleção de um dos quatro surtos históricos pré-processados (COVID-19, Ebola, H1N1 e SARS), reprodução temporal da incidência por 100 mil habitantes no mapa, consulta de totais por país e comparação quantitativa com a curva simulada:

![Diagrama de casos de uso do fluxo de pandemias reais](<../../diagramas/casos de uso/diagramas/casos de uso/fluxo de pandemias reais.png>)

---

## 7. Estrutura do Projeto e Plano de Desenvolvimento

### 7.1 Estrutura de Pastas do Repositório

```text
simulador-epidemias/
├── benchmarks/                       # Comparação de desempenho (único local com NetworkX)
│   └── bench_grafo.py
├── data/                             # Preparação offline dos datasets
│   ├── country_aliases.csv
│   ├── prepare_data.py
│   └── processed/                    # Arquivos limpos lidos pelo aplicativo (CSV e GeoJSON)
├── docs/                             # Documentação, diagramas UML, wireframes e artigo LaTeX
├── scripts/
│   └── build_exe.ps1                 # Script de empacotamento com PyInstaller
├── src/epidemia/
│   ├── main.py                       # Ponto de entrada da aplicação
│   ├── core/                         # Domínio puro (sem dependência de Qt)
│   │   ├── errors.py                 # Exceções do domínio
│   │   ├── seeds.py                  # Derivação determinística de sementes (SHA-256)
│   │   ├── graph/                    # Graph, pesos, BFS, DFS, componentes e Dijkstra
│   │   ├── analysis/                 # Grau, agrupamento, Brandes, comunidades, Tarjan e métricas SEIR
│   │   ├── epidemic/                 # SimulationConfig, calibração de β, modelo SEIRD, intervenções e engine
│   │   └── timeline/                 # Protocolo Timeline e StateBuffer
│   ├── world/                        # Alocação de vértices, geometria, grade espacial, builder e cenários
│   ├── datasets/                     # Leitores de data/processed/ usando apenas biblioteca padrão
│   ├── app/                          # Sessões (simulada e real), comparação, playback, configuração e exportação
│   └── ui/                           # Janela principal, painel de configuração, mapa QPainter, gráficos e player
└── tests/                            # Testes unitários, de integração e de arquitetura de camadas
```

### 7.2 Divisão em Módulos (M1 a M5)

| Módulo | Escopo Principal | Pacotes sob Responsabilidade |
|---|---|---|
| **M1 — Grafo Unificado e Núcleo** | Estrutura `Graph` com máscara de isolamento, BFS, DFS, componentes conexos, Dijkstra, alocação iterativa de vértices, geometria, grade espacial, rotas aéreas, cenários e sementes. | `core/graph/`, `world/`, `core/seeds.py`, `core/errors.py` |
| **M2 — Análise de Redes e Benchmark** | Grau, agrupamento local e global, intermediação aproximada de Brandes, comunidades por propagação de rótulos, pontes e articulações de Tarjan, métricas SEIR e benchmark com NetworkX. | `core/analysis/`, `benchmarks/` |
| **M3 — Motor de Simulação** | `SimulationConfig` imutável, calibração de $\beta$ por bisseção, transições SEIRD, isolamento e vacinação automáticos, `EpidemicEngine`, `StateBuffer`, `Timeline` e `SimulationSession`. | `core/epidemic/`, `core/timeline/`, `app/simulation_session.py` |
| **M4 — Dados e Comparação Real** | Script `prepare_data.py`, tabela de apelidos, geração de `data/processed/`, leitores `datasets/`, `RealTimeline`, `RealSession` e comparação simulado $\times$ real. | `data/`, `datasets/`, `app/real_session.py`, `app/comparison.py` |
| **M5 — Interface, Mapa e Saída** | Telas em `PySide6`, mapa com `QPainter`, curvas com `pyqtgraph`, player, `SimulationThread`, painel de resultados, salvar/carregar JSON, exportação CSV/PNG e executável. | `ui/`, `app/playback.py`, `app/panel_metrics.py`, `app/config_io.py`, `app/export.py`, `scripts/` |

### 7.3 Etapas do Cronograma de Execução
1. **Etapa 1 — Contratos e Base de Dados:** Definição das interfaces entre camadas (`Graph`, `Timeline`, `SimulationConfig`), configuração da suíte de testes (`pytest` e `ruff`) e execução do pipeline de dados gerando `data/processed/`.
2. **Etapa 2 — Implementação dos Módulos:** Construção do grafo global unificado e algoritmos de busca/caminho mínimo (M1), algoritmos de análise e benchmark (M2), motor SEIRD com intervenções e calibração (M3), sessões de dados reais (M4) e componentes visuais da interface (M5).
3. **Etapa 3 — Integração e Benchmark:** Integração das sessões simulada e real à interface gráfica, calibração sobre o grafo completo e coleta das medições de desempenho em `benchmarks/bench_grafo.py`.
4. **Etapa 4 — Validação Final e Entrega:** Verificação dos casos de referência, geração do executável Windows com `PyInstaller`, consolidação do relatório técnico no formato SBC (LaTeX) e gravação do vídeo demonstrativo.

---

## 8. Limitações do Modelo

1. **Malha aérea estática:** A base pública de rotas do OpenFlights reflete o retrato estático de junho de 2014, sendo aplicada uniformemente às quatro pandemias sem modelar fechamentos dinâmicos de fronteiras.
2. **População de ano único:** Os dados populacionais do OWID (~2022) são usados como referência única para todos os surtos analisados.
3. **Países sem rota aérea:** Entidades sem rotas internacionais registradas no OpenFlights permanecem isoladas na malha aérea.
4. **Grau médio em países no piso ($n_{\min} = 12$):** Para microestados fixados no piso de 12 vértices, o grau médio interno fica limitado superiormente a $\min(\bar{d}, 11)$.
5. **Isolamento simétrico:** A máscara de isolamento desativa todas as arestas do vértice, não distinguindo transmissão intradomiciliar durante o período isolado.
6. **Séries reais apenas com acumulados:** Como os datasets de COVID-19, Ebola e H1N1 não trazem série histórica de recuperados, o mapa do fluxo real exibe a intensidade de casos acumulados por 100 mil habitantes.
