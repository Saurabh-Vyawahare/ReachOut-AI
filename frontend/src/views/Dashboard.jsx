import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, ArrowDownRight, ChevronRight, RefreshCw, Wifi, WifiOff, LogOut } from 'lucide-react'
import { api } from '../data/api'
import { PIPELINE_JOBS, STANDOFF_DATA, GMAIL_ACCOUNTS as MOCK_GMAIL, ACTIVITY_FEED, QUALITY_SCORES } from '../data/mockData'

const TIME_RANGES = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This week' },
  { key: 'biweekly', label: '2 weeks' },
  { key: 'month', label: 'This month' },
]

function StatCard({ label, value, sub, trend, color, delay }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.35 }}
      className="bg-surface rounded-xl p-4 border border-border-light">
      <div className="text-xs text-gray-400 font-medium mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${color || 'text-stone-blue-800'}`}>{value}</div>
      {sub && <div className="text-[11px] text-gray-400 mt-1 flex items-center gap-1">
        {trend === 'up' && <ArrowUpRight size={12} className="text-success" />}
        {trend === 'down' && <ArrowDownRight size={12} className="text-error" />}
        {sub}
      </div>}
    </motion.div>
  )
}

function LivePipelineTable({ jobs, onNavigate }) {
  return (
    <div>
      <div className="grid grid-cols-[1.4fr_repeat(5,1fr)] gap-0 pb-1.5 border-b border-gray-100 mb-0">
        {['Company / role', 'Status', 'Winner', 'Contacts', 'QG Score', 'Gmail'].map(h => (
          <div key={h} className="text-[11px] text-gray-300 font-medium">{h}</div>
        ))}
      </div>
      {jobs.map(job => (
        <div key={job.id} className="grid grid-cols-[1.4fr_repeat(5,1fr)] gap-0 py-2 border-b border-gray-50 last:border-0 items-center hover:bg-stone-blue-50/30 rounded transition-colors cursor-pointer"
          onClick={() => onNavigate('pipeline', job.id)}>
          <div className="min-w-0">
            <div className="text-[13px] font-medium text-gray-700 truncate">{job.company}</div>
            <div className="text-[11px] text-gray-400 truncate">{job.job_title}</div>
          </div>
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium w-fit ${
            job.status === 'ERROR' ? 'bg-red-50 text-red-700' :
            job.status === 'DRAFTS_READY' ? 'bg-purple-50 text-purple-700' :
            job.status === 'SENT' ? 'bg-green-50 text-green-700' :
            job.status === 'SCOUTING' ? 'bg-blue-50 text-blue-700' :
            job.status === 'FU1' ? 'bg-gray-100 text-gray-600' :
            'bg-gray-100 text-gray-600'
          }`}>{job.status}</span>
          <span className="text-[11px] text-gray-500">{job.scout_winner || '—'}</span>
          <span className="text-[11px] text-gray-500">{job.contacts?.length || 0}</span>
          <span className="text-[11px] text-gray-500">{job.quality_score || '—'}</span>
          <span className="text-[11px] text-gray-400 truncate">{job.gmail_used ? job.gmail_used.split(',')[0].split('@')[0] : '—'}</span>
        </div>
      ))}
      {jobs.length === 0 && <p className="text-[12px] text-gray-300 text-center py-6">No pipeline jobs yet. Paste a JD URL to start.</p>}
    </div>
  )
}

function StandoffChart({ standoff }) {
  if (!standoff || standoff.total === 0) return <p className="text-[12px] text-gray-300 text-center py-4">No standoff data yet — run a few FINDs</p>
  const grokPct = Math.round((standoff.grok / standoff.total) * 100)
  const serpPct = 100 - grokPct
  return (
    <div>
      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 h-4 bg-gray-100 rounded-full overflow-hidden flex">
          <div className="h-full bg-orange-400/80 rounded-l-full transition-all" style={{ width: `${grokPct}%` }} />
          <div className="h-full bg-stone-blue/80 rounded-r-full transition-all" style={{ width: `${serpPct}%` }} />
        </div>
      </div>
      <div className="flex justify-center gap-5 text-[11px] text-gray-400">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-orange-400/80" /> Grok {standoff.grok} ({grokPct}%)</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-stone-blue/80" /> SerpAPI {standoff.serpapi} ({serpPct}%)</span>
      </div>
    </div>
  )
}

function GmailHealth({ accounts }) {
  return (
    <div className="space-y-2.5">
      {accounts.map((acc, i) => {
        const pct = (acc.used / acc.cap) * 100
        const label = acc.email?.split('@')[0] || `Account ${i+1}`
        return (
          <div key={i} className="flex items-center gap-2 text-[12px]">
            <span className="w-[85px] text-gray-400 truncate">{label}</span>
            <div className="flex-1 h-[7px] bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: pct > 80 ? '#EF4444' : pct > 50 ? '#F59E0B' : '#4A6FA5' }} />
            </div>
            <span className="w-[34px] text-right font-medium text-gray-500 text-[11px]">{acc.used}/{acc.cap}</span>
          </div>
        )
      })}
    </div>
  )
}

function ActivityFeed({ events }) {
  const colors = { reply: '#10B981', draft: '#4A6FA5', error: '#EF4444', warning: '#F59E0B', quality: '#D85A30', standoff: '#0F6E56', followup: '#8B5CF6', scout: '#4A6FA5', info: '#6B7280' }
  return (
    <div className="space-y-0">
      {events.slice(0, 8).map((item, i) => (
        <div key={i} className="flex gap-3 py-2.5 border-b border-gray-100 last:border-0">
          <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: colors[item.type] || '#6B7280' }} />
          <div className="min-w-0">
            <div className="text-[12px] text-gray-600 leading-relaxed">{item.message || item.text}</div>
            <div className="text-[11px] text-gray-300 mt-0.5">{item.time}</div>
          </div>
        </div>
      ))}
      {events.length === 0 && <p className="text-[12px] text-gray-300 text-center py-4">No activity yet — run the pipeline to see events here</p>}
    </div>
  )
}

export default function Dashboard({ onNavigate }) {
  const [range, setRange] = useState('today')
  const [isLive, setIsLive] = useState(false)
  const [loading, setLoading] = useState(true)
  const [dashboard, setDashboard] = useState(null)
  const [pipeline, setPipeline] = useState(null)
  const [activity, setActivity] = useState(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [dash, pipe, act] = await Promise.all([api.getDashboard(), api.getPipeline(), api.getActivity()])
      setDashboard(dash); setPipeline(pipe); setActivity(act); setIsLive(true)
    } catch (e) {
      console.warn('API not available, using mock data:', e.message)
      setIsLive(false)
    } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])
  useEffect(() => { if (!isLive) return; const t = setInterval(fetchData, 300000); return () => clearInterval(t) }, [isLive])

  const stats = dashboard?.stats || { active_pipeline: 0, drafts_ready: 0, sent: 0, replies: 0, reply_rate: 0 }
  const gmail = dashboard?.gmail || { accounts: MOCK_GMAIL, total_used: 0, total_remaining: 40 }
  const standoff = dashboard?.standoff || { grok: 0, serpapi: 0, total: 0 }
  const jobs = pipeline?.jobs || []
  const events = activity?.events || []

  return (
    <div>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-800">Dashboard</h1>
            <div className={`flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full ${isLive ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
              {isLive ? <Wifi size={11} /> : <WifiOff size={11} />}
              {isLive ? 'Live' : 'Offline'}
            </div>
          </div>
          <p className="text-sm text-gray-400 mt-0.5">{dashboard?.today || new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchData} className="p-2 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer" title="Refresh">
            <RefreshCw size={14} className={`text-gray-400 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <div className="flex items-center gap-1 bg-surface rounded-lg p-1 border border-border-light">
            {TIME_RANGES.map(t => (
              <button key={t.key} onClick={() => setRange(t.key)}
                className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition-all cursor-pointer ${range === t.key ? 'bg-stone-blue text-white' : 'text-gray-400 hover:text-gray-600 hover:bg-white'}`}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </motion.div>

      {stats.drafts_ready > 0 && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="mb-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-purple-50 border border-purple-200 cursor-pointer hover:bg-purple-100/60 transition-colors"
          onClick={() => onNavigate('pipeline')}>
          <div className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
          <span className="text-[13px] text-purple-700 font-medium">{stats.drafts_ready} draft{stats.drafts_ready !== 1 ? 's' : ''} waiting</span>
          <span className="text-[11px] text-purple-400 ml-auto">Review in Pipeline</span>
          <ChevronRight size={14} className="text-purple-300" />
        </motion.div>
      )}

      <div className="grid grid-cols-5 gap-3 mb-6">
        <StatCard label="Active pipeline" value={stats.active_pipeline} sub={`${jobs.length} total jobs`} delay={0.05} />
        <StatCard label="Emails sent" value={stats.sent} sub={`${gmail.total_used}/${gmail.total_used + gmail.total_remaining} today`} delay={0.08} />
        <StatCard label="Drafts to send" value={stats.drafts_ready} sub="Review and send" color={stats.drafts_ready > 0 ? 'text-purple-600' : 'text-gray-400'} delay={0.11} />
        <StatCard label="Replies" value={stats.replies} sub={`${stats.reply_rate}% reply rate`} trend={stats.replies > 0 ? 'up' : undefined} color="text-success" delay={0.14} />
        <StatCard label="Standoff" value={`${standoff.total}`} sub={standoff.total > 0 ? `Grok ${standoff.grok} / Serp ${standoff.serpapi}` : 'No data'} delay={0.17} />
      </div>

      <div className="grid grid-cols-[1.6fr_1fr] gap-4 mb-4">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}
          className="bg-white rounded-xl border border-border-light p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-gray-700">Pipeline</h2>
            <span className="text-[11px] text-gray-300">{isLive ? 'Live data' : 'Offline'}</span>
          </div>
          <LivePipelineTable jobs={jobs} onNavigate={onNavigate} />
        </motion.div>
        <div className="flex flex-col gap-4">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
            className="bg-white rounded-xl border border-border-light p-4">
            <h2 className="text-sm font-medium text-gray-700 mb-3">Standoff tracker</h2>
            <StandoffChart standoff={standoff} />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}
            className="bg-white rounded-xl border border-border-light p-4">
            <h2 className="text-sm font-medium text-gray-700 mb-3">Gmail health</h2>
            <GmailHealth accounts={gmail.accounts || MOCK_GMAIL} />
          </motion.div>
        </div>
      </div>

      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
        className="bg-white rounded-xl border border-border-light p-4">
        <h2 className="text-sm font-medium text-gray-700 mb-2">Activity feed</h2>
        <ActivityFeed events={events} />
      </motion.div>
    </div>
  )
}
