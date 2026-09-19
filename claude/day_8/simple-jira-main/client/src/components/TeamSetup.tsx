import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { createUser } from '../api/users'

const COLORS = ['#6366F1', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#0EA5E9']

interface Props { onComplete: () => void }

export default function TeamSetup({ onComplete }: Props) {
  const [members, setMembers] = useState([{ name: '', color: COLORS[0] }])
  const [saving, setSaving] = useState(false)

  const addMember = () => { if (members.length < 5) setMembers(prev => [...prev, { name: '', color: COLORS[prev.length % COLORS.length] }]) }
  const removeMember = (i: number) => setMembers(prev => prev.filter((_, idx) => idx !== i))
  const updateMember = (i: number, field: 'name' | 'color', value: string) =>
    setMembers(prev => prev.map((m, idx) => idx === i ? { ...m, [field]: value } : m))

  const handleSave = async () => {
    const valid = members.filter(m => m.name.trim())
    if (!valid.length) return
    setSaving(true)
    await Promise.all(valid.map(m => createUser({ name: m.name.trim(), color: m.color })))
    onComplete()
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-6">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-700 p-8 w-full max-w-md">
        <h1 className="font-mono text-2xl font-bold text-indigo-600 dark:text-indigo-400 mb-1">simple-jira</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Who is on the team?</p>
        <div className="space-y-3 mb-5">
          {members.map((m, i) => (
            <div key={i} className="flex items-center gap-3">
              <input type="color" value={m.color} onChange={e => updateMember(i, 'color', e.target.value)} className="w-9 h-9 rounded-full border-0 cursor-pointer bg-transparent" />
              <input value={m.name} onChange={e => updateMember(i, 'name', e.target.value)} placeholder={'Team member ' + (i + 1)} className="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              {members.length > 1 && <button onClick={() => removeMember(i)} className="p-1.5 text-slate-400 hover:text-red-500 cursor-pointer transition-colors"><X size={16} /></button>}
            </div>
          ))}
        </div>
        {members.length < 5 && (
          <button onClick={addMember} className="flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 cursor-pointer transition-colors mb-6"><Plus size={15} /> Add member</button>
        )}
        <button onClick={handleSave} disabled={saving || !members.some(m => m.name.trim())} className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium cursor-pointer transition-colors">
          {saving ? 'Setting up...' : 'Start using Simple Jira'}
        </button>
      </div>
    </div>
  )
}
