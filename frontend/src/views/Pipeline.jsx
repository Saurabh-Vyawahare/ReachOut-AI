import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import { PIPELINE_JOBS } from '../data/mockData'
import WorkflowCanvas from '../components/WorkflowCanvas'
import ResumeDropZone from '../components/ResumeDropZone'

export default function Pipeline({ selectedJobId }) {
  const [expandedJob, setExpandedJob] = useState(selectedJobId || null)

  const getStatusDot = (job) => {
    if (job.error) return 'bg-error'
    if (job.stages.scout.status === 'running') return 'bg-stone-blue animate-pulse'
    if (job.stages.monitor.repliedCount > 0) return 'bg-success'
    if (job.stages.emails.status === 'waiting') return 'bg-warning'
    if (job.stages.drafts.status === 'done' && job.stages.monitor.status === 'review') return 'bg-purple-400'
    return 'bg-green-400'
  }

  const getSummary = (job) => {
    if (job.error) return 'Error in pipeline'
    if (job.stages.scout.status === 'running') return 'Scouts running...'
    if (job.stages.monitor.repliedCount > 0) return `${job.stages.monitor.repliedCount} reply received`
    if (job.stages.emails.status === 'waiting') return 'Waiting for emails'
    if (job.stages.monitor.status === 'review') return 'Drafts ready for review'
    if (job.stages.monitor.status === 'fu1') return 'Follow-up #1 sent'
    if (job.stages.monitor.status === 'sent') return 'Monitoring replies'
    if (job.stages.drafts.status === 'done') return 'Drafts created'
    return 'Processing...'
  }

  return (
    <div>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
        <h1 className="text-xl font-semibold text-gray-800">Pipeline</h1>
        <p className="text-sm text-gray-400 mt-0.5">n8n workflow status for each job — expand to see visual flow</p>
      </motion.div>

      <div className="space-y-3">
        {PIPELINE_JOBS.map((job, i) => (
          <motion.div
            key={job.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-white rounded-xl border border-border-light overflow-hidden"
          >
            <button
              onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}
              className="w-full flex items-center gap-4 p-4 hover:bg-stone-blue-50/20 transition-colors cursor-pointer text-left"
            >
              <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${getStatusDot(job)}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-medium text-gray-700">{job.company}</span>
                  <span className="text-[12px] text-gray-300">—</span>
                  <span className="text-[12px] text-gray-400 truncate">{job.role}</span>
                </div>
                <div className="text-[11px] text-gray-300 mt-0.5 flex items-center gap-3">
                  <span>{job.location}</span>
                  <span className={`font-medium ${job.error ? 'text-error' : job.stages.monitor.repliedCount > 0 ? 'text-success' : 'text-gray-400'}`}>
                    {getSummary(job)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                {job.contacts.length > 0 && (
                  <span className="text-[11px] text-gray-400">{job.contacts.length} contacts</span>
                )}
                {expandedJob === job.id
                  ? <ChevronDown size={16} className="text-gray-300" />
                  : <ChevronRight size={16} className="text-gray-300" />}
              </div>
            </button>

            <AnimatePresence>
              {expandedJob === job.id && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="overflow-hidden"
                >
                  <div className="px-4 pb-4 border-t border-gray-100">
                    <div className="mt-4 mb-4 bg-stone-blue-50/20 rounded-xl border border-stone-blue-100/40 p-3 overflow-x-auto">
                      <WorkflowCanvas job={job} />
                    </div>

                    <div className="grid grid-cols-[1fr_260px] gap-5">
                      <div>
                        {job.error && (
                          <div className="p-3 rounded-xl bg-red-50 border border-red-100 mb-3">
                            <div className="flex items-center gap-2 text-[12px] text-red-600 font-medium mb-1">
                              <AlertTriangle size={13} /> Pipeline error
                            </div>
                            <p className="text-[11px] text-red-500 leading-relaxed">{job.error}</p>
                          </div>
                        )}

                        <div className="p-3 rounded-xl bg-gray-50 border border-gray-100">
                          <div className="text-[11px] text-gray-400 space-y-1.5">
                            <div className="flex justify-between">
                              <span>JD URL</span>
                              <a href={job.jdUrl} target="_blank" rel="noreferrer" className="text-stone-blue flex items-center gap-1 hover:underline">
                                View <ExternalLink size={10} />
                              </a>
                            </div>
                            <div className="flex justify-between">
                              <span>Added</span>
                              <span className="text-gray-600">{new Date(job.addedAt).toLocaleString()}</span>
                            </div>
                            {job.stages.validate.status === 'done' && (
                              <div className="flex justify-between">
                                <span>Standoff winner</span>
                                <span className="text-gray-600 font-medium">{job.stages.validate.winner === 'grok' ? 'Grok' : 'SerpAPI'}</span>
                              </div>
                            )}
                            {job.stages.compose.status === 'done' && (
                              <div className="flex justify-between">
                                <span>Quality score</span>
                                <span className="text-gray-600 font-medium">{job.stages.compose.score}/10{job.stages.compose.attempts > 1 ? ` (${job.stages.compose.attempts} attempts)` : ''}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <ResumeDropZone job={job} />
                      </div>

                      <div>
                        <h3 className="text-[12px] font-medium text-gray-400 mb-3">Contacts</h3>
                        {job.contacts.length === 0 ? (
                          <p className="text-[12px] text-gray-300 italic">No contacts found yet</p>
                        ) : (
                          <div className="space-y-2">
                            {job.contacts.map((c, ci) => (
                              <div key={ci} className="flex items-start gap-2 p-2.5 rounded-lg bg-stone-blue-50/30 border border-stone-blue-100/50">
                                <div className="w-7 h-7 rounded-full bg-stone-blue-100 flex items-center justify-center text-[11px] font-medium text-stone-blue-700 shrink-0">
                                  {c.name.split(' ').map(w => w[0]).join('')}
                                </div>
                                <div className="min-w-0">
                                  <div className="text-[12px] font-medium text-gray-700 flex items-center gap-1.5">
                                    {c.name}
                                    {c.replied && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-50 text-green-600 font-medium">Replied</span>}
                                  </div>
                                  <div className="text-[11px] text-gray-400">{c.title}</div>
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
