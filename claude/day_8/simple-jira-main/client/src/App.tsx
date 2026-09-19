import { useState, useEffect } from 'react'
import { useTheme } from './hooks/useTheme'
import { useStories } from './hooks/useStories'
import { Sun, Moon, Plus } from 'lucide-react'
import Board from './components/Board'
import StoryPanel from './components/StoryPanel'
import TeamSetup from './components/TeamSetup'
import { fetchUsers } from './api/users'
import type { Story } from './types'

export default function App() {
  const { theme, toggle } = useTheme()
  const { addStory, editStory, removeStory } = useStories()
  const [selectedStory, setSelectedStory] = useState<Story | null | undefined>(undefined)
  const [hasTeam, setHasTeam] = useState<boolean | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  useEffect(() => {
    fetchUsers().then(users => setHasTeam(users.length > 0))
  }, [])

  useEffect(() => {
    if (toast) { const t = setTimeout(() => setToast(null), 2500); return () => clearTimeout(t) }
  }, [toast])

  if (hasTeam === null) return null
  if (!hasTeam) return <TeamSetup onComplete={() => setHasTeam(true)} />

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 transition-colors duration-200">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 sticky top-0 z-30">
        <h1 className="font-mono text-lg font-semibold text-indigo-600 dark:text-indigo-400">simple-jira</h1>
        <div className="flex items-center gap-2">
          <button onClick={() => setSelectedStory(null)} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors">
            <Plus size={16} /> New Story
          </button>
          <button onClick={toggle} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors" aria-label="Toggle theme">
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>
      <Board onCardClick={setSelectedStory} />
      {selectedStory !== undefined && (
        <StoryPanel
          story={selectedStory}
          onClose={() => setSelectedStory(undefined)}
          onSave={async (id, data) => { await editStory(id, data); setToast('Story updated') }}
          onDelete={removeStory}
          onCreate={async (data) => { await addStory(data); setToast('Story created') }}
        />
      )}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-4 py-3 rounded-xl shadow-lg text-sm font-medium">
          ✓ {toast}
        </div>
      )}
    </div>
  )
}
