import { useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useWeatherQuery } from '../hooks/useWeatherQuery';
import { ResultsModule } from '../components/ResultsModule';
import { getEventById } from '../config/events';
import type { QueryParams } from '../types/weather';
import './Results.css';

export function Results() {
  const [searchParams] = useSearchParams();

  const queryParams = useMemo((): QueryParams | null => {
    const lat = parseFloat(searchParams.get('lat') || '');
    const lon = parseFloat(searchParams.get('lon') || '');
    const eventId = searchParams.get('event') || '';

    if (isNaN(lat) || isNaN(lon) || !eventId) {
      return null;
    }

    return { lat, lon, eventId };
  }, [searchParams]);

  const event = queryParams ? getEventById(queryParams.eventId) : null;
  const { data, loading, error } = useWeatherQuery(queryParams);

  // Invalid params
  if (!queryParams || !event) {
    return (
      <main className="results-page">
        <div className="results-container">
          <div className="error-state">
            <h2>Invalid Request</h2>
            <p>Please provide valid location coordinates and weather event.</p>
            <Link to="/" className="back-link">
              ← Back to Home
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="results-page">
      <div className="results-container">
        <nav className="results-nav">
          <Link to="/" className="back-link">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            Back
          </Link>
        </nav>

        {loading && (
          <div className="loading-state">
            <div className="loading-spinner-large" />
            <p>Fetching forecast data...</p>
          </div>
        )}

        {error && (
          <div className="error-state">
            <h2>Error</h2>
            <p>{error}</p>
            <Link to="/" className="back-link">
              ← Try Again
            </Link>
          </div>
        )}

        {data && <ResultsModule result={data} />}

        {/* Demo mode - show mock data when API not available */}
        {!loading && !error && !data && (
          <ResultsModule
            result={{
              location: {
                latitude: queryParams.lat,
                longitude: queryParams.lon,
              },
              event: event,
              timing: {
                firstBreachTime: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
                durationHours: 18,
                modelConsistency: 0.75,
                confidenceBand: {
                  earliest: new Date(Date.now() + 2.5 * 24 * 60 * 60 * 1000).toISOString(),
                  latest: new Date(Date.now() + 3.5 * 24 * 60 * 60 * 1000).toISOString(),
                },
              },
              forecastInitTime: new Date().toISOString(),
              queryTime: new Date().toISOString(),
              dataSource: 'ECMWF IFS 15-day forecast (Demo)',
            }}
          />
        )}
      </div>
    </main>
  );
}
