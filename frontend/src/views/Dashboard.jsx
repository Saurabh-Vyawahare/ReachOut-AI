import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  ArrowUpRight, ArrowDownRight, Clock, Mail, MessageSquare, 
  AlertTriangle, CheckCircle2, XCircle, Zap, ChevronRight
} from 'lucide-react'
import { PIPELINE_JOBS, STANDOFF_DATA, GMAIL_ACCOUNTS, ACTIVITY_FEED, QUALITY_SCORES } from '../data/mockData'

function StatCard({ label, value, sub, trend, color, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
      className="bg-surface rounded-xl p-4 border border-border-light"
    >
      <div className="text-xs text-gray-400 font-medium mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${color || 'text-stone-blue-800'}`}>{value}</div>
      {sub && (
        <div className="text-[11px] text-gray-400 mt-1 flex items-center gap-1">
          {trend === 'up' && <ArrowUpRight size={12} className="text-success" />}
          {trend === 'down' && <ArrowDownRight size={12} className="text-error" />}
          {sub}
        </div>
      )}
    </motion.div>
  )
}

function StageCell({ stage, stageKey }) {
  if (!stage || stage.status === 'pending') {
    return <span className="text-[11px] text-gray-300">—</span>
  }
  if (stage.status === 'running') {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-stone-blue font-medium">
        <span className="w-1.5 h-1.5 rounded-full bg-stone-blue animate-pulse" />
        Running
      </span>
    )
  }
  if (stage.status === 'error') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-50 text-red-700">
        Error
      </span>
    )
  }
  if (stage.status === 'waiting') {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700">
        Waiting
      </span>
    )
  }

  const pillStyles = {
    scout: 'bg-blue-50 text-blue-700',
    validate: 'bg-teal-50 text-teal-700',
    emails: 'bg-amber-50 text-amber-700',
    compose: 'bg-orange-50 text-orange-700',
    drafts: 'bg-purple-50 text-purple-700',
    monitor: 'bg-green-50 text-green-700',
  }

  const labels = {
    scout: 'Done',
    validate: stage.winner === 'grok' ? 'Grok' : 'Serp',
    emails: `${stage.found}/${stage.total}`,
    compose: `${stage.score}/10`,
    drafts: 'Ready',
    monitor: stage.status === 'sent' ? 'Sent' : stage.status === 'review' ? 'Review' : stage.status === 'fu1' ? 'FU1' : 'Done',
  }

  if (stageKey === 'monitor') {
    if (stage.status === 'sent' && stage.repliedCount > 0) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-green-50 text-green-700">
          {stage.repliedCount} reply
        </span>
      )
    }
    if (stage.status === 'review') {
      return <span className="text-[11px] text-gray-400">Review</span>
    }
    if (stage.status === 'fu1') {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 text-gray-600">
          FU1
        </span>
      )
    }
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${pillStyles[stageKey] || 'bg-gray-100 text-gray-600'}`}>
      {labels[stageKey] || 'Done'}
    </span>
  )
}

function StandoffChart() {
  const max = Math.max(...STANDOFF_DATA.daily.flatMap(d => [d.grok, d.serpapi]))
  const grokPct = Math.round((STANDOFF_DATA.grokWins / (STANDOFF_DATA.grokWins + STANDOFF_DATA.serpapiWins + STANDOFF_DATA.ties)) * 100)
  const serpapiPct = 100 - grokPct

  return (
    <div>
      <div className="flex items-center justify-center gap-1 mb-3">
        {STANDOFF_DATA.daily.map((d, i) => (
          <div key={i} className="flex gap-[2px] items-end h-[40px]" title={d.day}>
            <div className="w-[7px] rounded-t bg-orange-400/80 transition-all" style={{ height: `${(d.grok / max) * 36}px` }} />
            <div className="w-[7px] rounded-t bg-stone-blue/80 transition-all" style={{ height: `${(d.serpapi / max) * 36}px` }} />
          </div>
        ))}
      </div>
      <div className="flex justify-center gap-5 text-[11px] text-gray-400">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-orange-400/80" />
          Grok {grokPct}%
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-sm bg-stone-blue/80" />
          SerpAPI {serpapiPct}%
        </span>
      </div>
    </div>
  )
}

function GmailHealth() {
  return (
    <div className="space-y-2.5">
      {GMAIL_ACCOUNTS.map((acc, i) => {
        const pct = (acc.used / acc.cap) * 100
        const label = acc.email.split('@')[0]
        return (
          <div key={i} className="flex items-center gap-2 text-[12px]">
            <span className="w-[85px] text-gray-400 truncate">{label}</span>
            <div className="flex-1 h-[7px] bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${pct}%`,
                  background: pct > 80 ? '#EF4444' : pct > 50 ? '#F59E0B' : '#4A6FA5',
                }}
              />
            </div>
            <span className="w-[34px] text-right font-medium text-gray-500 text-[11px]">
              {acc.used}/{acc.cap}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function ActivityFeed() {
  return (
    <div className="space-y-0">
      {ACTIVITY_FEED.slice(0, 6).map(item => (
        <div key={item.id} className="flex gap-3 py-2.5 border-b border-gray-100 last:border-0">
          <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: item.color }} />
          <div className="min-w-0">
            <div className="text-[12px] text-gray-600 leading-relaxed">{item.text}</div>
            <div className="text-[11px] text-gray-300 mt-0.5">{item.time}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

function QualityScores() {
  return (
    <div className="space-y-0">
      {QUALITY_SCORES.map(item => (
        <div key={item.id} className="flex items-center gap-2 py-1.5 border-b border-gray-100 last:border-0">
          <span className={`w-[110px] truncate text-[12px] ${item.status === 'reject' ? 'text-amber-500' : 'text-gray-400'}`}>
            {item.company} — {item.contact}
          </span>
          <div className="flex-1 h-[5px] bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${item.score * 10}%`,
                background: item.status === 'reject' ? '#F59E0B' : '#10B981',
              }}
            />
          </div>
          <span className={`w-[18px] text-right text-[12px] font-medium ${
            item.status === 'reject' ? 'text-amber-500' : 'text-green-600'
          }`}>
            {item.score}
          </span>
        </div>
      ))}
    </div>
  )
}

const TIME_RANGES = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This week' },
  { key: 'biweekly', label: '2 weeks' },
  { key: 'month', label: 'This month' },
]

const RANGE_STATS = {
  today: { sent: 6, applied: 4, replies: 1, rate: 20, emails: 12, remaining: 3 },
  week: { sent: 28, applied: 15, replies: 4, rate: 32, emails: 45, remaining: 3 },
  biweekly: { sent: 52, applied: 28, replies: 7, rate: 27, emails: 84, remaining: 3 },
  month: { sent: 96, applied: 48, replies: 12, rate: 25, emails: 144, remaining: 3 },
}

export default function Dashboard({ onNavigate }) {
  const [range, setRange] = useState('today')
  const stats = RANGE_STATS[range]

  const activeJobs = PIPELINE_JOBS.filter(j => j.stages.monitor.status !== 'done').length
  const draftsReady = PIPELINE_JOBS.filter(j => j.stages.drafts.status === 'done' && j.stages.monitor.status === 'review').length
  const fuPending = PIPELINE_JOBS.filter(j => j.stages.monitor.status === 'fu1' || j.stages.monitor.status === 'fu2').length
  const totalGmailUsed = GMAIL_ACCOUNTS.reduce((s, a) => s + a.used, 0)
  const totalGmailCap = GMAIL_ACCOUNTS.reduce((s, a) => s + a.cap, 0)

  return (
    <div>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="flex items-center justify-between mb-4"
      >
        <div>
          <h1 className="text-xl font-semibold text-gray-800">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-0.5">Monday, March 23, 2026</p>
        </div>
        <div className="flex items-center gap-1 bg-surface rounded-lg p-1 border border-border-light">
          {TIME_RANGES.map(t => (
            <button
              key={t.key}
              onClick={() => setRange(t.key)}
              className={`px-3 py-1.5 rounded-md text-[12px] font-medium transition-all cursor-pointer ${
                range === t.key
                  ? 'bg-stone-blue text-white'
                  : 'text-gray-400 hover:text-gray-600 hover:bg-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </motion.div>

      {draftsReady > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 flex items-center gap-3 px-4 py-3 rounded-xl bg-purple-50 border border-purple-200 cursor-pointer hover:bg-purple-100/60 transition-colors"
          onClick={() => onNavigate('pipeline')}
        >
          <div className="w-2.5 h-2.5 rounded-full bg-purple-400 animate-pulse" />
          <span className="text-[13px] text-purple-700 font-medium">
            {draftsReady} draft{draftsReady !== 1 ? 's' : ''} waiting to be sent
          </span>
          <span className="text-[11px] text-purple-400 ml-auto">Click to review in Pipeline</span>
          <ChevronRight size={14} className="text-purple-300" />
        </motion.div>
      )}

      <div className="grid grid-cols-5 gap-3 mb-6">
        <StatCard label="Active pipeline" value={activeJobs} sub={`${stats.applied} applications`} delay={0.05} />
        <StatCard label="Emails sent" value={stats.sent} sub={`${totalGmailUsed}/${totalGmailCap} today`} delay={0.08} />
        <StatCard label="Drafts to send" value={stats.remaining} sub="Review and send" color={stats.remaining > 0 ? 'text-purple-600' : 'text-gray-400'} delay={0.11} />
        <StatCard label="Replies" value={stats.replies} sub={`${stats.rate}% reply rate`} trend="up" color="text-success" delay={0.14} />
        <StatCard label="Follow-ups" value={fuPending} sub="Next: Mon 9 AM" delay={0.17} />
      </div>

      <div className="grid grid-cols-[1.6fr_1fr] gap-4 mb-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="bg-white rounded-xl border border-border-light p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-gray-700">Pipeline</h2>
            <span className="text-[11px] text-gray-300">Today</span>
          </div>
          <div className="grid grid-cols-[1.4fr_repeat(6,1fr)] gap-0 pb-1.5 border-b border-gray-100 mb-0">
            {['Company / role', 'Scout', 'Validate', 'Emails', 'Compose', 'Drafts', 'Status'].map(h => (
              <div key={h} className="text-[11px] text-gray-300 font-medium">{h}</div>
            ))}
          </div>
          {PIPELINE_JOBS.map(job => (
            <div key={job.id} className="grid grid-cols-[1.4fr_repeat(6,1fr)] gap-0 py-2 border-b border-gray-50 last:border-0 items-center group hover:bg-stone-blue-50/30 rounded transition-colors cursor-pointer"
              onClick={() => onNavigate('pipeline', job.id)}
            >
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-gray-700 truncate flex items-center gap-1.5">
                  {job.company}
                  {job.error && <AlertTriangle size={12} className="text-error shrink-0" />}
                </div>
                <div className="text-[11px] text-gray-400 truncate">{job.role}</div>
              </div>
              <StageCell stage={job.stages.scout} stageKey="scout" />
              <StageCell stage={job.stages.validate} stageKey="validate" />
              <StageCell stage={job.stages.emails} stageKey="emails" />
              <StageCell stage={job.stages.compose} stageKey="compose" />
              <StageCell stage={job.stages.drafts} stageKey="drafts" />
              <StageCell stage={job.stages.monitor} stageKey="monitor" />
            </div>
          ))}
        </motion.div>

        <div className="flex flex-col gap-4">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-white rounded-xl border border-border-light p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-gray-700">Standoff tracker</h2>
              <span className="text-[11px] text-gray-300">30 day</span>
            </div>
            <StandoffChart />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
            className="bg-white rounded-xl border border-border-light p-4"
          >
            <h2 className="text-sm font-medium text-gray-700 mb-3">Gmail health</h2>
            <GmailHealth />
          </motion.div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-white rounded-xl border border-border-light p-4"
        >
          <h2 className="text-sm font-medium text-gray-700 mb-2">Activity feed</h2>
          <ActivityFeed />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="bg-white rounded-xl border border-border-light p-4"
        >
          <h2 className="text-sm font-medium text-gray-700 mb-2">Quality gate scores</h2>
          <QualityScores />
        </motion.div>
      </div>
    </div>
  )
}
