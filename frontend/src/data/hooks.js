import { useState, useEffect, useCallback } from 'react'
import { api } from './api'

export function useAPI(fetchFn, fallback = null, deps = []) {
  const [data, setData] = useState(fallback)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isLive, setIsLive] = useState(false)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const result = await fetchFn()
      setData(result)
      setIsLive(true)
      setError(null)
    } catch (e) {
      setError(e.message)
      setIsLive(false)
      // Keep fallback data if API fails
    } finally {
      setLoading(false)
    }
  }, [fetchFn, ...deps])

  useEffect(() => { refresh() }, [refresh])

  return { data, loading, error, isLive, refresh }
}

// Auto-refresh hook
export function usePolling(fetchFn, fallback, intervalMs = 10000) {
  const result = useAPI(fetchFn, fallback)

  useEffect(() => {
    if (!result.isLive) return
    const timer = setInterval(result.refresh, intervalMs)
    return () => clearInterval(timer)
  }, [result.isLive, result.refresh, intervalMs])

  return result
}
