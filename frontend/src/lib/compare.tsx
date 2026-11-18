import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export const MAX_COMPARE = 4
const STORAGE_KEY = 'paddle-finder.compare'

interface CompareState {
  ids: number[]
  has: (id: number) => boolean
  toggle: (id: number) => void
  remove: (id: number) => void
  clear: () => void
  full: boolean
}

const CompareContext = createContext<CompareState | null>(null)

function readStored(): number[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter(Number.isInteger).slice(0, MAX_COMPARE) : []
  } catch {
    return []
  }
}

/** The paddles picked for comparison, remembered in this browser between visits. */
export function CompareProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<number[]>(readStored)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(ids))
    } catch {
      // Storage can be unavailable (private mode); the list still works for this visit.
    }
  }, [ids])

  const toggle = useCallback((id: number) => {
    setIds((current) => {
      if (current.includes(id)) return current.filter((x) => x !== id)
      return current.length >= MAX_COMPARE ? current : [...current, id]
    })
  }, [])
  const remove = useCallback((id: number) => setIds((current) => current.filter((x) => x !== id)), [])
  const clear = useCallback(() => setIds([]), [])

  const value = useMemo<CompareState>(() => ({
    ids, toggle, remove, clear, has: (id) => ids.includes(id), full: ids.length >= MAX_COMPARE,
  }), [ids, toggle, remove, clear])

  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>
}

export function useCompare(): CompareState {
  const state = useContext(CompareContext)
  if (!state) throw new Error('useCompare must be used inside <CompareProvider>')
  return state
}
