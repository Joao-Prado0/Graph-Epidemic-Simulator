# Documento de Casos de Uso — Simulador de Epidemias em Redes

Tema 7, Teoria dos Grafos — PUC Minas

Este documento descreve os casos de uso da aplicação desktop nos dois fluxos do sistema: o **fluxo de simulação**, em que o usuário configura um cenário epidêmico e assiste à propagação sobre o grafo global, e o **fluxo de pandemias reais**, em que o usuário reproduz surtos históricos sobre o mesmo grafo. Os diagramas de casos de uso são inseridos nas áreas indicadas, gerados no PlantText.

---

## 1. Atores

| Ator | Tipo | Descrição |
|---|---|---|
| Usuário | Principal | Estudante ou professor avaliador que explora cenários e observa a propagação. Não precisa de conhecimento técnico para operar a interface. |
| Sistema de arquivos | Secundário | Armazenamento local usado para salvar e carregar configurações em JSON e para gravar os resultados exportados (CSV e PNG). |

Isolamento e vacinação não são ações do usuário. São decididos pelo próprio sistema, de forma aleatória e simulando comportamento realista (RF05, RF06, RN02). Por isso aparecem como comportamento do sistema nos casos de uso, e não como atores ou casos de uso separados.

---

## 2. Fronteira do sistema

O sistema é a aplicação desktop com três abas de nível superior: **Início**, **Simulação** e **Pandemias reais**. A aba Início (Tela 1) oferece a escolha entre os dois fluxos. A aba Simulação contém a configuração (Tela 2) e a execução (Tela 5), com as telas de gráficos (Tela 7) e exportação (Tela 13). A aba Pandemias reais contém a seleção de surto (Tela 8) e a visualização do surto (Tela 9).

Os dois fluxos compartilham o mesmo grafo global (RN05). A diferença entre eles é o cenário: demonstrativo, pelo modelo epidemiológico, ou real, pelos dados históricos.

---

## 3. Fluxo de simulação

### 3.1. Diagrama de casos de uso — Fluxo de simulação

**[ESPAÇO RESERVADO PARA O DIAGRAMA DE CASOS DE USO DO FLUXO DE SIMULAÇÃO — inserir imagem gerada no PlantText]**

*Figura 1 — Diagrama de casos de uso do fluxo de simulação.*

### 3.2. Casos de uso

| ID | Caso de uso | Ator | Pré-condição | Fluxo principal | Pós-condição | Requisitos |
|---|---|---|---|---|---|---|
| UC01 | Abrir fluxo de simulação | Usuário | Aplicação aberta | 1. Usuário clica em "Abrir fluxo" no card Simulação da aba Início. 2. Sistema exibe a Tela 2 (configuração). | Tela de configuração exibida | RF25 |
| UC02 | Configurar cenário epidêmico | Usuário | Configuração ainda não iniciada | 1. Usuário define R0 (slider ou campo numérico). 2. Define a taxa de saída γ, a mortalidade e o período de incubação. 3. Escolhe o nível de intervenção (Baixo, Médio, Alto ou Nenhum). 4. Escolhe a distribuição geográfica (Global ou Regional, Ebola). 5. Informa a semente. 6. Define o paciente zero (UC04). | Parâmetros válidos guardados na configuração | RF01, RF23, RN01 |
| UC03 | Calibrar β | Usuário | R0 informado | 1. Usuário clica em "Calibrar β". 2. Sistema calcula β por bisseção sobre o grafo gerado. 3. Sistema exibe o β calibrado e o erro em relação ao R0 alvo. | β calibrado exibido na faixa de status | RF01 (B2) |
| UC04 | Definir paciente zero | Usuário | Configuração em edição | 1. Usuário escolhe "Aleatório" (sorteio no início) ou "Manual". 2. No modo manual, informa o país e o número do vértice, ou usa "Sortear vértice". | Paciente zero definido | RF03 |
| UC05 | Salvar configuração | Usuário, Sistema de arquivos | Configuração válida | 1. Usuário clica em "Salvar configuração". 2. Sistema grava os parâmetros em um arquivo JSON escolhido pelo usuário. | Arquivo JSON gravado | RF07 |
| UC06 | Carregar configuração | Usuário, Sistema de arquivos | Arquivo JSON existente e válido | 1. Usuário clica em "Carregar configuração" (na Tela 1 ou na Tela 2). 2. Sistema lê o arquivo e valida os parâmetros. 3. Sistema preenche a configuração. | Configuração carregada | RF07, RN01 |
| UC07 | Iniciar simulação | Usuário | Configuração válida | 1. Usuário clica em "Iniciar simulação". 2. Sistema congela a configuração, gera o grafo com a semente informada e grava o dia 0. 3. Sistema exibe a Tela 5. | Simulação em execução; parâmetros travados | RF02, RF03, RN01, RN03 |
| UC08 | Controlar reprodução | Usuário | Simulação iniciada | 1. Usuário usa Play e Pausar. 2. Usa −1d e +1d para avançar ou recuar um dia. 3. Escolhe a velocidade (×1, ×2, ×5, ×10). 4. Move o controle deslizante de dias. | Reprodução ajustada; o rumo da epidemia não muda | RF04, RF11 |
| UC09 | Visualizar mapa da propagação | Usuário | Simulação iniciada | 1. Sistema pinta cada país pelo status dominante do dia (S, E, I, R, D ou Isolado). 2. Usuário usa zoom (+, −, roda do mouse), arrasta o mapa e clica em "Ajustar mapa". 3. Usuário passa o cursor sobre um país e vê o resumo nele. 4. Vértices aparecem quando o país ocupa pelo menos 40 px na tela. | Mapa atualizado conforme o dia | RF12, RF22 |
| UC10 | Acompanhar painel de resultados | Usuário | Simulação iniciada | 1. Sistema apresenta, no dia atual, casos ativos, pico, dia do pico, duração, óbitos, letalidade e R0 efetivo. 2. Sistema apresenta as métricas de comparação RF14, quando disponíveis. | Painel atualizado conforme o dia | RF21, RF14 |
| UC11 | Visualizar curvas SEIRD | Usuário | Simulação iniciada | 1. Usuário clica em "Ver curvas (Tela 7)". 2. Sistema mostra as curvas de S, E, I, R e D, com marcador do dia atual e a contagem de cada estado. 3. Usuário volta com "Voltar ao mapa". | Curvas exibidas | RF24 |
| UC12 | Exportar resultados | Usuário, Sistema de arquivos | Simulação iniciada | 1. Usuário clica em "Exportar dados...". 2. Usuário escolhe CSV, PNG ou ambos e a pasta de destino. 3. Sistema grava series_temporais.csv e/ou curvas_epidemicas.png e mostra o status de cada arquivo. | Arquivos gravados no destino escolhido | RF08 |
| UC13 | Reiniciar simulação | Usuário | Simulação iniciada | 1. Usuário clica em "Reiniciar simulação". 2. Sistema descarta o histórico e destrava a configuração. 3. Sistema volta à Tela 2. | Configuração editável novamente | RN01 |
| UC14 | Calcular análise de rede | Usuário | Simulação iniciada | 1. Usuário clica em "Calcular análise de rede". 2. Sistema calcula grau, intermediação, agrupamento e comunidades em segundo plano. 3. Sistema apresenta os resultados no painel. | Métricas de rede exibidas sem bloquear a interface | RF18, RF19, RNF03 |

### 3.3. Comportamento do sistema durante a simulação (sem ação do usuário)

| Comportamento | Descrição | Requisitos |
|---|---|---|
| Isolamento automático | A cada dia, infectados são isolados com probabilidade fixa pelo nível escolhido. O isolamento dura um número fixo de dias e não altera a topologia do grafo. | RF05, RN02 |
| Vacinação automática | A partir de um dia definido pelo nível, suscetíveis são vacinados com fração diária fixa. A eficácia é de 80%. | RF06, RN02 |
| Transmissão e progressão | Os estados S, E, I, R e D evoluem a cada passo conforme o modelo. | RF02, RNF05 |

---

## 4. Fluxo de pandemias reais

### 4.1. Diagrama de casos de uso — Fluxo de pandemias reais

**[ESPAÇO RESERVADO PARA O DIAGRAMA DE CASOS DE USO DO FLUXO DE PANDEMIAS REAIS — inserir imagem gerada no PlantText]**

*Figura 2 — Diagrama de casos de uso do fluxo de pandemias reais.*

### 4.2. Casos de uso

| ID | Caso de uso | Ator | Pré-condição | Fluxo principal | Pós-condição | Requisitos |
|---|---|---|---|---|---|---|
| UC15 | Abrir fluxo de pandemias reais | Usuário | Aplicação aberta | 1. Usuário clica em "Abrir fluxo" no card Pandemias reais da aba Início. 2. Sistema exibe a Tela 8 com a lista de surtos. | Lista de surtos exibida | RF25 |
| UC16 | Selecionar pandemia | Usuário | Lista de surtos exibida | 1. Usuário escolhe entre COVID-19, Ebola, H1N1 e SARS. 2. Clica em "Abrir". 3. Sistema carrega a série histórica já processada e exibe a Tela 9. | Pandemia carregada | RF09, RNF10 |
| UC17 | Visualizar incidência no mapa | Usuário | Pandemia carregada | 1. Sistema pinta cada país pela intensidade de casos acumulados por 100 mil habitantes, nas faixas da legenda. 2. Usuário usa zoom, arrasta o mapa e clica em "Ajustar mapa". | Mapa do dia de referência exibido | RF12, RF22 |
| UC18 | Reproduzir linha do tempo | Usuário | Pandemia carregada | 1. Usuário usa Play, Pausar, −1d, +1d e Reiniciar. 2. Escolhe a velocidade. 3. Seleciona a data de referência pela barra de dias. | Mapa, totais e data atualizados | RF11, RN04 |
| UC19 | Consultar país selecionado | Usuário | Pandemia carregada | 1. Usuário clica em um país no mapa. 2. Sistema mostra, na coluna direita, casos acumulados e óbitos acumulados naquela data. 3. Recuperados aparecem somente para a SARS; nos demais casos, o sistema informa "não disponível". | Totais do país exibidos | RF12, RN04 |
| UC20 | Comparar com modelo | Usuário | Pandemia carregada e simulação concluída | 1. Usuário clica em "Comparar com modelo". 2. Sistema alinha a curva simulada à curva real e calcula as métricas de comparação. 3. Se não houver simulação concluída, o painel informa "Indisponível". | Métricas RF14 exibidas | RF14, RN04 |
| UC21 | Voltar à lista de surtos | Usuário | Pandemia carregada | 1. Usuário clica em "← Todos os surtos". 2. Sistema volta à Tela 8. | Lista de surtos exibida | RF09 |

### 4.3. Comportamento do sistema no fluxo real

| Comportamento | Descrição | Requisitos |
|---|---|---|
| Sem isolamento e sem vacinação | Os dados históricos já refletem as medidas tomadas na época. Nenhum isolamento ou vacinação é simulado neste fluxo. | RN02 |
| Dados já processados | O sistema lê apenas os arquivos processados. A preparação dos datasets acontece fora da aplicação. | RNF10 |
| Aviso de dados ausentes | Se a série de uma pandemia não estiver disponível, o sistema informa a pendência em vez de falhar. | RNF08 |

---

## 5. Rastreabilidade entre casos de uso e requisitos

| Requisito | Casos de uso |
|---|---|
| RF01 | UC02, UC03 |
| RF02 | UC07 |
| RF03 | UC04, UC07 |
| RF04 | UC08 |
| RF05 | Comportamento de isolamento (3.3) |
| RF06 | Comportamento de vacinação (3.3) |
| RF07 | UC05, UC06 |
| RF08 | UC12 |
| RF09 | UC16, UC21 |
| RF11 | UC08, UC18 |
| RF12 | UC09, UC17, UC19 |
| RF14 | UC10, UC20 |
| RF18 | UC14 |
| RF19 | UC14 |
| RF21 | UC10 |
| RF22 | UC09, UC17 |
| RF23 | UC02 |
| RF24 | UC11 |
| RF25 | UC01, UC15 |
| RN01 | UC02, UC06, UC07, UC13 |
| RN02 | UC17, UC18 e comportamentos 3.3 e 4.3 |
| RN04 | UC18, UC19, UC20 |
| RN05 | Seção 2 |
| RNF03 | UC14 |
| RNF10 | UC16 |

---

## 6. Observações sobre a implementação atual

As diferenças abaixo entre a documentação de requisitos e a aplicação foram identificadas na versão atual, e devem ser consideradas ao apresentar os diagramas.

1. **Paciente zero (RF03).** A documentação prevê a escolha manual por clique no mapa. A aplicação oferece a escolha por país e número do vértice, e o sorteio aleatório. A seleção por clique não foi implementada.
2. **Inspeção de vértice (RF26).** A consulta de estado e métricas de um vértice individual não foi implementada. O mapa mostra os vértices pelo status, sem inspeção por clique.
3. **Análise de rede (RF18 a RF20).** As métricas são calculadas pelo botão "Calcular análise de rede" e exibidas no painel. Não há tela própria de análise de rede.
4. **Comparação com dados reais (RF14).** A comparação aparece como botão e painel no fluxo real, e depende de uma simulação concluída.
5. **Geração de rede alternativa (RF27).** Não implementada; é um adendo opcional da documentação.

---

## Apêndice A — Código PlantUML sugerido para o PlantText

Os trechos abaixo podem ser colados no PlantText para gerar os dois diagramas. Ajuste os nomes conforme o relatório final.

### A.1. Fluxo de simulação

![Diagrama de casos de uso do fluxo de simulação](<fluxo de simulação.png>)

### A.2. Fluxo de pandemias reais

![Diagrama de casos de uso do fluxo de pandemias reais](<fluxo de pandemias reais.png>)
