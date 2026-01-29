import { WEATHER_EVENTS, getOperatorSymbol } from '../config/events';
import type { WeatherEvent } from '../types/weather';
import './EventSelector.css';

interface EventSelectorProps {
  value: WeatherEvent | null;
  onChange: (event: WeatherEvent | null) => void;
}

export function EventSelector({ value, onChange }: EventSelectorProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const eventId = e.target.value;
    if (!eventId) {
      onChange(null);
      return;
    }
    const event = WEATHER_EVENTS.find(ev => ev.id === eventId);
    onChange(event || null);
  };

  return (
    <div className="event-selector">
      <label htmlFor="event" className="event-label">
        Weather Event
      </label>
      <select
        id="event"
        value={value?.id || ''}
        onChange={handleChange}
        className="event-select"
      >
        <option value="">Select a weather event...</option>
        {WEATHER_EVENTS.map(event => (
          <option key={event.id} value={event.id}>
            {event.name}
          </option>
        ))}
      </select>
      {value && (
        <p className="event-description">
          {value.description} ({getOperatorSymbol(value.operator)} {value.thresholdDisplay}{value.unit})
        </p>
      )}
    </div>
  );
}
