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
