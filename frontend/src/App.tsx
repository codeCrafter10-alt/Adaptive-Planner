import { useEffect, useState } from 'react';
import {
  createAvailability,
  deleteAvailability,
  listAvailability,
  updateAvailability,
} from './api/availability';
import {
  createAvailabilityException,
  deleteAvailabilityException,
  listAvailabilityExceptions,
  updateAvailabilityException,
} from './api/availability-exceptions';
import { createTask, deleteTask, listTasks, updateTask } from './api/tasks';
import AvailabilityList from './components/AvailabilityList';
import AvailabilityExceptionList from './components/AvailabilityExceptionList';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';
import type {
  Availability,
  AvailabilityCreateInput,
  AvailabilityUpdateInput,
} from './types/availability';
import type {
  AvailabilityException,
  AvailabilityExceptionCreateInput,
  AvailabilityExceptionUpdateInput,
} from './types/availability-exception';
import type { Task, TaskCreateInput, TaskUpdateInput } from './types/task';

type View = 'tasks' | 'availability';

function App() {
  const [view, setView] = useState<View>('tasks');

  // Task state
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Availability state
  const [availability, setAvailability] = useState<Availability[]>([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [availabilityError, setAvailabilityError] = useState<string | null>(null);
  const [availabilityActionError, setAvailabilityActionError] =
    useState<string | null>(null);

  // Availability exception state
  const [availabilityExceptions, setAvailabilityExceptions] = useState<
    AvailabilityException[]
  >([]);
  const [availabilityExceptionsLoading, setAvailabilityExceptionsLoading] =
    useState(false);
  const [availabilityExceptionsError, setAvailabilityExceptionsError] =
    useState<string | null>(null);
  const [
    availabilityExceptionsActionError,
    setAvailabilityExceptionsActionError,
  ] = useState<string | null>(null);

  useEffect(() => {
    listTasks()
      .then(setTasks)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : 'Failed to load tasks.',
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (view !== 'availability') return;

    let cancelled = false;

    setAvailabilityError(null);
    setAvailabilityLoading(true);

    listAvailability()
      .then((blocks) => {
        if (!cancelled) {
          setAvailability(blocks);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setAvailabilityError(
            err instanceof Error ? err.message : 'Failed to load availability.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAvailabilityLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [view]);

  useEffect(() => {
    if (view !== 'availability') return;

    let cancelled = false;

    setAvailabilityExceptionsError(null);
    setAvailabilityExceptionsLoading(true);

    listAvailabilityExceptions()
      .then((exceptions) => {
        if (!cancelled) {
          setAvailabilityExceptions(exceptions);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setAvailabilityExceptionsError(
            err instanceof Error
              ? err.message
              : 'Failed to load availability exceptions.',
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setAvailabilityExceptionsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [view]);

  useEffect(() => {
    setActionError(null);
    setAvailabilityActionError(null);
    setAvailabilityExceptionsActionError(null);
  }, [view]);

  // --------------------
  // Task handlers
  // --------------------

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
    setActionError(null);

    try {
      const wasCompleted = task.completed_at !== null;
      const updated = await updateTask(task.id, {
        completed: !wasCompleted,
      });

      setTasks((prev) =>
        prev.map((t) => (t.id === updated.id ? updated : t)),
      );

      setActionError(null);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'Failed to update task.',
      );
    }
  };

  const handleDelete = async (task: Task) => {
    setActionError(null);

    try {
      await deleteTask(task.id);

      setTasks((prev) => prev.filter((t) => t.id !== task.id));

      setActionError(null);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : 'Failed to delete task.',
      );
    }
  };

  // --------------------
  // Availability handlers
  // --------------------

  const handleCreateAvailability = async (
    input: AvailabilityCreateInput,
  ) => {
    setAvailabilityActionError(null);

    try {
      const block = await createAvailability(input);

      setAvailability((prev) =>
        [...prev, block].sort(
          (a, b) =>
            a.day_of_week - b.day_of_week ||
            a.start_time.localeCompare(b.start_time),
        ),
      );
    } catch (err) {
      setAvailabilityActionError(
        err instanceof Error
          ? err.message
          : 'Failed to add availability block.',
      );
      throw err;
    }
  };

  const handleUpdateAvailability = async (
    id: number,
    input: AvailabilityUpdateInput,
  ) => {
    setAvailabilityActionError(null);

    try {
      const updated = await updateAvailability(id, input);

      setAvailability((prev) =>
        [...prev.map((block) =>
          block.id === updated.id ? updated : block,
        )].sort(
          (a, b) =>
            a.day_of_week - b.day_of_week ||
            a.start_time.localeCompare(b.start_time),
        ),
      );
    } catch (err) {
      setAvailabilityActionError(
        err instanceof Error
          ? err.message
          : 'Failed to update availability block.',
      );
      throw err;
    }
  };

  const handleDeleteAvailability = async (
    block: Availability,
  ) => {
    setAvailabilityActionError(null);

    try {
      await deleteAvailability(block.id);

      setAvailability((prev) =>
        prev.filter((item) => item.id !== block.id),
      );
    } catch (err) {
      setAvailabilityActionError(
        err instanceof Error
          ? err.message
          : 'Failed to delete availability block.',
      );
      throw err;
    }
  };

  const handleCreateAvailabilityException = async (
    input: AvailabilityExceptionCreateInput,
  ) => {
    setAvailabilityExceptionsActionError(null);

    try {
      const exception = await createAvailabilityException(input);

      setAvailabilityExceptions((prev) =>
        [...prev, exception].sort(
          (a, b) => a.date.localeCompare(b.date) || a.id - b.id,
        ),
      );
    } catch (err) {
      setAvailabilityExceptionsActionError(
        err instanceof Error
          ? err.message
          : 'Failed to add availability exception.',
      );
      throw err;
    }
  };

  const handleUpdateAvailabilityException = async (
    id: number,
    input: AvailabilityExceptionUpdateInput,
  ) => {
    setAvailabilityExceptionsActionError(null);

    try {
      const updated = await updateAvailabilityException(id, input);

      setAvailabilityExceptions((prev) =>
        [...prev.map((exception) =>
          exception.id === updated.id ? updated : exception,
        )].sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id),
      );
    } catch (err) {
      setAvailabilityExceptionsActionError(
        err instanceof Error
          ? err.message
          : 'Failed to update availability exception.',
      );
      throw err;
    }
  };

  const handleDeleteAvailabilityException = async (
    exception: AvailabilityException,
  ) => {
    setAvailabilityExceptionsActionError(null);

    try {
      await deleteAvailabilityException(exception.id);

      setAvailabilityExceptions((prev) =>
        prev.filter((item) => item.id !== exception.id),
      );
    } catch (err) {
      setAvailabilityExceptionsActionError(
        err instanceof Error
          ? err.message
          : 'Failed to delete availability exception.',
      );
      throw err;
    }
  };

  return (
    <main className="app">
      <h1 style={{ fontSize: '1.7rem' }}>Adaptive Planner</h1>

      <nav className="app-navigation" aria-label="Main navigation">
        <button
          type="button"
          className={
            view === 'tasks'
              ? 'app-navigation-button active'
              : 'app-navigation-button'
          }
          onClick={() => setView('tasks')}
        >
          Tasks
        </button>

        <button
          type="button"
          className={
            view === 'availability'
              ? 'app-navigation-button active'
              : 'app-navigation-button'
          }
          onClick={() => setView('availability')}
        >
          Availability
        </button>
      </nav>

      {view === 'tasks' && (
        <>
          <TaskForm onCreate={handleCreate} />

          {loading && <p>Loading tasks…</p>}

          {error && <p className="app-error">{error}</p>}

          {!loading && !error && (
            <>
              {actionError && (
                <p className="app-error">{actionError}</p>
              )}

              <TaskList
                tasks={tasks}
                onToggleComplete={handleToggleComplete}
                onDelete={handleDelete}
                onUpdate={handleUpdate}
              />
            </>
          )}
        </>
      )}

      {view === 'availability' && (
        <>
          {availabilityLoading && (
            <p>Loading availability…</p>
          )}

          {availabilityError && (
            <p className="app-error">{availabilityError}</p>
          )}

          {!availabilityLoading && !availabilityError && (
            <>
              {availabilityActionError && (
                <p className="app-error">
                  {availabilityActionError}
                </p>
              )}

              <AvailabilityList
                availability={availability}
                onCreate={handleCreateAvailability}
                onUpdate={handleUpdateAvailability}
                onDelete={handleDeleteAvailability}
              />

              {availabilityExceptionsLoading && (
                <p>Loading availability exceptions…</p>
              )}

              {availabilityExceptionsError && (
                <p className="app-error">{availabilityExceptionsError}</p>
              )}

              {!availabilityExceptionsLoading &&
                !availabilityExceptionsError && (
                  <>
                    {availabilityExceptionsActionError && (
                      <p className="app-error">
                        {availabilityExceptionsActionError}
                      </p>
                    )}

                    <AvailabilityExceptionList
                      exceptions={availabilityExceptions}
                      onCreate={handleCreateAvailabilityException}
                      onUpdate={handleUpdateAvailabilityException}
                      onDelete={handleDeleteAvailabilityException}
                    />
                  </>
                )}
            </>
          )}
        </>
      )}
    </main>
  );
}

export default App;