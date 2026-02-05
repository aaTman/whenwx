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
        timestep_hours: float = 1.0
    ) -> tuple[xr.DataArray, xr.DataArray]:
        """
        Compute hours from first breach until condition ends.

        Returns the duration of the contiguous event starting at first breach,
        ending when the condition is no longer met (or end of forecast).

        Args:
            mask: Boolean DataArray indicating where condition is met
            time_dim: Name of the time dimension
            timestep_hours: Hours between timesteps (default 1 for ECMWF IFS hourly data)

        Returns:
            Tuple of (duration_hours, end_idx) where:
            - duration_hours: DataArray with contiguous duration in hours
            - end_idx: DataArray with the index where the first event ends (for next breach calc)
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

        # Find first False AFTER first True (end of contiguous event)
        not_mask = ~mask
        after_first = time_indices > first_idx
        not_mask_after = not_mask & after_first

        # Find where condition ends (first timestep after first_idx where condition is False)
        ever_ends = not_mask_after.any(dim=time_dim)
        end_idx = not_mask_after.argmax(dim=time_dim)

        # If condition never ends (stays True to end of forecast), use n_times
        end_idx = xr.where(ever_ends, end_idx, n_times)

        # Duration = end - start (in timesteps)
        duration_steps = end_idx - first_idx
        duration_hours = duration_steps.astype(float) * timestep_hours

        # Set to NaN where condition is never met
        ever_true = mask.any(dim=time_dim)
        duration_hours = duration_hours.where(ever_true)

        return duration_hours, end_idx

    def compute_next_breach(
        self,
        mask: xr.DataArray,
        first_end_idx: xr.DataArray,
        time_dim: str = 'time',
        timestep_hours: float = 1.0
    ) -> tuple[xr.DataArray, xr.DataArray]:
        """
        Find the next occurrence AFTER the first event ends.

        Args:
            mask: Boolean DataArray indicating where condition is met
            first_end_idx: Index where the first event ends (from compute_duration)
            time_dim: Name of the time dimension
            timestep_hours: Hours between timesteps

        Returns:
            Tuple of (next_breach_time, next_duration_hours)
        """
        n_times = mask.sizes[time_dim]
        time_coords = mask[time_dim]

        # Create index array - broadcast to match mask dimensions
        time_indices = xr.DataArray(
            np.arange(n_times),
            dims=[time_dim],
            coords={time_dim: time_coords}
        )

        # Broadcast time_indices and first_end_idx for comparison
        # This avoids dask indexing issues by doing element-wise comparison
        after_first_event = time_indices >= first_end_idx

        # Find where condition is True AFTER first event ends
        mask_after = mask & after_first_event

        # Check if there's any True after first event
        has_next = mask_after.any(dim=time_dim)

        # Use idxmax to get the actual time coordinate (not index)
        # This is what compute_first_breach does and it works with dask
        next_breach_time = mask_after.idxmax(dim=time_dim, skipna=True)

        # Set to NaT where there's no next occurrence
        next_breach_time = next_breach_time.where(has_next)

        # For duration, we need the index of next breach
        next_idx = mask_after.argmax(dim=time_dim)

        # Compute duration for the next event
        # Find first False AFTER next_idx
        not_mask = ~mask
        after_next = time_indices > next_idx
        not_mask_after_next = not_mask & after_next

        ever_ends_next = not_mask_after_next.any(dim=time_dim)
        next_end_idx = not_mask_after_next.argmax(dim=time_dim)

        # If next event never ends, use n_times
        next_end_idx = xr.where(ever_ends_next, next_end_idx, n_times)

        # Duration of next event
        next_duration_steps = next_end_idx - next_idx
        next_duration_hours = next_duration_steps.astype(float) * timestep_hours

        # Set to NaN where there's no next occurrence
        next_duration_hours = next_duration_hours.where(has_next)

        return next_breach_time, next_duration_hours

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
            - duration_hours: hours the first occurrence lasts
            - next_breach_time: datetime of second occurrence (if any)
            - next_duration_hours: hours the second occurrence lasts (if any)
        """
        if self.variable not in ds:
            raise ValueError(f"Variable '{self.variable}' not found in dataset")

        data = ds[self.variable]
        mask = self.compute_mask(data)

        # Auto-detect timestep from coordinate
        timestep_hours = 1.0  # default
        if time_dim in ds.coords and len(ds[time_dim]) > 1:
            step_values = ds[time_dim].values
            interval = step_values[1] - step_values[0]
            # Convert to hours (handle both timedelta64 and numeric)
            if np.issubdtype(type(interval), np.timedelta64):
                timestep_hours = float(interval / np.timedelta64(1, 'h'))
            else:
                # Assume seconds if numeric
                timestep_hours = float(interval) / 3600.0

        first_breach = self.compute_first_breach(mask, time_dim)
        duration, first_end_idx = self.compute_duration(mask, time_dim, timestep_hours=timestep_hours)

        # Compute next occurrence after first event ends
        next_breach, next_duration = self.compute_next_breach(
            mask, first_end_idx, time_dim, timestep_hours=timestep_hours
        )

        # Build output dataset
        result = xr.Dataset({
            'first_breach_time': first_breach,
            'duration_hours': duration,
            'next_breach_time': next_breach,
            'next_duration_hours': next_duration,
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
            'long_name': 'Duration of first occurrence',
            'unit': 'hours',  # Use 'unit' (not 'units') to avoid xarray timedelta auto-decode
            'description': 'How long the first event persists after first breach',
        }

        result['next_breach_time'].attrs = {
            'long_name': f'Next time {self.variable} {self.operator} {self.threshold}',
            'description': 'Timestamp of second occurrence after first ends, NaT if none',
        }

        result['next_duration_hours'].attrs = {
            'long_name': 'Duration of second occurrence',
            'unit': 'hours',
            'description': 'How long the second event persists',
        }

        return result
