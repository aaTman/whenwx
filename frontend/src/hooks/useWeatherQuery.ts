import { useState, useEffect } from 'react';
import type { WeatherQueryResult, QueryParams } from '../types/weather';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UseWeatherQueryReturn {
  data: WeatherQueryResult | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useWeatherQuery(params: QueryParams | null): UseWeatherQueryReturn {
  const [data, setData] = useState<WeatherQueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchTrigger, setFetchTrigger] = useState(0);

  useEffect(() => {
    if (!params) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const controller = new AbortController();

    async function fetchData() {
      if (!params) return;

      setLoading(true);
      setError(null);

      try {
        const url = new URL(`${API_BASE_URL}/query`);
        url.searchParams.set('lat', params.lat.toString());
        url.searchParams.set('lon', params.lon.toString());
        url.searchParams.set('event_id', params.eventId);

        const response = await fetch(url.toString(), {
          signal: controller.signal,
          headers: {
            'Accept': 'application/json',
          },
        });

        if (response.status === 429) {
          throw new Error('Rate limit exceeded. Please wait a minute before trying again.');
        }

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `Request failed: ${response.status}`);
        }

        const result = await response.json();
        setData(result);
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        setError(err instanceof Error ? err.message : 'Unknown error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    return () => controller.abort();
  }, [params?.lat, params?.lon, params?.eventId, fetchTrigger]);

  const refetch = () => setFetchTrigger(prev => prev + 1);

  return { data, loading, error, refetch };
}
