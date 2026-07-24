import type { Task, TaskCreateInput, TaskUpdateInput } from '../types/task';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  public readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function parseApiError(response: Response): Promise<ApiError> {
  if (response.status === 404) {
    return new ApiError('Task not found.', 404);
  }

  if (response.status >= 500) {
    return new ApiError('Something went wrong. Please try again.', response.status);
  }

  try {
    const data = await response.json();

    if (response.status === 422 && Array.isArray(data.detail)) {
      const message = data.detail
        .map((error: { loc?: unknown[]; msg: string }) => {
          const field = error.loc?.at(-1);

          switch (field) {
            case 'title':
              return `Title: ${error.msg}`;
            case 'description':
              return `Description: ${error.msg}`;
            case 'estimated_duration_minutes':
              return `Estimated duration: ${error.msg}`;
            case 'due_date':
              return `Due date: ${error.msg}`;
            case 'priority':
              return `Priority: ${error.msg}`;
            default:
              return error.msg;
          }
        })
        .join('\n');

      return new ApiError(message, 422);
    }
  } catch {
    // Ignore JSON parsing failures.
  }

  if (response.status === 400) {
    return new ApiError('Invalid request.', 400);
  }

  return new ApiError('Request failed.', response.status);
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw await parseApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new ApiError(
      'Unable to connect to the server. Please make sure the backend is running.',
      0,
    );
  }
}

export async function listTasks(): Promise<Task[]> {
  const response = await apiFetch(`${API_BASE_URL}/tasks`);
  return handleResponse<Task[]>(response);
}

export async function createTask(input: TaskCreateInput): Promise<Task> {
  const response = await apiFetch(`${API_BASE_URL}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  return handleResponse<Task>(response);
}

export async function updateTask(id: number, input: TaskUpdateInput): Promise<Task> {
  const response = await apiFetch(`${API_BASE_URL}/tasks/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  return handleResponse<Task>(response);
}

export async function deleteTask(id: number): Promise<void> {
  const response = await apiFetch(`${API_BASE_URL}/tasks/${id}`, {
    method: 'DELETE',
  });
  return handleResponse<void>(response);
}