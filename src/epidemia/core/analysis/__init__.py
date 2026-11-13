"""Subpacote de análise estrutural de grafos (M2)."""

from epidemia.core.analysis.bridges import (
    TarjanResult,
    find_articulation_points,
    find_bridges,
    find_bridges_and_articulation_points,
)
from epidemia.core.analysis.communities import (
    CommunityResult,
    ContractedGraph,
    contract_graph_by_country,
    label_propagation_communities,
)
from epidemia.core.analysis.metrics import (
    GraphLike,
    average_clustering_coefficient,
    average_degree,
    betweenness_centrality,
    clustering_coefficients,
    degrees,
    local_clustering_coefficient,
    vertex_degree,
)

__all__ = [
    "CommunityResult",
    "ContractedGraph",
    "GraphLike",
    "TarjanResult",
    "average_clustering_coefficient",
    "average_degree",
    "betweenness_centrality",
    "clustering_coefficients",
    "contract_graph_by_country",
    "degrees",
    "find_articulation_points",
    "find_bridges",
    "find_bridges_and_articulation_points",
    "label_propagation_communities",
    "local_clustering_coefficient",
    "vertex_degree",
]
