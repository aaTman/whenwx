"""
xpublish plugin for weather event timing queries.

Supports two modes:
1. Pre-computed: Read metrics from GCS zarr (legacy, requires batch processing)
2. On-demand: Compute metrics in real-time from Arraylake (fast, no batch processing)
"""

import os
from typing import Sequence, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
import xarray as xr
import numpy as np
import pandas as pd

from xpublish import Dependencies, Plugin, hookimpl

logger = logging.getLogger(__name__)

# On-demand computation mode (default: true)
ON_DEMAND_MODE = os.getenv('ON_DEMAND_MODE', 'true').lower() == 'true'


class ConfidenceBand(BaseModel):
    """Confidence band for timing estimates."""
    earliest: Optional[str] = Field(None, description="ISO timestamp of earliest estimate")
    latest: Optional[str] = Field(None, description="ISO timestamp of latest estimate")


class EventTiming(BaseModel):
    """Timing information for a weather event."""
    firstBreachTime: Optional[str] = Field(None, description="ISO timestamp of first occurrence")
    durationHours: Optional[float] = Field(None, description="Duration in hours")
    nextBreachTime: Optional[str] = Field(None, description="ISO timestamp of next occurrence after first ends")
    nextDurationHours: Optional[float] = Field(None, description="Duration of next occurrence in hours")
    modelConsistency: float = Field(..., ge=0, le=1, description="Model confidence (0-1)")
    confidenceBand: ConfidenceBand


class Location(BaseModel):
    """Geographic location."""
    latitude: float
    longitude: float
    name: Optional[str] = None


class WeatherEvent(BaseModel):
    """Weather event definition."""
    id: str
    name: str
    description: str
    variable: str
    threshold: float
    thresholdDisplay: float
    operator: str
    unit: str


class ForecastTimeSeries(BaseModel):
    """Time series data for charting."""
    leadTimesHours: list[float] = Field(..., description="Lead time from forecast init in hours")
    values: list[float] = Field(..., description="Values in display units (e.g., Celsius)")
    unit: str = Field(..., description="Display unit for values")


class WeatherQueryResponse(BaseModel):
    """Response model for weather timing queries."""
    location: Location
    event: WeatherEvent
    timing: EventTiming
    forecastInitTime: str
    queryTime: str
    dataSource: str = "ECMWF IFS 15-day forecast"
    timeSeries: Optional[ForecastTimeSeries] = None
    timezone: Optional[str] = None


# Event definitions (should match frontend)
EVENTS = {
    'freezing': WeatherEvent(
        id='freezing',
        name='Freezing Temperatures',
        description='Temperature drops below -10°C',
        variable='2t',
        threshold=263.15,
        thresholdDisplay=-10,
        operator='lt',
        unit='°C'
    ),
}


class WeatherQueryPlugin(Plugin):
    """
    xpublish plugin for weather event timing queries.

    Provides endpoints to query when weather conditions will be met
    at a specific location.
    """

    name: str = 'weather-query'
    dataset_router_prefix: str = ''
    dataset_router_tags: Sequence[str] = ['weather', 'timing']

    @hookimpl
    def dataset_router(self, deps: Dependencies):
        router = APIRouter(tags=list(self.dataset_router_tags))

        @router.get('/events')
        async def list_events():
            """List available weather event types."""
            return {
                'events': [event.model_dump() for event in EVENTS.values()]
            }

        @router.get('/query', response_model=WeatherQueryResponse)
        async def query_weather_timing(
            request: Request,
            lat: float = Query(..., ge=-90, le=90, description="Latitude"),
            lon: float = Query(..., ge=-180, le=180, description="Longitude"),
            event_id: str = Query(..., description="Weather event ID"),
            dataset: xr.Dataset = Depends(deps.dataset),
        ) -> WeatherQueryResponse:
            """
            Query when a weather condition will first be met at a location.

            Returns the first breach time, duration, and model consistency.
            """
            # Validate event
            if event_id not in EVENTS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown event: {event_id}. Available: {list(EVENTS.keys())}"
                )

            event = EVENTS[event_id]

            # Use on-demand computation if enabled
            if ON_DEMAND_MODE:
                return await _query_on_demand(lat, lon, event)

            # Otherwise use pre-computed data from GCS zarr
            return await _query_precomputed(lat, lon, event, event_id, dataset)

        @router.get('/health')
        async def health_check():
            """Health check endpoint."""
            return {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'mode': 'on-demand' if ON_DEMAND_MODE else 'pre-computed',
            }

        return router


async def _query_on_demand(lat: float, lon: float, event: WeatherEvent) -> WeatherQueryResponse:
    """
    Query using on-demand computation from Arraylake.

    This computes metrics for a single location in real-time,
    which is fast (~1-2 seconds) compared to batch processing.
    """
    from ..on_demand import compute_event_metrics

    try:
        metrics = compute_event_metrics(
            lat=lat,
            lon=lon,
            variable=event.variable,
            threshold=event.threshold,
            operator=event.operator,
        )
    except Exception as e:
        logger.error(f"On-demand computation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute metrics: {str(e)}"
        )

    # Format times as ISO strings
    first_breach_str = None
    if metrics.first_breach_time:
        first_breach_str = metrics.first_breach_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    next_breach_str = None
    if metrics.next_breach_time:
        next_breach_str = metrics.next_breach_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    return WeatherQueryResponse(
        location=Location(
            latitude=metrics.actual_lat,
            longitude=metrics.actual_lon,
        ),
        event=event,
        timing=EventTiming(
            firstBreachTime=first_breach_str,
            durationHours=metrics.duration_hours,
            nextBreachTime=next_breach_str,
            nextDurationHours=metrics.next_duration_hours,
            modelConsistency=0.75,  # TODO: Compute from multiple model runs
            confidenceBand=ConfidenceBand(
                earliest=None,
                latest=None,
            ),
        ),
        forecastInitTime=metrics.forecast_init_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        queryTime=datetime.utcnow().isoformat() + 'Z',
        timeSeries=ForecastTimeSeries(
            leadTimesHours=metrics.lead_times_hours,
            values=metrics.values_display,
            unit=event.unit,
        ),
        timezone=metrics.timezone,
    )


async def _query_precomputed(
    lat: float,
    lon: float,
    event: WeatherEvent,
    event_id: str,
    dataset: xr.Dataset
) -> WeatherQueryResponse:
    """
    Query using pre-computed data from GCS zarr.

    This is the legacy mode that reads from batch-processed data.
    """
    # Build variable names (prefixed with event_id from processing)
    first_breach_var = f'{event_id}_first_breach_time'
    duration_var = f'{event_id}_duration_hours'
    next_breach_var = f'{event_id}_next_breach_time'
    next_duration_var = f'{event_id}_next_duration_hours'

    # Check required variables exist
    if first_breach_var not in dataset:
        raise HTTPException(
            status_code=500,
            detail=f"Dataset missing variable: {first_breach_var}"
        )

    # Select nearest grid point
    try:
        point_data = dataset.sel(
            latitude=lat,
            longitude=lon,
            method='nearest'
        )
    except Exception as e:
        logger.error(f"Failed to select location: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to select location: {str(e)}"
        )

    # Extract values
    first_breach = point_data[first_breach_var].values
    duration = point_data[duration_var].values if duration_var in point_data else None
    next_breach = point_data[next_breach_var].values if next_breach_var in point_data else None
    next_duration = point_data[next_duration_var].values if next_duration_var in point_data else None

    # Get forecast init time from dataset
    forecast_init_time = None
    if 'time' in dataset.coords:
        time_val = dataset.coords['time'].values
        if hasattr(time_val, 'item'):
            time_val = time_val.item()
        forecast_init_time = pd.Timestamp(time_val)

    # Handle first_breach - can be timedelta64 (legacy) or float64 hours (new format)
    first_breach_str = None
    if first_breach is not None:
        if hasattr(first_breach, 'item'):
            first_breach = first_breach.item()

        if isinstance(first_breach, np.timedelta64):
            if not np.isnat(first_breach):
                td = pd.Timedelta(first_breach)
                if forecast_init_time:
                    first_breach_dt = forecast_init_time + td
                    first_breach_str = first_breach_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                else:
                    first_breach_str = f"+{td.total_seconds() / 3600:.0f}h"
        elif isinstance(first_breach, (int, float, np.floating, np.integer)):
            try:
                hours = float(first_breach)
                if not np.isnan(hours) and forecast_init_time:
                    first_breach_dt = forecast_init_time + pd.Timedelta(hours=hours)
                    first_breach_str = first_breach_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except (ValueError, TypeError):
                pass

    duration_val = None
    if duration is not None:
        if hasattr(duration, 'item'):
            duration = duration.item()
        if isinstance(duration, np.timedelta64):
            if not np.isnat(duration):
                td = pd.Timedelta(duration)
                duration_val = td.total_seconds() / 3600
        else:
            try:
                duration_float = float(duration)
                if not np.isnan(duration_float):
                    duration_val = duration_float
            except (ValueError, TypeError):
                pass

    # Handle next_breach
    next_breach_str = None
    if next_breach is not None:
        if hasattr(next_breach, 'item'):
            next_breach = next_breach.item()

        if isinstance(next_breach, np.timedelta64):
            if not np.isnat(next_breach):
                td = pd.Timedelta(next_breach)
                if forecast_init_time:
                    next_breach_dt = forecast_init_time + td
                    next_breach_str = next_breach_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance(next_breach, (int, float, np.floating, np.integer)):
            try:
                hours = float(next_breach)
                if not np.isnan(hours) and forecast_init_time:
                    next_breach_dt = forecast_init_time + pd.Timedelta(hours=hours)
                    next_breach_str = next_breach_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except (ValueError, TypeError):
                pass

    # Handle next_duration
    next_duration_val = None
    if next_duration is not None:
        if hasattr(next_duration, 'item'):
            next_duration = next_duration.item()
        if isinstance(next_duration, np.timedelta64):
            if not np.isnat(next_duration):
                td = pd.Timedelta(next_duration)
                next_duration_val = td.total_seconds() / 3600
        else:
            try:
                next_duration_float = float(next_duration)
                if not np.isnan(next_duration_float):
                    next_duration_val = next_duration_float
            except (ValueError, TypeError):
                pass

    # Get actual coordinates used
    actual_lat = float(point_data.latitude.values)
    actual_lon = float(point_data.longitude.values)

    # Get forecast init time string
    if forecast_init_time:
        forecast_init = forecast_init_time.isoformat() + 'Z'
    else:
        forecast_init = dataset.attrs.get('forecast_init_time', '')
        if not forecast_init:
            forecast_init = dataset.attrs.get('processing_time', datetime.utcnow().isoformat())

    return WeatherQueryResponse(
        location=Location(
            latitude=actual_lat,
            longitude=actual_lon,
        ),
        event=event,
        timing=EventTiming(
            firstBreachTime=first_breach_str,
            durationHours=duration_val,
            nextBreachTime=next_breach_str,
            nextDurationHours=next_duration_val,
            modelConsistency=0.75,
            confidenceBand=ConfidenceBand(
                earliest=None,
                latest=None,
            ),
        ),
        forecastInitTime=forecast_init,
        queryTime=datetime.utcnow().isoformat() + 'Z',
    )
