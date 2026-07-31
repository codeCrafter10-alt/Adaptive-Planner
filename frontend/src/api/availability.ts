import type {
  Availability,
  AvailabilityCreateInput,
  AvailabilityUpdateInput,
} from '../types/availability';

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

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
    return new ApiError('Availability block not found.', 404);
  }

  if (response.status >= 500) {
    return new ApiError(
      'Something went wrong. Please try again.',
      response.status,
    );
  }

  try {
    const data = await response.json();

    if (response.status === 409) {
      if (typeof data.detail === 'string') {
        return new ApiError(data.detail, 409);
      }

      return new ApiError(
        'Availability blocks cannot overlap.',
        409,
      );
    }

    if (response.status === 422 && Array.isArray(data.detail)) {
      const message = data.detail
        .map((error: { loc?: unknown[]; msg: string }) => {
          const field = error.loc?.at(-1);

          switch (field) {
            case 'day_of_week':
              return `Day: ${error.msg}`;
            case 'start_time':
              return `Start time: ${error.msg}`;
            case 'end_time':
              return `End time: ${error.msg}`;
            default:
              return error.msg;
          }
        })
        .join('\n');

      return new ApiError(message, 422);
    }

    if (typeof data.detail === 'string') {
      return new ApiError(data.detail, response.status);
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

async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new ApiError(
      'Unable to connect to the server. Please make sure the backend is running.',
      0,
    );
  }
}

export async function listAvailability(): Promise<Availability[]> {
  const response = await apiFetch(`${API_BASE_URL}/availability`);

  return handleResponse<Availability[]>(response);
}

export async function createAvailability(
  input: AvailabilityCreateInput,
): Promise<Availability> {
  const response = await apiFetch(`${API_BASE_URL}/availability`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });

  return handleResponse<Availability>(response);
}

export async function updateAvailability(
  id: number,
  input: AvailabilityUpdateInput,
): Promise<Availability> {
  const response = await apiFetch(
    `${API_BASE_URL}/availability/${id}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    },
  );

  return handleResponse<Availability>(response);
}

export async function deleteAvailability(
  id: number,
): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/availability/${id}`,
    {
      method: 'DELETE',
    },
  );

  return handleResponse<void>(response);
}