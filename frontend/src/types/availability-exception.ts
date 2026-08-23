export interface AvailabilityException {
  id: number;
  date: string;
  is_available: boolean;
  start_time: string | null;
  end_time: string | null;
  reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AvailabilityExceptionCreateInput {
  date: string;
  is_available: boolean;
  start_time: string | null;
  end_time: string | null;
  reason?: string | null;
}

export interface AvailabilityExceptionUpdateInput {
  date?: string;
  is_available?: boolean;
  start_time?: string | null;
  end_time?: string | null;
  reason?: string | null;
}
