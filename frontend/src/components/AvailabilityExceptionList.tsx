import { useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import AvailabilityExceptionForm from './AvailabilityExceptionForm';
import type {
  AvailabilityException,
  AvailabilityExceptionCreateInput,
  AvailabilityExceptionUpdateInput,
} from '../types/availability-exception';
import { formatHumanReadableDate } from '../utils/date';

interface AvailabilityExceptionListProps {
  exceptions: AvailabilityException[];
  onCreate: (input: AvailabilityExceptionCreateInput) => Promise<void>;
  onUpdate: (
    id: number,
    input: AvailabilityExceptionUpdateInput,
  ) => Promise<void>;
  onDelete: (exception: AvailabilityException) => Promise<void>;
}

function formatTime(time: string): string {
  const [hoursString, minutesString] = time.split(':');
  const hours = Number(hoursString);
  const minutes = Number(minutesString);

  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;

  return `${displayHours}:${String(minutes).padStart(2, '0')} ${period}`;
}

function formatDate(date: string): string {
  return formatHumanReadableDate(date);
}

function formatTimeRange(exception: AvailabilityException): string {
  if (!exception.start_time || !exception.end_time) {
    return 'Unavailable';
  }

  return `${formatTime(exception.start_time)} – ${formatTime(exception.end_time)}`;
}

function AvailabilityExceptionList({
  exceptions,
  onCreate,
  onUpdate,
  onDelete,
}: AvailabilityExceptionListProps) {
  const [adding, setAdding] = useState(false);
  const [editingExceptionId, setEditingExceptionId] = useState<number | null>(null);
  const [exceptionToDelete, setExceptionToDelete] = useState<AvailabilityException | null>(null);
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set());

  const handleAdd = () => {
    if (adding || editingExceptionId !== null || exceptionToDelete !== null) {
      return;
    }
    setAdding(true);
  };

  const handleEdit = (exception: AvailabilityException) => {
    if (pendingIds.has(exception.id)) return;
    if (adding || editingExceptionId !== null || exceptionToDelete !== null) {
      return;
    }

    setEditingExceptionId(exception.id);
  };

  const handleCancelForm = () => {
    setAdding(false);
    setEditingExceptionId(null);
  };

  const handleCreate = async (input: AvailabilityExceptionCreateInput) => {
    await onCreate(input);
    setAdding(false);
  };

  const handleUpdate = async (
    id: number,
    input: AvailabilityExceptionUpdateInput,
  ) => {
    await onUpdate(id, input);
    setEditingExceptionId(null);
  };

  const handleDelete = (exception: AvailabilityException) => {
    if (pendingIds.has(exception.id)) return;
    if (adding || editingExceptionId !== null || exceptionToDelete !== null) {
      return;
    }

    setExceptionToDelete(exception);
  };

  const confirmDelete = async () => {
    if (!exceptionToDelete) return;

    const exception = exceptionToDelete;

    setExceptionToDelete(null);
    setPendingIds((previous) => {
      const next = new Set(previous);
      next.add(exception.id);
      return next;
    });

    try {
      await onDelete(exception);
    } finally {
      setPendingIds((previous) => {
        const next = new Set(previous);
        next.delete(exception.id);
        return next;
      });
    }
  };

  return (
    <>
      <section className="availability-exception-section">
        <div className="availability-exception-header">
          <div>
            <h2 className="availability-exception-title">Exceptions</h2>
            <p className="availability-exception-description">
              Date-specific overrides for weekly availability.
            </p>
          </div>

          {!adding && editingExceptionId === null && (
            <button
              type="button"
              className="availability-exception-add-button"
              onClick={handleAdd}
            >
              + Add Exception
            </button>
          )}
        </div>

        {adding && (
          <div className="availability-exception-card availability-exception-card-editing">
            <AvailabilityExceptionForm
              mode="create"
              initialValues={{
                date: '',
                is_available: true,
                start_time: '',
                end_time: '',
                reason: '',
              }}
              submitLabel="Add Exception"
              submittingLabel="Adding…"
              onSubmit={handleCreate}
              onCancel={handleCancelForm}
            />
          </div>
        )}

        {exceptions.length === 0 && !adding && editingExceptionId === null && (
          <p className="availability-exception-empty">No upcoming exceptions.</p>
        )}

        <div className="availability-exception-list">
          {exceptions.map((exception) => {
            const isEditing = editingExceptionId === exception.id;
            const isPending = pendingIds.has(exception.id);
            const isDisabled =
              isPending ||
              adding ||
              (editingExceptionId !== null && !isEditing);

            if (isEditing) {
              return (
                <div
                  key={exception.id}
                  className="availability-exception-card availability-exception-card-editing"
                >
                  <AvailabilityExceptionForm
                    mode="edit"
                    initialValues={exception}
                    submitLabel="Save"
                    submittingLabel="Saving…"
                    onSubmit={(input) => handleUpdate(exception.id, input)}
                    onCancel={handleCancelForm}
                  />
                </div>
              );
            }

            return (
              <article key={exception.id} className="availability-exception-card">
                <div className="availability-exception-content">
                  <div className="availability-exception-date">
                    {formatDate(exception.date)}
                  </div>

                  <div className="availability-exception-status">
                    {exception.is_available
                      ? formatTimeRange(exception)
                      : 'Unavailable'}
                  </div>

                  {exception.reason && (
                    <div className="availability-exception-reason">
                      {exception.reason}
                    </div>
                  )}
                </div>

                <div className="availability-exception-actions">
                  <button
                    type="button"
                    className="availability-edit-button"
                    disabled={isDisabled}
                    onClick={() => handleEdit(exception)}
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    className="availability-delete-button"
                    disabled={isDisabled}
                    onClick={() => handleDelete(exception)}
                  >
                    {isPending ? 'Working…' : 'Delete'}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <ConfirmDialog
        open={exceptionToDelete !== null}
        title="Delete availability exception?"
        message={
          exceptionToDelete
            ? `Delete ${formatDate(exceptionToDelete.date)}?`
            : ''
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={confirmDelete}
        onCancel={() => setExceptionToDelete(null)}
      />
    </>
  );
}

export default AvailabilityExceptionList;
