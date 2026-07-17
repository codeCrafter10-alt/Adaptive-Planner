import type { Task } from '../types/task';

interface TaskListProps {
  tasks: Task[];
  onToggleComplete: (task: Task) => void;
  onDelete: (task: Task) => void;
}

function TaskList({ tasks, onToggleComplete, onDelete }: TaskListProps) {
  if (tasks.length === 0) {
    return <p className="task-list-empty">No tasks yet.</p>;
  }

  return (
    <ul className="task-list">
      {tasks.map((task) => {
        const isCompleted = task.completed_at !== null;
        return (
          <li key={task.id} className={`task-item priority-${task.priority}`}>
            <label>
              <input
                type="checkbox"
                checked={isCompleted}
                onChange={() => onToggleComplete(task)}
              />
              <span className={isCompleted ? 'task-title completed' : 'task-title'}>
                {task.title}
              </span>
            </label>
            <span className="task-meta">
              {task.estimated_duration_minutes} min · {task.priority} · due{' '}
              {new Date(task.due_date).toLocaleString()}
            </span>
            <button type="button" onClick={() => onDelete(task)}>
              Delete
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default TaskList;