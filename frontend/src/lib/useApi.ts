import { useEffect, useState } from 'react'

export interface ApiState<T> {
  data: T | null
  error: Error | null
  loading: boolean
}

/**
 * Run an API call when `key` changes and track its result.
 * Responses that arrive after the key has changed again are ignored.
 */
export function useApi<T>(load: () => Promise<T>, key: string): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ data: null, error: null, loading: true })

  useEffect(() => {
    let current = true
    setState((previous) => ({ ...previous, loading: true, error: null }))
    load()
      .then((data) => current && setState({ data, error: null, loading: false }))
      .catch((error: Error) => current && setState({ data: null, error, loading: false }))
    return () => {
      current = false
    }
    // `load` is recreated every render; `key` says when the request really changed.
  }, [key])

  return state
}
