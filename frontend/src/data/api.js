import { getAccessToken } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function fetchJSON(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = await getAccessToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, { headers, ...options })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

async function fetchWithAuth(path, options = {}) {
  const token = await getAccessToken()
  const headers = { ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
  return res.json()
}

export const api = {
  // ─── Dashboard ───
  getDashboard: (range = 'all') => fetchJSON(`/dashboard?range=${range}`),
  getPipeline: () => fetchJSON('/pipeline'),
  getStandoff: () => fetchJSON('/standoff'),
  getGmailHealth: () => fetchJSON('/gmail-health'),
  getActivity: () => fetchJSON('/activity'),

  // ─── Add Job from URL ───
  addJob: (jdUrl) =>
    fetchJSON('/add-job', {
      method: 'POST',
      body: JSON.stringify({ jd_url: jdUrl }),
    }),

  // ─── Run scouts for a specific row ───
  runScouts: (coldEmailRow) =>
    fetchJSON(`/run-scouts/${coldEmailRow}`, { method: 'POST' }),

  // ─── Update contact name/email ───
  updateContact: (row, contactIndex, name, email) =>
    fetchJSON('/update-contact', {
      method: 'POST',
      body: JSON.stringify({ row, contact_index: contactIndex, name, email }),
    }),

  // ─── Add a new contact manually ───
  addContact: (row, name) =>
    fetchJSON('/add-contact', {
      method: 'POST',
      body: JSON.stringify({ row, name }),
    }),

  // ─── Remove a contact ───
  removeContact: (row, contactIndex) =>
    fetchJSON('/remove-contact', {
      method: 'POST',
      body: JSON.stringify({ row, contact_index: contactIndex }),
    }),

  // ─── Generate drafts (with optional resume) ───
  generateDrafts: async (row, resumeFile) => {
    const token = await getAccessToken()
    const form = new FormData()
    form.append('row', row.toString())
    if (resumeFile) form.append('resume', resumeFile)
    const headers = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/generate-drafts`, {
      method: 'POST',
      body: form,
      headers,
    })
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`)
    return res.json()
  },

  // ─── Trigger find (legacy) ───
  triggerFind: (universeRow, jdUrl) =>
    fetchJSON('/trigger-find', {
      method: 'POST',
      body: JSON.stringify({ universe_row: universeRow, jd_url: jdUrl }),
    }),

  // ─── Update status ───
  updateStatus: (row, status) =>
    fetchJSON('/update-status', {
      method: 'POST',
      body: JSON.stringify({ row, status }),
    }),

  // ─── Run full pipeline (legacy) ───
  runPipeline: () => fetchJSON('/run-pipeline', { method: 'POST' }),
  runMonitor: () => fetchJSON('/run-monitor', { method: 'POST' }),

  // ─── Resume upload ───
  attachResume: async (row, file) => {
    const token = await getAccessToken()
    const form = new FormData()
    form.append('file', file)
    form.append('row', row.toString())
    const headers = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/attach-resume`, {
      method: 'POST',
      body: form,
      headers,
    })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  // ─── Chat ───
  chat: (message) =>
    fetchJSON('/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    }),
}
