import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LocationInput } from '../components/LocationInput';
import { EventSelector } from '../components/EventSelector';
import type { Location, WeatherEvent } from '../types/weather';
import './Home.css';

export function Home() {
  const navigate = useNavigate();
  const [location, setLocation] = useState<Location | null>(null);
  const [event, setEvent] = useState<WeatherEvent | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (location && event) {
      const params = new URLSearchParams({
        lat: location.latitude.toString(),
        lon: location.longitude.toString(),
        event: event.id,
      });
      navigate(`/results?${params.toString()}`);
    }
  };

  const isValid = location !== null && event !== null;

  return (
    <main className="home-page">
      <div className="home-container">
        <header className="home-header">
          <h1 className="home-title">
            When<span className="accent">WX</span>
          </h1>
          <p className="home-subtitle">
            Find out when weather conditions will occur at your location
          </p>
        </header>

        <form className="home-form" onSubmit={handleSubmit}>
          <LocationInput value={location} onChange={setLocation} />
          <EventSelector value={event} onChange={setEvent} />

          <button
            type="submit"
            disabled={!isValid}
            className="submit-button"
          >
            Find Out When
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
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </button>
        </form>

        <footer className="home-footer">
          <p>
            Powered by{' '}
            <a
              href="https://www.brightband.com/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Brightband's
            </a>{' '}
            ECMWF IFS forecast via{' '}
            <a
              href="https://earthmover.io/"
              target="_blank"
              rel="noopener noreferrer"
            >
              Earthmover
            </a>
          </p>
        </footer>
      </div>
    </main>
  );
}
