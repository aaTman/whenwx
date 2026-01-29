"""
Main entry point for the WhenWX API server.
"""

import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import xarray as xr

from .config import get_config
from .middleware import setup_rate_limiting, limiter
from .plugins import WeatherQueryPlugin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_dataset(zarr_path: str) -> xr.Dataset:
    """
    Load the zarr dataset from GCS or local path.

    Args:
        zarr_path: Path to zarr store (gs:// or local)

    Returns:
        xarray Dataset
    """
    logger.info(f"Loading dataset from {zarr_path}")

    if zarr_path.startswith('gs://'):
        import gcsfs
        fs = gcsfs.GCSFileSystem(token='google_default')
        mapper = fs.get_mapper(zarr_path)
        ds = xr.open_zarr(mapper, consolidated=True)
    else:
        ds = xr.open_zarr(zarr_path, consolidated=True)

    logger.info(f"Loaded dataset with variables: {list(ds.data_vars)}")
    return ds


def create_mock_dataset() -> xr.Dataset:
    """
    Create a mock dataset for testing/demo.

    Returns:
        xarray Dataset with mock weather data
    """
    import numpy as np
    import pandas as pd

    logger.info("Creating mock dataset for demo mode")

    # Smaller grid for demo
    lats = np.arange(-90, 90.5, 1.0)
    lons = np.arange(-180, 180, 1.0)

    # Create mock first breach times
    # Northern latitudes get freezing sooner
    np.random.seed(42)

    # Base: 3 days from now
    base_time = np.datetime64(datetime.utcnow()) + np.timedelta64(3, 'D')

    first_breach = np.full((len(lats), len(lons)), base_time, dtype='datetime64[ns]')

    # Adjust based on latitude (colder regions breach sooner)
    for i, lat in enumerate(lats):
        if lat > 50:  # Arctic regions - freezing imminent
            offset_hours = np.random.randint(-48, 24, len(lons))
            first_breach[i, :] = base_time + offset_hours.astype('timedelta64[h]')
        elif lat > 30:  # Temperate - might freeze
            offset_hours = np.random.randint(24, 120, len(lons))
            first_breach[i, :] = base_time + offset_hours.astype('timedelta64[h]')
        elif lat < -50:  # Antarctic
            offset_hours = np.random.randint(-48, 24, len(lons))
            first_breach[i, :] = base_time + offset_hours.astype('timedelta64[h]')
        else:  # Tropical - no freezing
            first_breach[i, :] = np.datetime64('NaT')

    # Duration: 6-48 hours where it freezes
    duration = np.where(
        np.isnat(first_breach),
        np.nan,
        np.random.uniform(6, 48, first_breach.shape)
    )

    ds = xr.Dataset(
        {
            'freezing_first_breach_time': (['latitude', 'longitude'], first_breach),
            'freezing_duration_hours': (['latitude', 'longitude'], duration),
        },
        coords={
            'latitude': lats,
            'longitude': lons,
        },
        attrs={
            'title': 'WhenWX Mock Weather Data',
            'source': 'Mock data for demo',
            'processing_time': datetime.utcnow().isoformat(),
            'forecast_init_time': datetime.utcnow().isoformat(),
        }
    )

    return ds


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app
    """
    config = get_config()

    # Check for demo mode
    demo_mode = os.getenv('DEMO_MODE', 'false').lower() == 'true'
    local_zarr = os.getenv('LOCAL_ZARR_PATH')

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: Load dataset
        if demo_mode:
            app.state.dataset = create_mock_dataset()
        elif local_zarr:
            app.state.dataset = load_dataset(local_zarr)
        else:
            try:
                app.state.dataset = load_dataset(config.zarr_path)
            except Exception as e:
                logger.warning(f"Failed to load GCS dataset: {e}. Using mock data.")
                app.state.dataset = create_mock_dataset()

        yield

        # Shutdown: Cleanup
        logger.info("Shutting down")

    app = FastAPI(
        title="WhenWX API",
        description="Weather event timing prediction API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Setup CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup rate limiting
    setup_rate_limiting(app)

    # Create xpublish-style dependency
    def get_dataset():
        return app.state.dataset

    # Create plugin and register routes
    from xpublish import Dependencies

    class AppDeps:
        """Dependencies provider for the plugin."""
        def dataset(self):
            return app.state.dataset

    deps = Dependencies(dataset=get_dataset)

    plugin = WeatherQueryPlugin()
    router = plugin.dataset_router(deps)

    # Apply rate limit to query endpoint
    @app.middleware("http")
    async def rate_limit_queries(request: Request, call_next):
        if "/query" in request.url.path:
            # Apply 1 request per minute limit
            await limiter.check(config.rate_limit, request)
        return await call_next(request)

    # Register routes
    app.include_router(router)

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "WhenWX API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == '__main__':
    import uvicorn

    config = get_config()
    uvicorn.run(
        "api.src.main:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
    )
