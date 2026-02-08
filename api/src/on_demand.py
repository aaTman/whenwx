"""
On-demand computation of weather event metrics.

Instead of pre-computing metrics for the entire global grid (slow),
this module computes metrics for a single location on-the-fly (fast).
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime

import numpy as np
import xarray as xr
import pandas as pd
from timezonefinder import TimezoneFinder

logger = logging.getLogger(__name__)

# Module-level instance (loads data once, fast subsequent lookups)
_timezone_finder = TimezoneFinder()

# Cache the Arraylake session to avoid reconnecting on every request
_arraylake_session = None
_arraylake_ds = None
_last_refresh = None
CACHE_TTL_SECONDS = 300  # Refresh cache every 5 minutes


@dataclass
class EventMetrics:
    """Computed metrics for a weather event at a location."""
    first_breach_time: Optional[datetime]
    duration_hours: Optional[float]
    next_breach_time: Optional[datetime]
    next_duration_hours: Optional[float]
    forecast_init_time: datetime
    actual_lat: float
    actual_lon: float
    lead_times_hours: list
    values_display: list
    timezone: str


def get_arraylake_dataset() -> xr.Dataset:
    """
    Get or create a cached Arraylake dataset connection.

    Returns the latest forecast data from Arraylake, refreshing
    the cache periodically to pick up new model runs.
    """
    global _arraylake_session, _arraylake_ds, _last_refresh

    now = datetime.utcnow()

    # Check if we need to refresh the cache
    if (_arraylake_ds is None or
        _last_refresh is None or
        (now - _last_refresh).total_seconds() > CACHE_TTL_SECONDS):

        logger.info("Refreshing Arraylake dataset cache")

        import arraylake

        token = os.getenv('ARRAYLAKE_TOKEN')
        if not token:
            raise ValueError("ARRAYLAKE_TOKEN environment variable not set")

        client = arraylake.Client(token=token)
        repo = client.get_repo('extreme-earth/ifs-hres')
        session = repo.readonly_session('main')

        ds = xr.open_zarr(
            session.store,
            decode_timedelta=True,
            consolidated=False
        )

        _arraylake_ds = ds
        _arraylake_session = session
        _last_refresh = now

        logger.info(f"Loaded Arraylake dataset with variables: {list(ds.data_vars)}")

    return _arraylake_ds


def compute_event_metrics(
    lat: float,
    lon: float,
    variable: str,
    threshold: float,
    operator: str,
) -> EventMetrics:
    """
    Compute weather event metrics for a single location on-demand.

    This is much faster than pre-computing for the entire grid because
    we only load and process data for one point.

    Args:
        lat: Latitude
        lon: Longitude
        variable: Weather variable name (e.g., '2t' for 2m temperature)
        threshold: Threshold value in native units
        operator: Comparison operator ('lt', 'gt', 'lte', 'gte', 'eq')

    Returns:
        EventMetrics with computed breach times and durations
    """
    ds = get_arraylake_dataset()

    # Select the latest model initialization time
    if 'time' in ds.dims:
        latest_time = ds.time.max().values
        ds_latest = ds.sel(time=latest_time)
        forecast_init_time = pd.Timestamp(latest_time).to_pydatetime()
    else:
        ds_latest = ds
        forecast_init_time = datetime.utcnow()

    # Select nearest grid point - this is the key optimization!
    # We only load data for ONE point instead of the entire grid
    point_data = ds_latest.sel(
        latitude=lat,
        longitude=lon,
        method='nearest'
    )

    actual_lat = float(point_data.latitude.values)
    actual_lon = float(point_data.longitude.values)

    # Get the variable data for this point
    if variable not in point_data:
        raise ValueError(f"Variable '{variable}' not found in dataset")

    # Load the time series data for this single point (fast!)
    data = point_data[variable].compute()

    # Get the time dimension (usually 'step' for forecast data)
    time_dim = 'step' if 'step' in data.dims else 'time'

    # Compute the mask based on operator
    if operator == 'lt':
        mask = data < threshold
    elif operator == 'gt':
        mask = data > threshold
    elif operator == 'lte':
        mask = data <= threshold
    elif operator == 'gte':
        mask = data >= threshold
    elif operator == 'eq':
        mask = np.abs(data - threshold) < 1e-6
    else:
        raise ValueError(f"Unknown operator: {operator}")

    # Get time coordinates
    time_coords = mask[time_dim].values
    mask_values = mask.values

    # Compute first breach
    first_breach_time, duration_hours, first_end_idx = _compute_first_breach_and_duration(
        mask_values, time_coords, forecast_init_time
    )

    # Compute next breach (after first event ends)
    next_breach_time, next_duration_hours = _compute_next_breach(
        mask_values, time_coords, forecast_init_time, first_end_idx
    )

    # Build time series for charting
    lead_times_hours = [
        pd.Timedelta(t).total_seconds() / 3600 if isinstance(t, np.timedelta64)
        else float(t)
        for t in time_coords
    ]

    raw_values = data.values
    # Convert Kelvin to Celsius for temperature variables, filtering out NaN/Inf
    valid_mask = np.isfinite(raw_values)
    if variable in ('2t', 't2m', '2m_temperature'):
        values_display = [round(float(v) - 273.15, 2) if valid_mask[i] else None for i, v in enumerate(raw_values)]
    else:
        values_display = [round(float(v), 2) if valid_mask[i] else None for i, v in enumerate(raw_values)]

    # Filter out entries with None values (keep only valid data points)
    paired = [(h, v) for h, v in zip(lead_times_hours, values_display) if v is not None]
    if paired:
        lead_times_hours, values_display = [list(x) for x in zip(*paired)]
    else:
        lead_times_hours, values_display = [], []

    # Determine timezone from coordinates
    tz_str = _timezone_finder.timezone_at(lat=actual_lat, lng=actual_lon) or "UTC"

    return EventMetrics(
        first_breach_time=first_breach_time,
        duration_hours=duration_hours,
        next_breach_time=next_breach_time,
        next_duration_hours=next_duration_hours,
        forecast_init_time=forecast_init_time,
        actual_lat=actual_lat,
        actual_lon=actual_lon,
        lead_times_hours=lead_times_hours,
        values_display=values_display,
        timezone=tz_str,
    )


def _compute_first_breach_and_duration(
    mask: np.ndarray,
    time_coords: np.ndarray,
    forecast_init_time: datetime,
) -> Tuple[Optional[datetime], Optional[float], int]:
    """
    Compute first breach time and duration for a 1D mask.

    Returns:
        Tuple of (first_breach_time, duration_hours, end_index)
    """
    # Find first True
    true_indices = np.where(mask)[0]

    if len(true_indices) == 0:
        # Condition never met
        return None, None, len(mask)

    first_idx = true_indices[0]

    # Convert time coordinate to datetime
    time_val = time_coords[first_idx]
    if isinstance(time_val, np.timedelta64):
        first_breach_time = forecast_init_time + pd.Timedelta(time_val).to_pytimedelta()
    else:
        first_breach_time = pd.Timestamp(time_val).to_pydatetime()

    # Find end of first contiguous event
    end_idx = first_idx + 1
    while end_idx < len(mask) and mask[end_idx]:
        end_idx += 1

    # Calculate duration
    if end_idx < len(time_coords):
        end_time_val = time_coords[end_idx]
        start_time_val = time_coords[first_idx]
        if isinstance(end_time_val, np.timedelta64):
            duration = pd.Timedelta(end_time_val - start_time_val).total_seconds() / 3600
        else:
            duration = (pd.Timestamp(end_time_val) - pd.Timestamp(start_time_val)).total_seconds() / 3600
    else:
        # Event continues to end of forecast
        end_time_val = time_coords[-1]
        start_time_val = time_coords[first_idx]
        if isinstance(end_time_val, np.timedelta64):
            duration = pd.Timedelta(end_time_val - start_time_val).total_seconds() / 3600
        else:
            duration = (pd.Timestamp(end_time_val) - pd.Timestamp(start_time_val)).total_seconds() / 3600

    return first_breach_time, duration, end_idx


def _compute_next_breach(
    mask: np.ndarray,
    time_coords: np.ndarray,
    forecast_init_time: datetime,
    first_end_idx: int,
) -> Tuple[Optional[datetime], Optional[float]]:
    """
    Compute next breach time after the first event ends.

    Returns:
        Tuple of (next_breach_time, next_duration_hours)
    """
    # Look for True values after first_end_idx
    remaining_mask = mask[first_end_idx:]
    true_indices = np.where(remaining_mask)[0]

    if len(true_indices) == 0:
        # No next occurrence
        return None, None

    # Adjust index to full array
    next_idx = first_end_idx + true_indices[0]

    # Convert time coordinate to datetime
    time_val = time_coords[next_idx]
    if isinstance(time_val, np.timedelta64):
        next_breach_time = forecast_init_time + pd.Timedelta(time_val).to_pytimedelta()
    else:
        next_breach_time = pd.Timestamp(time_val).to_pydatetime()

    # Find end of next contiguous event
    next_end_idx = next_idx + 1
    while next_end_idx < len(mask) and mask[next_end_idx]:
        next_end_idx += 1

    # Calculate duration
    if next_end_idx < len(time_coords):
        end_time_val = time_coords[next_end_idx]
        start_time_val = time_coords[next_idx]
        if isinstance(end_time_val, np.timedelta64):
            duration = pd.Timedelta(end_time_val - start_time_val).total_seconds() / 3600
        else:
            duration = (pd.Timestamp(end_time_val) - pd.Timestamp(start_time_val)).total_seconds() / 3600
    else:
        # Event continues to end of forecast
        end_time_val = time_coords[-1]
        start_time_val = time_coords[next_idx]
        if isinstance(end_time_val, np.timedelta64):
            duration = pd.Timedelta(end_time_val - start_time_val).total_seconds() / 3600
        else:
            duration = (pd.Timestamp(end_time_val) - pd.Timestamp(start_time_val)).total_seconds() / 3600

    return next_breach_time, duration
