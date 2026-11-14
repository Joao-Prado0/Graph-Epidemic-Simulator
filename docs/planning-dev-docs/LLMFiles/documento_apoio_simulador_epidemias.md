# Simulador de Epidemias em Redes

Documento de apoio ao projeto – Teoria dos Grafos (Tema 7)

*Versão 0.8 – revisão do grupo – 14/11/2026*

**Para que serve este documento.** É material de apoio interno do grupo (5 integrantes): reúne o que já foi discutido e decidido, as propostas em avaliação e os requisitos. O relatório oficial (LaTeX, template SBC, 12 a 15 páginas) será escrito pelo grupo; este texto serve de base e pode ser reaproveitado nele. Itens marcados como **proposta** ainda não foram validados pelo grupo. Itens marcados como **[pendente]** serão resolvidos durante a implementação ou dependem de terceiros.

---

## 1. Contexto e enunciado

O trabalho prático pede uma ferramenta computacional que resolva um problema aplicado por meio da modelagem, implementação e análise de grafos, com interface de interação, avaliação dos resultados, análise de complexidade e discussão de limitações. O grupo escolheu o tema 7: Simulador de Epidemias em Redes, isto é, representar uma rede de indivíduos (ou regiões) e simular a propagação de doenças, com ajuste de parâmetros como taxa de contágio, recuperação e isolamento.

### 1.1 Restrições e entregas exigidas pelo enunciado

- Prazo: 22/11, até as 23:59, pelo Canvas. Cada membro do grupo deve entregar uma cópia; quem não entregar recebe nota zero.
- Entrega em um .zip com o código-fonte, o código-fonte do relatório (.tex) e o PDF do relatório.
- Relatório em LaTeX no template oficial da SBC, entre 12 e 15 páginas, contextualizando a ideia, a modelagem (com diagramas UML), os resultados e as telas, e indicando o que cada membro fez.
- Repositório Git com histórico de desenvolvimento; commits individuais serão avaliados.
- Apresentação oral de 10 minutos com demonstração e slides, com participação de todos os membros.
- Vídeo de 12 a 18 minutos mostrando o funcionamento e as features produzidas por cada aluno.
- É proibido usar bibliotecas prontas para criar e processar o grafo (como NetworkX), exceto para comparação de performance.
- Só são avaliadas entregas com todos os itens; a falta de um deles resulta em nota zero. Cópias são zeradas.

---

## 2. Definição do problema e escopo

### 2.1 Problema

Entender como uma doença se espalha depende da estrutura de contatos entre as pessoas e do comportamento da própria doença. Redes com hubs, aglomerados e poucas conexões entre comunidades produzem epidemias muito diferentes, e medidas como isolamento e vacinação têm efeitos que variam conforme quem é isolado ou vacinado. A ferramenta deve tornar esse comportamento visível e explorável, usando algoritmos de grafos para modelar a propagação e analisar a rede.

### 2.2 Objetivos

- Simular a propagação de uma epidemia sobre um grafo, com parâmetros definidos pelo usuário antes de iniciar (fluxo de simulação), sobre o mesmo grafo global usado no fluxo de pandemias reais.
- Reproduzir visualmente pandemias reais a partir de datasets públicos (fluxo de pandemias reais), sobre o mesmo grafo global do fluxo de simulação, com os estados agregados por país.
- Aplicar e analisar algoritmos de grafos (busca, caminhos mínimos, centralidades, comunidades, pontes) no contexto da epidemia, com análise de complexidade.
- Apresentar tudo em uma aplicação desktop com visual inspirado no jogo Plague Inc: pontos em um mapa que mudam de cor conforme o contágio. A inspiração é apenas visual, não de comportamento.

### 2.3 Princípio de funcionamento: demonstrativo, não interativo

- O usuário configura o cenário antes de iniciar a simulação; depois, apenas assiste, sem alterar o rumo da epidemia.
- Os parâmetros ficam travados após o início; para mudar algo, reinicia-se.
- Os dois fluxos compartilham o mesmo grafo global; a diferença entre eles é apenas o cenário: demonstrativo (modelo epidemiológico) ou real (dados históricos).
- Os controles de reprodução (iniciar, pausar, velocidade, reiniciar) continuam disponíveis, pois não alteram a epidemia e são úteis na apresentação e no vídeo.
- Isolamento e vacinação são decididos pelo sistema, de forma aleatória e simulando comportamento realista, sem controle do usuário. A intenção é limitar a complexidade de uso e de implementação.
- Decidido: o motor simula e grava o estado de cada vértice a cada passo, e a interface apenas reproduz com linha do tempo. Assim, os dois fluxos usam o mesmo player (dados simulados ou dados reais).

### 2.4 Dentro do escopo

- Aplicação desktop em Python, com executável.
- Estrutura de grafo e algoritmos implementados pelo grupo.
- Grafo global de vértices agrupados por país, com conexões geométricas internas e arestas entre países pelas rotas aéreas.
- Modelo epidemiológico por compartimentos (S, E, I, R e D), com flags de isolado e vacinado, e isolamento e vacinação automáticos (aleatórios, sem controle do usuário).
- Quatro pandemias/surtos reais (COVID-19, Ebola, H1N1 e SARS) e um grafo de regiões construído sobre eles.
- Gráficos de resultados, métricas da rede e benchmark de desempenho.

### 2.5 Fora do escopo

- Previsão epidemiológica com validade científica ou uso em decisões reais de saúde pública; a ferramenta é um simulador didático.
- Modelos de mobilidade detalhados (rotas individuais, horários) e ajuste automático de parâmetros aos dados reais (este último pode entrar como extra).
- Versão web ou mobile.
- Alterar parâmetros ou intervir na epidemia depois que a simulação começa; escolha, pelo usuário, de quem é isolado ou vacinado.
- Geradores de rede além da geométrica aleatória (extra opcional, para quem quiser estudar e implementar).

### 2.6 Usuários

Estudantes e o professor avaliador, que usam a ferramenta para explorar cenários e verificar a correção da implementação. Não é preciso conhecimento técnico para operar a interface.

---

## 3. Decisões e propostas até agora

### 3.1 Decidido pelo grupo

| Tema | Decisão |
| --- | --- |
| Tema | Tema 7: Simulador de Epidemias em Redes. |
| Plataforma | Aplicação desktop, código em Python, com uma biblioteca Python para a interface e geração de executável. |
| Visual | Inspirado no Plague Inc. No fluxo de simulação, o polígono de cada país é pintado pelo status dominante do dia (uma cor por status: S, E, I, R, D e isolado). No fluxo real, o polígono é pintado pela intensidade de casos acumulados por 100 mil habitantes (seção 3.5). Os vértices aparecem somente quando o país ocupa, na tela, uma largura de pelo menos 40 px; abaixo de 36 px são ocultados. |
| Fluxos | (1) Simulação, com parâmetros como mortalidade, contágio, recuperação e nível de isolamento definidos antes de iniciar; (2) visualização de pandemias reais. |
| Grafo unificado | Os dois fluxos usam o mesmo grafo: cada país é um conjunto de vértices (indivíduos) em quantidade proporcional à população (fórmula da seção 3.3), com conexões internas por proximidade geométrica e arestas entre países pelas rotas aéreas do OpenFlights. A diferença entre os fluxos é apenas o cenário (demonstrativo ou real). |
| Comportamento | Demonstrativo: o usuário configura antes de iniciar e depois assiste, sem alterar o rumo da simulação. A inspiração no Plague Inc é apenas visual. |
| Rede (simulação) | Geométrica aleatória. As demais (Erdős–Rényi, Barabási–Albert, Watts–Strogatz) ficam como extra opcional. |
| Isolamento e vacinação | Automáticos e aleatórios, simulando comportamento realista; sem controle do usuário. |
| Comunidades | Detecção por propagação de rótulos (opção mais simples). |
| Stack | Stack tecnológica confirmada (seção 3.2); o professor liberou o uso de NumPy no núcleo (04/11/2026). |
| Dados | Datasets do Kaggle com informações de pandemias reais (seção 3.4), mais OWID e OpenFlights. |
| Equipe | 5 integrantes; o relatório oficial em LaTeX é escrito pelo grupo. |
| Nomes | Código em inglês; documentação em português (decisão de 03/11/2026). |
| Repositório | Público. Os dados processados são licenciados sob ODbL 1.0; os CSVs brutos do Kaggle não são versionados (decisão de 03/11/2026). |

### 3.2 Stack tecnológica confirmada

| Componente | Escolha |
| --- | --- |
| Linguagem | Python 3.12 (mesma versão para todos os integrantes). |
| Interface | PySide6 (Qt). Mapa e vértices desenhados com QPainter, em lote, para suportar milhares de pontos animados. |
| Gráficos | pyqtgraph, para as curvas em tempo real integradas à interface Qt. |
| Núcleo do grafo | Estrutura própria (lista de adjacência), com NumPy para arrays de estado e uma representação CSR onde o desempenho exigir. NumPy liberado pelo professor (04/11/2026). NetworkX apenas no benchmark. |
| Simulação | Executada em thread separada (QThread), comunicando-se com a interface por sinais do Qt. |
| Mapa | GeoJSON do mundo (Natural Earth, convertido de shapefile uma vez antes do processamento), desenhado com QPainter. |
| Empacotamento | PyInstaller. Nuitka fica como alternativa caso haja problema de build ou desempenho. |
| Testes | pytest, cobrindo o núcleo do grafo e os algoritmos. |
| Ambiente | Ambiente virtual (venv) com requirements.txt versionado no Git. |

### 3.3 Propostas em avaliação e parâmetros de alocação

| Tópico | Proposta |
| --- | --- |
| Modelo | Compartimentos S, E, I, R e D, com flags independentes de isolado e vacinado, em passos de um dia. Transições pela forma exponencial, 1 − exp(−taxa). Isolamento automático: a cada passo, cada vértice infectado tem uma probabilidade de se isolar por alguns dias (arestas desativadas temporariamente). Vacinação automática: a partir de um dia definido, uma fração dos suscetíveis é vacinada por dia; o vacinado passa a R, com eficácia de 0,8. O nível escolhido (baixo, médio ou alto) é convertido em constantes fixas. |
| Player único | Decidido: o motor simula e grava o estado de cada vértice a cada passo; a interface apenas reproduz, com linha do tempo. Os dois fluxos usam o mesmo player. |
| Grafo unificado | Um único grafo para os dois fluxos. Cada país é um conjunto de vértices (indivíduos), em quantidade dada pela fórmula do cenário global. Dentro de cada país, os vértices se conectam por proximidade geométrica (raio pela fórmula r ≈ √(d̄ / (π · ρ)), com d̄ entre 6 e 10, e grade espacial para não comparar todos os pares). Entre países, as arestas vêm das rotas aéreas do OpenFlights (seção 3.6). No fluxo real, os estados dos vértices são agregados por país e comparados com a série real. |
| Cenário global | Número de vértices por país proporcional à população de forma sublinear, com orçamento total fixo (N_total): a alocação é iterativa. Parâmetros: n_min = 12, α = 0,5 e N_total provisório de 8.000 (faixa de 5 mil a 10 mil), a confirmar por benchmark. Países cuja parcela fica abaixo de n_min são fixados em n_min, e o orçamento restante é redistribuído entre os demais, com arredondamento pelo maior resto para que a soma seja exatamente N_total. O grau médio efetivo é min(d̄, n_i − 1), porque países no piso têm estrutura quase completa (limitação a registrar). O ranking por posição (Índia 225, China 224...) fica apenas como alternativa de demonstração, não como regra. |
| Cenário regional (Ebola) | Os países que atingem 10 casos acumulados nos primeiros 60 dias a partir do dia 0 do surto recebem a redistribuição do orçamento de vértices; os demais ficam no piso n_min. O grafo global é mantido. O prazo de 60 dias é configurável. |
| Escala | Meta preliminar de 5 a 10 mil vértices por padrão (N_total provisório de 8.000). Definir por benchmark (1 mil, 5 mil, 10 mil, 50 mil) na máquina mais fraca do grupo. |

### 3.4 Datasets do Kaggle

| Dataset | Descrição | Uso previsto |
| --- | --- | --- |
| COVID-19 | Casos confirmados e mortes por dia, por país (JHU, acumulados). Recuperados não são usados (dados, D12). | Pandemia longa, global. Principal dataset do fluxo real. |
| Ebola 2014–2016 | Casos e mortes acumulados, por país e dia (29/08/2014 a 23/03/2016). | Surto regional (África Ocidental); cenário local. |
| H1N1 2009 | Casos e mortes por país, dia a dia, de 24 de abril a 6 de julho de 2009. | Pandemia curta; boa para demonstração rápida. |
| SARS 2003 | Casos, mortes e recuperados por país, de 17/03 a 11/07/2003. Único conjunto com recuperados. | Surto bem delimitado. |
| HIV/AIDS | Descartado: não é série de propagação diária. | — |

Nenhum desses datasets traz as arestas do grafo; elas vêm do OpenFlights (rotas aéreas). Os nomes de país são convertidos para ISO3 com o OWID, que também fornece população. Colunas, período e granularidade foram conferidos nos arquivos (documento de dados, seção 3).

### 3.5 Regras de cor no mapa

**Fluxo de simulação:** cada país é pintado pelo status dominante no dia, calculado a partir dos vértices do país (o status com mais vértices, com uma cor por status: S, E, I, R, D e isolado).

**Fluxo de pandemias reais (decisão de 03/11/2026):** cada país é pintado pela intensidade de casos acumulados por 100 mil habitantes, em escala sequencial. O limiar de 10 por 100 mil (equivalente a 0,01% da população) é o início da escala. Os óbitos aparecem como indicador separado.

**Motivo:** as séries reais trazem só acumulados, sem casos ativos. Com recuperados ausentes em COVID, Ebola e H1N1, uma regra de status dominante calculada por I = 1 − D − R deixaria o país sempre na cor de I. A intensidade mostra a magnitude da epidemia em cada país sem depender de um status inferido.

### 3.6 Fonte das arestas

As arestas entre países vêm das rotas aéreas do OpenFlights. Cada par de países (não dirigido) recebe:

- um número bruto de rotas (`routes`), gravado no `edges.csv` pelo script de dados;
- `k_ij = min(k_max, ceil(routes_ij / escala))` arestas entre vértices escolhidos ao acaso, com semente fixa;
- um peso de contágio `w_ij = log(1 + routes_ij) / log(1 + max routes)`, com probabilidade de transmissão `p_ij = 1 − exp(−β · w_ij)`;
- um custo de caminho `−ln(p_ij)` para o Dijkstra (distância efetiva de Brockmann & Helbing, 2013).

Rotas com codeshare, rotas domésticas e rotas entre um território agregado e sua metrópole são descartadas. Países sem rota ficam isolados, com aviso na interface.

---

## 4. Requisitos

Prioridades: Essencial (necessário para a entrega), Desejável (agrega valor se houver tempo) e Extra (bônus). Os módulos referem-se à divisão proposta na seção 5; o responsável por cada módulo será definido pelo grupo.

### 4.1 Requisitos funcionais – fluxo de simulação

| ID | Requisito | Prioridade | Módulo |
| --- | --- | --- | --- |
| RF01 | Configurar, antes de iniciar, os parâmetros da doença: R0 (a partir dele, o sistema calibra β), taxa total de saída de I (γ), taxa de mortalidade (divide a saída de I entre óbito e recuperação), período de incubação e nível de intervenção. Os parâmetros ficam travados após o início. | Essencial | M3, M5 |
| RF02 | Gerar o grafo unificado: países com vértices proporcionais à população, conexões internas geométricas e arestas entre países por rotas aéreas, com semente configurável e tamanho definido por benchmark. | Essencial | M1 |
| RF03 | Definir o(s) paciente(s) zero, de forma manual (clique no mapa) ou aleatória. | Essencial | M3, M5 |
| RF04 | Controlar a reprodução da simulação: iniciar, pausar, retomar, avançar um passo, reiniciar e ajustar a velocidade (controles que não alteram o rumo da epidemia). | Essencial | M3, M5 |
| RF05 | Isolamento automático: o sistema isola vértices infectados de forma aleatória, simulando comportamento realista (probabilidade por passo e duração fixas, derivadas do nível configurado), sem controle do usuário sobre quem é isolado. Vale apenas para o fluxo de simulação. | Essencial | M3 |
| RF06 | Vacinação automática: o sistema vacina, de forma aleatória, uma fração dos suscetíveis por passo a partir de um dia definido, conforme a configuração prévia. Vacinados passam a R com a flag de vacinado. Vale apenas para o fluxo de simulação. | Desejável | M3 |
| RF07 | Salvar e carregar a configuração de um cenário, em JSON (`app/config_io.py`). | Desejável | M5 |
| RF08 | Exportar resultados da simulação: CSV (`app/export.py`) e imagem dos gráficos (`ui/charts_view.py`). | Desejável | M5 |
| RF27 | Outros geradores de rede (Erdős–Rényi, Barabási–Albert, Watts–Strogatz) para as conexões internas de cada país, com seletor simples de nomes amigáveis. Adendo opcional para quem implementar o módulo. | Extra | M4 |

### 4.2 Requisitos funcionais – fluxo de pandemias reais

| ID | Requisito | Prioridade | Módulo |
| --- | --- | --- | --- |
| RF09 | Selecionar a pandemia a visualizar entre as disponíveis (COVID-19, Ebola, H1N1, SARS). O carregamento dos dados é tarefa interna (RNF10), não ação do usuário. | Essencial | M4, M5 |
| RF10 | Construir o grafo unificado a partir das rotas aéreas (arestas entre países ligando vértices dos dois países). | Essencial | M1 |
| RF11 | Reproduzir a evolução temporal com linha do tempo (play, pausa e seleção de data). | Essencial | M5 |
| RF12 | Exibir casos, mortes e recuperados por país no mapa (cor do polígono pela intensidade de casos por 100 mil habitantes, seção 3.5) e em gráficos. | Essencial | M4, M5 |
| RF13 | Montar o cenário global, para os dois fluxos (simulação e pandemias reais), com vértices por país proporcionais à população (fórmula da seção 3.3). | Essencial | M1 |
| RF14 | Comparar a curva simulada pelo modelo com a curva real, agregando os estados dos vértices por país. Casos são comparados como I + R + D e mortes como D; recuperados só no SARS. | Extra | M3, M4, M5 |

### 4.3 Requisitos funcionais – grafos e análise

| ID | Requisito | Prioridade | Módulo |
| --- | --- | --- | --- |
| RF15 | Estrutura própria de grafo com inserção e remoção de vértices e arestas, com pesos. | Essencial | M1 |
| RF16 | Busca em largura e em profundidade; componentes conexos. | Essencial | M1 |
| RF17 | Caminho mínimo (Dijkstra), por exemplo para tempo de chegada da doença entre regiões. | Essencial | M1 |
| RF18 | Métricas de rede: grau, ao menos uma centralidade (intermediação ou proximidade) e coeficiente de agrupamento (local por vértice e média global). | Essencial | M2 |
| RF19 | Detecção de comunidades por propagação de rótulos, com semente fixa para resultado reproduzível. | Desejável | M2 |
| RF20 | Pontos de articulação e pontes (algoritmo de Tarjan, em uma única DFS). | Desejável | M2 |
| RF21 | Painel de métricas da epidemia: percentual infectado, pico, duração, mortes e R0 efetivo, estimado pelo crescimento inicial com a forma SEIR, (1 + r/σ)(1 + r/γ). A estimativa vale só durante o crescimento e é indicada como efetiva quando há isolamento ou vacinação. | Essencial | M2, M5 |

### 4.4 Requisitos funcionais – interface

| ID | Requisito | Prioridade | Módulo |
| --- | --- | --- | --- |
| RF22 | Mapa com polígonos de países coloridos pelo status dominante (simulação) ou pela intensidade de casos (pandemias reais), e, com zoom suficiente, vértices coloridos pelo status do próprio vértice (simulação), com animação da propagação. Os vértices são exibidos a partir de 40 px de largura do país na tela e ocultados abaixo de 36 px. | Essencial | M5 |
| RF23 | Painel de controles com campos e sliders para os parâmetros. | Essencial | M5 |
| RF24 | Gráficos em tempo real das curvas S, E, I, R e D. | Essencial | M5 |
| RF25 | Tela inicial para escolher entre os dois fluxos. | Essencial | M5 |
| RF26 | Zoom e pan no mapa; inspeção de vértice (estado e métricas). | Desejável | M5 |

### 4.5 Requisitos não funcionais

| ID | Requisito | Prioridade |
| --- | --- | --- |
| RNF01 | Implementação em Python 3.12 com PySide6, aplicação desktop, sem bibliotecas prontas de grafos (exceto no benchmark). | Essencial |
| RNF02 | Animação fluida (meta preliminar a validar por benchmark: cerca de 5 mil vértices a pelo menos 20 quadros por segundo). | Essencial |
| RNF03 | Interface responsiva: a simulação roda em thread separada da interface. | Essencial |
| RNF04 | Geração de executável com PyInstaller (Nuitka como alternativa), ao menos para o sistema operacional do grupo. | Essencial |
| RNF05 | Reprodutibilidade: semente aleatória configurável, necessária porque rede, isolamento, vacinação e propagação de rótulos usam aleatoriedade. Mesma semente e mesmos parâmetros dão o mesmo resultado. | Essencial |
| RNF06 | Código modular em camadas, com testes unitários do núcleo do grafo e dos algoritmos. | Essencial |
| RNF07 | Git com commits individuais e frequentes por membro. | Essencial |
| RNF08 | Mensagens de erro claras (por exemplo, dataset inválido ou parâmetro fora da faixa). | Desejável |
| RNF09 | Análise de complexidade dos algoritmos e comparação de desempenho documentadas para o relatório. | Essencial |
| RNF10 | Dados pré-processados: o aplicativo só lê arquivos já processados, e a preparação dos datasets é feita fora dele. | Essencial |

### 4.6 Regras de negócio

| ID | Regra |
| --- | --- |
| RN01 | Os parâmetros ficam travados após o início da simulação; para alterá-los, é preciso reiniciar. |
| RN02 | Isolamento e vacinação existem apenas no fluxo de simulação. No fluxo de pandemias reais, os dados já refletem as medidas tomadas na época. |
| RN03 | Com a mesma semente e os mesmos parâmetros, a simulação produz o mesmo resultado. |
| RN04 | No fluxo de pandemias reais, a animação reproduz os dados reais, agregados por país; o modelo só entra na comparação opcional (RF14). |
| RN05 | Os dois fluxos usam o mesmo grafo; a diferença é o cenário. |

---

## 5. Divisão em módulos (proposta)

Base para discutir a divisão entre os 5 integrantes. Cada módulo deve render ao menos uma feature para mostrar no vídeo e commits individuais. O M5 concentra interface e resultados; pode ser dividido conforme as afinidades. **A atribuição de responsáveis é decisão do grupo e não consta deste documento.**

| Módulo | Nome | Escopo |
| --- | --- | --- |
| M1 | Núcleo do grafo e grafo unificado | Estrutura de dados, inserção e remoção, BFS, DFS, componentes conexos, Dijkstra; alocação de vértices por população, posições, conexões geométricas internas, arestas entre países, pesos, funções de probabilidade e custo, cenários; sementes e exceções próprias. |
| M2 | Análise de redes e benchmark | Centralidades, agrupamento (local e global), comunidades, pontos de articulação e pontes. Benchmark de desempenho (com NetworkX só aqui). |
| M3 | Motor de simulação | Modelo de compartimentos, calibração de β, parâmetros, isolamento e vacinação automáticos, gravação do histórico de estados. |
| M4 | Dados e comparação com dados reais | Script de preparação dos dados, geometria processada (GeoJSON), leitura dos processados, fluxo real e comparação com dados reais (RF14). |
| M5 | Interface, mapa e resultados | Janela, renderização inspirada no Plague Inc, tela de configuração prévia, player com linha do tempo, animações, gráficos, configuração salva e carregada (RF07), exportação (RF08), métricas do painel, testes, executável e consolidação de diagramas para o relatório. |

---

## 6. Pontos em aberto

**Dependem de terceiros ou de medição:**

- **Resolvido (04/11/2026):** o professor liberou NumPy no núcleo do grafo e uso de shapely no script de preparação de dados. O arquivo de arestas derivado do OpenFlights é versionado em `data/processed/edges.csv`, com licença ODbL e atribuição no relatório e no README.
- **[pendente]** Verificar que PySide6, pyqtgraph e PyInstaller instalam e rodam nas máquinas dos 5 integrantes, e fixar as versões no requirements.txt.
- **[pendente]** Conferir no protótipo, na máquina mais fraca do grupo, os valores de 40 px (entrada) e 36 px (saída) para exibição dos vértices.
- **[pendente]** Definir por benchmark: N_total (provisório, 8.000), β, k_max, escala e d̄.
- **[pendente]** Recontar as rotas e os países sem rota ao rodar o script de dados, com a tabela de apelidos completa.
- **[pendente]** Ler diretamente o artigo de Lipsitch et al. (2003) e conferir a faixa de R0 do SARS antes de citar.

**Decisões do grupo:**

- **Decidido (14/11/2026):** o campo de RF01 é γ, taxa total de saída de I (arquitetura, ponto 9.2, item 9).
- **[pendente]** Valor de M: número mínimo de vértices infectados por país para o dia 0 (modelagem, seção 7.2).
- **[pendente]** Definir os responsáveis por módulo.
- **[pendente]** Plano de desenvolvimento e cronograma (outro chat, depois do restante do planejamento).

**Itens da lista anterior já resolvidos e removidos deste ponto:** histórico gravado durante a execução (E2); rotas em arestas (D18); raio de conexão (fórmula A5); N_total, n_min e α (valores fixados, com N_total provisório); cenário regional (B4); limiar do dia 0 (B5); níveis de isolamento e vacinação (C5, provisórios); R0 pelo crescimento (B6); paciente zero (C6); colunas dos datasets (conferidas); HIV/AIDS (descartado); extras (C1, somente como opções futuras); regra de status dominante do fluxo real (substituída pela intensidade, A12).

---

## 7. Próximos passos do documento

- Casos de uso (diagrama e descrição), cobrindo os dois fluxos. Em elaboração por outro integrante.
- Diagramas UML (classes, componentes, sequência e atividades), preferencialmente em PlantUML ou Mermaid, incluindo a divisão do mapa em duas camadas (polígonos dos países e vértices). Em elaboração por outro integrante.
- Plano de desenvolvimento: responsabilidades por membro e cronograma até 22/11. Em outro chat, depois de definido o restante do planejamento.

Já concluídos: modelagem (revisão 2, 14/11/2026), documento de dados (versão 0.8) e arquitetura (versão 0.6).

---

## 8. Histórico de alterações

| Versão | Data | Mudanças |
| --- | --- | --- |
| 0.1 | 16/10/2026 | Primeira versão: contexto, escopo, propostas e requisitos. |
| 0.2 | 17/10/2026 | Stack tecnológica confirmada (seção 3.2). |
| 0.3 | 28/10/2026 | Sistema demonstrativo, com configuração antes de iniciar; só rede geométrica aleatória (demais como extra); isolamento e vacinação automáticos; RF09 reescrito; RF19 por propagação de rótulos; RNF05 passa a essencial; novos RNF10 e regras de negócio. |
| 0.4 | 29/10/2026 | Grafo unificado entre os dois fluxos: cada país é um conjunto de vértices proporcional à população, com conexões internas geométricas e arestas entre países pelas rotas aéreas (OpenFlights). |
| 0.5 | 03/11/2026 | Regra de renderização do mapa: polígono pelo status dominante e vértices a partir de 40 px (36 px para ocultar); seção 3.5 com a regra de status dominante do fluxo real. |
| 0.6 | 03/11/2026 | Correções: período do H1N1 (24/04 a 06/07/2009); COVID sem recuperados (D12); Python 3.12 para todos; alocação iterativa com total fixo, n_min = 12, α = 0,5 e N_total provisório de 8.000 (3.3); HIV descartado e colunas conferidas (3.4). Decisões de modelagem incorporadas: flags de isolado e vacinado; cor do fluxo real por intensidade (3.5, RF12, RF22); fonte das arestas (3.6); cenário regional (3.3); RF01, RF06, RF14 e RF21 atualizados (R0 efetivo SEIR, comparação por I + R + D e D). Módulos de RF07 e RF08 (4.1, 5). Pontos em aberto reorganizados (6). Repositório público e nomes em inglês (3.1). Arquitetura e modelagem marcadas como concluídas (7). |
| 0.7 | 03/11/2026 | Equipe de 5 integrantes; divisão em 5 módulos (seção 5): M6 incorporado ao M5 (resultados, RF07, RF08) e benchmark movido para o M2. Atribuições de RF07, RF08, RF14, RF21 e RF24 atualizadas. Arquitetura referenciada na versão 0.5. |
| 0.8 | 14/11/2026 | RF01: campo de γ como taxa total de saída de I; RF02, RF10 e RF13 passam ao M1 (construção do grafo unificado); M1 e M4 redefinidos na seção 5 (M1 com `world/`, sementes e erros; M4 com dados e comparação); valor de M do dia 0 pendente (seção 6); data da resposta do professor corrigida para 04/11/2026. |
