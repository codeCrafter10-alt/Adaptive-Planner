export type TaskPriority = 'low' | 'medium' | 'high';

export interface Task {
  id: number;
  title: string;
  description: string | null;
  estimated_duration_minutes: number;
  due_date: string;
  priority: TaskPriority;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreateInput {
  title: string;
  description?: string | null;
  estimated_duration_minutes: number;
  due_date: string;
  priority?: TaskPriority;
}

export interface TaskUpdateInput {
  title?: string;
  description?: string | null;
  estimated_duration_minutes?: number;
  due_date?: string;
  priority?: TaskPriority;
  completed?: boolean;
}