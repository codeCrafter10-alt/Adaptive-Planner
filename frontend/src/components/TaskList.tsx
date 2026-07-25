import { useState } from 'react';
import ConfirmDialog from './ConfirmDialog';
import TaskEditForm from './TaskEditForm';
import type { Task, TaskUpdateInput } from '../types/task';

interface TaskListProps {
  tasks: Task[];
  onToggleComplete: (task: Task) => Promise<void>;
  onDelete: (task: Task) => Promise<void>;
  onUpdate: (task: Task, input: TaskUpdateInput) => Promise<void>;
}

function TaskList({ tasks, onToggleComplete, onDelete, onUpdate }: TaskListProps) {
  const [pendingTaskIds, setPendingTaskIds] = useState<Set<number>>(new Set());
  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null);
  const formatPriority = (priority: Task['priority']) =>
    priority.charAt(0).toUpperCase() + priority.slice(1);

  // Tasks created/edited without an explicit due time are stored at
  // 23:59:59 (see TaskForm/TaskEditForm's fallback). An explicit time
  // always comes from <input type="time">, which never produces seconds,
  // so it saves as 23:59:00 — distinguishable from the sentinel. This lets
  // a genuine "due at 11:59 PM" still display while the "no time chosen"
  // default stays hidden. Seconds themselves are never shown either way.
  const formatDueDate = (isoDueDate: string) => {
    const due = new Date(isoDueDate);
    const isNoTimeSentinel =
      due.getHours() === 23 && due.getMinutes() === 59 && due.getSeconds() === 59;
    const datePart = due.toLocaleDateString();

    if (isNoTimeSentinel) {
      return datePart;
    }

    const timePart = due.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    return `${datePart}, ${timePart}`;
  };

  const handleToggle = async (task: Task) => {
    if (pendingTaskIds.has(task.id)) return; // prevent duplicate actions for this task
    setPendingTaskIds((prev) => {
      const next = new Set(prev);
      next.add(task.id);
      return next;
    });
    try {
      await onToggleComplete(task);
    } finally {
      setPendingTaskIds((prev) => {
        const next = new Set(prev);
        next.delete(task.id);
        return next;
      });
    }
  };

  const handleDelete = (task: Task) => {
    if (pendingTaskIds.has(task.id)) return;
    setTaskToDelete(task);
  };

  const confirmDelete = async () => {
    if (!taskToDelete) return;
    const task = taskToDelete;
    setTaskToDelete(null);
    setPendingTaskIds((prev) => {
      const next = new Set(prev);
      next.add(task.id);
      return next;
    });
    try {
      await onDelete(task);
    } finally {
      setPendingTaskIds((prev) => {
        const next = new Set(prev);
        next.delete(task.id);
        return next;
      });
    }
  };

  const handleEdit = (task: Task) => {
    if (pendingTaskIds.has(task.id)) return;
    setEditingTaskId(task.id);
  };

  const handleSaveEdit = async (task: Task, input: TaskUpdateInput) => {
    await onUpdate(task, input);
    setEditingTaskId(null);
  };

  if (tasks.length === 0) {
    return <p className="task-list-empty">No tasks yet.</p>;
  }

  return (
    <>
      <ul className="task-list">
        {tasks.map((task) => {
          const isCompleted = task.completed_at !== null;
          const isPending = pendingTaskIds.has(task.id);
          const isEditing = editingTaskId === task.id;
          // While one task is being edited, block actions on every other task
          // so in-progress edits can't be silently discarded.
          const isDisabled = isPending || (editingTaskId !== null && !isEditing);

          if (isEditing) {
            return (
              <li key={task.id} className={`task-item priority-${task.priority}`}>
                <TaskEditForm
                  task={task}
                  onSave={(input) => handleSaveEdit(task, input)}
                  onCancel={() => setEditingTaskId(null)}
                />
              </li>
            );
          }

          return (
            <li key={task.id} className={`task-item priority-${task.priority}`}>
              <div className="task-content">
                <label className="task-checkbox-label">
                  <input
                    type="checkbox"
                    className="task-checkbox-input"
                    checked={isCompleted}
                    disabled={isDisabled}
                    onChange={() => handleToggle(task)}
                  />
                  <span className="checkmark" aria-hidden="true">
                    <svg viewBox="0 0 12 10" focusable="false" aria-hidden="true">
                      <path d="M1 5L4.5 8.5L11 1.5" />
                    </svg>
                  </span>
                  <span className={isCompleted ? 'task-title completed' : 'task-title'}>
                    {task.title}
                  </span>
                </label>
                <div className="task-meta">
                  <span className="task-meta-item task-meta-duration">
                    <span className="task-meta-label">Duration</span>
                    <span className="task-meta-value">{task.estimated_duration_minutes} min</span>
                  </span>
                  <span className="task-meta-item task-meta-priority">
                    <span className="task-meta-label">Priority</span>
                    <span className="task-meta-value">{formatPriority(task.priority)}</span>
                  </span>
                  <span className="task-meta-item task-meta-due">
                    <span className="task-meta-label">Due</span>
                    <span className="task-meta-value">{formatDueDate(task.due_date)}</span>
                  </span>
                </div>
              </div>
              <div className="task-item-actions">
                <button
                  type="button"
                  className="task-edit-button"
                  disabled={isDisabled}
                  onClick={() => handleEdit(task)}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="task-delete-button task-delete-button-destructive"
                  disabled={isDisabled}
                  onClick={() => handleDelete(task)}
                >
                  {isPending ? 'Working…' : 'Delete'}
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <ConfirmDialog
        open={taskToDelete !== null}
        title="Delete task?"
        message={taskToDelete ? `Delete '${taskToDelete.title}'?` : ''}
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={confirmDelete}
        onCancel={() => setTaskToDelete(null)}
      />
    </>
  );
}

export default TaskList;