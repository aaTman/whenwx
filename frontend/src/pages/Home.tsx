import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LocationInput } from '../components/LocationInput';
import { ThresholdBuilder } from '../components/ThresholdBuilder';
import type { Location } from '../types/weather';
import type { WeatherVariable } from '../config/variables';
import './Home.css';

export function Home() {
  const navigate = useNavigate();
  const [location, setLocation] = useState<Location | null>(null);
  const [selectedVariable, setSelectedVariable] = useState<WeatherVariable | null>(null);
  const [threshold, setThreshold] = useState<number>(0);
  const [operator, setOperator] = useState<'lt' | 'gt'>('lt');

  const handleVariableChange = (variable: WeatherVariable | null) => {
    setSelectedVariable(variable);
    if (variable) {
      setThreshold(variable.defaultThreshold);
      setOperator(variable.defaultOperator);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (location && selectedVariable) {
      // Convert threshold from display units to backend storage units
      const backendThreshold = selectedVariable.convertToBackend(threshold);
      const params = new URLSearchParams({
        lat: location.latitude.toString(),
        lon: location.longitude.toString(),
        variable: selectedVariable.id,
        threshold: backendThreshold.toString(),
        operator: operator,
      });
      navigate(`/results?${params.toString()}`);
    }
  };

  const isValid = location !== null && selectedVariable !== null;

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
          <ThresholdBuilder
            selectedVariable={selectedVariable}
            threshold={threshold}
            operator={operator}
            onVariableChange={handleVariableChange}
            onThresholdChange={setThreshold}
            onOperatorChange={setOperator}
          />

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
