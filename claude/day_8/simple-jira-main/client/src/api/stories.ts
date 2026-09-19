import type { Story } from '../types'
const BASE = '/api/stories'
export const fetchStories = (): Promise<Story[]> => fetch(BASE).then(r => r.json())
export const createStory = (data: Partial<Story>): Promise<Story> =>
  fetch(BASE, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json())
export const updateStory = (id: number, data: Partial<Story>): Promise<Story> =>
  fetch(BASE + '/' + id, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }).then(r => r.json())
export const deleteStory = (id: number): Promise<void> =>
  fetch(BASE + '/' + id, { method: 'DELETE' }).then(() => undefined)
