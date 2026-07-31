export interface Availability {
  id: number;
  day_of_week: number;
  start_time: string;
  end_time: string;
  created_at: string;
  updated_at: string;
}

export interface AvailabilityCreateInput {
  day_of_week: number;
  start_time: string;
  end_time: string;
}

export type AvailabilityUpdateInput = AvailabilityCreateInput;

export const WEEKDAYS = [
  { value: 0, label: 'Monday' },
  { value: 1, label: 'Tuesday' },
  { value: 2, label: 'Wednesday' },
  { value: 3, label: 'Thursday' },
  { value: 4, label: 'Friday' },
  { value: 5, label: 'Saturday' },
  { value: 6, label: 'Sunday' },
] as const;