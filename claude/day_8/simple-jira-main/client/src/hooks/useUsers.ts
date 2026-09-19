import { useState, useEffect } from 'react'
import type { User } from '../types'
import { fetchUsers } from '../api/users'

export function useUsers() {
  const [users, setUsers] = useState<User[]>([])
  useEffect(() => { fetchUsers().then(setUsers) }, [])
  return users
}
