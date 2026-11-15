# Módulo M5: Interface Gráfica, Mapa e Resultados (`ui/`)

Esta pasta contém a camada visual e de interação com o usuário do **Simulador de Epidemias em Redes**, construída em **Python 3.12** com **PySide6** (Qt) e **pyqtgraph**.

---

## 1. Estrutura dos Arquivos

- **`main_window.py`**: Janela principal da aplicação (`MainWindow`), contendo duas abas:
  - **Simulação**: mapa interativo, player temporal, gráficos em tempo real, painel de configuração e painel de métricas da epidemia e da rede.
  - **Pandemias reais**: lista das pandemias embutidas (COVID-19, Ebola, H1N1, SARS), exibindo metadados de cenário enquanto aguarda o processamento do M4.
  - Inclui o worker assíncrono `NetworkAnalysisWorker` para cálculo de métricas de rede (grau, intermediação aproximada e comunidades) sem travar a interface.
- **`config_panel.py`**: Painel lateral com campos e sliders para configuração dos parâmetros SEIRD (R0 informado, γ, mortalidade, incubação), intervenções (isolamento e vacinação), semente aleatória, paciente zero, calibração de β e botões para salvar/carregar configurações em JSON.
- **`map_view.py`**: Renderizador do mapa global (`MapView` e `MapCanvas`) utilizando `QPainter` em lote com caminhos pré-calculados (`QPainterPath`):
  - Coloração dos polígonos dos países por status epidemiológico dominante do dia (ou intensidade de casos por 100 mil habitantes no fluxo real).
  - Exibição de nós individuais condicionada aos limiares de largura do país na tela (histerese: entrada a $\ge 40\text{ px}$, saída abaixo de $36\text{ px}$).
  - Suporte a zoom (+/− e roda do mouse), arraste (pan), botão de ajuste automático e tooltip com informações do país ao passar o cursor.
- **`player_bar.py`**: Barra de reprodução temporal (`PlayerBar`) conectada ao `PlaybackController`:
  - Botões de play, pausa, avanço diário (+1d), recuo (-1d) e reinício (reset).
  - Seletor exclusivo de velocidade ($\times 1, \times 2, \times 5, \times 10$).
  - Slider temporal para navegação direta pelos dias gravados.
- **`charts_view.py`**: Visualizador de séries temporais com `pyqtgraph` (`ChartsView`):
  - Curvas dos compartimentos S (verde), E (laranja), I (vermelho), R (azul) e D (cinza).
  - Marcador vertical indicando o dia atualmente exibido no player.
  - Exportação direta do gráfico em imagem PNG via `pyqtgraph.exporters.ImageExporter`.
- **`simulation_thread.py`**: Thread trabalhadora desacoplada (`SimulationThread`, `QThread`):
  - Executa calibração de $\beta$, inicialização e laço de `session.run_day()` fora da thread de GUI (RNF03).
  - Anuncia novos dias por meio do sinal `day_ready(int)`.
- **`styles.py`**: Definições visuais, paleta oficial de cores dos compartimentos, parâmetros de histerese e folha de estilo completa em QSS para o tema escuro.

---

## 2. Como Rodar a Aplicação

### Pré-requisitos
Instale as dependências do projeto:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Execução via Linha de Comando
Na raiz do repositório, execute:
```bash
python -m epidemia.main
```

### Execução dos Testes
Para rodar a suíte de testes unitários e de integração da interface (em modo offscreen, sem abrir janelas):
```bash
pytest tests/
```
