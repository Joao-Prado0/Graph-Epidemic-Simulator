"""Exporta a API pública do pacote ``core.timeline`` (M3)."""

from epidemia.core.timeline.buffer import (
    DEFAULT_DAY_ZERO_VERTEX_THRESHOLD,
    SimulationTimeline,
    StateBuffer,
)
from epidemia.core.timeline.protocol import (
    FLAG_ISOLATED,
    FLAG_VACCINATED,
    STATE_D,
    STATE_E,
    STATE_I,
    STATE_MASK,
    STATE_R,
    STATE_S,
    CompartmentCounts,
    CountryCounts,
    CountryInfo,
    Timeline,
    decode_vertex_state,
    encode_vertex_byte,
    is_isolated_byte,
    is_vaccinated_byte,
)

__all__ = [
    "DEFAULT_DAY_ZERO_VERTEX_THRESHOLD",
    "FLAG_ISOLATED",
    "FLAG_VACCINATED",
    "STATE_D",
    "STATE_E",
    "STATE_I",
    "STATE_MASK",
    "STATE_R",
    "STATE_S",
    "CompartmentCounts",
    "CountryCounts",
    "CountryInfo",
    "SimulationTimeline",
    "StateBuffer",
    "Timeline",
    "decode_vertex_state",
    "encode_vertex_byte",
    "is_isolated_byte",
    "is_vaccinated_byte",
]
