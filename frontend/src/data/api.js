import { getAccessToken } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function fetchJSON(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' }

  // Add auth token if available
  const token = await getAccessToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { headers, ...options })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

export const api = {
  getDashboard: () => fetchJSON('/dashboard'),
  getPipeline: () => fetchJSON('/pipeline'),
  getStandoff: () => fetchJSON('/standoff'),
  getGmailHealth: () => fetchJSON('/gmail-health'),
  getActivity: () => fetchJSON('/activity'),

  triggerFind: (universeRow, jdUrl) =>
    fetchJSON('/trigger-find', {
      method: 'POST',
      body: JSON.stringify({ universe_row: universeRow, jd_url: jdUrl }),
    }),

  updateStatus: (row, status) =>
    fetchJSON('/update-status', {
      method: 'POST',
      body: JSON.stringify({ row, status }),
    }),

  runPipeline: () => fetchJSON('/run-pipeline', { method: 'POST' }),
  runMonitor: () => fetchJSON('/run-monitor', { method: 'POST' }),

  attachResume: async (row, file) => {
    const token = await getAccessToken()
    const form = new FormData()
    form.append('file', file)
    form.append('row', row.toString())
    const headers = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/attach-resume`, { method: 'POST', body: form, headers })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  chat: (message) =>
    fetchJSON('/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
}
