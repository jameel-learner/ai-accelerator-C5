import type { User } from '../types'
const BASE = '/api/users'
export const fetchUsers = (): Promise<User[]> => fetch(BASE).then(r => r.json())
export const createUser = (data: Pick<User, 'name' | 'color'>): Promise<User> =>
  fetch(BASE, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json())
