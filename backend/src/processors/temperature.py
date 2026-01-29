"""
Temperature threshold processor.
"""

from typing import Literal
from .base import WeatherProcessor


class TemperatureProcessor(WeatherProcessor):
    """
    Processor for temperature threshold events.

    Detects when temperature drops below or rises above a specified threshold.
    """

    def __init__(
        self,
        event_id: str,
        threshold_kelvin: float,
        operator: Literal['lt', 'gt', 'lte', 'gte'] = 'lt',
        variable: str = '2t'
    ):
        """
        Initialize the temperature processor.

        Args:
            event_id: Unique identifier for this event
            threshold_kelvin: Temperature threshold in Kelvin
            operator: Comparison operator ('lt' for cold, 'gt' for hot)
            variable: Brightband variable name (default: '2t' for 2m temperature)
        """
        self._event_id = event_id
        self._threshold = threshold_kelvin
        self._operator = operator
        self._variable = variable

    @property
    def event_id(self) -> str:
        return self._event_id

    @property
    def variable(self) -> str:
        return self._variable

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def operator(self) -> Literal['lt', 'gt', 'lte', 'gte', 'eq']:
        return self._operator

    @classmethod
    def celsius_to_kelvin(cls, celsius: float) -> float:
        """Convert Celsius to Kelvin."""
        return celsius + 273.15

    @classmethod
    def kelvin_to_celsius(cls, kelvin: float) -> float:
        """Convert Kelvin to Celsius."""
        return kelvin - 273.15

    @classmethod
    def freezing_below(cls, threshold_celsius: float = -10.0) -> 'TemperatureProcessor':
        """
        Create a processor for detecting freezing temperatures.

        Args:
            threshold_celsius: Temperature threshold in Celsius (default: -10°C)

        Returns:
            TemperatureProcessor configured for freezing detection
        """
        return cls(
            event_id='freezing',
            threshold_kelvin=cls.celsius_to_kelvin(threshold_celsius),
            operator='lt',
            variable='2t'
        )

    @classmethod
    def heat_above(cls, threshold_celsius: float = 35.0) -> 'TemperatureProcessor':
        """
        Create a processor for detecting high temperatures.

        Args:
            threshold_celsius: Temperature threshold in Celsius (default: 35°C)

        Returns:
            TemperatureProcessor configured for heat detection
        """
        return cls(
            event_id='heat',
            threshold_kelvin=cls.celsius_to_kelvin(threshold_celsius),
            operator='gt',
            variable='2t'
        )
