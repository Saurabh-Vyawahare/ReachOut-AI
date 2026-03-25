import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink, Wifi, WifiOff, RefreshCw } from 'lucide-react'
import { api } from '../data/api'
import { PIPELINE_JOBS } from '../data/mockData'
import ResumeDropZone from '../components/ResumeDropZone'

function getStatusDot(job) {
  const s = job.status
  if (s === 'ERROR') return 'bg-error'
  if (s === 'SCOUTING') return 'bg-stone-blue animate-pulse'
  if (s === 'REPLIED') return 'bg-success'
  if (s === 'DRAFTS_READY') return 'bg-purple-400'
  if (s === 'FU1' || s === 'FU2') return 'bg-amber-400'
  if (s === 'SENT') return 'bg-green-400'
  if (s === 'FIND' || s === 'READY' || s === 'COMPOSING') return 'bg-stone-blue animate-pulse'
  return 'bg-gray-300'
}

function getSummary(job) {
  const s = job.status
  if (s === 'ERROR') return 'Error in pipeline'
  if (s === 'SCOUTING') return 'Scouts running...'
  if (s === 'COMPOSING') return 'Generating emails...'
  if (s === 'FIND') return 'Waiting for FIND...'
  if (s === 'READY') return 'Ready to compose'
  if (s === 'DRAFTS_READY') return 'Drafts ready — review and send'
  if (s === 'SENT') return 'Sent — monitoring replies'
  if (s === 'REPLIED') return 'Reply received!'
  if (s === 'FU1') return 'Follow-up #1 sent'
  if (s === 'FU2') return 'Follow-up #2 sent'
  if (s === 'DONE') return 'Complete'
  return s || 'Processing...'
}

function StatusPill({ status }) {
  const styles = {
    ERROR: 'bg-red-50 text-red-700',
    SCOUTING: 'bg-blue-50 text-blue-700',
    COMPOSING: 'bg-orange-50 text-orange-700',
    FIND: 'bg-blue-50 text-blue-700',
    READY: 'bg-amber-50 text-amber-700',
    DRAFTS_READY: 'bg-purple-50 text-purple-700',
    SENT: 'bg-green-50 text-green-700',
    REPLIED: 'bg-green-50 text-green-700',
    FU1: 'bg-gray-100 text-gray-600',
    FU2: 'bg-gray-100 text-gray-600',
    DONE: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium ${styles[status] || 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

function InfoRow({ label, value, mono }) {
  if (!value) return null
  return (
    <div className="flex justify-between py-1">
      <span className="text-gray-400">{label}</span>
      <span className={`text-gray-600 ${mono ? 'font-mono text-[10px]' : ''}`}>{value}</span>
    </div>
  )
}

function buildMockStages(job) {
  // Convert flat API data to stage structure for WorkflowCanvas compatibility
  return {
    scout: { status: job.scout_winner ? 'done' : job.status === 'SCOUTING' ? 'running' : job.status === 'ERROR' ? 'error' : 'pending', winner: job.scout_winner, time: '' },
    validate: { status: job.scout_winner ? 'done' : 'pending', winner: job.scout_winner, contacts: job.contacts?.length || 0 },
    emails: { status: job.contacts?.some(c => c.email) ? 'done' : job.contacts?.length > 0 ? 'waiting' : 'pending', found: job.contacts?.filter(c => c.email).length || 0, total: job.contacts?.length || 0 },
    compose: { status: job.quality_score ? 'done' : 'pending', score: parseFloat(job.quality_score) || 0, attempts: 1 },
    drafts: { status: job.gmail_used ? 'done' : 'pending', account: job.gmail_used },
    monitor: { status: job.status === 'REPLIED' ? 'replied' : job.status === 'SENT' ? 'sent' : job.status === 'FU1' ? 'fu1' : 'pending', repliedCount: job.reply_from ? 1 : 0 },
  }
}

export default function Pipeline({ selectedJobId }) {
  const [expandedJob, setExpandedJob] = useState(selectedJobId || null)
  const [jobs, setJobs] = useState([])
  const [isLive, setIsLive] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      const data = await api.getPipeline()
      setJobs(data.jobs || [])
      setIsLive(true)
    } catch (e) {
      console.warn('Pipeline API offline:', e.message)
      setIsLive(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])
  useEffect(() => { if (!isLive) return; const t = setInterval(fetchData, 300000); return () => clearInterval(t) }, [isLive])

  return (
    <div>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">Pipeline</h1>
            <p className="text-sm text-gray-400 mt-0.5">Workflow status for each job — expand to see details</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={fetchData} className="p-2 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
              <RefreshCw size={14} className={`text-gray-400 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <div className={`flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full ${isLive ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
              {isLive ? <Wifi size={11} /> : <WifiOff size={11} />}
              {isLive ? `${jobs.length} jobs` : 'Offline'}
            </div>
          </div>
        </div>
      </motion.div>

      {jobs.length === 0 && !loading && (
        <div className="text-center py-16">
          <p className="text-gray-400 text-[14px]">No pipeline jobs yet.</p>
          <p className="text-gray-300 text-[12px] mt-1">Paste a JD URL in the Universe tab or click "Add job URL" to start.</p>
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job, i) => (
          <motion.div key={job.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            className="bg-white rounded-xl border border-border-light overflow-hidden">

            <button onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
              className="w-full flex items-center gap-4 p-4 hover:bg-stone-blue-50/20 transition-colors cursor-pointer text-left">
              <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${getStatusDot(job)}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-medium text-gray-700">{job.company}</span>
                  <span className="text-[12px] text-gray-300">—</span>
                  <span className="text-[12px] text-gray-400 truncate">{job.job_title}</span>
                </div>
                <div className="text-[11px] text-gray-300 mt-0.5 flex items-center gap-3">
                  <span>{job.location}</span>
                  <span className={`font-medium ${job.status === 'ERROR' ? 'text-error' : job.status === 'REPLIED' ? 'text-success' : 'text-gray-400'}`}>
                    {getSummary(job)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusPill status={job.status} />
                {job.contacts?.length > 0 && <span className="text-[11px] text-gray-400">{job.contacts.length} contacts</span>}
                {expandedJob === job.id ? <ChevronDown size={16} className="text-gray-300" /> : <ChevronRight size={16} className="text-gray-300" />}
              </div>
            </button>

            <AnimatePresence>
              {expandedJob === job.id && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} className="overflow-hidden">
                  <div className="px-4 pb-4 border-t border-gray-100">
                    <div className="grid grid-cols-[1fr_260px] gap-5 mt-4">
                      <div>
                        {job.notes && job.status === 'ERROR' && (
                          <div className="p-3 rounded-xl bg-red-50 border border-red-100 mb-3">
                            <div className="flex items-center gap-2 text-[12px] text-red-600 font-medium mb-1">
                              <AlertTriangle size={13} /> Pipeline error
                            </div>
                            <p className="text-[11px] text-red-500 leading-relaxed">{job.notes}</p>
                          </div>
                        )}

                        <div className="p-3 rounded-xl bg-gray-50 border border-gray-100 text-[11px]">
                          <InfoRow label="Status" value={job.status} />
                          <InfoRow label="Scout winner" value={job.scout_winner} />
                          <InfoRow label="Quality score" value={job.quality_score ? `${job.quality_score}/10` : null} />
                          <InfoRow label="Gmail account" value={job.gmail_used} mono />
                          <InfoRow label="Sent date" value={job.sent_date} />
                          <InfoRow label="Follow-up 1" value={job.fu1_date} />
                          <InfoRow label="Follow-up 2" value={job.fu2_date} />
                          <InfoRow label="Notes" value={job.notes && job.status !== 'ERROR' ? job.notes : null} />
                        </div>

                        {job.status === 'DRAFTS_READY' && (
                          <div className="mt-3 p-3 rounded-xl bg-stone-blue-50/30 border border-stone-blue-100/50">
                            <p className="text-[12px] text-stone-blue-700 font-medium">Resume drop zone</p>
                            <p className="text-[11px] text-gray-400 mt-1">Drag a PDF here to attach to all {job.company} drafts</p>
                          </div>
                        )}
                      </div>

                      <div>
                        <h3 className="text-[12px] font-medium text-gray-400 mb-3">Contacts</h3>
                        {(!job.contacts || job.contacts.length === 0) ? (
                          <p className="text-[12px] text-gray-300 italic">No contacts found yet</p>
                        ) : (
                          <div className="space-y-2">
                            {job.contacts.map((c, ci) => (
                              <div key={ci} className="flex items-start gap-2 p-2.5 rounded-lg bg-stone-blue-50/30 border border-stone-blue-100/50">
                                <div className="w-7 h-7 rounded-full bg-stone-blue-100 flex items-center justify-center text-[11px] font-medium text-stone-blue-700 shrink-0">
                                  {c.name?.split(' ').map(w => w[0]).join('').slice(0, 2) || '?'}
                                </div>
                                <div className="min-w-0">
                                  <div className="text-[12px] font-medium text-gray-700">{c.name}</div>
                                  {c.email ? (
                                    <div className="text-[11px] text-stone-blue mt-0.5 font-mono">{c.email}</div>
                                  ) : (
                                    <div className="text-[11px] text-amber-500 mt-0.5 font-medium">Email needed</div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
