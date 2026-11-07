# Simulador de Epidemias em Redes

Trabalho Prático da disciplina de **Teoria dos Grafos** (Tema 7) — PUC Minas.

Aplicação desktop em Python 3.12 (PySide6 + pyqtgraph) para simulação epidemiológica (modelo SEIRD com isolamento e vacinação automáticos) e reprodução de pandemias históricas (COVID-19, Ebola, H1N1 e SARS) sobre um grafo global unificado.

## Documentação e Setup

- **Guia de configuração do ambiente:** [docs/planning-dev-docs/LLMFiles/setup_ambiente.md](docs/planning-dev-docs/LLMFiles/setup_ambiente.md)
- **Arquitetura e estrutura de pastas:** [docs/planning-dev-docs/LLMFiles/arquitetura_simulador_epidemias.md](docs/planning-dev-docs/LLMFiles/arquitetura_simulador_epidemias.md)
- **Modelagem matemática e epidemiológica:** [docs/planning-dev-docs/LLMFiles/modelagem_simulador_epidemias.md](docs/planning-dev-docs/LLMFiles/modelagem_simulador_epidemias.md)
- **Preparação e normalização de dados:** [docs/planning-dev-docs/LLMFiles/dados_datasets_e_preparacao.md](docs/planning-dev-docs/LLMFiles/dados_datasets_e_preparacao.md)
- **Divisão de responsabilidades por módulo:** [docs/planning-dev-docs/LLMFiles/responsabilidades_modulos.md](docs/planning-dev-docs/LLMFiles/responsabilidades_modulos.md)

## Execução Rápida

Com o ambiente virtual `.venv` ativo:

```powershell
# Executar a aplicação
python -m epidemia.main

# Executar testes e verificação de código
pytest
ruff check .
ruff format --check .
```

## Licenças

- O código-fonte do aplicativo segue a licença definida em `LICENSE` na raiz do repositório.
- Essa licença **não cobre** a pasta `data/`. Os dados processados em `data/processed/` (incluindo `edges.csv`, derivado do OpenFlights) possuem licenciamento próprio sob **ODbL 1.0** — consulte [data/README.md](data/README.md) e [data/LICENSE-ODbL.txt](data/LICENSE-ODbL.txt).
