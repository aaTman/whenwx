import { useState, useEffect } from 'react';
import { WEATHER_VARIABLES } from '../config/variables';
import type { WeatherVariable } from '../config/variables';
import './ThresholdBuilder.css';

interface ThresholdBuilderProps {
  selectedVariable: WeatherVariable | null;
  threshold: number;
  operator: 'lt' | 'gt';
  onVariableChange: (variable: WeatherVariable | null) => void;
  onThresholdChange: (value: number) => void;
  onOperatorChange: (op: 'lt' | 'gt') => void;
}

export function ThresholdBuilder({
  selectedVariable,
  threshold,
  operator,
  onVariableChange,
  onThresholdChange,
  onOperatorChange,
}: ThresholdBuilderProps) {
  // Local string state so the user can clear the field while typing
  const [inputValue, setInputValue] = useState(String(threshold));

  // Sync when parent threshold changes (e.g., variable switch resets default)
  useEffect(() => {
    setInputValue(String(threshold));
  }, [threshold]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    setInputValue(raw);
    const parsed = parseFloat(raw);
    if (!isNaN(parsed)) {
      onThresholdChange(parsed);
    }
  };

  const handleInputBlur = () => {
    // On blur, if empty or invalid, reset to current threshold
    const parsed = parseFloat(inputValue);
    if (isNaN(parsed)) {
      setInputValue(String(threshold));
    }
  };

  const handleVariableChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const varId = e.target.value;
    if (!varId) {
      onVariableChange(null);
      return;
    }
    const variable = WEATHER_VARIABLES.find(v => v.id === varId);
    if (variable) {
      onVariableChange(variable);
      // Reset to defaults for new variable
      onThresholdChange(variable.defaultThreshold);
      onOperatorChange(variable.defaultOperator);
    }
  };

  return (
    <div className="threshold-builder">
      <label htmlFor="variable" className="tb-label">
        Weather Variable
      </label>
      <select
        id="variable"
        value={selectedVariable?.id || ''}
        onChange={handleVariableChange}
        className="tb-select"
      >
        <option value="">Select a variable...</option>
        {WEATHER_VARIABLES.map(v => (
          <option key={v.id} value={v.id}>
            {v.label}
          </option>
        ))}
      </select>

      {selectedVariable && (
        <div className="tb-threshold-row">
          <label htmlFor="threshold" className="tb-label">
            Threshold
          </label>
          <div className="tb-input-group">
            <div className="tb-operator-toggle">
              <button
                type="button"
                className={`tb-op-btn ${operator === 'lt' ? 'active' : ''}`}
                onClick={() => onOperatorChange('lt')}
              >
                Below
              </button>
              <button
                type="button"
                className={`tb-op-btn ${operator === 'gt' ? 'active' : ''}`}
                onClick={() => onOperatorChange('gt')}
              >
                Above
              </button>
            </div>
            <div className="tb-value-input">
              <input
                id="threshold"
                type="number"
                value={inputValue}
                onChange={handleInputChange}
                onBlur={handleInputBlur}
                min={selectedVariable.min}
                max={selectedVariable.max}
                step={selectedVariable.step}
                className="tb-number"
              />
              <span className="tb-unit">{selectedVariable.displayUnit}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
