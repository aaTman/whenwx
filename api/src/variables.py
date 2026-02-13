"""
Variable registry for weather variables.

Each variable defines its ECMWF name, unit conversions, and whether
it's a derived quantity (e.g., wind speed from u/v components).
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class VariableConfig:
    """Configuration for a weather variable."""
    id: str                          # Frontend-facing ID (e.g., '2t', 'wind_speed', 'tprate')
    label: str                       # Human-readable label
    ecmwf_variables: list[str]       # ECMWF variable name(s) to load
    display_unit: str                # Unit shown to users (e.g., '°C', 'km/h')
    storage_unit: str                # Unit in the dataset (e.g., 'K', 'm/s')
    to_display: Callable[[float], float] = field(default=lambda: lambda x: x)
    to_storage: Callable[[float], float] = field(default=lambda: lambda x: x)
    is_derived: bool = False         # True if computed from multiple variables


# --- Conversion functions ---

def _kelvin_to_celsius(k: float) -> float:
    return k - 273.15

def _celsius_to_kelvin(c: float) -> float:
    return c + 273.15

def _ms_to_kmh(ms: float) -> float:
    return ms * 3.6

def _kmh_to_ms(kmh: float) -> float:
    return kmh / 3.6


# --- Variable registry ---

VARIABLE_REGISTRY: dict[str, VariableConfig] = {}


def _register(config: VariableConfig) -> None:
    VARIABLE_REGISTRY[config.id] = config


_register(VariableConfig(
    id='2t',
    label='Temperature',
    ecmwf_variables=['2t'],
    display_unit='°C',
    storage_unit='K',
    to_display=_kelvin_to_celsius,
    to_storage=_celsius_to_kelvin,
))

_register(VariableConfig(
    id='wind_speed',
    label='Wind Speed',
    ecmwf_variables=['10u', '10v'],
    display_unit='km/h',
    storage_unit='m/s',
    to_display=_ms_to_kmh,
    to_storage=_kmh_to_ms,
    is_derived=True,
))


def get_variable(variable_id: str) -> Optional[VariableConfig]:
    """Look up a variable by its ID."""
    return VARIABLE_REGISTRY.get(variable_id)


def get_all_variables() -> list[VariableConfig]:
    """Return all registered variables."""
    return list(VARIABLE_REGISTRY.values())


# Legacy event mapping
LEGACY_EVENT_MAP: dict[str, dict] = {
    'freezing': {
        'variable': '2t',
        'threshold': 263.15,  # -10°C in Kelvin
        'operator': 'lt',
    },
}
