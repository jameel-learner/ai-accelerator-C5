# Simple Jira — Design Document
**Date:** 2026-03-30
**Status:** Approved

---

## Overview

Simple Jira is a lightweight Kanban-based user story ticketing system for small teams of 2–3 engineers. It replaces Jira's complexity with a focused, fast, local web app that runs with a single command.

---

## Goals

- Zero-friction ticket management for small teams
- Single `npm run dev` to run locally
- No accounts, no cloud dependency, no ceremony
- Light/dark mode, developer-friendly aesthetic

---

## Architecture

**Approach:** Monorepo, single process — one `client/` (React + Vite) and one `server/` (Express + SQLite) directory. Express serves the API; Vite proxies `/api` calls during development.

```
simple-jira/
├── client/                  # React (Vite)
│   ├── src/
│   │   ├── components/      # Board, Card, Column, Modal, Sidebar
│   │   ├── hooks/           # useStories, useTheme
│   │   ├── api/             # fetch wrappers for REST calls
│   │   └── App.tsx
│   └── vite.config.ts       # proxy → localhost:4000
│
├── server/                  # Express + SQLite
│   ├── db/
│   │   ├── schema.sql       # stories, users tables
│   │   └── db.ts            # better-sqlite3 singleton
│   ├── routes/
│   │   ├── stories.ts       # CRUD + column move
│   │   └── users.ts         # list assignees
│   └── index.ts             # Express app, serves /api/*
│
├── package.json             # root scripts: dev, build, start
└── .env                     # PORT, DB_PATH
```

**Run:** `npm install && npm run dev` at the root starts both Vite (`:3000`) and Express (`:4000`) via `concurrently`.

---

## Data Model

```sql
stories (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  title       TEXT NOT NULL,
  description TEXT,
  status      TEXT NOT NULL DEFAULT 'backlog',  -- backlog | in_progress | review | done
  assignee    INTEGER REFERENCES users(id),
  priority    TEXT NOT NULL DEFAULT 'medium',   -- high | medium | low
  position    INTEGER NOT NULL DEFAULT 0,
  archived    INTEGER NOT NULL DEFAULT 0,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)

users (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  name  TEXT NOT NULL,
  color TEXT NOT NULL  -- hex color for avatar
)
```

---

## API Surface

```
GET    /api/stories          -- all stories (non-archived), ordered by status + position
POST   /api/stories          -- create story
PATCH  /api/stories/:id      -- update fields (title, description, status, assignee, priority, position)
DELETE /api/stories/:id      -- soft-delete (sets archived=1)

GET    /api/users            -- list team members
POST   /api/users            -- create team member
```

---

## Kanban Columns

| Column | Status Value | Accent Color |
|---|---|---|
| Backlog | `backlog` | `#94A3B8` (slate) |
| In Progress | `in_progress` | `#6366F1` (indigo) |
| Review | `review` | `#F59E0B` (amber) |
| Done | `done` | `#22C55E` (green) |

---

## Design System

### Style
Clean flat dashboard. Precise, minimal, task-focused.

### Color Palette

| Role | Light Mode | Dark Mode |
|---|---|---|
| Background | `#F8FAFC` | `#0F172A` |
| Surface (cards) | `#FFFFFF` | `#1E293B` |
| Border | `#E2E8F0` | `#334155` |
| Primary | `#6366F1` | `#818CF8` |
| Text primary | `#0F172A` | `#F8FAFC` |
| Text muted | `#64748B` | `#94A3B8` |
| Success | `#22C55E` | `#4ADE80` |
| Warning | `#F59E0B` | `#FBB040` |

### Typography
- **Headings / Labels:** Fira Code (500–600)
- **Body / Descriptions:** Fira Sans (400)
- **Story Titles:** Fira Sans (600)

### Icons
Lucide React throughout. No emojis as icons.

---

## Components

### Board Layout
Full-width horizontal scroll. Four fixed columns with card count badge in header. Top bar: app name, "+ New Story" button, team avatars, theme toggle.

### Story Card
White/dark surface. 4px left border indicating priority (red=high, yellow=medium, gray=low). Shows title, assignee avatar, priority badge. 150ms hover lift.

### Story Panel (slide-over)
Right-side panel overlaid on board. Fields: Title, Description, Assignee (dropdown), Priority (High/Medium/Low). Keeps board visible while editing.

### Drag & Drop
`@hello-pangea/dnd` for smooth reorder within and across columns. Card at 80% opacity while dragging. Drop target highlighted with dashed border. "Move to →" dropdown as fallback.

### Delete Flow
Always behind a confirm dialog ("Are you sure?"). Soft-delete only — sets `archived=1`.

### First-Run Setup
If no users exist, show a setup screen: enter 2–3 team member names and pick a color.

---

## Routes

| Route | Description |
|---|---|
| `/` | Kanban board (main view) |
| `/story/:id` | Deep-linkable story detail |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript |
| Styling | Tailwind CSS v3 |
| Drag & Drop | @hello-pangea/dnd |
| Backend | Node.js, Express, TypeScript |
| Database | SQLite via better-sqlite3 |
| Dev runner | concurrently |

---

## UX Rules (from UI/UX Pro analysis)

- All clickable elements: `cursor-pointer`
- Hover states: smooth `150–300ms` transitions
- Delete: always confirm dialog, never direct
- Success feedback: toast notification after create/update
- Light mode text: minimum 4.5:1 contrast ratio
- `prefers-reduced-motion` respected
- Responsive at 375px, 768px, 1024px, 1440px
- Focus states visible for keyboard navigation
