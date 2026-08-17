import { useEffect, useState } from 'react';
import type { SubmitEventHandler } from 'react';
import type {
  AvailabilityExceptionCreateInput,
} from '../types/availability-exception';

type AvailabilityType = 'available' | 'unavailable';

interface AvailabilityExceptionFormProps {
  initialValues?: {
    date: string;
    is_available: boolean;
    start_time: string | null;
    end_time: string | null;
    reason: string | null;
  };
  submitLabel: string;
  submittingLabel: string;
  onSubmit: (input: AvailabilityExceptionCreateInput) => Promise<void>;
  onCancel?: () => void;
}

function AvailabilityExceptionForm({
  initialValues,
  submitLabel,
  submittingLabel,
  onSubmit,
  onCancel,
}: AvailabilityExceptionFormProps) {
  const [date, setDate] = useState(initialValues?.date ?? '');
  const [availabilityType, setAvailabilityType] = useState<AvailabilityType>(
    initialValues?.is_available === false
      ? 'unavailable'
      : 'available',
  );
  const [startTime, setStartTime] = useState(
    initialValues?.start_time?.slice(0, 5) ?? '',
  );
  const [endTime, setEndTime] = useState(
    initialValues?.end_time?.slice(0, 5) ?? '',
  );
  const [reason, setReason] = useState(initialValues?.reason ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDate(initialValues?.date ?? '');
    setAvailabilityType(
      initialValues?.is_available === false ? 'unavailable' : 'available',
    );
    setStartTime(initialValues?.start_time?.slice(0, 5) ?? '');
    setEndTime(initialValues?.end_time?.slice(0, 5) ?? '');
    setReason(initialValues?.reason ?? '');
    setError(null);
  }, [initialValues]);

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault();

    if (!date) {
      setError('Date is required.');
      return;
    }

    if (availabilityType === 'available') {
      if (!startTime || !endTime) {
        setError('Start time and end time are required when available.');
        return;
      }

      if (startTime >= endTime) {
        setError('Start time must be before end time.');
        return;
      }
    }

    setError(null);
    setSubmitting(true);

    try {
      await onSubmit({
        date,
        is_available: availabilityType === 'available',
        start_time: availabilityType === 'available' ? startTime : null,
        end_time: availabilityType === 'available' ? endTime : null,
        reason: reason.trim() || null,
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
    <form className="availability-exception-form" onSubmit={handleSubmit}>
      <div className="availability-exception-form-fields">
        <label className="field">
          <span className="label-text">Date</span>
          <input
            type="date"
            required
            value={date}
            disabled={submitting}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="label-text">Availability type</span>
          <select
            value={availabilityType}
            disabled={submitting}
            onChange={(event) =>
              setAvailabilityType(event.target.value as AvailabilityType)
            }
          >
            <option value="available">Available</option>
            <option value="unavailable">Unavailable</option>
          </select>
        </label>

        {availabilityType === 'available' && (
          <>
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
          </>
        )}

        <label className="field availability-exception-reason-field">
          <span className="label-text">
            Reason<span className="muted">(optional)</span>
          </span>
          <input
            type="text"
            value={reason}
            disabled={submitting}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
      </div>

      <div className="availability-exception-form-actions">
        <button type="submit" className="availability-exception-form-submit" disabled={submitting}>
          {submitting ? submittingLabel : submitLabel}
        </button>

        {onCancel && (
          <button
            type="button"
            className="availability-exception-form-cancel"
            disabled={submitting}
            onClick={onCancel}
          >
            Cancel
          </button>
        )}
      </div>

      {error && (
        <div className="availability-exception-form-errors">
          {error.split(/\n+/).map((message, index) => (
            <p key={index} className="availability-exception-form-error">
              {message}
            </p>
          ))}
        </div>
      )}
    </form>
  );
}

export default AvailabilityExceptionForm;
