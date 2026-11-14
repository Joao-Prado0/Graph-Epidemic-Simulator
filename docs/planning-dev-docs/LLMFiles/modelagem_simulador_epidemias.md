# Modelagem do Simulador de Epidemias em Redes

Tema 7, Teoria dos Grafos. Versão de planejamento, revisão 2, 14/11/2026 (revisão 1, de 03/11/2026: incubação e γ corrigidos com as fontes do projeto; revisão 2: γ como entrada do usuário, dia 0 por vértices infectados, alocação iterativa, Natural Earth em GeoJSON, repositório público e resposta do professor em 04/11). Base para a implementação. Itens marcados como **[pendente]** serão resolvidos durante a implementação ou dependem de terceiros, e devem constar como pendentes nos documentos.

---

## 1. Escopo e princípio de funcionamento

O simulador é demonstrativo. Tem dois fluxos que compartilham o mesmo grafo:

- **Fluxo de simulação:** o usuário configura os parâmetros antes de iniciar (R0, taxa total de saída de I (γ), mortalidade, incubação e nível de intervenção). Depois, apenas assiste. Isolamento e vacinação são decididos pelo sistema, de forma aleatória, sem controle do usuário.
- **Fluxo de pandemias reais:** reproduz casos e mortes de quatro surtos (COVID-19, Ebola 2014–2016, H1N1 2009 e SARS 2003), agregados por país. Recuperados só existem no SARS.

Os parâmetros ficam travados após o início. Para mudar algo, reinicia-se. Os controles de reprodução (iniciar, pausar, retomar, avançar um passo, reiniciar e velocidade) continuam disponíveis.

A ferramenta é didática. Não tem validade epidemiológica nem deve ser usada em decisões de saúde pública.

---

## 2. Grafo unificado

### 2.1 Decisão

Os dois fluxos usam o mesmo grafo global. Cada país é representado por um conjunto de vértices (indivíduos), em quantidade proporcional à população. Dentro de cada país, os vértices se conectam por proximidade geométrica. Entre países, as arestas vêm das rotas aéreas do OpenFlights.

**Justificativa:** a comparação com dados reais exige a mesma granularidade. Um único motor reduz código, testes e erros. A diferença entre os fluxos fica apenas no cenário.

### 2.2 Tipo de grafo

- **Não direcionado.** Contato e transporte são de via dupla. A direção da infecção pertence ao estado dos vértices, não à aresta.
- A rota A→B e B→A do OpenFlights é somada em um único par não ordenado.

### 2.3 Alocação de vértices por país (cenário global)

Para cada país *i*, com população *p_i*:

```
n_i ∝ p_i^α, com soma igual a N_total (procedimento iterativo abaixo)
```

| Parâmetro | Valor | Situação |
|---|---|---|
| N_total | 8.000 | provisório, a confirmar por benchmark de desempenho visual (RNF02) |
| n_min | 12 | decidido |
| α | 0,5 | decidido |

**Total fixo.** A regra `max(n_min, …)` faria o total exceder N_total. Por isso a alocação é iterativa:

1. Calcular a alocação proporcional sobre o orçamento restante, considerando apenas os países que ainda não estão no piso.
2. Fixar em n_min os países cuja parcela ficou abaixo de n_min, e subtrair esse valor do orçamento.
3. Repetir até que nenhum país fique abaixo do piso.
4. Arredondar pelo método do maior resto, para que a soma seja exatamente N_total.

Testes: a soma é igual a N_total, cada país tem pelo menos n_min, e a alocação não decresce com a população.

**Ranking por posição** (Índia 225, China 224...) fica só como alternativa de demonstração.

### 2.4 Conexões internas por país (rede geométrica)

- Os vértices de cada país são sorteados dentro do polígono do país (Natural Earth 50m, versão 5.1.1).
- Dois vértices se conectam se a distância for menor que o raio *r*.
- O raio é calculado pelo grau médio alvo *d̄*:

```
r ≈ √(d̄ / (π · ρ))
```

onde ρ é a densidade de vértices do país e d̄ está entre 6 e 10 **[pendente: valor a definir por benchmark]**.

**Justificativa:** um raio fixo faria o grau médio variar com a densidade, tornando países grandes e pequenos estruturalmente diferentes.

**Grau efetivo em países pequenos.** Para países no piso, d̄ efetivo = min(d̄, n_i − 1). Limitação a registrar no relatório.

A busca de vizinhos usa grade espacial, para não comparar todos os pares.

### 2.5 Arestas entre países (rotas aéreas)

Para cada par de países (i, j) com `routes_ij` rotas no OpenFlights:

- **Descarte:** rotas com `codeshare = Y`, rotas domésticas (incluindo as entre um território agregado e sua metrópole) e rotas com aeroporto ausente.
- **Multiplicidade:**

```
k_ij = min(k_max, ceil(routes_ij / escala))
```

Cada uma das *k_ij* arestas liga dois vértices escolhidos uniformemente ao acaso, com semente fixa, um em cada país. **[pendente: k_max e escala a definir por benchmark]**

- **Peso normalizado:**

```
w_ij = log(1 + routes_ij) / log(1 + max routes)
```

Cada aresta herda `w_ij`.

**Justificativa:** o número de arestas cresce com o tráfego, com teto. O logaritmo reduz o domínio dos pares com muito tráfego.

### 2.6 Pesos: contágio e custo de caminho

- **Probabilidade de transmissão por aresta:**

```
p_ij = 1 − exp(−β · w_ij)
```

- **Custo de caminho (para Dijkstra):**

```
custo_ij = −ln(p_ij)      (com p limitado a 0,999)
```

Esta é a distância efetiva de Brockmann & Helbing (2013). Os custos são não negativos, e somar custos equivale a multiplicar probabilidades.

**Calibração de β.** O usuário informa o R0 (RF01). Antes de iniciar, o sistema gera o grafo, roda simulações curtas com valores de teste de β e ajusta β por bisseção até o R0 medido ficar próximo do informado. A fórmula analítica de Newman para redes, R0 ≈ T·(⟨k²⟩/⟨k⟩ − 1), serve só como verificação. A configuração é travada depois da calibração. O tempo de calibração entra no benchmark. As funções de probabilidade e custo recebem β como argumento e são chamadas pelo M3 depois da calibração; por isso o grafo guarda apenas o peso `w` (M1).

**Justificativa:** usar `routes` diretamente como custo inverteria a semântica. O arquivo `edges.csv` guarda `routes` bruto; as transformações são feitas pelo aplicativo.

### 2.7 Países sem rota

Os países sem nenhuma rota no OpenFlights ficam isolados na rede aérea, com aviso na interface. Não se criam arestas artificiais. A contagem exata sai do script de preparação de dados **[pendente: recontagem com a tabela de apelidos completa]**. O documento de dados, na versão 0.6, estima 216 com rota e 14 sem, sobre 230 entidades; o universo foi corrigido para 229 (ver seção 3.2), e a contagem precisa ser refeita.

**Limitação a registrar:** sem voos, a doença não sai do país pela via aérea.

### 2.8 Propriedades do grafo

- Estrutura: lista de adjacência, com vetor de arestas ativas (máscara) para o isolamento.
- Vértices: país, posição, estado epidemiológico, flag de isolamento, flag de vacinado e tempo restante de isolamento.
- Arestas: vértice de origem, vértice de destino, peso de contágio, custo de caminho.

---

## 3. Dados de entrada e universo de entidades

### 3.1 Fontes

- **OWID (owid-covid-data.csv):** tabela mestra de países (ISO3, população e atributos). Não entra no aplicativo.
- **OpenFlights (airports, routes, countries):** arestas entre países.
- **Natural Earth 50m, Admin 0 Countries (versão 5.1.1):** polígonos dos países, para posição dos vértices e centroides. Entrada convertida uma vez de shapefile para GeoJSON, por qualquer ferramenta, antes da execução do script (decidido).
- **Kaggle (quatro surtos):** séries diárias de casos, mortes e recuperados.

Todos os nomes de país são convertidos para ISO3 antes de qualquer cruzamento.

### 3.2 Universo de entidades

O OWID tem 237 códigos com continente preenchido, incluindo `OWID_CYN` (Norte do Chipre, população própria). Kosovo (`OWID_KOS`) não está entre esses 237, mas tem população e entra no modelo.

- **Universo:** 237 − 8 territórios agregados − 1 (`OWID_CYN`, agregado ao Chipre) + 1 (Kosovo) = **229 entidades**.
- Oito territórios são agregados ao país-mãe, porque no Natural Earth 50m não têm polígono próprio: Gibraltar ao Reino Unido; Bonaire, Saba e Santo Eustáquio aos Países Baixos; Tokelau à Nova Zelândia; Guadalupe, Guiana Francesa, Martinica, Mayotte e Reunião à França.
- Feições do Natural Earth sem entidade no modelo ficam de fora: Antártida, Terra Adélia, Heard e McDonald, Norfolk, Geórgia do Sul, Território Britânico do Oceano Índico, Somalilândia e Siachen.
- Ilhas Åland são agregadas à Finlândia.

### 3.3 Chave de junção e geometria

- Chave por `ISO_A3_EH` do Natural Earth, com fallback em `ADM0_A3`.
- Feições de um mesmo país são agregadas pelo código antes do cálculo de centroide.
- Países que cruzam o antimeridiano (Rússia, Fiji, EUA, Kiribati e Nova Zelândia) exigem tratamento específico no centroide.
- A escala 50m é usada porque cobre microestados.

### 3.4 Séries dos surtos

- Dias contínuos, com forward-fill para datas faltantes.
- Máximo acumulado (cummax) para corrigir quedas retroativas.
- Territórios agregados somam casos e mortes ao país-mãe.
- Recuperados só existem no SARS.

### 3.5 Fontes e licenças

Os dados seguem as licenças registradas na pesquisa de 03/11/2026:

- JHU CSSE e OWID: CC BY 4.0, com atribuição.
- Natural Earth: domínio público.
- OpenFlights: ODbL 1.0. Em repositório público, o arquivo de arestas deve ser licenciado sob ODbL, com aviso de origem e com o script de derivação publicado. **Repositório público (D25).**
- Datasets do Kaggle de imdevskp: sem licença explícita. Não versionar em repositório público; obter por script.

---

## 4. Modelo epidemiológico

### 4.1 Estados

Cinco estados epidemiológicos: **S, E, I, R, D**. Dois atributos ortogonais:

- **Isolado (flag):** booleano, independente do estado epidemiológico. Um vértice pode estar I e isolado ao mesmo tempo.
- **Vacinado (flag):** booleano, independente do estado. Vacinados passam ao estado R e recebem a flag de vacinado. Assim, o R natural é R com flag de vacinado desligada.

**Justificativa:** E faz a incubação ter efeito sobre a dinâmica. A flag de vacinado permite excluir vacinados da comparação com dados reais (seção 7.1), sem criar um estado V.

### 4.2 Passo de tempo

Um passo equivale a **um dia**. As séries reais são diárias.

Transições por passo, com a forma exponencial para manter a probabilidade entre 0 e 1:

```
P(E → I) = 1 − exp(−σ)
P(saída de I) = 1 − exp(−γ)
```

onde σ = 1/incubação e γ = taxa total de saída de I.

Cada saída de I vai para D com probabilidade igual à mortalidade, e para R com a probabilidade complementar.

**Justificativa:** esta divisão fecha a relação entre γ, mortalidade e os dois destinos, sem um γ separado para recuperação.

### 4.3 Contágio

Um vértice I contamina um vizinho S com probabilidade `p_ij` (seção 2.6), em cada passo em que a aresta está ativa. Arestas com vértice isolado ficam inativas.

### 4.4 Isolamento

- **Gatilho:** a cada passo, cada vértice infectado (I) tem probabilidade de se isolar, conforme o nível.
- **Efeito:** a máscara de arestas do vértice fica inativa pela duração do isolamento. A estrutura do grafo não muda.
- **Retorno:** ao fim do período, o vértice volta com as mesmas arestas.
- **Isolado não é contaminado:** o isolamento bloqueia todas as arestas do vértice. No máximo, o doente é hospitalizado, mas não impede o deslocamento de pessoas. Limitação a registrar.
- **Isolado pode morrer:** a morte depende da doença, não do contato.

### 4.5 Vacinação

- A partir de um dia de início, uma fração diária dos suscetíveis (S) é vacinada.
- Cada dia, uma fração dos suscetíveis é vacinada. Um vacinado vai para R, com flag de vacinado, com probabilidade igual à eficácia (0,8, fixa); se a vacina falhar, permanece S.

### 4.6 Morte

D é absorvente. Só se chega a D a partir de I, com probabilidade de mortalidade definida pelo usuário.

### 4.7 Parâmetros do usuário

Definidos antes do início, e travados depois:

- R0 (a partir dele, β é calibrado, seção 2.6);
- taxa total de saída de I (γ);
- taxa de mortalidade;
- período de incubação (σ);
- nível de intervenção (baixo, médio ou alto).

Decidido (14/11/2026): o usuário informa γ, a taxa total de saída de I; a mortalidade define a divisão da saída entre D e R (seção 4.2).

---

## 5. Níveis de intervenção (provisório)

Os níveis controlam apenas isolamento e vacinação.

| Nível | Isolamento (prob. diária, duração) | Vacinação (dia de início, fração diária) |
|---|---|---|
| Baixo | 0,05 e 7 dias | dia 180, 0,2% |
| Médio | 0,15 e 10 dias | dia 120, 0,5% |
| Alto | 0,30 e 14 dias | dia 60, 1,0% |

Eficácia da vacina: 0,8, fixa.

**Justificativa.** São escolhas de projeto, não derivadas dos datasets. Os níveis são monotônicos em intensidade de intervenção.

**Status:** provisório. **[pendente: validar por sensibilidade no protótipo (se os níveis produzem diferenças visíveis no pico e no tamanho final) e levantar fontes da literatura sobre medidas não farmacológicas e vacinação, conforme a pesquisa em andamento]**. Recomendação para o relatório: tratar os valores como premissas, com análise de sensibilidade.

---

## 6. Calibração inicial

Dados usados: `data.csv` do H1N1 (24/04 a 06/07/2009) e `sars_2003_complete_dataset_clean.csv` (17/03 a 11/07/2003, com recuperados).

### 6.1 H1N1

- Trecho de 08/05 a 05/06 (2.501 a 22.027 casos): r ≈ 0,078/dia. Este trecho é usado. A fase inicial é distorcida por registros acumulados de primeira semana.
- Método: com r observado, σ = 1/incubação e R0, a relação R0 = (1 + r/σ)(1 + r/γ) dá γ = r / (R0/(1 + r/σ) − 1).
- Incubação de 1,4 dias (Lessler et al., 2009): σ ≈ 0,71. Com R0 de referência de 1,5: γ ≈ 0,22/dia (infecciosidade de cerca de 4,5 dias).
- Faixa de R0 de 1,4 a 1,6 (Fraser et al., 2009): γ entre 0,18 e 0,30/dia.
- Letalidade observada: cerca de 0,45%, com muitos casos ativos no fim da série.

### 6.2 SARS

- Trecho de 31/03 a 14/04 (1.634 a 3.186 casos): r ≈ 0,048/dia.
- Incubação de 4,0 dias (Lessler et al., 2009): σ = 0,25. Com R0 de referência de 3: γ ≈ 0,032/dia (cerca de 31 dias).
- Incubação de 6,4 dias (Donnelly et al., 2003) como limite superior da sensibilidade: γ ≈ 0,037/dia.
- Faixa de R0 de 2 a 4: γ entre 0,020 e 0,071/dia. A calibração do SARS é a mais sensível ao R0 escolhido.
- Recuperação observada a partir de 14/04, usada como verificação de γ. Ressalva: o registro tem atraso de notificação.
- Letalidade observada: cerca de 9,4%.

### 6.3 Sensibilidade e fontes

Fontes localizadas no projeto: R0 do H1N1 em Fraser et al. (2009); R0 do SARS em Lipsitch et al. (2003), cuja leitura direta ainda é pendente. **[pendente: conferir as citações no original antes de constar no relatório.]**

---

## 7. Comparação com dados reais (fluxo real)

### 7.1 Quantidades comparadas

- **Casos acumulados simulados** = I + R + D, sem vacinados. Exclui E, porque casos notificados são de sintomáticos.
- **Mortes acumuladas** = D.
- **Recuperados acumulados** = R sem vacinados. Só no SARS.

Não há modelo de subnotificação.

### 7.2 Alinhamento e escala

- **Dia 0 por país (decidido em 14/11/2026):** primeiro dia em que o número de vértices infectados do país atinge M. Na simulação, conta-se em vértices. No fluxo real, o mesmo M vira casos pela população do país: M × população_i / n_i, porque cada vértice representa essa fração da população. **[pendente: valor de M]**
- **Escala:** comparação por frações (acumulados divididos pela população do país ou do cenário).

### 7.3 Métricas, em ordem de prioridade

1. Erro quadrático médio entre as curvas normalizadas, no intervalo comum, para casos e mortes. Recuperados só no SARS.
2. Diferença de dia do pico, medido por **novos casos por dia** (diferença do acumulado de I + R + D), nos dois lados. O real não tem casos ativos.
3. Diferença do tamanho final da epidemia (fração total infectada).

### 7.4 Calibração

- **Manual inicial:** contágio pela fase inicial e recuperação pela série do SARS, como na seção 6.
- **Ajuste fino por grade:** sobre a métrica 1, marcado como extra.

### 7.5 Regra de cor no fluxo real

No mapa, o polígono de cada país é pintado pela intensidade de casos acumulados por 100 mil habitantes, em escala sequencial. O limiar de 10 por 100 mil (equivalente a 0,01% da população) é o início da escala. Os óbitos aparecem como indicador separado.

**Motivo:** as séries reais trazem só acumulados. Com R = 0 em COVID, Ebola e H1N1, a regra por status dominante deixaria o país sempre na cor de I.

---

## 8. Algoritmos e complexidade

| Algoritmo | Uso | Grafo | Complexidade |
|---|---|---|---|
| Busca em largura e profundidade | Componentes conexos; tempo de chegada em saltos | Completo | O(V + E) |
| Dijkstra | Tempo esperado de chegada entre países, com custo `−ln(p)` | Completo ou contraído | O((V + E) log V) |
| Tarjan (pontes e articulações) | Arestas e vértices críticos | Completo | O(V + E), em uma DFS |
| Propagação de rótulos | Comunidades entre países | Contraído por país | Quase linear |
| Grau | Métrica no painel | Completo | O(V + E) |
| Coeficiente de agrupamento | Métrica de rede (RF18): local por vértice e média global | Completo | O(Σ k_v²) com conjuntos de vizinhança |
| Intermediação aproximada | Análise de centralidade, por amostragem de fontes | Completo | O(k · (V + E)), com k fontes amostradas |
| Intermediação exata | Só no benchmark | Completo | O(V · E) |
| Grade espacial | Criação das arestas geométricas | Vértices por país | Quase linear, em vez de quadrático |

**Custo por passo da simulação:** O(V + E) ativas. Com 8 mil vértices e grau médio de 6 a 10, são algo como 50 mil a 80 mil verificações por passo.

**Algoritmos na simulação:**

- **Antes de iniciar:** calibração de β (seção 2.6) e paciente zero manual ou aleatório. Centralidade é só análise.
- **A cada passo:** iteração sobre vizinhos ativos (núcleo do modelo).
- **Após o término:** componentes, Tarjan e comunidades, para a análise da rede e da epidemia.

---

## 9. Estrutura de dados e execução

- **Lista de adjacência**, com vetor de arestas ativas (máscara).
- **NumPy liberado pelo professor (04/11/2026):** arrays de estado e máscara em NumPy, e CSR como otimização. O núcleo de grafo continua próprio.
- **Histórico de estados:** gravado durante a execução, em um buffer com um `bytearray` de estados por dia. A reprodução segue o buffer. O fluxo real carrega o histórico pronto dos arquivos processados, pelo mesmo player. Memória: cerca de 8 KB por dia, com 8 mil vértices.
- A simulação roda em thread separada da interface.

---

## 10. Cenário regional (Ebola)

No cenário regional, o orçamento de vértices é redistribuído para os países que atingem 10 casos acumulados nos primeiros 60 dias a partir do dia 0 do surto. O prazo de 60 dias é configurável. Os demais países ficam no piso n_min. O grafo global é mantido.

Para a demonstração, Guiné, Libéria e Serra Leoa são o resultado esperado.

**Justificativa:** preserva o grafo unificado. O cenário regional é uma questão de parâmetros de alocação.

---

## 11. Validação e reprodutibilidade

### 11.1 Caso de referência

Três níveis de teste:

1. **Grafo completo, sem isolamento nem vacinação:** a dinâmica deve aproximar o SIR clássico. A curva simulada deve ficar dentro de uma tolerância da solução numérica (proposta: 5% no pico).
2. **Grafo sem arestas:** nenhuma propagação além do paciente zero. Testa a máscara.
3. **Grafos pequenos com resposta conhecida:** caminho (todas as arestas são pontes, Tarjan); ciclo (nenhuma ponte); caminho mínimo calculado à mão (Dijkstra).

### 11.2 Invariante de conservação

Em todo passo: **S + E + I + R + D = N**, por país e no total.

### 11.3 Política de sementes

- Uma semente global, fornecida pelo usuário.
- Cada subsistema deriva a sua semente de forma determinística, a partir da global e do nome do subsistema, por hash estável (`hashlib`). Subsistemas: rede, paciente zero, isolamento, vacinação, rótulos e calibração de β.
- Cada subsistema usa gerador próprio.

**Teste:** mesma semente e mesmos parâmetros geram o mesmo buffer, verificado por hash.

### 11.4 Benchmark

- NetworkX só nas comparações de desempenho, nunca no núcleo.
- Tamanhos de referência: 1 mil, 5 mil, 10 mil e 50 mil vértices, na máquina mais fraca do grupo.
- Critério visual: pelo menos 20 quadros por segundo com cerca de 5 mil vértices (RNF02).

---

## 12. Parâmetros a definir por benchmark

| Parâmetro | Situação |
|---|---|
| N_total | provisório, 8.000 |
| β | calibrado por simulação curta, seção 2.6 |
| k_max e escala | a definir |
| d̄ | faixa de 6 a 10 |
| σ (incubação) | H1N1 1,4 dias; SARS 4,0 dias, com faixa até 6,4 |
| γ (taxa total de saída de I) | entrada do usuário (RF01); valores de referência na seção 6 |
| Níveis de intervenção | provisórios, a validar por sensibilidade |
| Prazo de seleção do cenário regional | 60 dias, configurável |

---

## 13. Limitações do modelo

- **Dados de rotas desatualizados:** o OpenFlights parou de atualizar em junho de 2014. É um retrato estático, aplicado às quatro pandemias.
- **População de um único ano:** a população do OWID é de cerca de 2022, usada também para as pandemias de 2003, 2009 e 2014–2016.
- **Países sem rota:** ficam sem conexão aérea.
- **Isolado não é contaminado:** o modelo não captura a transmissão dentro do domicílio do vértice isolado.
- **Isolamento e vacinação sem fonte nos dados:** os níveis são premissas do modelo.
- **Tempo de geração do H1N1:** Fraser et al. (2009) estimam 1,9 dias. A infecciosidade de 4,5 dias usada aqui é maior. A diferença deve ser declarada no relatório.
- **Recuperados com atraso:** o registro do SARS mede mais a notificação do que a duração clínica.
- **R0 de referência:** depende da fonte; a calibração é sensível a esse valor.
- **Fluxo real sem interação:** as medidas nas pandemias reais já estão refletidas nos dados.
- **Escala reduzida:** 8 mil vértices representam milhões de habitantes. A comparação é por frações.
- **Grafo geométrico dentro do país:** a conectividade interna é uma aproximação, não um dado de mobilidade real.
- **Cor do fluxo real:** a escala por casos acumulados não mostra a dinâmica de casos ativos, porque o dado não os traz.

---

## 14. Pendências

Pendências de planejamento, que serão resolvidas durante a implementação ou dependem de terceiros:

- **Professor (respondido em 04/11):** NumPy no núcleo do grafo e `shapely` no script de preparação liberados; OpenFlights versionado sob ODbL, com atribuição.
- **Repositório:** público (D25, decidido). Os CSVs brutos do Kaggle ficam fora do Git.
- **Fontes:** localizadas no projeto para R0 (Fraser et al., 2009; Lipsitch et al., 2003, leitura pendente), incubação (Lessler et al., 2009; Donnelly et al., 2003) e controle de surtos (Ferguson et al., 2005). Conferir as citações no original antes de constar no relatório. Isolamento e vacinação seguem como premissas, com sensibilidade.
- **Benchmark:** N_total, β, k_max, escala e d̄.
- **Níveis de intervenção:** validar por sensibilidade no protótipo.
- **Dados:** recontagem de países com e sem rota pelo script, com a tabela de apelidos completa.
- **Dia 0 por país:** valor de M (seção 7.2).
- **Limiar de 40 px e 36 px** para exibição de vértices: validar no protótipo.
- **Casos de uso, responsabilidades e diagramas UML:** fora deste documento, a cargo de outros chats do grupo.
- **Plano de desenvolvimento e cronograma:** em outro chat, depois de definido o restante do planejamento.
