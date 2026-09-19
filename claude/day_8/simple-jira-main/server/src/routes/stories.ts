import { Router } from 'express'
import db from '../db/db'

const router = Router()

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

router.post('/', (req, res) => {
  const { title, description = '', status = 'backlog', assignee_id = null, priority = 'medium' } = req.body
  if (!title) return res.status(400).json({ error: 'title is required' })

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

router.patch('/:id', (req, res) => {
  const { id } = req.params
  const fields = req.body

  const allowed = ['title', 'description', 'status', 'assignee_id', 'priority', 'position']
  const keys = Object.keys(fields).filter(k => allowed.includes(k))
  if (!keys.length) return res.status(400).json({ error: 'no valid fields to update' })

  const updates = keys.map(k => `${k} = ?`).join(', ')
  const values = keys.map(k => fields[k])

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

router.delete('/:id', (req, res) => {
  db.prepare('UPDATE stories SET archived = 1 WHERE id = ?').run(req.params.id)
  res.status(204).send()
})

export default router
