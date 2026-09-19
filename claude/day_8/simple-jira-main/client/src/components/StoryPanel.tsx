import { useState, useEffect } from 'react'
import { X, Trash2 } from 'lucide-react'
import type { Story, Priority, Status } from '../types'
import { useUsers } from '../hooks/useUsers'

interface Props {
  story: Story | null
  onClose: () => void
  onSave: (id: number, data: Partial<Story>) => void
  onDelete: (id: number) => void
  onCreate: (data: Partial<Story>) => void
}

export default function StoryPanel({ story, onClose, onSave, onDelete, onCreate }: Props) {
  const users = useUsers()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assigneeId, setAssigneeId] = useState<number | null>(null)
  const [priority, setPriority] = useState<Priority>('medium')
  const [status, setStatus] = useState<Status>('backlog')
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => {
    if (story) {
      setTitle(story.title)
      setDescription(story.description || '')
      setAssigneeId(story.assignee_id)
      setPriority(story.priority)
      setStatus(story.status)
    } else {
      setTitle(''); setDescription(''); setAssigneeId(null); setPriority('medium'); setStatus('backlog')
    }
  }, [story])

  const handleSave = () => {
    if (!title.trim()) return
    const data = { title, description, assignee_id: assigneeId, priority, status }
    if (story) onSave(story.id, data)
    else onCreate(data)
    onClose()
  }

  const handleDelete = () => { if (story) { onDelete(story.id); onClose() } }

  return (
    <>
      <div className="fixed inset-0 bg-black/20 dark:bg-black/40 z-40" onClick={onClose} />
      <aside className="fixed right-0 top-0 h-full w-full max-w-md bg-white dark:bg-slate-900 shadow-2xl z-50 flex flex-col border-l border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="font-mono font-semibold text-slate-900 dark:text-slate-100">{story ? 'Edit Story' : 'New Story'}</h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors"><X size={18} /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div>
            <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">Title *</label>
            <input value={title} onChange={e => setTitle(e.target.value)} placeholder="What needs to be done?" className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={4} placeholder="More details..." className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">Assignee</label>
              <select value={assigneeId ?? ''} onChange={e => setAssigneeId(e.target.value ? Number(e.target.value) : null)} className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer">
                <option value="">Unassigned</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value as Priority)} className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer">
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">Column</label>
            <select value={status} onChange={e => setStatus(e.target.value as Status)} className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer">
              <option value="backlog">Backlog</option>
              <option value="in_progress">In Progress</option>
              <option value="review">Review</option>
              <option value="done">Done</option>
            </select>
          </div>
        </div>
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
          {story ? (
            <button onClick={() => setShowConfirm(true)} className="flex items-center gap-1.5 text-red-500 hover:text-red-600 text-sm cursor-pointer transition-colors"><Trash2 size={15} /> Delete</button>
          ) : <span />}
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors">Cancel</button>
            <button onClick={handleSave} disabled={!title.trim()} className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium cursor-pointer transition-colors">{story ? 'Save' : 'Create'}</button>
          </div>
        </div>
      </aside>
      {showConfirm && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-2xl max-w-sm w-full mx-4 border border-slate-200 dark:border-slate-700">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-2">Delete story?</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setShowConfirm(false)} className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium cursor-pointer transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
