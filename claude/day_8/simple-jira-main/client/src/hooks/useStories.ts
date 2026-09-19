import { useState, useEffect, useCallback } from 'react'
import type { Story, Status } from '../types'
import { fetchStories, createStory, updateStory, deleteStory } from '../api/stories'

export function useStories() {
  const [stories, setStories] = useState<Story[]>([])
  const [loading, setLoading] = useState(true)
  const load = useCallback(async () => {
    const data = await fetchStories()
    setStories(data)
    setLoading(false)
  }, [])
  useEffect(() => { load() }, [load])
  const addStory = async (data: Partial<Story>) => {
    const story = await createStory(data)
    setStories(prev => [...prev, story])
    return story
  }
  const editStory = async (id: number, data: Partial<Story>) => {
    const updated = await updateStory(id, data)
    setStories(prev => prev.map(s => s.id === id ? updated : s))
    return updated
  }
  const removeStory = async (id: number) => {
    await deleteStory(id)
    setStories(prev => prev.filter(s => s.id !== id))
  }
  const moveStory = async (id: number, newStatus: Status, newPosition: number) => {
    setStories(prev => prev.map(s => s.id === id ? { ...s, status: newStatus, position: newPosition } : s))
    await updateStory(id, { status: newStatus, position: newPosition })
  }
  const storiesByStatus = (status: Status) =>
    stories.filter(s => s.status === status).sort((a, b) => a.position - b.position)
  return { stories, loading, addStory, editStory, removeStory, moveStory, storiesByStatus }
}
