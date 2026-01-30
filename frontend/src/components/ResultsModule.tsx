import type { WeatherQueryResult } from '../types/weather';
import { getOperatorSymbol } from '../config/events';
import './ResultsModule.css';

interface ResultsModuleProps {
  result: WeatherQueryResult;
}

export function ResultsModule({ result }: ResultsModuleProps) {
  const { timing, event, location, forecastInitTime } = result;

  const formatDateTime = (isoString: string | null): string => {
    if (!isoString) return 'Not expected in forecast period';
    const date = new Date(isoString);
    return date.toLocaleString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short',
    });
  };

  const formatDuration = (hours: number | null): string => {
    if (hours === null) return 'N/A';
    if (hours < 1) return `${Math.round(hours * 60)} minutes`;
    if (hours < 24) return `${Math.round(hours)} hours`;
    const days = Math.floor(hours / 24);
    const remainingHours = Math.round(hours % 24);
    if (remainingHours === 0) return `${days} day${days > 1 ? 's' : ''}`;
    return `${days} day${days > 1 ? 's' : ''} ${remainingHours} hr${remainingHours > 1 ? 's' : ''}`;
  };

  // Check if the event is happening now (first breach time is at or before current time)
  const isHappeningNow = (): boolean => {
    if (!timing.firstBreachTime) return false;
    const breachDate = new Date(timing.firstBreachTime);
    return breachDate <= new Date();
  };

  // Calculate end time based on first breach + duration
  const getEndTime = (): string | null => {
    if (!timing.firstBreachTime || timing.durationHours === null) return null;
    const startDate = new Date(timing.firstBreachTime);
    const endDate = new Date(startDate.getTime() + timing.durationHours * 60 * 60 * 1000);
    return endDate.toISOString();
  };

  const happeningNow = isHappeningNow();
  const endTime = getEndTime();

  const getConsistencyLevel = (consistency: number): { label: string; className: string } => {
    if (consistency >= 0.8) return { label: 'High', className: 'high' };
    if (consistency >= 0.5) return { label: 'Medium', className: 'medium' };
    return { label: 'Low', className: 'low' };
  };

  const consistencyInfo = getConsistencyLevel(timing.modelConsistency);

  return (
    <div className="results-module">
      <header className="results-header">
        <h2 className="results-title">
          {event.name}
        </h2>
        <p className="results-subtitle">
          {getOperatorSymbol(event.operator)} {event.thresholdDisplay}{event.unit} at{' '}
          {location.latitude.toFixed(2)}°, {location.longitude.toFixed(2)}°
        </p>
      </header>

      <div className="results-grid">
        {/* First Breach Card */}
        <div className={`result-card ${happeningNow ? 'happening-now' : 'primary'}`}>
          <div className="card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h3 className="card-label">First Occurrence</h3>
          <p className="card-value">
            {happeningNow
              ? 'Happening Now'
              : timing.firstBreachTime
                ? formatDateTime(timing.firstBreachTime)
                : 'Not expected'}
          </p>
        </div>

        {/* Duration Card */}
        <div className="result-card">
          <div className="card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="2" x2="12" y2="6" />
              <line x1="12" y1="18" x2="12" y2="22" />
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
              <line x1="2" y1="12" x2="6" y2="12" />
              <line x1="18" y1="12" x2="22" y2="12" />
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
            </svg>
          </div>
          <h3 className="card-label">Duration</h3>
          <p className="card-value">{formatDuration(timing.durationHours)}</p>
          {endTime && (
            <p className="card-subvalue">Ends {formatDateTime(endTime)}</p>
          )}
        </div>

        {/* Model Consistency Card */}
        <div className="result-card disabled">
          <div className="coming-soon-badge">Coming Soon</div>
          <div className="card-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 3v18h18" />
              <path d="M18 17V9" />
              <path d="M13 17V5" />
              <path d="M8 17v-3" />
            </svg>
          </div>
          <h3 className="card-label">Model Confidence</h3>
          <p className="card-value">
            <span className={`consistency-badge ${consistencyInfo.className}`}>
              {consistencyInfo.label}
            </span>
            <span className="consistency-percent">
              {Math.round(timing.modelConsistency * 100)}%
            </span>
          </p>
        </div>
      </div>

      {/* Confidence Band */}
      {timing.confidenceBand.earliest && timing.confidenceBand.latest && (
        <div className="confidence-band">
          <h4>Timing Range</h4>
          <p>
            Models suggest timing between{' '}
            <strong>{formatDateTime(timing.confidenceBand.earliest)}</strong> and{' '}
            <strong>{formatDateTime(timing.confidenceBand.latest)}</strong>
          </p>
        </div>
      )}

      <footer className="results-footer">
        <p>
          Forecast initialized: {new Date(forecastInitTime).toLocaleString('en-US', { timeZone: 'UTC', dateStyle: 'medium', timeStyle: 'short' })} UTC
        </p>
        <p className="data-source">
          Powered by <a href="https://www.brightband.com/" target="_blank" rel="noopener noreferrer">Brightband's</a> ECMWF IFS forecast via <a href="https://earthmover.io/" target="_blank" rel="noopener noreferrer">Earthmover</a>
        </p>
      </footer>
    </div>
  );
}
