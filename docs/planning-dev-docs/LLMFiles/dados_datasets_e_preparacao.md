# Dados do projeto: datasets, normalização e script de preparação

Simulador de Epidemias em Redes – Documento de apoio (Tema 7)

*Versão 0.7 – revisão do grupo – 03/11/2026*

**Para que serve este documento.** Registra o que o grupo decidiu sobre os dados (quais arquivos usar, de onde vêm as arestas, como normalizar nomes), a estrutura de pastas e a especificação do script de preparação, para que alguém do grupo possa implementá-lo. Itens marcados como **proposta** ainda não foram validados pelo grupo. Itens marcados como **a verificar** dependem de conferir os arquivos ou perguntar ao professor. Itens marcados como **[pendente]** serão resolvidos durante a implementação ou dependem de terceiros.

---

## 1. Visão geral do modelo de dados

O fluxo de pandemias reais precisa de três tipos de dado:

1. **Fatos:** casos, mortes (e recuperados, quando existirem) por país e por dia, de cada pandemia.
2. **Tabela mestra de países:** código ISO, nome, população, atributos estáticos e coordenadas.
3. **Arestas:** conexões entre países, com peso, para formar o grafo de regiões.

Nenhum dos datasets do Kaggle traz as arestas, nem a população por país. Por isso usamos duas fontes complementares: o **OWID** (tabela mestra) e o **OpenFlights** (arestas por rotas aéreas).

Princípio central: **o código ISO3 é a chave de tudo.** Todos os nomes de país, de todas as fontes, são convertidos para ISO3 antes de qualquer cruzamento.

---

## 2. Arquivos usados

### 2.1 Núcleo (obrigatórios)

| Fonte | Arquivo(s) | Papel |
| --- | --- | --- |
| COVID-19 (JHU/Kaggle) | `RAW_global_confirmed_cases.csv`, `RAW_global_deaths.csv` | Séries acumuladas por país (22/01/2020 a 09/03/2023) |
| Ebola 2014–2016 | `ebola_2014_2016_clean.csv` | Casos e mortes acumulados por país (29/08/2014 a 23/03/2016) |
| H1N1 2009 | `data.csv` | Única série temporal do H1N1 (24/04/2009 a 06/07/2009) |
| SARS 2003 | `sars_2003_complete_dataset_clean.csv` | Casos, mortes e **recuperados** por país (17/03/2003 a 11/07/2003) |
| OWID COVID | `owid-covid-data.csv` | Fonte da tabela mestra de países (ISO, população, atributos). **Não entra no aplicativo** |
| OpenFlights | `airports.dat`, `routes.dat`, `countries.dat` | Arestas entre países e nomes → ISO |
| Natural Earth | Admin 0 – Countries, 50m, versão 5.1.1 (242 feições). Recebido em shapefile e convertido **uma vez** para GeoJSON (`ne_50m_admin_0_countries.json`) por qualquer ferramenta de conversão, antes da execução do script | Polígonos dos países: centroide, mapa e posição dos vértices (D15). Domínio público (conferido em 03/11/2026) |

### 2.2 Opcionais (desejável ou extra)

| Arquivo | Uso possível |
| --- | --- |
| `summary_data_clean.csv` (SARS) | Casos importados por país, útil para escolher paciente zero (desejável) |
| `summary_south_america.csv` (H1N1) | Casos estimados no Brasil, Chile e Peru (extra) |
| `RAW_us_confirmed_cases.csv`, `RAW_us_deaths.csv` | COVID por condado nos EUA (extra) |

### 2.3 Descartados

| Arquivo | Motivo |
| --- | --- |
| `CONVENIENT_*` (global e EUA) | Mesmos dados dos RAW, reorganizados |
| `ebola_data_db_format.csv` | Mesmo conteúdo do arquivo clean, em formato indicador/valor |
| `summary_*` do H1N1 (África, Ásia, Europa, EUA, Índia, Alemanha) | Fotos de um momento sem data, não comparáveis com a série diária |
| HIV/AIDS | Não é série de propagação. Descartado |
| Feições do Natural Earth: ATA, ATF, HMD, NFK, SGS, IOT, SOL, KAS | Sem correspondência no OWID ou fora do escopo; não entram no modelo |

### 2.4 Fontes a citar no relatório

Kaggle: COVID-19 (autor antgoldbloom, a partir dos dados do Johns Hopkins CSSE); Ebola 2014–2016, H1N1 2009 e SARS 2003 (autor imdevskp, com dados originários da OMS); Our World in Data (OWID); OpenFlights (rotas até junho de 2014, aeroportos até janeiro de 2017); Natural Earth (Admin 0 – Countries, 50m, versão 5.1.1). As referências em BibTeX e ABNT estão em `referencias.bib` e `referencias_abnt.md`.

**Licenças conferidas em 03/11/2026** (pesquisa de apoio, não parecer jurídico):

- **JHU CSSE (COVID-19):** CC BY 4.0. Atribuir a JHU CSSE e citar Dong, Du & Gardner (2020). Os arquivos `RAW_*` vêm de espelho no Kaggle; citar a JHU como fonte primária.
- **OWID:** CC BY. Dados de terceiros seguem a licença original (casos e mortes vêm da OMS).
- **Natural Earth:** domínio público, sem condições.
- **OpenFlights:** ODbL 1.0 (base) e DbCL (conteúdo). O arquivo de arestas `edges.csv` é base derivada e deve ser licenciado sob ODbL 1.0, com aviso de origem e com o script de derivação publicado (seção 4, D25).
- **Kaggle imdevskp (Ebola, H1N1, SARS, COVID-19):** licença "Other (specified in description)", sem texto de licença encontrado. Os CSVs não são versionados no repositório (seção 4, D25).

---

## 3. Diagnóstico dos datasets

Resumo dos problemas encontrados nos arquivos, que o script precisa tratar.

### 3.1 COVID-19 (JHU)

- Formato largo: uma coluna por data, valores **acumulados**.
- 289 linhas, 201 países. Oito países vêm divididos em províncias (China 34, Canadá 16, Reino Unido 15, França 12, Austrália 8, Holanda 5, Dinamarca 3, Nova Zelândia 3). É preciso **somar por país**.
- Linhas que não são países: `Diamond Princess`, `MS Zaandam`, `Summer Olympics 2020`, `Winter Olympics 2022`, `Antarctica`.
- 6 linhas sem Lat/Long (partes do Canadá e da China, Diamond Princess e MS Zaandam).
- 362 quedas nos acumulados (correções retroativas).
- Sem população e sem recuperados.

### 3.2 Ebola

- 10 países; Guiné, Libéria e Serra Leoa concentram quase todos os casos. Os demais são casos isolados (Nigéria, EUA, Mali, Senegal, Espanha, Reino Unido, Itália).
- Intervalos entre datas de até 85 dias.
- Quedas nos acumulados (Libéria 85, Guiné 44, Nigéria 2, Serra Leoa 2, Senegal 1).
- A Libéria tem 365 linhas contra 259 datas distintas: o arquivo clean mistura duas séries. A principal tem 259 datas e termina com 10.666 casos e 4.806 mortes. A `Liberia 2` do formato db tem 105 datas (03/07/2015 a 23/03/2016), termina com 9 casos e 3 mortes e começa com um valor atípico (40 casos). A `Guinea 2` só existe no formato db (1 registro) e não aparece no clean.
- 4 valores nulos de casos em Reino Unido e Mali.
- Sem recuperados.

### 3.3 H1N1

- 148 países, 50 datas, intervalos de até 3 dias.
- Muitos países com 1 ou 2 observações.
- 36 nomes não casam com o OWID (ex.: `Bosnia and Hezegovina` com erro de grafia, `Cap Verde`, `Brunei Darussalam`, `UK`, e territórios como `Bermuda, UKOT` e `French Polynesia, FOC`).
- O mesmo território aparece sob grafias diferentes, em intervalos de datas que não se sobrepõem (ex.: `France, Martinique, FOC` em 17/06 e `Martinique, FOC` de 19/06 a 06/07; três grafias para Curaçao). Cada grafia deve virar a mesma entidade pelo apelido (D21).
- Quedas nos acumulados em 5 países (Bahamas, Costa Rica, Polinésia Francesa, Maurício, Nova Zelândia).
- Sem recuperados.

### 3.4 SARS

- 37 países, 96 datas, intervalos de até 3 dias. Único conjunto com recuperados.
- **Duplicata na China em 12/04/2003**, com dois registros muito diferentes (1.309 casos e 62 casos). O registro de 1.309 casos (igual ao do dia anterior) mantém o acumulado crescente; o de 62 casos é descartado (D23).
- Quedas nos acumulados em 18 países (casos) e 12 (recuperados).
- Nomes divergentes: `Taiwan, China` na série e `Taiwan` no summary.

### 3.5 OWID

- 350 mil linhas, 67 colunas, de 01/01/2020 a 24/10/2023. Arquivo de 92 MB.
- Mistura países e agregados (`World`, `Africa`, faixas de renda, `England`, `Scotland` etc.); os agregados têm `iso_code` começando por `OWID_`. Exceção: o Kosovo vem como `OWID_KOS`, tem população no arquivo e entra no modelo (D19).
- População preenchida em todos os 237 países com continente. Atributos estáticos com cobertura parcial (densidade 213, idade mediana 200, PIB per capita 194, leitos 172, expectativa de vida 233).
- Sem latitude e longitude.
- Oito territórios sem polígono próprio no Natural Earth 50m (GIB, BES, GLP, GUF, MTQ, MYT, REU, TKL) são agregados ao país-mãe (D9). O `OWID_CYN` (Norte do Chipre) é entidade própria no OWID, com continente (Ásia), e é agregado ao Chipre (D24). O universo do modelo fica em **229 entidades** (237 − 8 territórios − `OWID_CYN` + `OWID_KOS`). Este número substitui o 230 de versões anteriores.

### 3.6 OpenFlights

- 7.698 aeroportos em 237 países; 67.663 rotas; 261 países em `countries.dat` (20 sem ISO).
- 220 rotas com origem sem ID e 221 com destino sem ID; 523 rotas apontam para aeroportos que não estão em `airports.dat`.
- Recontagem provisória (apelidos básicos, exclusão de codeshare, agregação de territórios e Kosovo: D9, D14 e D19): 28.497 rotas internacionais, 2.255 pares de países (não dirigido) e 216 entidades com ao menos uma rota. Com codeshare seriam 34.644 rotas, 2.299 pares e 218 entidades. **[pendente: estes números foram calculados sobre 230 entidades. Com o universo de 229 (CYN agregado ao Chipre), a contagem precisa ser refeita pelo script, com a tabela de apelidos completa.]**
- Entidades sem rota na recontagem provisória: Andorra, Eswatini, Lesotho, Liechtenstein, Mônaco, Montserrat, Palestina, Pitcairn, São Bartolomeu, Santa Helena, São Martinho (parte francesa), San Marino, Síria e Vaticano. Eswatini e Lesotho só têm rota via codeshare e ficam isoladas com a D14. O número anterior (12 países, incluindo Mianmar e Antártida) vinha de nomes que não casavam (`Burma`) e do Kosovo.
- Cobertura nas pandemias (estimativa): COVID-19 com 9 entidades sem aresta (Andorra, Eswatini, Lesotho, Liechtenstein, Mônaco, Palestina, San Marino, Síria e Vaticano); H1N1 com 3 (Mônaco, Síria e Palestina); Ebola e SARS, nenhuma.
- 22 nomes do `airports.dat` não casam com o OWID (ex.: `Burma`, `Congo (Kinshasa)`, `Czech Republic`, `East Timor`, `Swaziland`, `Macedonia`) e vão para a tabela de apelidos. Sem entidade no modelo, e portanto `DROP` pela regra da D9: Antarctica, British Indian Ocean Territory, Cocos (Keeling) Islands, Christmas Island, Johnston Atoll, Midway Islands, Wake Island, Norfolk Island e Svalbard.
- Exceções por aeroporto: Pristina (`PRN`) consta como `Serbia` e deve ir para `KOS`; `Netherlands Antilles` reúne 5 aeroportos de entidades diferentes (`BON`, `EUX` e `SAB` para BES, agregado ao NLD; `CUR` para CUW; `SXM` para SXM). Nomes de território usados no arquivo: Guadeloupe (7 aeroportos), French Guiana (6), Reunion (3), Gibraltar, Martinique e Mayotte (1 cada); Tokelau e Bonaire, Saba e Santo Eustáquio não aparecem por nome.
- **Dados de rotas desatualizados:** o fornecedor parou de atualizar em junho de 2014. É um retrato estático, aplicado às quatro pandemias; isso deve constar nas limitações do relatório.

---

## 4. Decisões

| # | Tema | Decisão | Status |
| --- | --- | --- | --- |
| D1 | Séries de COVID | Usar JHU (`RAW_global_*`); OWID só para a tabela mestra | Decidido |
| D2 | Arquivos | Usar só as fontes do núcleo (seção 2.1); demais opcionais ou descartados | Decidido |
| D3 | Fonte das arestas | OpenFlights (rotas aéreas), não fronteiras | Decidido |
| D4 | Chave de cruzamento | ISO3 em todas as fontes | Decidido |
| D5 | Onde normalizar | Fora do aplicativo, por script rodado uma vez por quem prepara os dados | Decidido |
| D6 | Conteúdo do repositório | Aplicativo lê só `data/processed/`; brutos fora do repositório; script e tabela de apelidos versionados | Decidido |
| D7 | Execução do script | Uma vez pelo responsável pelos dados (M4), com saída versionada no Git. O aplicativo nunca roda o script | Decidido |
| D8 | Não-países (Diamond Princess, MS Zaandam, Olimpíadas, Antártida) | Descartar, junto com as feições do Natural Earth sem entidade no modelo (ATA, ATF, HMD, NFK, SGS, IOT, SOL, KAS) | Decidido |
| D9 | Territórios sem polígono próprio no Natural Earth 50m | Agregar ao país-mãe: GIB ao GBR; BES ao NLD; TKL ao NZL; GLP, GUF, MTQ, MYT e REU ao FRA. Casos, mortes e população são somados ao país-mãe; as rotas entre território e metrópole viram domésticas e são excluídas. Os demais territórios (ex.: Curaçao, Bermudas) seguem a regra anterior: manter se tiverem ISO na tabela mestra, senão descartar e registrar em log | Decidido |
| D10 | Acumulados com quedas | Aplicar máximo acumulado (`cummax`) por entidade de origem (D21) | Decidido |
| D11 | Datas faltantes | Série diária contínua: preencher com o último valor anterior; antes do primeiro registro, zero | Decidido |
| D12 | Recuperados | Coluna vazia onde não existe (COVID, Ebola, H1N1); preenchida só no SARS | Decidido |
| D13 | Peso e direção das arestas | Não dirigido. O `edges.csv` guarda o número bruto de rotas (`routes`). A transformação em peso de contágio e em custo de caminho é feita pelo aplicativo, não pelo script | Decidido |
| D14 | Rotas em codeshare | Excluir `codeshare = Y`, pois esses registros repetem voos já operados por outra companhia e contam o mesmo tráfego duas vezes | Decidido |
| D15 | Coordenadas dos países | Usar os polígonos do Natural Earth 50m para posicionar os vértices dentro do país e calcular o centroide. Chave por `ISO_A3_EH`, com fallback em `ADM0_A3` quando vier −99 (no arquivo conferido: Kosovo, Norte do Chipre, Somalilândia e Siachen; Noruega e França têm `ISO_A3` −99, mas `ISO_A3_EH` preenchido). Feições do mesmo país são agregadas pelo código (a Austrália tem três); ALA é agregada à FIN e CYN ao CYP. Lat/Long do JHU e média dos aeroportos deixam de ser usados. Revisar países que cruzam o antimeridiano (Rússia, Fiji, EUA, Kiribati e Nova Zelândia) com o próprio polígono | Decidido |
| D16 | Países sem nenhuma rota | Manter isolados e exibir aviso na interface. Não criar arestas artificiais. Registrar como limitação do modelo (sem voos, a doença não sai do país pela via aérea). A contagem é refeita pelo script (seção 3.6) | Decidido |
| D17 | NumPy no núcleo do grafo | Liberado pelo professor (03/11/2026); não afeta este script | Decidido (03/11/2026) |
| D18 | Multiplicidade das arestas | Cada par de países gera `k_ij = min(k_max, ceil(routes_ij / escala))` arestas entre vértices escolhidos aleatoriamente (com semente), e o peso de cada aresta é o peso derivado de `routes_ij`. `k_max` e `escala` a definir por benchmark | Decidido |
| D19 | Kosovo | Entra no modelo (`OWID_KOS` no OWID, `KOS` no Natural Earth) com `iso3 = KOS`. É a única exceção à exclusão dos códigos `OWID_` | Decidido |
| D20 | Geometria processada | O script grava `countries.geojson` com uma feição por entidade do modelo, já agregada, usada pelo mapa e pelo sorteio de posições dos vértices. Somente `Polygon` e `MultiPolygon` (o aplicativo usa só a biblioteca padrão); os polígonos que cruzam o antimeridiano (Rússia, Fiji, EUA) ficam divididos em partes | Decidido |
| D21 | Ordem de agregação das séries | Preencher datas e aplicar `cummax` em cada entidade de origem antes de somar no país-mãe, para não subestimar totais quando território e país-mãe reportam em datas diferentes. A entidade de origem é a entidade resolvida pelo apelido: grafias diferentes do mesmo território (ex.: `Martinique, FOC` e `France, Martinique, FOC`) formam uma só série | Decidido |
| D22 | Libéria no Ebola | Em cada data com mais de uma linha, manter a de maior `cases` (a série principal, que confere com o formato db em todas as 259 datas) e descartar a série `Liberia 2` (9 casos e 3 mortes ao final, contra 10.666 e 4.806 da principal; menos de 0,1% dos casos) | Decidido |
| D23 | Duplicata da China no SARS (12/04/2003) | Manter o registro que preserva o acumulado crescente (1.309 casos) e descartar o de 62 casos | Decidido |
| D24 | População do Norte do Chipre | Somar a população de `OWID_CYN` (382.836) à do Chipre, como nos territórios da D9, pois o polígono é agregado ao Chipre (D15). `OWID_CYN` sai do universo de 229 entidades | Decidido |
| D25 | Repositório público | O repositório é público. `data/processed/` (incluindo `edges.csv`) é licenciado sob ODbL 1.0, com arquivo de licença próprio na pasta e atribuições no README de `data/`. O código do aplicativo tem licença própria, que não cobre `data/`. Os CSVs brutos do Kaggle não são versionados: o README indica onde baixá-los | Decidido (03/11/2026) |

**Limitação a registrar no relatório:** a população do OWID é um valor único recente (cerca de 2022), usado também para as pandemias de 2003, 2009 e 2014–2016.

**Limitação a registrar no relatório:** o Natural Earth traça as fronteiras de fato (quem controla o território), não as de direito.

---

## 5. Estrutura de pastas

O aplicativo carrega apenas `data/processed/`. Os arquivos brutos não ficam no repositório nem em uma pasta do projeto: o script recebe o caminho deles como argumento.

```
data/
├── README.md              # origem dos brutos, passo a passo, decisões, limitações, atribuições
├── LICENSE-ODbL.txt       # licença do conteúdo derivado de OpenFlights (D25)
├── prepare_data.py        # script de preparação (um arquivo só)
├── country_aliases.csv    # tabela de apelidos: alias (nome ou código) → ISO3 (ou DROP) e país-mãe, quando agregado
└── processed/             # o que o aplicativo carrega (versionado no Git)
    ├── countries.csv
    ├── countries.geojson  # polígonos agregados por iso3 (mapa e posição dos vértices)
    ├── covid19.csv
    ├── ebola.csv
    ├── h1n1.csv
    ├── sars.csv
    ├── edges.csv
    └── sars_imported.csv  # opcional (a partir do summary do SARS)
```

Os testes que validam `data/processed/` ficam na pasta de testes já prevista para o pytest (por exemplo `tests/test_data.py`).

O README de `data/` deve indicar, para cada arquivo bruto, o nome, a fonte e onde baixar, para que qualquer pessoa consiga reproduzir o processo. Também deve conter as atribuições exigidas por cada fonte (seção 2.4). A cópia de DATA_SOURCES.md, quando existir, segue o mesmo conteúdo **[pendente: decidir se o arquivo é separado ou integrado ao README]**.

---

## 6. Esquemas dos arquivos de saída

### 6.1 `countries.csv` (tabela mestra)

Uma linha por país. Colunas: `iso3`, `name`, `continent`, `population`, `population_density`, `median_age`, `gdp_per_capita`, `hospital_beds_per_thousand`, `life_expectancy`, `human_development_index`, `lat`, `lon`.

- Uma linha por entidade do modelo: **229** após a agregação de territórios (D9), a exclusão de `OWID_CYN` (D24) e a inclusão do Kosovo (D19).
- Origem: OWID, excluindo `iso_code` que comece por `OWID_`, exceto `OWID_KOS` (D19). Valores nulos nos atributos estáticos permanecem vazios.
- `population`: soma da população do país-mãe e dos territórios agregados (D9); no Chipre, soma também a do Norte do Chipre (`OWID_CYN`, D24). Os demais atributos estáticos são os do país-mãe.
- `lat`, `lon`: centroide do polígono do Natural Earth (D15).

### 6.2 `covid19.csv`, `ebola.csv`, `h1n1.csv`, `sars.csv` (séries)

Esquema único: `iso3`, `date`, `cases`, `deaths`, `recovered`.

- `date` em formato ISO 8601 (`AAAA-MM-DD`), **uma linha por país e por dia**, sem lacunas entre a primeira e a última data da pandemia.
- `cases`, `deaths`, `recovered`: acumulados, inteiros, não decrescentes. `recovered` vazio onde não existe (D12).

### 6.3 `edges.csv`

Colunas: `iso3_a`, `iso3_b`, `routes`, com `iso3_a < iso3_b` (par não dirigido, sem repetição).

- `routes` é o número bruto de rotas entre os dois países, sem normalização. As transformações (peso de contágio e custo de caminho, ver D13) ficam a cargo do aplicativo.
- O arquivo contém apenas pares de países. As arestas entre vértices são geradas pelo aplicativo a partir de D18.
- Licença: ODbL 1.0 (D25).

### 6.4 `country_aliases.csv` (entrada mantida à mão)

Colunas: `alias`, `iso3`, `parent_iso3`, `note`.

- `alias`: o nome como aparece em alguma fonte (comparado após normalização), o código da feição (Natural Earth) ou o código IATA de um aeroporto com o prefixo `iata:` (exceções do OpenFlights, ex.: `iata:PRN`).
- `iso3`: o código de destino, ou o valor literal `DROP` para descartar o registro (não-países). Para territórios agregados (D9), é o `iso3` do próprio território (ex.: `MTQ`), que mantém sua identidade para a D21.
- `parent_iso3`: preenchido só nos territórios agregados (D9), com o `iso3` do país-mãe (ex.: `FRA`); vazio nos demais. A `note` registra "agregado ao país-mãe".
- `note`: justificativa curta (ex.: "grafia errada no H1N1").

### 6.5 `countries.geojson` (geometria)

Uma feição por entidade do modelo, com a propriedade `iso3` igual à de `countries.csv`.

- Origem: Natural Earth 50m, em GeoJSON (conversão única do shapefile, seção 2.1). As feições do mesmo país (a Austrália tem três) e as dos territórios agregados (D9; ALA à FIN; CYN ao CYP) são fundidas na feição do país de destino. Feições sem entidade no modelo ficam de fora.
- Usado pelo aplicativo para desenhar o mapa e sortear a posição dos vértices dentro de cada país. O centroide de `countries.csv` sai desta mesma geometria.
- Conferido no arquivo 50m: Rússia e Fiji chegam a ±180° e EUA, Kiribati e Nova Zelândia cruzam o antimeridiano; todos já vêm divididos em partes. O cálculo do centroide deve deslocar as longitudes negativas em +360° para esses países (D15).
- Tamanho medido em simulação sobre o arquivo 50m (242 feições, 168 propriedades, 4,46 MB): com uma feição por entidade (229), só `iso3` e coordenadas arredondadas, fica entre 1,4 MB (2 casas decimais) e 1,6 MB (3 casas). Pequeno o bastante para o Git e para o executável.

---

## 7. Especificação do script `prepare_data.py`

### 7.1 Interface

```
python data/prepare_data.py --raw <pasta_com_os_brutos> --out data/processed
```

- `--raw`: pasta com os arquivos brutos (seção 2.1). Os nomes dos arquivos são os originais do Kaggle, OWID e OpenFlights, e o arquivo `ne_50m_admin_0_countries.json` (GeoJSON convertido do Natural Earth).
- `--out`: pasta de saída (padrão `data/processed`).
- O script **falha com mensagem clara** se faltar algum arquivo bruto, e **termina com erro** se sobrar algum nome sem ISO e sem entrada em `country_aliases.csv` (nunca descarta países em silêncio).
- Dependências do script (pandas e, para a geometria, shapely) são instaladas só por quem rodar o script e **não entram** no `requirements.txt` do aplicativo. Com a entrada em GeoJSON, a leitura é feita com a biblioteca padrão (`json`), e `pyshp` deixa de ser necessário. **Liberado pelo professor (03/11/2026).**
- Execução determinística: mesma entrada, mesma saída.

### 7.2 Funções sugeridas

| Função | O que faz |
| --- | --- |
| `normalize_name(s)` | Minúsculas, remove acentos e pontuação, colapsa espaços. É usada em todo nome de país antes de comparar |
| `load_aliases(path)` | Lê `country_aliases.csv` e devolve um dicionário com nomes já normalizados |
| `build_countries(owid, geometry)` | Gera a tabela mestra e o dicionário `nome normalizado → ISO3` a partir dos nomes do OWID. Soma a população dos territórios agregados ao país-mãe (D9), mantém `OWID_KOS` (D19), exclui `OWID_CYN` após somar sua população ao Chipre (D24), e calcula `lat` e `lon` pelos centroides dos polígonos (D15) |
| `build_geometry(natural_earth, aliases)` | Lê os polígonos do GeoJSON, resolve a chave (`ISO_A3_EH`, com fallback em `ADM0_A3`), funde as feições do mesmo país e dos territórios agregados, descarta as feições sem entidade no modelo e grava `countries.geojson` (D20) |
| `resolve_iso(name, ref, aliases)` | Devolve o ISO3, ou `DROP`, ou `None` se não resolver. Ordem: tabela de apelidos, depois nome do OWID |
| `finalize_series(df)` | Para cada entidade de origem, monta a grade diária, preenche datas faltantes e aplica `cummax`; só depois soma no país de destino (D21) e converte para inteiro |
| `prepare_covid(...)`, `prepare_ebola(...)`, `prepare_h1n1(...)`, `prepare_sars(...)` | Leitura e regras específicas de cada fonte (seção 7.3) |
| `build_edges(airports, routes, aliases)` | Gera o grafo de países por rotas (seção 7.4) |
| `validate(...)` | Verificações finais (seção 7.5) |
| `main()` | Lê os argumentos, executa tudo na ordem e grava a saída |

### 7.3 Etapas e regras por fonte

**Ordem de execução:**

1. Carregar `country_aliases.csv`.
2. Montar a geometria (`countries.geojson`), a tabela mestra (`countries.csv`) e o dicionário de nomes a partir do OWID.
3. Preparar cada pandemia (regras abaixo), resolvendo cada nome para ISO3 com `resolve_iso`.
4. Montar as arestas.
5. Validar e gravar.

**COVID-19 (JHU):**

- Ler casos e mortes; transformar de largo para longo (uma linha por país, província e dia); converter a data do formato `m/d/aa`.
- Resolver o ISO3 do país (`US` → `USA`, `Korea, South` → `KOR`, `Burma` → `MMR` etc. via tabela de apelidos).
- Descartar os nomes marcados como `DROP`.
- Somar as províncias por país e data.

**Ebola:**

- Usar `ebola_2014_2016_clean.csv` (colunas de casos e mortes acumulados).
- Tratar a duplicidade de datas da Libéria (seção 3.2) antes de agrupar: em cada data com mais de uma linha, manter a de maior `cases` (a série principal) e descartar a série `Liberia 2` (D22). Registrar a regra no README.
- Tratar os 4 nulos de casos do Reino Unido e do Mali (preencher com o valor anterior, ou zero se for o início).
- Aplicar `finalize_series` (intervalos de até 85 dias entre datas serão preenchidos com o último valor).

**H1N1:**

- Usar `data.csv` (colunas de casos e mortes acumulados; ignorar `Link`).
- Resolver os nomes com a tabela de apelidos e aplicar D8 e D9 aos territórios: os agregados somam casos e mortes ao país-mãe, sem `DROP`.
- Países com poucas observações são mantidos; a série diária fica constante nos intervalos entre registros.

**SARS:**

- Usar `sars_2003_complete_dataset_clean.csv` (casos, mortes e recuperados).
- Resolver a duplicata da China em 12/04/2003: manter o registro de 1.309 casos, que preserva o acumulado crescente (D23), e registrar a regra no README.
- Aplicar `cummax` também em `recovered`.
- Opcional: gerar `sars_imported.csv` a partir de `summary_data_clean.csv` (casos importados por país), resolvendo `Taiwan` para o mesmo ISO3 de `Taiwan, China`.

**Regras comuns (`finalize_series`):**

1. Para cada entidade de origem (nome já resolvido pelo apelido, com as grafias diferentes do mesmo território reunidas numa só entidade, antes de juntar com outras), criar a grade diária contínua entre a primeira e a última data da pandemia.
2. Preencher com o último valor anterior; antes do primeiro registro, zero.
3. Aplicar o máximo acumulado em `cases`, `deaths` e `recovered`.
4. Somar por `iso3` e `date` (junta províncias e territórios agregados ao mesmo país, D9 e D21).
5. Converter para inteiros; `recovered` fica vazio onde não existe na fonte.

### 7.4 Geração das arestas

1. Ler `airports.dat` (colunas: id, nome, cidade, país, IATA, ICAO, lat, lon, ...). Converter o nome do país de cada aeroporto em ISO3 com `resolve_iso` (nomes do OpenFlights, como `Burma`, `Macedonia`, `Czech Republic`, `East Timor`). Aplicar antes as exceções por aeroporto (`iata:PRN` para `KOS`; `iata:BON`, `iata:EUX` e `iata:SAB` para `BES`; `iata:CUR` para `CUW`; `iata:SXM` para `SXM`), pois o OpenFlights lista esses aeroportos sob `Serbia` e `Netherlands Antilles`.
2. Ler `routes.dat` (colunas: companhia, ..., origem, ID da origem, destino, ID do destino, codeshare, paradas, equipamento). O arquivo usa `\N` para valores ausentes.
3. Descartar rotas com ID de origem ou destino ausente e rotas cujo aeroporto não existe em `airports.dat`.
4. Associar cada rota ao país de origem e ao de destino; descartar as rotas domésticas (mesmo país, incluindo as entre um território agregado e o país-mãe, D9). Os nomes de território usados no `airports.dat` precisam estar na tabela de apelidos como agregados ao país-mãe.
5. Excluir `codeshare = Y` (D14).
6. Contar rotas por par de países, **sem direção** (ordenar o par pelo ISO3), e gravar em `edges.csv`.
7. Registrar no log os países da tabela mestra que ficaram sem nenhuma aresta (D16).

### 7.5 Validações (o script falha se alguma falhar)

- Todo `iso3` de toda série e de `edges.csv` existe em `countries.csv`.
- Cada `iso3` de `countries.csv` tem exatamente uma feição em `countries.geojson`, e vice-versa.
- A soma das populações de `countries.csv` é igual à das entidades do OWID incluídas (sem perda com a agregação).
- O número de linhas de `countries.csv` é 229.
- Não há nomes sem resolução (nem para ISO3 nem para `DROP`).
- Em cada série: não há `NaN` em `cases` e `deaths`, as datas são contínuas e os acumulados são não decrescentes.
- `edges.csv`: sem laços (`iso3_a != iso3_b`), sem pares repetidos e com `routes > 0`.
- Imprimir um resumo: quantos nomes foram resolvidos direto, quantos por apelido, quantos descartados, e quantos países de cada pandemia estão sem aresta.

### 7.6 Testes (pytest)

Testes sobre `data/processed/`, rodados pelo grupo e independentes do script:

- Os esquemas dos arquivos (colunas e tipos).
- Cada série tem acumulados não decrescentes e datas contínuas.
- Todo ISO3 das séries e das arestas existe na tabela mestra.
- `countries.geojson` e `countries.csv` têm o mesmo conjunto de `iso3`.
- O grafo carregado a partir de `edges.csv` tem o número esperado de arestas e nenhum laço.

---

## 8. Pontos em aberto

- **Resolvido (03/11/2026):** o professor liberou o uso de shapely no pré-processamento.
- **Resolvido (03/11/2026):** o professor liberou o NumPy no núcleo do grafo (D17).
- **[pendente]** Recontar rotas e países sem rota ao rodar o script, com a tabela de apelidos completa. Os números da seção 3.6 foram calculados sobre 230 entidades e são provisórios.
- **[pendente]** Escolher a forma de atribuição: arquivo `DATA_SOURCES.md` separado ou integrado ao README de `data/` (seção 5).
- **[pendente]** Definir β, `k_max` e `escala` (D18) por benchmark, durante a implementação do aplicativo.

Licenças conferidas (seção 2.4). Citações de referências do relatório: conferir no original antes de constar no texto final.

---

## 9. Como reproduzir (texto para o README de `data/`)

1. Baixar os arquivos brutos de cada fonte (seção 2.1) para uma pasta qualquer, fora do repositório.
2. Converter o shapefile do Natural Earth para GeoJSON, com qualquer ferramenta, e salvar como `ne_50m_admin_0_countries.json` na mesma pasta.
3. Instalar as dependências do script (pandas e shapely) em um ambiente à parte do aplicativo.
4. Rodar `python data/prepare_data.py --raw <pasta> --out data/processed`.
5. Conferir o resumo impresso. Se houver nomes sem resolução, acrescentar linhas em `country_aliases.csv` e rodar de novo.
6. Fazer commit do script, da tabela de apelidos e de `data/processed/`, com a licença ODbL na pasta de dados derivados (D25).

---

## 10. Histórico de alterações

| Versão | Data | Mudanças |
| --- | --- | --- |
| 0.1 | 17/10/2026 | Primeira versão: datasets, decisões D1 a D17, estrutura de pastas, esquemas e especificação do script. |
| 0.2 | 29/10/2026 | Ajustes para a unificação do grafo: D13 (peso bruto), D14 (codeshare), D15 (coordenadas por Natural Earth), D16 (países isolados), nova D18 (multiplicidade de arestas); seções 6.3, 7.2 e 7.4 atualizadas. |
| 0.3 | 30/10/2026 | Agregação de territórios e Natural Earth: fonte obrigatória (2.1, 2.3, 2.4); D8 e D9 (feições fora do modelo e territórios agregados ao país-mãe); D15 detalhada; novas D19 (Kosovo), D20 (geometria processada) e D21 (ordem de agregação das séries); universo de 230 entidades; novo `countries.geojson` (5 e 6.5); seções 3.5, 3.6, 6.1, 6.4, 7.1 a 7.6, 8 e 9 atualizadas. |
| 0.4 | 02/11/2026 | Decisões do grupo: D8, D10 a D12, D14 a D16 e D18 a D21 passam a Decidido; HIV/AIDS descartado; novas D22 (Libéria, proposta) e D23 (China no SARS); recontagem das rotas e exceções por aeroporto (3.6, 7.4); coluna `parent_iso3` na tabela de apelidos (6.4); formato da geometria (D20, 6.5); biblioteca de geometria a confirmar com o professor (7.1, 8); fontes do Kaggle corrigidas (2.4); pontos em aberto atualizados. |
| 0.5 | 03/11/2026 | D22 (Libéria) passa a Decidido; nova D24 (população do Norte do Chipre somada ao Chipre, 6.1); pontos em aberto atualizados; referências em BibTeX e ABNT (2.4). |
| 0.6 | 03/11/2026 | Conferência do arquivo do Natural Earth: chaves e universo de 230 entidades confirmados, D15 e seção 6.5 ajustadas (chave `ISO_A3_EH`, antimeridiano, tamanho do `countries.geojson`). |
| 0.7 | 03/11/2026 | Universo corrigido para **229 entidades**: `OWID_CYN` é entidade própria com continente (Ásia), agregada ao Chipre (3.5, 6.1, 7.2, 7.5, D24). Recontagem de rotas marcada como pendente (3.6). Entrada do Natural Earth em GeoJSON, convertido uma vez de shapefile (2.1, 6.5, 7.1, 9); `pyshp` deixa de ser necessário. Licenças conferidas (2.4, D25). Repositório público (D25; estrutura de pastas, seção 5). Pendências atualizadas (8). |
