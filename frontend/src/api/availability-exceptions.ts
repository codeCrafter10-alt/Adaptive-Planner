import type {
  AvailabilityException,
  AvailabilityExceptionCreateInput,
  AvailabilityExceptionUpdateInput,
} from '../types/availability-exception';

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
    return new ApiError('Availability exception not found.', 404);
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
        'Availability exception for this date already exists.',
        409,
      );
    }

    if (response.status === 422 && Array.isArray(data.detail)) {
      const message = data.detail
        .map((error: { loc?: unknown[]; msg: string }) => {
          const field = error.loc?.at(-1);

          switch (field) {
            case 'date':
              return `Date: ${error.msg}`;
            case 'is_available':
              return `Availability type: ${error.msg}`;
            case 'start_time':
              return `Start time: ${error.msg}`;
            case 'end_time':
              return `End time: ${error.msg}`;
            case 'reason':
              return `Reason: ${error.msg}`;
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

export async function listAvailabilityExceptions(): Promise<
  AvailabilityException[]
> {
  const response = await apiFetch(`${API_BASE_URL}/availability/exceptions`);

  return handleResponse<AvailabilityException[]>(response);
}

export async function createAvailabilityException(
  input: AvailabilityExceptionCreateInput,
): Promise<AvailabilityException> {
  const response = await apiFetch(`${API_BASE_URL}/availability/exceptions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  });

  return handleResponse<AvailabilityException>(response);
}

export async function updateAvailabilityException(
  id: number,
  input: AvailabilityExceptionUpdateInput,
): Promise<AvailabilityException> {
  const response = await apiFetch(
    `${API_BASE_URL}/availability/exceptions/${id}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(input),
    },
  );

  return handleResponse<AvailabilityException>(response);
}

export async function deleteAvailabilityException(
  id: number,
): Promise<void> {
  const response = await apiFetch(
    `${API_BASE_URL}/availability/exceptions/${id}`,
    {
      method: 'DELETE',
    },
  );

  return handleResponse<void>(response);
}
