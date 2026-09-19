import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import db from './db/db'
import usersRouter from './routes/users'
import storiesRouter from './routes/stories'

const app = express()
const PORT = process.env.PORT || 4000

app.use(cors())
app.use(express.json())

app.use('/api/users', usersRouter)
app.use('/api/stories', storiesRouter)

app.get('/api/health', (_req, res) => res.json({ ok: true }))

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`))

export { db }
