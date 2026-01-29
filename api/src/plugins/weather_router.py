"""
xpublish plugin for weather event timing queries.
"""

from typing import Sequence, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
import xarray as xr
import numpy as np

from xpublish import Dependencies, Plugin, hookimpl

logger = logging.getLogger(__name__)


class ConfidenceBand(BaseModel):
    """Confidence band for timing estimates."""
    earliest: Optional[str] = Field(None, description="ISO timestamp of earliest estimate")
    latest: Optional[str] = Field(None, description="ISO timestamp of latest estimate")


class EventTiming(BaseModel):
    """Timing information for a weather event."""
    firstBreachTime: Optional[str] = Field(None, description="ISO timestamp of first occurrence")
    durationHours: Optional[float] = Field(None, description="Duration in hours")
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


class WeatherQueryResponse(BaseModel):
    """Response model for weather timing queries."""
    location: Location
    event: WeatherEvent
    timing: EventTiming
    forecastInitTime: str
    queryTime: str
    dataSource: str = "ECMWF IFS 15-day forecast"


# Event definitions (should match frontend)
EVENTS = {
    'freezing': WeatherEvent(
        id='freezing',
        name='Freezing Temperatures',
        description='Temperature drops below -10°C',
        variable='t2m',
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

            # Build variable names (prefixed with event_id from processing)
            first_breach_var = f'{event_id}_first_breach_time'
            duration_var = f'{event_id}_duration_hours'

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

            # Handle NaT/NaN values
            first_breach_str = None
            if not np.isnat(first_breach):
                # Convert numpy datetime64 to Python datetime string
                first_breach_dt = np.datetime64(first_breach, 'ns')
                first_breach_str = str(first_breach_dt)[:19] + 'Z'

            duration_val = None
            if duration is not None and not np.isnan(duration):
                duration_val = float(duration)

            # Get actual coordinates used
            actual_lat = float(point_data.latitude.values)
            actual_lon = float(point_data.longitude.values)

            # Get forecast init time from dataset attributes
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
                    modelConsistency=0.75,  # TODO: Compute from multiple model runs
                    confidenceBand=ConfidenceBand(
                        earliest=None,  # TODO: Compute from ensemble
                        latest=None,
                    ),
                ),
                forecastInitTime=forecast_init,
                queryTime=datetime.utcnow().isoformat() + 'Z',
            )

        @router.get('/health')
        async def health_check():
            """Health check endpoint."""
            return {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }

        return router
