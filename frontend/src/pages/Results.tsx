import { useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useWeatherQuery } from '../hooks/useWeatherQuery';
import { ResultsModule } from '../components/ResultsModule';
import { getVariableById } from '../config/variables';
import type { QueryParams } from '../types/weather';
import './Results.css';

export function Results() {
  const [searchParams] = useSearchParams();

  const queryParams = useMemo((): QueryParams | null => {
    const lat = parseFloat(searchParams.get('lat') || '');
    const lon = parseFloat(searchParams.get('lon') || '');

    if (isNaN(lat) || isNaN(lon)) return null;

    // New mode: variable + threshold + operator
    const variable = searchParams.get('variable');
    const thresholdStr = searchParams.get('threshold');
    const operator = searchParams.get('operator') as 'lt' | 'gt' | null;

    if (variable && thresholdStr && operator) {
      const threshold = parseFloat(thresholdStr);
      if (isNaN(threshold)) return null;
      return { lat, lon, variable, threshold, operator };
    }

    // Legacy mode: event=freezing → map to variable params
    const eventId = searchParams.get('event');
    if (eventId === 'freezing') {
      return { lat, lon, variable: '2t', threshold: 263.15, operator: 'lt' };
    }
    if (eventId) {
      return { lat, lon, eventId };
    }

    return null;
  }, [searchParams]);

  const { data, loading, error } = useWeatherQuery(queryParams);

  // Look up variable config for display
  const variableConfig = queryParams?.variable ? getVariableById(queryParams.variable) : null;

  // Invalid params
  if (!queryParams) {
    return (
      <main className="results-page">
        <div className="results-container">
          <div className="error-state">
            <h2>Invalid Request</h2>
            <p>Please provide valid location coordinates and weather event.</p>
            <Link to="/" className="back-link">
              &larr; Back to Home
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
              &larr; Try Again
            </Link>
          </div>
        )}

        {data && <ResultsModule result={data} />}

        {/* Demo mode - show mock data when API not available */}
        {!loading && !error && !data && variableConfig && (
          <ResultsModule
            result={{
              location: {
                latitude: queryParams.lat,
                longitude: queryParams.lon,
              },
              event: {
                id: `custom_${variableConfig.id}`,
                name: variableConfig.label,
                description: `${variableConfig.label} ${queryParams.operator === 'lt' ? 'below' : 'above'} threshold`,
                variable: variableConfig.id,
                threshold: queryParams.threshold ?? 0,
                thresholdDisplay: queryParams.threshold !== undefined
                  ? Math.round(variableConfig.convertFromBackend(queryParams.threshold) * 100) / 100
                  : 0,
                operator: queryParams.operator ?? 'lt',
                unit: variableConfig.displayUnit,
              },
              timing: {
                firstBreachTime: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
                durationHours: 18,
                nextBreachTime: null,
                nextDurationHours: null,
                modelConsistency: 0.75,
                confidenceBand: {
                  earliest: new Date(Date.now() + 2.5 * 24 * 60 * 60 * 1000).toISOString(),
                  latest: new Date(Date.now() + 3.5 * 24 * 60 * 60 * 1000).toISOString(),
                },
              },
              forecastInitTime: new Date().toISOString(),
              queryTime: new Date().toISOString(),
              dataSource: 'ECMWF IFS 15-day forecast (Demo)',
              timeSeries: {
                leadTimesHours: Array.from({ length: 120 }, (_, i) => i * 3),
                values: Array.from({ length: 120 }, (_, i) => {
                  const hour = i * 3;
                  return Math.round((-5 + 8 * Math.sin(hour / 24 * Math.PI * 2 / 6) - hour * 0.03) * 100) / 100;
                }),
                unit: variableConfig.displayUnit,
              },
              timezone: 'America/New_York',
            }}
          />
        )}
      </div>
    </main>
  );
}
