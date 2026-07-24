import { useState } from 'react';
import type { TaskCreateInput, TaskPriority } from '../types/task';

interface TaskFormProps {
  onCreate: (input: TaskCreateInput) => Promise<void>;
}

const emptyForm = {
  title: '',
  description: '',
  estimatedDurationMinutes: '',
  dueDate: '',
  dueTime: '',
  priority: 'medium' as TaskPriority,
};

function TaskForm({ onCreate }: TaskFormProps) {
  const [form, setForm] = useState(emptyForm);
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

    const deadline = new Date(`${form.dueDate}T${form.dueTime || '23:59'}:00`);

    setError(null);
    setSubmitting(true);
    try {
      await onCreate({
        title: form.title.trim(),
        description: form.description.trim() || null,
        estimated_duration_minutes: durationMinutes,
        due_date: deadline.toISOString(),
        priority: form.priority,
      });
      setForm(emptyForm);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="task-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Task title"
        value={form.title}
        onChange={(e) => setForm({ ...form, title: e.target.value })}
      />
      <input
        type="text"
        placeholder="Description (optional)"
        value={form.description}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
      />
      <input
        type="number"
        placeholder="Estimated minutes"
        min={1}
        value={form.estimatedDurationMinutes}
        onChange={(e) => setForm({ ...form, estimatedDurationMinutes: e.target.value })}
      />
      <input
        type="date"
        aria-label="Due date"
        required
        value={form.dueDate}
        onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
      />
      <input
        type="time"
        aria-label="Due time (optional)"
        value={form.dueTime}
        onChange={(e) => setForm({ ...form, dueTime: e.target.value })}
      />
      <select
        value={form.priority}
        onChange={(e) => setForm({ ...form, priority: e.target.value as TaskPriority })}
      >
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>
      <button type="submit" disabled={submitting}>
        {submitting ? 'Adding…' : 'Add Task'}
      </button>
      {error && <p className="task-form-error">{error}</p>}
    </form>
  );
}

export default TaskForm;