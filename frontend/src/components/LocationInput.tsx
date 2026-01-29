import { useState, useEffect } from 'react';
import { useGeolocation } from '../hooks/useGeolocation';
import type { Location } from '../types/weather';
import './LocationInput.css';

interface LocationInputProps {
  value: Location | null;
  onChange: (location: Location | null) => void;
}

export function LocationInput({ value, onChange }: LocationInputProps) {
  const [inputValue, setInputValue] = useState('');
  const { location: geoLocation, loading, error, requestLocation } = useGeolocation();

  // Sync geolocation result to parent
  useEffect(() => {
    if (geoLocation) {
      onChange(geoLocation);
      setInputValue(`${geoLocation.latitude.toFixed(4)}, ${geoLocation.longitude.toFixed(4)}`);
    }
  }, [geoLocation, onChange]);

  // Parse manual coordinate input
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);

    // Try to parse coordinates (lat, lon format)
    const match = val.match(/^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$/);
    if (match) {
      const lat = parseFloat(match[1]);
      const lon = parseFloat(match[2]);
      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        onChange({ latitude: lat, longitude: lon });
        return;
      }
    }

    // If not valid coordinates, clear the location
    if (val.trim() === '') {
      onChange(null);
    }
  };

  const handleUseCurrentLocation = () => {
    requestLocation();
  };

  return (
    <div className="location-input">
      <label htmlFor="location" className="location-label">
        Location
      </label>
      <div className="location-input-group">
        <input
          id="location"
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          placeholder="Enter coordinates (lat, lon)"
          className="location-text-input"
        />
        <button
          type="button"
          onClick={handleUseCurrentLocation}
          disabled={loading}
          className="location-button"
          title="Use current location"
        >
          {loading ? (
            <span className="loading-spinner" />
          ) : (
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
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v4" />
              <path d="M12 18v4" />
              <path d="M2 12h4" />
              <path d="M18 12h4" />
            </svg>
          )}
        </button>
      </div>
      {error && <p className="location-error">{error}</p>}
      {value && (
        <p className="location-preview">
          {value.latitude.toFixed(4)}°, {value.longitude.toFixed(4)}°
        </p>
      )}
    </div>
  );
}
