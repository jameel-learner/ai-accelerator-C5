# Simple Jira Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local Kanban web app for 2–3 engineers with a React frontend, Express/SQLite backend, drag-and-drop cards, light/dark theme toggle, and a slide-over story panel.

**Architecture:** Monorepo with `client/` (React + Vite + Tailwind) and `server/` (Express + better-sqlite3). Vite proxies `/api` to Express on port 4000. A single `npm run dev` at the root starts both via `concurrently`.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS v3, @hello-pangea/dnd, Express, better-sqlite3, concurrently, Fira Code + Fira Sans (Google Fonts), Lucide React

---

## Task 1: Project Scaffold

**Files:**
- Create: `package.json` (root)
- Create: `server/package.json`
- Create: `server/tsconfig.json`
- Create: `client/` (via Vite)
- Create: `.env`
- Create: `.gitignore`

**Step 1: Initialize root package**

```bash
cd /Users/growthschool/Downloads/engg_accl_c4
npm init -y
```

**Step 2: Create server directory and install dependencies**

```bash
mkdir server && cd server
npm init -y
npm install express better-sqlite3 cors dotenv
npm install -D typescript ts-node @types/express @types/better-sqlite3 @types/cors @types/node nodemon
cd ..
```

**Step 3: Create server tsconfig**

Create `server/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "rootDir": "src",
    "outDir": "dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

**Step 4: Scaffold the React client with Vite**

```bash
npm create vite@latest client -- --template react-ts
cd client
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install @hello-pangea/dnd lucide-react
cd ..
```

**Step 5: Configure Tailwind**

Edit `client/tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['"Fira Code"', 'monospace'],
        sans: ['"Fira Sans"', 'sans-serif'],
      },
      colors: {
        primary: {
          light: '#6366F1',
          dark: '#818CF8',
        },
      },
    },
  },
  plugins: [],
}
```

Edit `client/src/index.css` (replace contents):
```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: 'Fira Sans', sans-serif;
}
```

**Step 6: Configure Vite proxy**

Edit `client/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:4000',
    },
  },
})
```

**Step 7: Create root package.json scripts**

Edit root `package.json`:
```json
{
  "name": "simple-jira",
  "version": "1.0.0",
  "scripts": {
    "dev": "concurrently \"npm run dev:server\" \"npm run dev:client\"",
    "dev:server": "cd server && npx nodemon --watch src --ext ts --exec ts-node src/index.ts",
    "dev:client": "cd client && npm run dev",
    "build": "cd client && npm run build"
  },
  "devDependencies": {
    "concurrently": "^8.2.0"
  }
}
```

```bash
npm install
```

**Step 8: Create .env and .gitignore**

Create `.env`:
```
PORT=4000
DB_PATH=./server/data/simple-jira.db
```

Create `.gitignore`:
```
node_modules/
dist/
client/dist/
server/data/
.env
```

**Step 9: Commit**

```bash
git init
git add .
git commit -m "feat: scaffold monorepo with React/Vite client and Express server"
```

---

## Task 2: Database Schema & Connection

**Files:**
- Create: `server/src/db/schema.sql`
- Create: `server/src/db/db.ts`
- Create: `server/data/` (directory, git-ignored)

**Step 1: Write the schema**

Create `server/src/db/schema.sql`:
```sql
CREATE TABLE IF NOT EXISTS users (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  name  TEXT NOT NULL,
  color TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  description TEXT,
  status      TEXT NOT NULL DEFAULT 'backlog',
  assignee_id INTEGER REFERENCES users(id),
  priority    TEXT NOT NULL DEFAULT 'medium',
  position    INTEGER NOT NULL DEFAULT 0,
  archived    INTEGER NOT NULL DEFAULT 0,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Step 2: Create db singleton**

Create `server/src/db/db.ts`:
```ts
import Database from 'better-sqlite3'
import path from 'path'
import fs from 'fs'

const DB_PATH = process.env.DB_PATH || './data/simple-jira.db'
const schemaPath = path.join(__dirname, 'schema.sql')

// Ensure data directory exists
const dir = path.dirname(DB_PATH)
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })

const db = new Database(DB_PATH)
db.pragma('journal_mode = WAL')
db.pragma('foreign_keys = ON')

// Run schema
const schema = fs.readFileSync(schemaPath, 'utf8')
db.exec(schema)

export default db
```

**Step 3: Verify db boots without error**

Create `server/src/index.ts` (minimal):
```ts
import 'dotenv/config'
import express from 'express'
import db from './db/db'

const app = express()
const PORT = process.env.PORT || 4000

app.get('/api/health', (_req, res) => {
  res.json({ ok: true })
})

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`)
})
```

```bash
cd server && npx ts-node src/index.ts
# Expected: "Server running on http://localhost:4000"
# curl http://localhost:4000/api/health → {"ok":true}
```

**Step 4: Commit**

```bash
git add server/src/
git commit -m "feat: add SQLite schema and db singleton"
```

---

## Task 3: Users API

**Files:**
- Create: `server/src/routes/users.ts`
- Modify: `server/src/index.ts`

**Step 1: Create users router**

Create `server/src/routes/users.ts`:
```ts
import { Router } from 'express'
import db from '../db/db'

const router = Router()

router.get('/', (_req, res) => {
  const users = db.prepare('SELECT * FROM users ORDER BY name').all()
  res.json(users)
})

router.post('/', (req, res) => {
  const { name, color } = req.body
  if (!name || !color) {
    return res.status(400).json({ error: 'name and color are required' })
  }
  const result = db.prepare('INSERT INTO users (name, color) VALUES (?, ?)').run(name, color)
  const user = db.prepare('SELECT * FROM users WHERE id = ?').get(result.lastInsertRowid)
  res.status(201).json(user)
})

export default router
```

**Step 2: Mount router in index.ts**

Edit `server/src/index.ts`:
```ts
import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import db from './db/db'
import usersRouter from './routes/users'

const app = express()
const PORT = process.env.PORT || 4000

app.use(cors())
app.use(express.json())

app.use('/api/users', usersRouter)

app.get('/api/health', (_req, res) => res.json({ ok: true }))

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`))
```

**Step 3: Manually test**

```bash
# Start server
cd server && npx ts-node src/index.ts

# Create a user
curl -X POST http://localhost:4000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","color":"#6366F1"}'
# Expected: {"id":1,"name":"Alice","color":"#6366F1"}

# List users
curl http://localhost:4000/api/users
# Expected: [{"id":1,"name":"Alice","color":"#6366F1"}]
```

**Step 4: Commit**

```bash
git add server/src/
git commit -m "feat: add users CRUD API"
```

---

## Task 4: Stories API

**Files:**
- Create: `server/src/routes/stories.ts`
- Modify: `server/src/index.ts`

**Step 1: Create stories router**

Create `server/src/routes/stories.ts`:
```ts
import { Router } from 'express'
import db from '../db/db'

const router = Router()

// GET all non-archived stories with assignee info
router.get('/', (_req, res) => {
  const stories = db.prepare(`
    SELECT s.*, u.name as assignee_name, u.color as assignee_color
    FROM stories s
    LEFT JOIN users u ON s.assignee_id = u.id
    WHERE s.archived = 0
    ORDER BY s.status, s.position ASC
  `).all()
  res.json(stories)
})

// POST create story
router.post('/', (req, res) => {
  const { title, description = '', status = 'backlog', assignee_id = null, priority = 'medium' } = req.body
  if (!title) return res.status(400).json({ error: 'title is required' })

  // Position at end of column
  const maxPos = db.prepare(
    'SELECT COALESCE(MAX(position), -1) as max FROM stories WHERE status = ? AND archived = 0'
  ).get(status) as { max: number }

  const result = db.prepare(`
    INSERT INTO stories (title, description, status, assignee_id, priority, position)
    VALUES (?, ?, ?, ?, ?, ?)
  `).run(title, description, status, assignee_id, priority, maxPos.max + 1)

  const story = db.prepare(`
    SELECT s.*, u.name as assignee_name, u.color as assignee_color
    FROM stories s LEFT JOIN users u ON s.assignee_id = u.id
    WHERE s.id = ?
  `).get(result.lastInsertRowid)

  res.status(201).json(story)
})

// PATCH update story (fields + position for drag-drop)
router.patch('/:id', (req, res) => {
  const { id } = req.params
  const fields = req.body

  const allowed = ['title', 'description', 'status', 'assignee_id', 'priority', 'position']
  const updates = Object.keys(fields)
    .filter(k => allowed.includes(k))
    .map(k => `${k} = ?`)
    .join(', ')

  if (!updates) return res.status(400).json({ error: 'no valid fields to update' })

  const values = Object.keys(fields)
    .filter(k => allowed.includes(k))
    .map(k => fields[k])

  db.prepare(`UPDATE stories SET ${updates}, updated_at = CURRENT_TIMESTAMP WHERE id = ?`)
    .run(...values, id)

  const story = db.prepare(`
    SELECT s.*, u.name as assignee_name, u.color as assignee_color
    FROM stories s LEFT JOIN users u ON s.assignee_id = u.id
    WHERE s.id = ?
  `).get(id)

  if (!story) return res.status(404).json({ error: 'story not found' })
  res.json(story)
})

// DELETE soft-delete
router.delete('/:id', (req, res) => {
  db.prepare('UPDATE stories SET archived = 1 WHERE id = ?').run(req.params.id)
  res.status(204).send()
})

export default router
```

**Step 2: Mount router**

Add to `server/src/index.ts`:
```ts
import storiesRouter from './routes/stories'
// ...
app.use('/api/stories', storiesRouter)
```

**Step 3: Manually test**

```bash
# Create a story
curl -X POST http://localhost:4000/api/stories \
  -H "Content-Type: application/json" \
  -d '{"title":"Set up CI","priority":"high"}'

# List stories
curl http://localhost:4000/api/stories

# Move to in_progress
curl -X PATCH http://localhost:4000/api/stories/1 \
  -H "Content-Type: application/json" \
  -d '{"status":"in_progress"}'

# Delete (soft)
curl -X DELETE http://localhost:4000/api/stories/1
# Expected: 204 No Content
```

**Step 4: Commit**

```bash
git add server/src/
git commit -m "feat: add stories CRUD API with soft delete"
```

---

## Task 5: API Client (Frontend)

**Files:**
- Create: `client/src/api/stories.ts`
- Create: `client/src/api/users.ts`
- Create: `client/src/types.ts`

**Step 1: Define types**

Create `client/src/types.ts`:
```ts
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
```

**Step 2: Create stories API module**

Create `client/src/api/stories.ts`:
```ts
import { Story, Status } from '../types'

const BASE = '/api/stories'

export const fetchStories = (): Promise<Story[]> =>
  fetch(BASE).then(r => r.json())

export const createStory = (data: Partial<Story>): Promise<Story> =>
  fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json())

export const updateStory = (id: number, data: Partial<Story>): Promise<Story> =>
  fetch(`${BASE}/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json())

export const deleteStory = (id: number): Promise<void> =>
  fetch(`${BASE}/${id}`, { method: 'DELETE' }).then(() => undefined)
```

**Step 3: Create users API module**

Create `client/src/api/users.ts`:
```ts
import { User } from '../types'

const BASE = '/api/users'

export const fetchUsers = (): Promise<User[]> =>
  fetch(BASE).then(r => r.json())

export const createUser = (data: Pick<User, 'name' | 'color'>): Promise<User> =>
  fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).then(r => r.json())
```

**Step 4: Commit**

```bash
git add client/src/api/ client/src/types.ts
git commit -m "feat: add typed API client modules"
```

---

## Task 6: Theme Hook & App Shell

**Files:**
- Create: `client/src/hooks/useTheme.ts`
- Modify: `client/src/App.tsx`
- Modify: `client/index.html`

**Step 1: Create useTheme hook**

Create `client/src/hooks/useTheme.ts`:
```ts
import { useState, useEffect } from 'react'

export type Theme = 'light' | 'dark'

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem('theme') as Theme
    return stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  })

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggle = () => setTheme(t => (t === 'light' ? 'dark' : 'light'))
  return { theme, toggle }
}
```

**Step 2: Replace App.tsx with shell**

Replace `client/src/App.tsx`:
```tsx
import { useTheme } from './hooks/useTheme'
import { Sun, Moon } from 'lucide-react'

export default function App() {
  const { theme, toggle } = useTheme()

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 transition-colors duration-200">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
        <h1 className="font-mono text-xl font-600 tracking-tight text-indigo-600 dark:text-indigo-400">
          simple-jira
        </h1>
        <div className="flex items-center gap-3">
          <button
            onClick={toggle}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors duration-150"
            aria-label="Toggle theme"
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>

      {/* Board placeholder */}
      <main className="p-6">
        <p className="text-slate-500 dark:text-slate-400 font-mono text-sm">Board loading...</p>
      </main>
    </div>
  )
}
```

**Step 3: Add Google Fonts to index.html**

Edit `client/index.html` `<head>`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

**Step 4: Run and verify theme toggle works**

```bash
npm run dev
# Open http://localhost:3000 — click sun/moon, verify dark mode toggles
```

**Step 5: Commit**

```bash
git add client/src/ client/index.html
git commit -m "feat: add theme toggle with localStorage persistence"
```

---

## Task 7: useStories Hook

**Files:**
- Create: `client/src/hooks/useStories.ts`

**Step 1: Create hook**

Create `client/src/hooks/useStories.ts`:
```ts
import { useState, useEffect, useCallback } from 'react'
import { Story, Status } from '../types'
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

  // Move card across columns (drag-drop)
  const moveStory = async (id: number, newStatus: Status, newPosition: number) => {
    // Optimistic update
    setStories(prev =>
      prev.map(s => s.id === id ? { ...s, status: newStatus, position: newPosition } : s)
    )
    await updateStory(id, { status: newStatus, position: newPosition })
  }

  const storiesByStatus = (status: Status) =>
    stories.filter(s => s.status === status).sort((a, b) => a.position - b.position)

  return { stories, loading, addStory, editStory, removeStory, moveStory, storiesByStatus }
}
```

**Step 2: Commit**

```bash
git add client/src/hooks/useStories.ts
git commit -m "feat: add useStories hook with optimistic updates"
```

---

## Task 8: StoryCard Component

**Files:**
- Create: `client/src/components/StoryCard.tsx`

**Step 1: Create component**

Create `client/src/components/StoryCard.tsx`:
```tsx
import { Story } from '../types'
import { Draggable } from '@hello-pangea/dnd'

const priorityBorder: Record<string, string> = {
  high: 'border-l-red-500',
  medium: 'border-l-amber-400',
  low: 'border-l-slate-300',
}

const priorityLabel: Record<string, string> = {
  high: 'P1',
  medium: 'P2',
  low: 'P3',
}

interface Props {
  story: Story
  index: number
  onClick: (story: Story) => void
}

export default function StoryCard({ story, index, onClick }: Props) {
  return (
    <Draggable draggableId={String(story.id)} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onClick(story)}
          className={`
            bg-white dark:bg-slate-800
            border border-slate-200 dark:border-slate-700
            border-l-4 ${priorityBorder[story.priority]}
            rounded-lg p-3 mb-2 cursor-pointer
            shadow-sm hover:shadow-md
            transition-all duration-150
            ${snapshot.isDragging ? 'opacity-80 shadow-lg rotate-1' : ''}
          `}
        >
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug mb-2">
            {story.title}
          </p>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {story.assignee_name && (
                <span
                  className="w-5 h-5 rounded-full text-white text-xs flex items-center justify-center font-mono font-bold"
                  style={{ backgroundColor: story.assignee_color || '#94A3B8' }}
                  title={story.assignee_name}
                >
                  {story.assignee_name[0].toUpperCase()}
                </span>
              )}
            </div>
            <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
              {priorityLabel[story.priority]}
            </span>
          </div>
        </div>
      )}
    </Draggable>
  )
}
```

**Step 2: Commit**

```bash
git add client/src/components/StoryCard.tsx
git commit -m "feat: add draggable StoryCard component"
```

---

## Task 9: KanbanColumn Component

**Files:**
- Create: `client/src/components/KanbanColumn.tsx`

**Step 1: Create component**

Create `client/src/components/KanbanColumn.tsx`:
```tsx
import { Droppable } from '@hello-pangea/dnd'
import { Story, Status } from '../types'
import StoryCard from './StoryCard'

const columnConfig: Record<Status, { label: string; accent: string }> = {
  backlog:     { label: 'Backlog',     accent: 'border-t-slate-400' },
  in_progress: { label: 'In Progress', accent: 'border-t-indigo-500' },
  review:      { label: 'Review',      accent: 'border-t-amber-400' },
  done:        { label: 'Done',        accent: 'border-t-green-500' },
}

interface Props {
  status: Status
  stories: Story[]
  onCardClick: (story: Story) => void
}

export default function KanbanColumn({ status, stories, onCardClick }: Props) {
  const { label, accent } = columnConfig[status]

  return (
    <div className={`
      flex-1 min-w-[260px] max-w-[320px]
      bg-slate-100 dark:bg-slate-800/50
      border-t-4 ${accent}
      rounded-xl p-3 flex flex-col
    `}>
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="font-mono font-semibold text-sm text-slate-700 dark:text-slate-300 uppercase tracking-wide">
          {label}
        </h2>
        <span className="font-mono text-xs bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded-full px-2 py-0.5">
          {stories.length}
        </span>
      </div>

      <Droppable droppableId={status}>
        {(provided, snapshot) => (
          <div
            ref={provided.innerRef}
            {...provided.droppableProps}
            className={`
              flex-1 min-h-[120px] rounded-lg transition-colors duration-150
              ${snapshot.isDraggingOver ? 'bg-indigo-50 dark:bg-indigo-900/20 border-2 border-dashed border-indigo-300 dark:border-indigo-700' : ''}
            `}
          >
            {stories.map((story, index) => (
              <StoryCard key={story.id} story={story} index={index} onClick={onCardClick} />
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add client/src/components/KanbanColumn.tsx
git commit -m "feat: add KanbanColumn with Droppable zone"
```

---

## Task 10: Board Component with Drag & Drop

**Files:**
- Create: `client/src/components/Board.tsx`

**Step 1: Create Board**

Create `client/src/components/Board.tsx`:
```tsx
import { DragDropContext, DropResult } from '@hello-pangea/dnd'
import { Status } from '../types'
import { useStories } from '../hooks/useStories'
import KanbanColumn from './KanbanColumn'
import { Story } from '../types'

const COLUMNS: Status[] = ['backlog', 'in_progress', 'review', 'done']

interface Props {
  onCardClick: (story: Story) => void
}

export default function Board({ onCardClick }: Props) {
  const { loading, storiesByStatus, moveStory } = useStories()

  const onDragEnd = (result: DropResult) => {
    const { destination, source, draggableId } = result
    if (!destination) return
    if (destination.droppableId === source.droppableId && destination.index === source.index) return

    moveStory(
      parseInt(draggableId),
      destination.droppableId as Status,
      destination.index
    )
  }

  if (loading) {
    return (
      <div className="flex gap-4 p-6 overflow-x-auto">
        {COLUMNS.map(col => (
          <div key={col} className="flex-1 min-w-[260px] max-w-[320px] h-48 bg-slate-100 dark:bg-slate-800/50 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="flex gap-4 p-6 overflow-x-auto min-h-[calc(100vh-80px)]">
        {COLUMNS.map(status => (
          <KanbanColumn
            key={status}
            status={status}
            stories={storiesByStatus(status)}
            onCardClick={onCardClick}
          />
        ))}
      </div>
    </DragDropContext>
  )
}
```

**Step 2: Commit**

```bash
git add client/src/components/Board.tsx
git commit -m "feat: add Board with DragDropContext"
```

---

## Task 11: Story Slide-Over Panel

**Files:**
- Create: `client/src/components/StoryPanel.tsx`
- Create: `client/src/hooks/useUsers.ts`

**Step 1: Create useUsers hook**

Create `client/src/hooks/useUsers.ts`:
```ts
import { useState, useEffect } from 'react'
import { User } from '../types'
import { fetchUsers } from '../api/users'

export function useUsers() {
  const [users, setUsers] = useState<User[]>([])
  useEffect(() => { fetchUsers().then(setUsers) }, [])
  return users
}
```

**Step 2: Create StoryPanel**

Create `client/src/components/StoryPanel.tsx`:
```tsx
import { useState, useEffect } from 'react'
import { X, Trash2 } from 'lucide-react'
import { Story, Priority, Status } from '../types'
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
      setTitle('')
      setDescription('')
      setAssigneeId(null)
      setPriority('medium')
      setStatus('backlog')
    }
  }, [story])

  const handleSave = () => {
    if (!title.trim()) return
    const data = { title, description, assignee_id: assigneeId, priority, status }
    if (story) onSave(story.id, data)
    else onCreate(data)
    onClose()
  }

  const handleDelete = () => {
    if (story) { onDelete(story.id); onClose() }
  }

  if (story === undefined) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 dark:bg-black/40 z-40" onClick={onClose} />

      {/* Panel */}
      <aside className="fixed right-0 top-0 h-full w-full max-w-md bg-white dark:bg-slate-900 shadow-2xl z-50 flex flex-col border-l border-slate-200 dark:border-slate-700">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="font-mono font-semibold text-slate-900 dark:text-slate-100">
            {story ? 'Edit Story' : 'New Story'}
          </h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors">
            <X size={18} />
          </button>
        </div>

        {/* Form */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          <div>
            <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">
              Title *
            </label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="What needs to be done?"
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">
              Description
            </label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={4}
              placeholder="More details..."
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">
                Assignee
              </label>
              <select
                value={assigneeId ?? ''}
                onChange={e => setAssigneeId(e.target.value ? Number(e.target.value) : null)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
              >
                <option value="">Unassigned</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">
                Priority
              </label>
              <select
                value={priority}
                onChange={e => setPriority(e.target.value as Priority)}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono font-semibold text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-wide">
              Column
            </label>
            <select
              value={status}
              onChange={e => setStatus(e.target.value as Status)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
            >
              <option value="backlog">Backlog</option>
              <option value="in_progress">In Progress</option>
              <option value="review">Review</option>
              <option value="done">Done</option>
            </select>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
          {story ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="flex items-center gap-1.5 text-red-500 hover:text-red-600 text-sm cursor-pointer transition-colors"
            >
              <Trash2 size={15} /> Delete
            </button>
          ) : <span />}
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!title.trim()}
              className="px-4 py-2 text-sm rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium cursor-pointer transition-colors"
            >
              {story ? 'Save' : 'Create'}
            </button>
          </div>
        </div>
      </aside>

      {/* Confirm Delete Dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/40">
          <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-2xl max-w-sm w-full mx-4 border border-slate-200 dark:border-slate-700">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 mb-2">Delete story?</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">This action cannot be undone.</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium cursor-pointer transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

**Step 3: Commit**

```bash
git add client/src/components/StoryPanel.tsx client/src/hooks/useUsers.ts
git commit -m "feat: add slide-over story panel with confirm delete"
```

---

## Task 12: First-Run Team Setup Screen

**Files:**
- Create: `client/src/components/TeamSetup.tsx`

**Step 1: Create component**

Create `client/src/components/TeamSetup.tsx`:
```tsx
import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { createUser } from '../api/users'

const COLORS = ['#6366F1', '#22C55E', '#F59E0B', '#EF4444', '#8B5CF6', '#0EA5E9']

interface Props {
  onComplete: () => void
}

export default function TeamSetup({ onComplete }: Props) {
  const [members, setMembers] = useState([{ name: '', color: COLORS[0] }])
  const [saving, setSaving] = useState(false)

  const addMember = () => {
    if (members.length >= 5) return
    setMembers(prev => [...prev, { name: '', color: COLORS[prev.length % COLORS.length] }])
  }

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
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">Who's on the team?</p>

        <div className="space-y-3 mb-5">
          {members.map((m, i) => (
            <div key={i} className="flex items-center gap-3">
              <input
                type="color"
                value={m.color}
                onChange={e => updateMember(i, 'color', e.target.value)}
                className="w-9 h-9 rounded-full border-0 cursor-pointer bg-transparent"
              />
              <input
                value={m.name}
                onChange={e => updateMember(i, 'name', e.target.value)}
                placeholder={`Team member ${i + 1}`}
                className="flex-1 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {members.length > 1 && (
                <button onClick={() => removeMember(i)} className="p-1.5 text-slate-400 hover:text-red-500 cursor-pointer transition-colors">
                  <X size={16} />
                </button>
              )}
            </div>
          ))}
        </div>

        {members.length < 5 && (
          <button onClick={addMember} className="flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 cursor-pointer transition-colors mb-6">
            <Plus size={15} /> Add member
          </button>
        )}

        <button
          onClick={handleSave}
          disabled={saving || !members.some(m => m.name.trim())}
          className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium cursor-pointer transition-colors"
        >
          {saving ? 'Setting up...' : 'Start using Simple Jira'}
        </button>
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add client/src/components/TeamSetup.tsx
git commit -m "feat: add first-run team setup screen"
```

---

## Task 13: Wire Everything Together in App.tsx

**Files:**
- Modify: `client/src/App.tsx`

**Step 1: Replace App.tsx with full wired version**

```tsx
import { useState, useEffect } from 'react'
import { useTheme } from './hooks/useTheme'
import { useStories } from './hooks/useStories'
import { Sun, Moon, Plus } from 'lucide-react'
import Board from './components/Board'
import StoryPanel from './components/StoryPanel'
import TeamSetup from './components/TeamSetup'
import { fetchUsers } from './api/users'
import { Story } from './types'

export default function App() {
  const { theme, toggle } = useTheme()
  const { addStory, editStory, removeStory } = useStories()
  const [selectedStory, setSelectedStory] = useState<Story | null | undefined>(undefined)
  const [hasTeam, setHasTeam] = useState<boolean | null>(null)

  // Check if team is set up
  useEffect(() => {
    fetchUsers().then(users => setHasTeam(users.length > 0))
  }, [])

  if (hasTeam === null) return null // loading

  if (!hasTeam) {
    return <TeamSetup onComplete={() => setHasTeam(true)} />
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-50 transition-colors duration-200">
      {/* Top Bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 sticky top-0 z-30">
        <h1 className="font-mono text-lg font-semibold text-indigo-600 dark:text-indigo-400">
          simple-jira
        </h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedStory(null)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium cursor-pointer transition-colors"
          >
            <Plus size={16} /> New Story
          </button>
          <button
            onClick={toggle}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors"
            aria-label="Toggle theme"
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>
        </div>
      </header>

      <Board onCardClick={setSelectedStory} />

      {selectedStory !== undefined && (
        <StoryPanel
          story={selectedStory}
          onClose={() => setSelectedStory(undefined)}
          onSave={editStory}
          onDelete={removeStory}
          onCreate={addStory}
        />
      )}
    </div>
  )
}
```

**Step 2: Run full app and verify end-to-end**

```bash
npm run dev
```

Checklist:
- [ ] First-run team setup shows if no users
- [ ] Board renders 4 columns
- [ ] "+ New Story" opens slide-over
- [ ] Create a story — appears in Backlog
- [ ] Drag card to In Progress — updates immediately
- [ ] Click card — opens panel with existing data
- [ ] Edit and save — card reflects changes
- [ ] Delete — confirm dialog, then card disappears
- [ ] Theme toggle — persists on refresh

**Step 3: Commit**

```bash
git add client/src/App.tsx
git commit -m "feat: wire full app — board, panels, team setup, theme toggle"
```

---

## Task 14: Polish — Toast Notifications & Empty States

**Files:**
- Create: `client/src/components/Toast.tsx`
- Modify: `client/src/App.tsx`
- Modify: `client/src/components/KanbanColumn.tsx`

**Step 1: Create minimal Toast**

Create `client/src/components/Toast.tsx`:
```tsx
import { useEffect } from 'react'
import { CheckCircle } from 'lucide-react'

interface Props {
  message: string
  onDismiss: () => void
}

export default function Toast({ message, onDismiss }: Props) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 2500)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 px-4 py-3 rounded-xl shadow-lg text-sm font-medium animate-in">
      <CheckCircle size={16} className="text-green-400 dark:text-green-600" />
      {message}
    </div>
  )
}
```

**Step 2: Add empty state to KanbanColumn**

In `KanbanColumn.tsx`, inside the Droppable div, add after `{stories.map(...)}`:
```tsx
{stories.length === 0 && !snapshot.isDraggingOver && (
  <p className="text-xs font-mono text-slate-400 dark:text-slate-600 text-center pt-6 pb-2">
    Drop cards here
  </p>
)}
```

**Step 3: Wire toast into App.tsx**

Add toast state and trigger after `addStory` / `editStory`:
```tsx
const [toast, setToast] = useState<string | null>(null)

// In panel onSave/onCreate callbacks, after the call:
setToast(story ? 'Story updated' : 'Story created')
```

**Step 4: Final run and verify**

```bash
npm run dev
# Verify: toast appears after create/update, empty columns show hint text
```

**Step 5: Final commit**

```bash
git add client/src/
git commit -m "feat: add toast notifications and empty column states"
```

---

## Done

Simple Jira is complete. Run with:

```bash
npm run dev
# Client: http://localhost:3000
# API:    http://localhost:4000
```
