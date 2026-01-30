import { useState, useCallback } from 'react';

export interface GeocodingResult {
  lat: string;
  lon: string;
  display_name: string;
  name?: string;
  address?: {
    city?: string;
    town?: string;
    village?: string;
    state?: string;
    country?: string;
    postcode?: string;
  };
}

interface UseGeocodingReturn {
  results: GeocodingResult[];
  loading: boolean;
  error: string | null;
  search: (query: string) => Promise<void>;
  clear: () => void;
}

const NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search';

export function useGeocoding(): UseGeocodingReturn {
  const [results, setResults] = useState<GeocodingResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (query: string) => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        q: query,
        format: 'json',
        limit: '5',
        addressdetails: '1',
      });

      const response = await fetch(`${NOMINATIM_URL}?${params}`, {
        headers: {
          'Accept': 'application/json',
          // Nominatim requires a User-Agent
          'User-Agent': 'WhenWX/1.0',
        },
      });

      if (!response.ok) {
        throw new Error('Geocoding request failed');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Geocoding failed');
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setResults([]);
    setError(null);
  }, []);

  return { results, loading, error, search, clear };
}
