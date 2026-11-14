"""Exceções de domínio do Simulador de Epidemias.
Concentra a hierarquia de erros próprios do núcleo para que as camadas de
domínio nunca dependam de caixas de diálogo ou componentes de interface.
"""

from __future__ import annotations


class EpidemiaError(Exception):
    """Classes base para todas as exceções de domínio do simulador."""


class ParameterOutOfRangeError(EpidemiaError, ValueError):
    """Indica que um parâmetro de configuração ou modelo está fora da faixa válida"""


class GraphError(EpidemiaError):
    """Indica uma operação inválida na estrutura ou nos algoritmos do grafo."""


class VertexNotFoundError(GraphError, KeyError):
    """Indica referência a um índice de vértice inexistente ou removido"""


class InvalidEdgeError(GraphError, ValueError):
    """Indica a tentativa de criar ou acessar uma aresta inválida (ex.: auto-laço ou peso <= 0)"""


class InvalidDatasetError(EpidemiaError):
    """Indica inconsistência estrutural ou de esquema nos arquivos de data/processed/."""
