import { useState } from 'react';
import type { Task, TaskPriority, TaskUpdateInput } from '../types/task';

interface TaskEditFormProps {
  task: Task;
  onSave: (input: TaskUpdateInput) => Promise<void>;
  onCancel: () => void;
}

function splitDueDate(iso: string): { date: string; time: string } {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  const date = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  // 23:59:59 is the "no time chosen" sentinel (see TaskForm/TaskEditForm's
  // due-date construction). Leave the time field blank so an unedited save
  // falls back through the same sentinel branch instead of turning into an
  // explicit 11:59 PM.
  const isNoTimeSentinel = d.getHours() === 23 && d.getMinutes() === 59 && d.getSeconds() === 59;
  const time = isNoTimeSentinel ? '' : `${pad(d.getHours())}:${pad(d.getMinutes())}`;

  return { date, time };
}

function buildFormFromTask(task: Task) {
  const { date, time } = splitDueDate(task.due_date);
  return {
    title: task.title,
    description: task.description ?? '',
    estimatedDurationMinutes: String(task.estimated_duration_minutes),
    dueDate: date,
    dueTime: time,
    priority: task.priority,
  };
}

function TaskEditForm({ task, onSave, onCancel }: TaskEditFormProps) {
  const [form, setForm] = useState(() => buildFormFromTask(task));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    const durationMinutes = Number(form.estimatedDurationMinutes);
    if (!form.title.trim() || !durationMinutes || durationMinutes <= 0) {
      setError('Title and a positive estimated duration are required.');
      return;
    }
    if (!form.dueDate) {
      setError('Due date is required.');
      return;
    }

    // Same sentinel convention as TaskForm: explicit times always save with
    // :00 seconds (from <input type="time">); a blank time falls back to
    // 23:59:59 so it stays distinguishable from an explicit 11:59 PM.
    const deadline = form.dueTime
      ? new Date(`${form.dueDate}T${form.dueTime}:00`)
      : new Date(`${form.dueDate}T23:59:59`);

    setError(null);
    setSubmitting(true);
    try {
      await onSave({
        title: form.title.trim(),
        description: form.description.trim() || null,
        estimated_duration_minutes: durationMinutes,
        due_date: deadline.toISOString(),
        priority: form.priority as TaskPriority,
      });
      // On success the parent unmounts this form (edit mode closes), so no
      // further state updates are needed here.
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
      setSubmitting(false);
    }
  };

  return (
    <form className="task-form task-edit-form" onSubmit={handleSubmit}>
      <label className="field">
        <span className="label-text">Title</span>
        <input
          type="text"
          value={form.title}
          disabled={submitting}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="label-text">Description<span className="muted">(optional)</span></span>
        <input
          type="text"
          value={form.description}
          disabled={submitting}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="label-text">Estimated minutes</span>
        <input
          type="number"
          min={1}
          value={form.estimatedDurationMinutes}
          disabled={submitting}
          onChange={(e) => setForm({ ...form, estimatedDurationMinutes: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="label-text">Due date</span>
        <input
          type="date"
          required
          value={form.dueDate}
          disabled={submitting}
          onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="label-text">Due time<span className="muted">(optional)</span></span>
        <input
          type="time"
          value={form.dueTime}
          disabled={submitting}
          onChange={(e) => setForm({ ...form, dueTime: e.target.value })}
        />
      </label>

      <label className="field">
        <span className="label-text">Priority</span>
        <select
          value={form.priority}
          disabled={submitting}
          onChange={(e) => setForm({ ...form, priority: e.target.value as TaskPriority })}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </label>

      <div className="task-form-actions">
        <button type="submit" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save'}
        </button>
        <button type="button" disabled={submitting} onClick={onCancel}>
          Cancel
        </button>
      </div>

      {error && (
        <div className="task-form-errors">
          {error.split(/\n+/).map((m, i) => (
            <p key={i} className="task-form-error">{m}</p>
          ))}
        </div>
      )}
    </form>
  );
}

export default TaskEditForm;