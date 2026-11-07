# Setup do ambiente: Simulador de Epidemias em Redes

Passo a passo para colocar o projeto de pé em Windows, com VS Code, Python 3.12 e GitHub. Versão 1.2, 03/11/2026. Complementa o documento de apoio (v0.7), o documento de dados (v0.7), o documento de modelagem (revisão 1) e o documento de arquitetura (v0.5).

## 0. Como ler este guia

| Quem faz | Passos |
|---|---|
| Todos juntos | 1 e 2 |
| Uma pessoa só (dono do repositório) | 3 e 4 |
| Cada integrante | 5, 6, 8, 9 e 10 |
| Só quem implementa o módulo M4 (dados) | 7 |
| Uma pessoa, depois que todos validarem | 11 |

### Por que o setup tem estes itens

O ambiente foi desenhado a partir das decisões já fechadas:

| Decisão do projeto | Efeito no setup |
|---|---|
| Sem bibliotecas prontas de grafo (NetworkX só no benchmark) | NetworkX fica em `requirements-dev.txt`, em uma pasta `benchmarks/` separada, com regra automática (Ruff e pytest) que barra o uso em `src/` |
| NumPy liberado pelo professor (03/11/2026) | Pode ser usado no núcleo do grafo; a versão entra no `requirements.txt` ao ser fixada (passo 15) |
| Scripts de dados rodam offline, com pandas fora do `requirements.txt` do app (D5 a D7) | Segundo ambiente virtual (`.venv-data`), usado só por quem prepara os dados |
| Brutos fora do repositório; `data/processed/` versionado (D6) | Pasta de brutos fora do projeto; `data/` com README, tabela de apelidos e `processed/` |
| Repositório público, com dados derivados sob ODbL (D25) | Licença ODbL em `data/LICENSE-ODbL.txt`; licença do código na raiz; CSVs brutos do Kaggle fora do Git |
| Natural Earth entra em GeoJSON (dados, D20) | Conversão única do shapefile antes do script (passo 7) |
| Dados embutidos no executável (RNF10) | Passo de empacotamento com `--add-data` documentado |
| Simulação em thread separada, buffer de estados por dia (E2, RNF03) | A prova de conceito do passo 4.5 já usa QThread e um buffer de bytearrays |
| 8 mil vértices a pelo menos 20 quadros por segundo (RNF02), no computador mais fraco do grupo | A prova de conceito mede o FPS com 8 mil pontos em QPainter; o checklist coleta os números de cada máquina |
| Python 3.12 para todos | `requires-python` restrito a 3.12 no `pyproject.toml` |
| Commits individuais avaliados, 5 integrantes | Configuração de Git por pessoa, branches, pull requests e CI opcional |
| Só Windows | Comandos em PowerShell; o executável é gerado no Windows |

---

## 1. Instalar as ferramentas (todos)

1. **Python 3.12.10** em python.org/downloads (a mesma versão 3.12 para todos). No instalador, marque **"Add python.exe to PATH"** e mantenha o **py launcher**.
2. **Git for Windows** em git-scm.com (opções padrão).
3. **VS Code** em code.visualstudio.com.
4. Conta no **GitHub**, com o mesmo e-mail que será usado nos commits.

Confira no PowerShell:

```powershell
py -3.12 --version
git --version
code --version
```

Se `py -3.12` falhar, o Windows pode estar usando o atalho da Microsoft Store. Vá em Configurações, Aplicativos, Configurações avançadas, Aliases de execução de aplicativo, e desligue `python.exe` e `python3.exe`.

## 3. Criar o repositório no GitHub (uma pessoa)

1. No GitHub: **New repository**, nome `simulador-epidemias`, **público** (decisão D25 dos dados), **sem** README, `.gitignore` ou licença. Os arquivos são criados localmente nos passos seguintes.
2. Em **Settings, Collaborators**, adicione os outros 4.
3. Em **Settings, Branches**, proteja a `main`: exigir pull request antes de mesclar.

## 4. Criar o esqueleto local e o primeiro commit (a mesma pessoa)

### 4.1 Pastas

```powershell
mkdir simulador-epidemias
cd simulador-epidemias
git init
mkdir src\epidemia, tests, benchmarks, scripts, .vscode, .github\workflows, data\processed, docs\diagramas, docs\relatorio
New-Item src\epidemia\__init__.py, tests\__init__.py, benchmarks\.gitkeep, data\processed\.gitkeep, docs\diagramas\.gitkeep, docs\relatorio\.gitkeep -ItemType File
```

Resultado:

```
simulador-epidemias/
├── .github/workflows/ci.yml        # CI opcional (passo 4.4)
├── .vscode/                        # settings.json e extensions.json
├── benchmarks/                     # único lugar onde NetworkX é permitido
├── data/
│   ├── README.md                   # origem dos brutos, passo a passo, atribuições
│   ├── LICENSE-ODbL.txt            # licença dos dados derivados (D25); criado no passo 4.2
│   ├── country_aliases.csv         # alias -> ISO3 (ou DROP)
│   ├── requirements-data.txt       # dependências do script de preparação
│   ├── prepare_data.py             # criado depois pelo responsável pelo M4
│   └── processed/                  # o que o aplicativo carrega (versionado)
├── docs/
│   ├── arquitetura.md              # documento de arquitetura (cópia, passo 4.6)
│   ├── modelagem_simulador_epidemias.md
│   ├── dados_datasets_e_preparacao.md
│   ├── documento_apoio_simulador_epidemias.md
│   ├── setup_ambiente.md
│   ├── diagramas/                  # Mermaid ou PlantUML
│   └── relatorio/                  # fontes .tex que vão no .zip
├── scripts/build_exe.ps1
├── src/epidemia/                   # esqueleto provisório (ver 4.5)
├── tests/
├── LICENSE                         # licença do código (a definir; ver 4.2)
├── .gitattributes
├── .gitignore
├── pyproject.toml
├── README.md
├── requirements.txt
└── requirements-dev.txt
```

Os brutos **não** ficam no repositório nem em uma pasta do projeto (decisão D6). Cada pessoa que for rodar o script guarda os arquivos em uma pasta fora do repositório, por exemplo `C:\dados-brutos-epidemia\`.

### 4.2 Arquivos da raiz

**`.gitignore`**

```
.venv/
.venv-data/
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
.ruff_cache/
build/
dist/
*.spec
*.zip
.idea/
.vscode/*
!.vscode/settings.json
!.vscode/extensions.json
```

**`.gitattributes`**

```
* text=auto
*.py text eol=lf
*.md text eol=lf
*.csv text eol=lf
*.ps1 text eol=crlf
```

**`pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "epidemia"
version = "0.1.0"
requires-python = ">=3.12,<3.13"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "TID"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"networkx".msg = "NetworkX só é permitido em benchmarks/ (comparação de desempenho)."

[tool.ruff.lint.per-file-ignores]
"benchmarks/**" = ["TID251"]
```

**`requirements.txt`** (o que o aplicativo precisa para rodar)

```
PySide6
pyqtgraph
```

NumPy não aparece de propósito. O pyqtgraph o instala como dependência, então ele estará nas máquinas de todos, e o professor liberou o NumPy no núcleo do grafo (03/11/2026). O teste do passo 4.3 precisa ser ajustado na implementação (ver pendências).

**`requirements-dev.txt`** (desenvolvimento, testes, benchmark e empacotamento)

```
-r requirements.txt
pytest
ruff
pyinstaller
networkx
```

`networkx` entra aqui apenas para o benchmark.

**`data/requirements-data.txt`** (proposta; quem implementar o M4 pode ajustar)

```
pandas
shapely
```

`pandas` é a dependência prevista no documento de dados, para a leitura das séries e das tabelas. `shapely` faz a união das feições de um mesmo país e o cálculo dos centroides, incluindo o tratamento do antimeridiano (Rússia, Fiji, EUA). **[pendente: confirmar com o professor o uso de shapely no script de preparação.]** `pyshp` não é mais necessário, porque o Natural Earth entra em GeoJSON (dados, seção 2.1). São bibliotecas de preparação offline, não de grafos, e ficam fora do `requirements.txt` do aplicativo.

**`data/country_aliases.csv`** (só o cabeçalho por enquanto)

```
alias,iso3,parent_iso3,note
```

**`data/README.md`**

```
# Dados do projeto

Preparação dos datasets: ver docs/dados_datasets_e_preparacao.md.
O aplicativo lê apenas data/processed/. Arquivos brutos ficam fora do repositório.
Os dados derivados de OpenFlights (data/processed/edges.csv) são licenciados sob ODbL 1.0 (ver LICENSE-ODbL.txt).
```

**`data/LICENSE-ODbL.txt`**: copiar o texto da Open Database License 1.0 disponível em opendatacommons.org/licenses/odbl/1-0/, com o aviso de origem ao fim: "Contém dados do OpenFlights (openflights.org/data.php), sob ODbL 1.0; conteúdos sob DbCL." O arquivo acompanha `data/processed/edges.csv` (dados, D25).

**`LICENSE`** (raiz): licença do código do aplicativo. **[pendente: escolher a licença do código, por exemplo MIT; ela não cobre a pasta `data/`.]**

**`README.md`**: nome do projeto, um link para este guia (`docs/setup_ambiente.md`) e a indicação de que os dados em `data/processed/` têm licença própria.

**`scripts/build_exe.ps1`**

```powershell
$ErrorActionPreference = "Stop"
pyinstaller --noconfirm --clean --noconsole --name SimuladorEpidemias --paths src src\epidemia\main.py
# Quando o aplicativo passar a ler dados (RNF10), acrescentar:
#   --add-data "data\processed;data\processed"
Write-Host "Executavel em dist\SimuladorEpidemias\SimuladorEpidemias.exe"
```

### 4.3 Configuração do VS Code e testes

**`.vscode/settings.json`**

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": { "source.organizeImports": "explicit" }
  },
  "files.eol": "\n"
}
```

**`.vscode/extensions.json`**

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "eamodio.gitlens",
    "James-Yu.latex-workshop",
    "yzhang.markdown-all-in-one",
    "bierner.markdown-mermaid",
    "jebbs.plantuml"
  ]
}
```

Para os diagramas UML, **Mermaid é a opção mais simples**: não exige instalar nada. PlantUML é opcional e pede Java e Graphviz para renderizar localmente.

**`tests/test_smoke.py`**

```python
import importlib


def test_dependencias_importam():
    for nome in ("PySide6", "pyqtgraph"):
        importlib.import_module(nome)


def test_pacote_do_projeto_importa():
    import epidemia  # noqa: F401
```

**`tests/test_regras_projeto.py`** (protege duas regras do enunciado e da modelagem)

```python
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]

# Trocar para True quando o professor confirmar o uso de NumPy no núcleo do grafo.
NUMPY_LIBERADO = False


def _arquivos_que_importam(modulo: str) -> list[Path]:
    padrao = re.compile(rf"^\s*(import|from)\s+{modulo}\b", re.MULTILINE)
    return [
        arquivo
        for arquivo in (RAIZ / "src").rglob("*.py")
        if padrao.search(arquivo.read_text(encoding="utf-8"))
    ]


def test_networkx_nao_aparece_em_src():
    assert _arquivos_que_importam("networkx") == []


@pytest.mark.skipif(NUMPY_LIBERADO, reason="NumPy liberado pelo professor")
def test_numpy_nao_aparece_em_src():
    assert _arquivos_que_importam("numpy") == []
```

**`tests/architecture/test_camadas.py`**: as regras de dependência entre as camadas (arquitetura, seção 5) serão adicionadas quando o esqueleto de `src/epidemia/` for criado. **[pendente: criar junto com o esqueleto da arquitetura.]**

### 4.4 CI opcional (recomendado)

Roda Ruff e pytest a cada pull request, no mesmo Windows em que o grupo trabalha. **`.github/workflows/ci.yml`**:

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
jobs:
  testes:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: python -m pip install --upgrade pip
      - run: pip install -r requirements-dev.txt
      - run: pip install -e .
      - run: ruff check .
      - run: ruff format --check .
      - run: pytest
```

Depois de rodar a primeira vez, em **Settings, Branches**, marque o job `testes` como verificação obrigatória.

### 4.5 Prova de conceito do ambiente

`src/epidemia/main.py` é provisório e serve só para validar a infraestrutura em cada máquina. Ele exercita as quatro peças que o projeto vai usar: janela PySide6, desenho de pontos em lote com QPainter, simulação em QThread gravando um buffer de bytearrays (um por dia) e gráfico pyqtgraph. Os estados são aleatórios e **não representam o modelo epidemiológico**. Ele será substituído pelo esqueleto da arquitetura (v0.4, seção 8).

```python
"""Prova de conceito do ambiente (provisoria).

Valida PySide6, QPainter em lote, QThread com buffer de estados e pyqtgraph.
Os estados sao aleatorios: nao ha modelo epidemiologico aqui.
"""

import random
import sys
import time

import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

N_VERTICES = 8000
SEMENTE = 42
# Estados: 0=S, 1=E, 2=I, 3=R, 4=D
CORES = [
    QColor("#4caf50"),
    QColor("#ffb300"),
    QColor("#e53935"),
    QColor("#42a5f5"),
    QColor("#212121"),
]
PESOS = [0.70, 0.05, 0.15, 0.08, 0.02]


class Simulador(QThread):
    dia_gravado = Signal(int)

    def __init__(self, historico: list, n: int, semente: int):
        super().__init__()
        self._historico = historico
        self._n = n
        self._rng = random.Random(semente)

    def run(self):
        while not self.isInterruptionRequested():
            estados = bytearray(self._rng.choices(range(5), weights=PESOS, k=self._n))
            self._historico.append(estados)
            self.dia_gravado.emit(len(self._historico) - 1)
            self.msleep(100)


class Mapa(QWidget):
    def __init__(self, historico: list):
        super().__init__()
        rng = random.Random(SEMENTE)
        self._pontos = [(rng.random(), rng.random()) for _ in range(N_VERTICES)]
        self._historico = historico
        self._dia = 0
        self.quadros = 0
        self.setMinimumSize(640, 360)

    def mostrar_dia(self, dia: int):
        self._dia = dia

    def paintEvent(self, _evento):
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), QColor("#eceff1"))
        if self._historico:
            estados = self._historico[self._dia]
            largura, altura = self.width(), self.height()
            grupos = [QPolygonF() for _ in CORES]
            for (x, y), estado in zip(self._pontos, estados):
                grupos[estado].append(QPointF(x * largura, y * altura))
            for cor, grupo in zip(CORES, grupos):
                caneta = QPen(cor)
                caneta.setWidth(4)
                caneta.setCapStyle(Qt.RoundCap)
                pintor.setPen(caneta)
                pintor.drawPoints(grupo)
            self.quadros += 1
        pintor.end()


class Janela(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulador de Epidemias - verificacao do ambiente")
        self.historico: list[bytearray] = []
        self.infectados: list[int] = []

        self.mapa = Mapa(self.historico)
        self.grafico = pg.PlotWidget(title="Infectados (I) por dia")
        self.curva = self.grafico.plot([], [], pen=pg.mkPen("#e53935", width=2))
        self.rotulo = QLabel("FPS: -")

        caixa = QVBoxLayout()
        caixa.addWidget(self.mapa, 3)
        caixa.addWidget(self.grafico, 1)
        caixa.addWidget(self.rotulo)
        centro = QWidget()
        centro.setLayout(caixa)
        self.setCentralWidget(centro)

        self.simulador = Simulador(self.historico, N_VERTICES, SEMENTE)
        self.simulador.dia_gravado.connect(self._novo_dia)
        self.simulador.start()

        self._t0 = time.perf_counter()
        self.timer_quadro = QTimer(self)
        self.timer_quadro.timeout.connect(self.mapa.update)
        self.timer_quadro.start(16)
        self.timer_fps = QTimer(self)
        self.timer_fps.timeout.connect(self._atualizar_fps)
        self.timer_fps.start(1000)

    def _novo_dia(self, dia: int):
        self.mapa.mostrar_dia(dia)
        self.infectados.append(self.historico[dia].count(2))
        self.curva.setData(self.infectados)

    def _atualizar_fps(self):
        agora = time.perf_counter()
        fps = self.mapa.quadros / (agora - self._t0)
        self.mapa.quadros = 0
        self._t0 = agora
        self.rotulo.setText(
            f"{N_VERTICES} vertices | FPS: {fps:.1f} | dias gravados: {len(self.historico)}"
        )

    def closeEvent(self, evento):
        self.simulador.requestInterruption()
        self.simulador.wait(2000)
        super().closeEvent(evento)


def main() -> int:
    app = QApplication(sys.argv)
    janela = Janela()
    janela.resize(900, 700)
    janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

### 4.6 Documentos e primeiro commit

Copie para `docs/` os documentos do projeto, com as versões atuais:

- `modelagem_simulador_epidemias.md` (revisão 1);
- `dados_datasets_e_preparacao.md` (v0.7);
- `arquitetura.md` (v0.4), a partir de `arquitetura_simulador_epidemias.md`;
- `documento_apoio_simulador_epidemias.md` (v0.6, em markdown);
- `setup_ambiente.md` (este guia, v1.1).

Assim todo o grupo, e qualquer assistente de IA usado na implementação, parte do mesmo contexto. Quando algum desses documentos for atualizado, substitua a cópia.

Faça os passos 6 e 9 na sua máquina e, com tudo funcionando:

```powershell
git add .
git commit -m "Esqueleto inicial do projeto e configuracao do ambiente"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/simulador-epidemias.git
git push -u origin main
```

Como a `main` está protegida, se o push direto for recusado, crie o primeiro commit antes de ativar a proteção, ou faça o push por uma branch e abra o pull request.

## 5. Clonar o repositório (os outros 4)

```powershell
git clone https://github.com/USUARIO-DO-DONO/simulador-epidemias.git
cd simulador-epidemias
code .
```

## 6. Criar o ambiente virtual do aplicativo (cada integrante)

Na raiz do projeto:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python --version
```

Deve mostrar 3.12.10. Se mostrar outra versão, apague a pasta `.venv` e refaça. Se o PowerShell bloquear o script de ativação, rode uma vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Instale as dependências e o pacote do projeto em modo editável:

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

O `pip install -e .` faz o pacote `epidemia` ser encontrado de qualquer pasta, tanto pelo VS Code quanto pelos testes e pelo PyInstaller.

## 7. Ambiente de dados (só quem implementa o M4)

O script `prepare_data.py` roda **offline, uma vez**, e o resultado em `data/processed/` é versionado no Git (D5 a D7). O aplicativo nunca roda o script. Por isso o ambiente é separado:

```powershell
py -3.12 -m venv .venv-data
.venv-data\Scripts\Activate.ps1
pip install -r data\requirements-data.txt
```

Os arquivos brutos (COVID JHU, Ebola, H1N1, SARS, OWID, OpenFlights e Natural Earth 50m versão 5.1.1) ficam em uma pasta fora do projeto. O Natural Earth precisa de uma conversão única antes do script: converter o shapefile (`.shp`, `.dbf`, `.shx`, `.prj`) para GeoJSON, com qualquer ferramenta de conversão, e salvar o resultado como `ne_50m_admin_0_countries.json` na mesma pasta. Depois, o script recebe o caminho:

```powershell
python data\prepare_data.py --raw C:\dados-brutos-epidemia --out data\processed
```

Antes de publicar o resultado, confira as citações das fontes (documento de dados, seção 2.4). O arquivo `data\LICENSE-ODbL.txt` deve acompanhar `data\processed\edges.csv` no commit (D25). Para voltar ao ambiente do aplicativo, rode `deactivate` e ative o `.venv`.

## 8. Configurar o VS Code (cada integrante)

1. Ao abrir a pasta, aceite **"Instalar extensões recomendadas"**.
2. `Ctrl+Shift+P`, **Python: Select Interpreter**, e escolha o do `.venv`.
3. Abra um terminal novo (`Ctrl+'`) e veja se aparece `(.venv)`.
4. Quem for mexer nos dados escolhe o interpretador `.venv-data` apenas nos arquivos de `data/`.

## 9. Validar a máquina (cada integrante)

Com o `.venv` ativo, na raiz:

```powershell
python -m epidemia.main
pytest
ruff check .
ruff format --check .
```

A janela da prova de conceito deve abrir, mostrando 8 mil pontos mudando de cor, uma curva de infectados e, embaixo, a linha com o FPS. Deixe rodar uns 10 segundos e **anote o FPS**, que é o primeiro dado do benchmark do RNF02 (meta de 20 quadros por segundo ou mais). Feche a janela pelo X e confirme que o processo termina sem travar, o que valida o encerramento da thread. (João Prado 07/11 fps com media em 40)

Depois gere o executável:

```powershell
.\scripts\build_exe.ps1
```

O resultado fica em `dist\SimuladorEpidemias\`. Abra o `.exe` **fora do VS Code** e veja se a janela aparece e se o FPS é parecido com o do modo normal. A pasta é mais confiável com Qt que `--onefile`, que abre mais devagar; o formato final do executável fica para a fase de empacotamento.

Se o Windows Defender marcar o executável como suspeito (acontece com executáveis gerados por PyInstaller), anote, porque isso precisa ser considerado na entrega. Nuitka só entra se houver problema de build ou de desempenho. (João Prado 07/11 não aconteceu, abriu normal)

## 11. Fixar as versões (uma pessoa, depois que todos validarem)

Os arquivos de requisitos estão sem versão para o primeiro teste. Quando os 5 tiverem instalado sem erro:

```powershell
pip freeze
```

Copie as versões **apenas dos pacotes que estão nos arquivos de requisitos** (PySide6, pyqtgraph, pytest, ruff, pyinstaller, networkx e, em `data/requirements-data.txt`, pandas e shapely) para o formato `PySide6==x.y.z` e faça um commit. Assim todos usam as mesmas versões.

## 12. Relatório em LaTeX e diagramas

- **Relatório:** o enunciado exige o template oficial da SBC. O caminho mais simples é escrever no **Overleaf**, usando o template indicado no enunciado, e copiar os fontes `.tex` para `docs/relatorio/` a cada marco (e antes da entrega), já que o `.zip` precisa conter o `.tex` e o PDF. Quem preferir editar localmente precisa instalar o MiKTeX ou o TeX Live, que são pesados, junto com a extensão LaTeX Workshop.
- **Diagramas UML:** em `docs/diagramas/`, em Mermaid ou PlantUML, versionados como texto.
- **Responsabilidades por membro:** o relatório precisa indicar o que cada um fez; manter essa lista desde o início facilita.

## 13. Checklist de validação

Cada integrante devolve ao grupo:

| Item | Resultado |
|---|---|
| `python --version` dentro do `.venv` | 3.12.10 |
| `pip install -r requirements-dev.txt` e `pip install -e .` sem erro | sim/não |
| Janela da prova de conceito abre e fecha sem travar | sim/não |
| FPS com 8.000 vértices (modo Python) | número |
| `pytest`, `ruff check` e `ruff format --check` passam | sim/não |
| Executável gerado e abre fora do VS Code | sim/não |
| FPS do executável | número |
| Commit de teste aparece com o seu nome no GitHub | sim/não |
| Dados da máquina: processador, memória RAM e se tem placa de vídeo dedicada | texto |

A última linha serve para identificar a **máquina mais fraca do grupo**, que é a referência do benchmark (1 mil, 5 mil, 10 mil e 50 mil vértices) e da escolha final de N_total.

Para a verificação do protótipo com os limiares de exibição de vértices (40 px para mostrar e 36 px para ocultar, arquitetura seção 4.1), quem fizer o teste visual com o mapa completo anota o zoom em que os vértices aparecem em cada país de referência (Brasil, Índia, Cuba, Suíça e Cabo Verde) e registra no checklist.

## 14. Problemas comuns no Windows

| Sintoma | O que fazer |
|---|---|
| `py -3.12` não encontrado ou abre a Microsoft Store | Desligar os aliases de execução do Python (passo 1) e reinstalar com o py launcher |
| "A execução de scripts foi desabilitada" ao ativar o venv | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: epidemia` | Ativar o `.venv` e rodar `pip install -e .` |
| VS Code não acha o interpretador | `Ctrl+Shift+P`, Python: Select Interpreter, escolher o `.venv` |
| Aviso de quebra de linha (CRLF/LF) no Git | Já tratado por `core.autocrlf` e `.gitattributes`; não alterar |
| Executável fecha logo ao abrir | Rodar `dist\SimuladorEpidemias\SimuladorEpidemias.exe` pelo terminal sem `--noconsole` (editar temporariamente o script de build) para ver o erro |
| Antivírus bloqueia o `.exe` | Registrar o caso; não desativar o antivírus da máquina inteira |

## 15. Pontos em aberto que afetam o setup

Resolvidos nesta versão e removidos da lista: local do GeoJSON do mapa (`data/processed/countries.geojson`, decisão C3); geometria do aplicativo só com biblioteca padrão (arquitetura, ponto 9.2, item 4); estrutura interna de `src/epidemia/` (arquitetura v0.4, seção 8); e a licença dos dados (ODbL, D25).

Continuam abertos:

- **NumPy no núcleo do grafo (D17): liberado pelo professor (03/11/2026).** Ajustar `NUMPY_LIBERADO` em `tests/test_regras_projeto.py` e listar `numpy` no `requirements.txt` na implementação.
- **shapely no script de preparação: liberado pelo professor (03/11/2026).** A união de polígonos e o centroide usam shapely.
- **[pendente] Licença do código (raiz):** escolher, por exemplo MIT. Ela não cobre `data/`.
- **[pendente] Dados no executável (RNF10):** acrescentar `--add-data "data\processed;data\processed"` ao `build_exe.ps1` e acessar os arquivos por caminho que funcione dentro do executável, quando o aplicativo passar a ler dados.
- **[pendente] Testes de arquitetura:** `tests/architecture/test_camadas.py` será criado junto com o esqueleto de `src/epidemia/`.
- **[pendente] Pasta `benchmarks/`:** ainda vazia; é onde o NetworkX poderá ser usado quando o benchmark for implementado.

---

## 16. Histórico de alterações

| Versão | Data | Mudanças |
|---|---|---|
| 1.0 | 31/10/2026 | Primeira versão do guia de setup. |
| 1.1 | 03/11/2026 | Python 3.12 restrito no `pyproject.toml`; `pyshp` removido do ambiente de dados e conversão do Natural Earth para GeoJSON incluída no passo 7; licença ODbL em `data/` e licença do código na raiz (passos 3, 4.1, 4.2 e 10); repositório público (passo 3); cópias dos documentos atualizadas (4.6); checklist com o teste dos limiares de vértices (13); pendências atualizadas (15). |
| 1.2 | 03/11/2026 | Equipe de 5 integrantes (§3, §5, §11 e tabela inicial de avaliação); documento de apoio na v0.7 e arquitetura na v0.5, que dividem o trabalho em 5 módulos. |
