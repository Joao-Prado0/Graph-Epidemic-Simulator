# Benchmarks de Desempenho (M2)

Esta pasta concentra o script de benchmark de desempenho do núcleo do grafo e dos algoritmos de análise (`benchmarks/bench_grafo.py`), incluindo a comparação direta com o **NetworkX** exigida pelo enunciado (RNF01, RNF02 e RNF09).

> **Regra do projeto:** `benchmarks/` é o **único** diretório do repositório onde a importação de `networkx` é permitida (verificada automaticamente via Ruff `TID251` e `pytest`).

## Como executar

Com o ambiente virtual ativo na raiz do repositório:

```powershell
# Execução completa nos tamanhos de referência (1.000, 5.000, 10.000 e 50.000 vértices)
python benchmarks/bench_grafo.py

# Execução rápida para validação local (500, 1.000 e 2.500 vértices)
python benchmarks/bench_grafo.py --quick

# Exportar tabela para CSV
python benchmarks/bench_grafo.py --csv benchmarks/resultados_benchmark.csv
```
