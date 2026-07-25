import { useEffect, useState } from 'react';
import { createTask, deleteTask, listTasks, updateTask } from './api/tasks';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';
import type { Task, TaskCreateInput, TaskUpdateInput } from './types/task';

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    listTasks()
      .then(setTasks)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load tasks.'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async (input: TaskCreateInput) => {
    const task = await createTask(input);
    setTasks((prev) => [...prev, task]);
  };

  // Errors intentionally propagate to the caller (TaskEditForm), which
  // displays them inline — matching handleCreate's convention rather than
  // the top-level actionError banner used by toggle/delete below.
  const handleUpdate = async (task: Task, input: TaskUpdateInput) => {
    const updated = await updateTask(task.id, input);
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
  };

  const handleToggleComplete = async (task: Task) => {
    // clear any previous action error when starting a new action
    setActionError(null);
    try {
      const wasCompleted = task.completed_at !== null;
      const updated = await updateTask(task.id, { completed: !wasCompleted });

      setTasks((prev) =>
        prev.map((t) => (t.id === updated.id ? updated : t))
      );
      // clear action error on success
      setActionError(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to update task.');
    }
  };

  const handleDelete = async (task: Task) => {
    // clear any previous action error when starting a new delete
    setActionError(null);
    try {
      await deleteTask(task.id);

      setTasks((prev) =>
        prev.filter((t) => t.id !== task.id)
      );
      // clear action error on success
      setActionError(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete task.');
    }
  };

  return (
    <main className="app">
      <h1 style={{ fontSize: '1.7rem' }}>Adaptive Planner</h1>
      <TaskForm onCreate={handleCreate} />
      {loading && <p>Loading tasks…</p>}
      {error && <p className="app-error">{error}</p>}
      {!loading && !error && (
        <>
          {actionError && <p className="app-error">{actionError}</p>}
          <TaskList
            tasks={tasks}
            onToggleComplete={handleToggleComplete}
            onDelete={handleDelete}
            onUpdate={handleUpdate}
          />
        </>
      )}
    </main>
  );
}

export default App;