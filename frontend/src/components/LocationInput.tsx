import { useState, useEffect, useRef } from 'react';
import { useGeolocation } from '../hooks/useGeolocation';
import { useGeocoding, GeocodingResult } from '../hooks/useGeocoding';
import type { Location } from '../types/weather';
import './LocationInput.css';

interface LocationInputProps {
  value: Location | null;
  onChange: (location: Location | null) => void;
}

export function LocationInput({ value, onChange }: LocationInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  const { location: geoLocation, loading: geoLoading, error: geoError, requestLocation } = useGeolocation();
  const { results: geocodeResults, loading: geocodeLoading, search: geocodeSearch, clear: clearGeocoding } = useGeocoding();

  // Sync geolocation result to parent
  useEffect(() => {
    if (geoLocation) {
      onChange(geoLocation);
      setInputValue(`${geoLocation.latitude.toFixed(4)}, ${geoLocation.longitude.toFixed(4)}`);
      setShowSuggestions(false);
    }
  }, [geoLocation, onChange]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);

    // Clear existing timer
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }

    // Try to parse as coordinates first (lat, lon format)
    const match = val.match(/^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$/);
    if (match) {
      const lat = parseFloat(match[1]);
      const lon = parseFloat(match[2]);
      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        onChange({ latitude: lat, longitude: lon });
        setShowSuggestions(false);
        clearGeocoding();
        return;
      }
    }

    // If not coordinates, search for address after debounce
    if (val.trim().length >= 2) {
      const timer = setTimeout(() => {
        geocodeSearch(val);
        setShowSuggestions(true);
      }, 300);
      setDebounceTimer(timer);
    } else {
      clearGeocoding();
      setShowSuggestions(false);
    }

    // Clear location if input is empty
    if (val.trim() === '') {
      onChange(null);
    }
  };

  const handleSuggestionClick = (result: GeocodingResult) => {
    const lat = parseFloat(result.lat);
    const lon = parseFloat(result.lon);

    // Get a friendly name
    const name = result.name ||
      result.address?.city ||
      result.address?.town ||
      result.address?.village ||
      result.display_name.split(',')[0];

    onChange({ latitude: lat, longitude: lon, name });
    setInputValue(result.display_name);
    setShowSuggestions(false);
    clearGeocoding();
  };

  const handleUseCurrentLocation = () => {
    requestLocation();
  };

  const handleInputFocus = () => {
    if (geocodeResults.length > 0) {
      setShowSuggestions(true);
    }
  };

  const loading = geoLoading || geocodeLoading;

  return (
    <div className="location-input">
      <label htmlFor="location" className="location-label">
        Location
      </label>
      <div className="location-input-group">
        <div className="location-input-wrapper">
          <input
            ref={inputRef}
            id="location"
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            placeholder="Enter address, city, or ZIP code"
            className="location-text-input"
            autoComplete="off"
          />
          {showSuggestions && geocodeResults.length > 0 && (
            <div ref={suggestionsRef} className="location-suggestions">
              {geocodeResults.map((result, index) => (
                <button
                  key={index}
                  type="button"
                  className="location-suggestion"
                  onClick={() => handleSuggestionClick(result)}
                >
                  <span className="suggestion-name">
                    {result.name || result.display_name.split(',')[0]}
                  </span>
                  <span className="suggestion-detail">
                    {result.display_name}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
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
      {geoError && <p className="location-error">{geoError}</p>}
      {value && (
        <p className="location-preview">
          {value.name ? `${value.name} · ` : ''}{value.latitude.toFixed(4)}°, {value.longitude.toFixed(4)}°
        </p>
      )}
    </div>
  );
}
