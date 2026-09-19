import Database from 'better-sqlite3'
import path from 'path'
import fs from 'fs'

const DB_PATH = process.env.DB_PATH || './data/simple-jira.db'
const schemaPath = path.join(__dirname, 'schema.sql')

// Ensure data directory exists
const dir = path.dirname(path.resolve(DB_PATH))
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })

const db = new Database(path.resolve(DB_PATH))
db.pragma('journal_mode = WAL')
db.pragma('foreign_keys = ON')

// Run schema
const schema = fs.readFileSync(schemaPath, 'utf8')
db.exec(schema)

export default db
