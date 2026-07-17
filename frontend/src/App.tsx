import { useEffect, useState } from 'react';
import { createTask, deleteTask, listTasks, updateTask } from './api/tasks';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';
import type { Task, TaskCreateInput } from './types/task';

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const handleToggleComplete = async (task: Task) => {
    const wasCompleted = task.completed_at !== null;
    const updated = await updateTask(task.id, { completed: !wasCompleted });
    setTasks((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
  };

  const handleDelete = async (task: Task) => {
    await deleteTask(task.id);
    setTasks((prev) => prev.filter((t) => t.id !== task.id));
  };

  return (
    <main className="app">
      <h1>Adaptive Planner</h1>
      <TaskForm onCreate={handleCreate} />
      {loading && <p>Loading tasks…</p>}
      {error && <p className="app-error">{error}</p>}
      {!loading && !error && (
        <TaskList tasks={tasks} onToggleComplete={handleToggleComplete} onDelete={handleDelete} />
      )}
    </main>
  );
}

export default App;