import type { WeatherEvent } from '../types/weather';

/**
 * Weather events configuration
 *
 * This is the expandable framework for adding new weather event types.
 * Each event defines the variable, threshold, and comparison operator
 * used to detect when the condition is met.
 */

export const WEATHER_EVENTS: WeatherEvent[] = [
  {
    id: 'freezing',
    name: 'Freezing Temperatures',
    description: 'Temperature drops below -10°C',
    variable: '2t',
    threshold: 263.15,      // -10°C in Kelvin
    thresholdDisplay: -10,
    operator: 'lt',
    unit: '°C'
  },
  // Future events can be added here:
  // {
  //   id: 'heavy-rain',
  //   name: 'Heavy Rain',
  //   description: 'Precipitation rate exceeds 10 mm/hr',
  //   variable: 'tprate',
  //   threshold: 0.00278,   // ~10 mm/hr in kg/m²/s
  //   thresholdDisplay: 10,
  //   operator: 'gt',
  //   unit: 'mm/hr'
  // },
  // {
  //   id: 'high-wind',
  //   name: 'High Winds',
  //   description: 'Wind speed exceeds 50 km/h',
  //   variable: 'wind10m',
  //   threshold: 13.89,     // 50 km/h in m/s
  //   thresholdDisplay: 50,
  //   operator: 'gt',
  //   unit: 'km/h'
  // },
];

export function getEventById(id: string): WeatherEvent | undefined {
  return WEATHER_EVENTS.find(event => event.id === id);
}

export function getOperatorSymbol(operator: WeatherEvent['operator']): string {
  const symbols: Record<WeatherEvent['operator'], string> = {
    lt: '<',
    gt: '>',
    lte: '≤',
    gte: '≥',
    eq: '='
  };
  return symbols[operator];
}
