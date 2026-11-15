"""Motor de simulação epidemiológica SEIRD sobre grafo ponderado (M3)."""

from epidemia.core.epidemic.calibration import (
    DEFAULT_BETA_MAX,
    DEFAULT_BETA_MIN,
    DEFAULT_CALIBRATION_HORIZON_DAYS,
    DEFAULT_CALIBRATION_TRIALS,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_TOLERANCE,
    CalibrationResult,
    calibrate_beta,
    measure_empirical_r0,
    newman_analytic_r0,
)
from epidemia.core.epidemic.engine import DayRecord, EpidemicEngine
from epidemia.core.epidemic.interventions import (
    apply_daily_isolation,
    apply_daily_vaccination,
    release_isolation,
)
from epidemia.core.epidemic.model import (
    DeterministicTrajectory,
    edge_infection_probability,
    exit_probability,
    progression_probability,
    rate_to_daily_probability,
    solve_mean_field_seird,
)
from epidemia.core.epidemic.parameters import (
    DEFAULT_VACCINE_EFFICACY,
    INTERVENTION_TABLE,
    LEVEL_HIGH,
    LEVEL_LOW,
    LEVEL_MEDIUM,
    LEVEL_NONE,
    InterventionParams,
    SimulationConfig,
    normalize_intervention_level,
    resolve_intervention_params,
)

__all__ = [
    "CalibrationResult",
    "DEFAULT_BETA_MAX",
    "DEFAULT_BETA_MIN",
    "DEFAULT_CALIBRATION_HORIZON_DAYS",
    "DEFAULT_CALIBRATION_TRIALS",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_TOLERANCE",
    "DEFAULT_VACCINE_EFFICACY",
    "DayRecord",
    "DeterministicTrajectory",
    "EpidemicEngine",
    "INTERVENTION_TABLE",
    "InterventionParams",
    "LEVEL_HIGH",
    "LEVEL_LOW",
    "LEVEL_MEDIUM",
    "LEVEL_NONE",
    "SimulationConfig",
    "apply_daily_isolation",
    "apply_daily_vaccination",
    "calibrate_beta",
    "edge_infection_probability",
    "exit_probability",
    "measure_empirical_r0",
    "newman_analytic_r0",
    "normalize_intervention_level",
    "progression_probability",
    "rate_to_daily_probability",
    "release_isolation",
    "resolve_intervention_params",
    "solve_mean_field_seird",
]
