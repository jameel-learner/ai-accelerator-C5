export type Priority = 'high' | 'medium' | 'low'
export type Status = 'backlog' | 'in_progress' | 'review' | 'done'

export interface User {
  id: number
  name: string
  color: string
}

export interface Story {
  id: number
  title: string
  description: string
  status: Status
  assignee_id: number | null
  assignee_name: string | null
  assignee_color: string | null
  priority: Priority
  position: number
  created_at: string
  updated_at: string
}
