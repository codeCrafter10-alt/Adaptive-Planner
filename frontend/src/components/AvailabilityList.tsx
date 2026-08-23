import { useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import AvailabilityForm from './AvailabilityForm';
import {
  WEEKDAYS,
  type Availability,
  type AvailabilityCreateInput,
  type AvailabilityUpdateInput,
} from '../types/availability';

interface AvailabilityListProps {
  availability: Availability[];
  onCreate: (input: AvailabilityCreateInput) => Promise<void>;
  onUpdate: (id: number, input: AvailabilityUpdateInput) => Promise<void>;
  onDelete: (availability: Availability) => Promise<void>;
}
function formatTime(time: string): string {
  const [hoursString, minutesString] = time.split(':');
  const hours = Number(hoursString);
  const minutes = Number(minutesString);

  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;

  return `${displayHours}:${String(minutes).padStart(2, '0')} ${period}`;
}

function formatTimeRange(block: Availability): string {
  return `${formatTime(block.start_time)} – ${formatTime(block.end_time)}`;
}

function AvailabilityList({
  availability,
  onCreate,
  onUpdate,
  onDelete,
}: AvailabilityListProps) {
  const [addingDay, setAddingDay] = useState<number | null>(null);
  const [editingBlockId, setEditingBlockId] = useState<number | null>(null);
  const [availabilityToDelete, setAvailabilityToDelete] =
    useState<Availability | null>(null);
  const [pendingIds, setPendingIds] = useState<Set<number>>(new Set());

  const getBlocksForDay = (dayOfWeek: number) =>
    availability.filter((block) => block.day_of_week === dayOfWeek);

  const handleAdd = (dayOfWeek: number) => {
    if (
      addingDay !== null ||
      editingBlockId !== null ||
      availabilityToDelete !== null
    ) return;
    setAddingDay(dayOfWeek);
  };

  const handleEdit = (block: Availability) => {
    if (pendingIds.has(block.id)) return;
    if (
      addingDay !== null ||
      editingBlockId !== null ||
      availabilityToDelete !== null
    ) return;

    setEditingBlockId(block.id);
  };

  const handleCancelForm = () => {
    setAddingDay(null);
    setEditingBlockId(null);
  };

  const handleCreate = async (input: AvailabilityCreateInput) => {
    await onCreate(input);
    setAddingDay(null);
  };

  const handleUpdate = async (
    id: number,
    input: AvailabilityUpdateInput,
  ) => {
    await onUpdate(id, input);
    setEditingBlockId(null);
  };

  const handleDelete = (block: Availability) => {
    if (pendingIds.has(block.id)) return;
    if (
      addingDay !== null ||
      editingBlockId !== null ||
      availabilityToDelete !== null
    ) {
      return;
    }

    setAvailabilityToDelete(block);
  };

  const confirmDelete = async () => {
    if (!availabilityToDelete) return;

    const block = availabilityToDelete;

    setAvailabilityToDelete(null);

    setPendingIds((previous) => {
      const next = new Set(previous);
      next.add(block.id);
      return next;
    });

    try {
      await onDelete(block);
    } finally {
      setPendingIds((previous) => {
        const next = new Set(previous);
        next.delete(block.id);
        return next;
      });
    }
  };

  const renderDay = (day: (typeof WEEKDAYS)[number]) => {
    const blocks = getBlocksForDay(day.value);
    const isAdding = addingDay === day.value;

    return (
      <section key={day.value} className="availability-day">
        <div className="availability-day-header">
          <h2 className="availability-day-title">{day.label}</h2>
        </div>

        <div className="availability-day-content">
          {blocks.length === 0 && !isAdding && (
            <p className="availability-day-empty">No availability set.</p>
          )}

          {blocks.map((block) => {
            const isEditing = editingBlockId === block.id;
            const isPending = pendingIds.has(block.id);
            const isDisabled =
              isPending ||
              addingDay !== null ||
              (editingBlockId !== null && !isEditing);

            if (isEditing) {
              return (
                <div
                  key={block.id}
                  className="availability-block availability-block-editing"
                >
                  <AvailabilityForm
                    mode="edit"
                    initialValues={block}
                    submitLabel="Save"
                    submittingLabel="Saving…"
                    onSubmit={(input) => handleUpdate(block.id, input)}
                    onCancel={handleCancelForm}
                  />
                </div>
              );
            }

            return (
              <div key={block.id} className="availability-block">
                <span className="availability-time">
                  {formatTimeRange(block)}
                </span>

                <div className="availability-block-actions">
                  <button
                    type="button"
                    className="availability-edit-button"
                    disabled={isDisabled}
                    onClick={() => handleEdit(block)}
                  >
                    Edit
                  </button>

                  <button
                    type="button"
                    className="availability-delete-button"
                    disabled={isDisabled}
                    onClick={() => handleDelete(block)}
                  >
                    {isPending ? 'Working…' : 'Delete'}
                  </button>
                </div>
              </div>
            );
          })}

          {isAdding && (
            <div className="availability-block availability-block-editing">
              <AvailabilityForm
                mode="create"
                initialValues={{
                  day_of_week: day.value,
                  start_time: '',
                  end_time: '',
                }}
                submitLabel="Add Block"
                submittingLabel="Adding…"
                onSubmit={handleCreate}
                onCancel={handleCancelForm}
              />
            </div>
          )}

          {!isAdding && addingDay === null && editingBlockId === null && (
            <button
              type="button"
              className="availability-add-button"
              onClick={() => handleAdd(day.value)}
            >
              + Add Block
            </button>
          )}
        </div>
      </section>
    );
  };

  return (
    <>
      <div className="availability-list">
        {WEEKDAYS.map(renderDay)}
      </div>

      <ConfirmDialog
        open={availabilityToDelete !== null}
        title="Delete availability block?"
        message={
          availabilityToDelete
            ? `Delete ${formatTimeRange(availabilityToDelete)} on ${
                WEEKDAYS[availabilityToDelete.day_of_week].label
              }?`
            : ''
        }
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={confirmDelete}
        onCancel={() => setAvailabilityToDelete(null)}
      />
    </>
  );
}

export default AvailabilityList;