# Dados do Projeto: Simulador de Epidemias em Redes (M4)

Este diretório gerencia os dados de entrada, a normalização geográfica e o pipeline
offline de pré-processamento para o Simulador de Epidemias.

---

## Estrutura do Diretório

```
data/
├── README.md              # Este documento (atribuições, instruções e decisões)
├── LICENSE-ODbL.txt       # Licença ODbL 1.0 do conjunto derivado de rotas aéreas
├── country_aliases.csv    # Dicionário de sinônimos, exceções IATA e territórios agregados
├── prepare_data.py        # Script unificado de pré-processamento offline (M4)
├── requirements-data.txt  # Dependências do ambiente offline (pandas, shapely)
└── processed/             # Única pasta de dados consumida pelo aplicativo (versionada)
    ├── countries.csv      # Tabela mestra com 229 entidades e atributos estáticos
    ├── countries.geojson  # Geometrias unificadas dos polígonos dos países
    ├── edges.csv          # Arestas internacionais brutas baseadas em rotas aéreas
    ├── covid19.csv        # Série temporal contínua da COVID-19 (JHU CSSE / OMS)
    ├── ebola.csv          # Série temporal contínua do surto de Ebola 2014–2016
    ├── h1n1.csv           # Série temporal contínua da Gripe Suína A(H1N1) 2009
    └── sars.csv           # Série temporal do SARS 2003 (com recuperados)
```

---

## Como Reproduzir a Preparação dos Dados

Conforme as decisões **D5 a D7**, o aplicativo em execução lê apenas os arquivos já
processados em `data/processed/`. O script de preparação roda **offline**, uma única vez.

### 1. Criar e Ativar o Ambiente de Dados
```powershell
py -3.12 -m venv .venv-data
.venv-data\Scripts\Activate.ps1
pip install -r data\requirements-data.txt
```

### 2. Obter os Arquivos Brutos
Baixe os arquivos das fontes oficiais para uma pasta externa (ex.: `C:\dados-brutos-epidemia\`):
- **OWID**: `owid-covid-data.csv`
- **Natural Earth**: `ne_50m_admin_0_countries.json` (convertido previamente do shapefile 50m v5.1.1)
- **OpenFlights**: `airports.dat`, `routes.dat`, `countries.dat`
- **COVID-19 (JHU)**: `RAW_global_confirmed_cases.csv`, `RAW_global_deaths.csv`
- **Ebola 2014–2016**: `ebola_2014_2016_clean.csv`
- **H1N1 2009**: `data.csv`
- **SARS 2003**: `sars_2003_complete_dataset_clean.csv`

### 3. Executar o Script
```powershell
python data/prepare_data.py --raw C:\dados-brutos-epidemia --out data/processed
```

---

## Licenças e Atribuição das Fontes de Dados (ABNT)

Conforme a decisão **D25**, o repositório é público e os dados derivados seguem as licenças originais:

1. **Johns Hopkins University CSSE (COVID-19):**
   - Licença: Creative Commons Attribution 4.0 International (CC BY 4.0).
   - Atribuição: *"COVID-19 Data Repository by the Center for Systems Science and Engineering (CSSE) at Johns Hopkins University"*, https://github.com/CSSEGISandData/COVID-19. Citação: Dong, Du & Gardner (2020), *The Lancet Infectious Diseases*, 20(5):533–534.
2. **Our World in Data (OWID):**
   - Licença: Creative Commons BY (CC BY 4.0).
   - Atribuição: *"Our World in Data COVID-19 dataset"*, https://github.com/owid/covid-19-data. Casos e mortes originários da OMS.
3. **Natural Earth (Admin 0 – Countries, 50m v5.1.1):**
   - Licença: Domínio Público.
   - Atribuição: *"Made with Natural Earth. Free vector and raster map data @ naturalearthdata.com"*.
4. **OpenFlights (Airport, Route and Airline Database):**
   - Licença: Open Database License (ODbL) 1.0 (base) e Database Contents License (DbCL) (conteúdo).
   - Atribuição: *"Contém dados do OpenFlights (https://openflights.org/data.php), sob ODbL 1.0; conteúdos sob DbCL. O arquivo data/processed/edges.csv é uma base derivada, licenciada sob a ODbL 1.0; método de derivação em data/prepare_data.py"*.
5. **Kaggle / imdevskp (Ebola, H1N1, SARS):**
   - Dados coletados de relatórios oficiais da Organização Mundial da Saúde (OMS). Não redistribuídos na forma bruta em repositório público; obtidos via script de extração offline.
