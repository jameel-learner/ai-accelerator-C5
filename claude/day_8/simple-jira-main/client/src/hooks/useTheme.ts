import { useState, useEffect } from 'react'
export type Theme = 'light' | 'dark'

function getStoredTheme(): Theme {
  try {
    const stored = localStorage.getItem('theme') as Theme
    if (stored) return stored
  } catch {}
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getStoredTheme)
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try { localStorage.setItem('theme', theme) } catch {}
  }, [theme])
  const toggle = () => setTheme(t => t === 'light' ? 'dark' : 'light')
  return { theme, toggle }
}
