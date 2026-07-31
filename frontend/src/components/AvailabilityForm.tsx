import { useEffect, useState } from 'react';
import type { SubmitEventHandler } from 'react';
import {
  WEEKDAYS,
  type AvailabilityCreateInput
} from '../types/availability';

interface AvailabilityFormProps {
    mode: 'create' | 'edit';
    initialValues?: {
        day_of_week: number;
        start_time: string;
        end_time: string;
    };
    submitLabel: string;
    submittingLabel: string;
    onSubmit: (input: AvailabilityCreateInput) => Promise<void>;
    onCancel?: () => void;
}

function AvailabilityForm({
    mode,
    initialValues,
    submitLabel,
    submittingLabel,
    onSubmit,
    onCancel,
}: AvailabilityFormProps) {
  const [dayOfWeek, setDayOfWeek] = useState(
    initialValues?.day_of_week ?? 0,
  );
  const [startTime, setStartTime] = useState(
    initialValues?.start_time?.slice(0, 5) ?? '',
  );
  const [endTime, setEndTime] = useState(
    initialValues?.end_time?.slice(0, 5) ?? '',
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDayOfWeek(initialValues?.day_of_week ?? 0);
    setStartTime(initialValues?.start_time?.slice(0, 5) ?? '');
    setEndTime(initialValues?.end_time?.slice(0, 5) ?? '');
    setError(null);
  }, [initialValues]);

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();

    if (!startTime || !endTime) {
      setError('Start time and end time are required.');
      return;
    }

    if (startTime >= endTime) {
      setError('Start time must be before end time.');
      return;
    }

    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Something went wrong.',
      );
      setSubmitting(false);
    }
  };

  return (
    <form className="availability-form" onSubmit={handleSubmit}>
      {mode === 'edit' && (
        <label className="field">
            <span className="label-text">Day</span>
            <select
            value={dayOfWeek}
            disabled={submitting}
            onChange={(event) => setDayOfWeek(Number(event.target.value))}
            >
            {WEEKDAYS.map((day) => (
                <option key={day.value} value={day.value}>
                {day.label}
                </option>
            ))}
            </select>
        </label>
        )}

      <label className="field">
        <span className="label-text">Start time</span>
        <input
          type="time"
          required
          value={startTime}
          disabled={submitting}
          onChange={(event) => setStartTime(event.target.value)}
        />
      </label>

      <label className="field">
        <span className="label-text">End time</span>
        <input
          type="time"
          required
          value={endTime}
          disabled={submitting}
          onChange={(event) => setEndTime(event.target.value)}
        />
      </label>

      <div className="availability-form-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? submittingLabel : submitLabel}
        </button>

        {onCancel && (
          <button
            type="button"
            disabled={submitting}
            onClick={onCancel}
          >
            Cancel
          </button>
        )}
      </div>

      {error && (
        <div className="availability-form-errors">
          {error.split(/\n+/).map((message, index) => (
            <p key={index} className="availability-form-error">
              {message}
            </p>
          ))}
        </div>
      )}
    </form>
  );
}

export default AvailabilityForm;