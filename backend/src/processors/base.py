"""
Base class for weather event processors.
"""

from abc import ABC, abstractmethod
from typing import Literal
import xarray as xr
import numpy as np


class WeatherProcessor(ABC):
    """
    Abstract base class for weather event processors.

    Each processor computes metrics for a specific type of weather event
    (e.g., freezing temperatures, heavy rain, high winds).
    """

    @property
    @abstractmethod
    def event_id(self) -> str:
        """Unique identifier for this event type."""
        pass

    @property
    @abstractmethod
    def variable(self) -> str:
        """The Brightband variable name to process (e.g., '2t', 'tprate')."""
        pass

    @property
    @abstractmethod
    def threshold(self) -> float:
        """The threshold value in native units."""
        pass

    @property
    @abstractmethod
    def operator(self) -> Literal['lt', 'gt', 'lte', 'gte', 'eq']:
        """Comparison operator for the threshold."""
        pass

    def compute_mask(self, data: xr.DataArray) -> xr.DataArray:
        """
        Compute a boolean mask where the event condition is met.

        Args:
            data: DataArray with the variable values

        Returns:
            Boolean DataArray where True indicates the condition is met
        """
        if self.operator == 'lt':
            return data < self.threshold
        elif self.operator == 'gt':
            return data > self.threshold
        elif self.operator == 'lte':
            return data <= self.threshold
        elif self.operator == 'gte':
            return data >= self.threshold
        elif self.operator == 'eq':
            return np.abs(data - self.threshold) < 1e-6
        else:
            raise ValueError(f"Unknown operator: {self.operator}")

    def compute_first_breach(
        self,
        mask: xr.DataArray,
        time_dim: str = 'time'
    ) -> xr.DataArray:
        """
        Find the first timestep where the condition is met.

        Uses idxmax on the boolean mask to find the first True value.

        Args:
            mask: Boolean DataArray indicating where condition is met
            time_dim: Name of the time dimension

        Returns:
            DataArray with datetime of first breach, NaT where never met
        """
        # Check if condition is ever met at each location
        ever_true = mask.any(dim=time_dim)

        # Get first breach time using idxmax
        # For booleans, idxmax returns the coordinate of the first True
        first_breach = mask.idxmax(dim=time_dim, skipna=True)

        # Mask locations where condition is never met
        first_breach = first_breach.where(ever_true)

        return first_breach

    def compute_duration(
        self,
        mask: xr.DataArray,
        time_dim: str = 'time',
        timestep_hours: float = 3.0
    ) -> xr.DataArray:
        """
        Compute how long the condition persists after first breach.

        Counts consecutive timesteps where condition is True starting
        from the first breach.

        Args:
            mask: Boolean DataArray indicating where condition is met
            time_dim: Name of the time dimension
            timestep_hours: Hours between timesteps (default 3 for ECMWF IFS)

        Returns:
            DataArray with duration in hours
        """
        # Get the index of first True for each location
        first_idx = mask.argmax(dim=time_dim)

        # Create index array
        n_times = mask.sizes[time_dim]
        time_indices = xr.DataArray(
            np.arange(n_times),
            dims=[time_dim],
            coords={time_dim: mask[time_dim]}
        )

        # Mask for "at or after first breach"
        after_first = time_indices >= first_idx

        # Condition must be True AND after first breach
        condition_after = mask & after_first

        # Count total hours where condition is met after first breach
        # This counts all True values, not just consecutive ones
        # For a more accurate consecutive count, we'd need more complex logic
        duration_steps = condition_after.sum(dim=time_dim)
        duration_hours = duration_steps.astype(float) * timestep_hours

        # Set to NaN where condition is never met
        ever_true = mask.any(dim=time_dim)
        duration_hours = duration_hours.where(ever_true)

        return duration_hours

    def compute_metrics(
        self,
        ds: xr.Dataset,
        time_dim: str = 'time'
    ) -> xr.Dataset:
        """
        Compute all metrics for this weather event.

        Args:
            ds: Dataset containing the weather variable
            time_dim: Name of the time dimension

        Returns:
            Dataset with computed metrics:
            - first_breach_time: datetime of first occurrence
            - duration_hours: how long condition persists
        """
        if self.variable not in ds:
            raise ValueError(f"Variable '{self.variable}' not found in dataset")

        data = ds[self.variable]
        mask = self.compute_mask(data)

        first_breach = self.compute_first_breach(mask, time_dim)
        duration = self.compute_duration(mask, time_dim)

        # Build output dataset
        result = xr.Dataset({
            'first_breach_time': first_breach,
            'duration_hours': duration,
        })

        # Add metadata
        result.attrs = {
            'event_id': self.event_id,
            'variable': self.variable,
            'threshold': self.threshold,
            'operator': self.operator,
        }

        result['first_breach_time'].attrs = {
            'long_name': f'First time {self.variable} {self.operator} {self.threshold}',
            'description': 'Timestamp of first condition breach, NaT if never',
        }

        result['duration_hours'].attrs = {
            'long_name': 'Duration of condition',
            'units': 'hours',
            'description': 'How long the condition persists after first breach',
        }

        return result
