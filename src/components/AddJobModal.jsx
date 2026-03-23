import { useState } from 'react'
import { motion } from 'framer-motion'
import { X, Link, Zap } from 'lucide-react'

export default function AddJobModal({ onClose }) {
  const [url, setUrl] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = () => {
    if (!url.trim()) return
    setSubmitted(true)
    setTimeout(() => onClose(), 1500)
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ background: 'rgba(15, 29, 48, 0.5)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        onClick={e => e.stopPropagation()}
        className="w-[480px] bg-white rounded-2xl border border-border-light overflow-hidden"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-[15px] font-medium text-gray-700">Add job to pipeline</h2>
          <button onClick={onClose} className="text-gray-300 hover:text-gray-500 transition-colors cursor-pointer">
            <X size={18} />
          </button>
        </div>

        <div className="p-5">
          {!submitted ? (
            <>
              <label className="block text-[12px] text-gray-400 font-medium mb-2">Job description URL</label>
              <div className="flex items-center gap-2 mb-3">
                <div className="relative flex-1">
                  <Link size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-300" />
                  <input
                    type="url"
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                    placeholder="https://boards.greenhouse.io/company/jobs/..."
                    className="w-full pl-9 pr-4 py-2.5 rounded-xl border border-border-light text-[13px] text-gray-700 placeholder-gray-300 focus:outline-none focus:border-stone-blue-200 focus:ring-2 focus:ring-stone-blue-50"
                    autoFocus
                  />
                </div>
              </div>
              <p className="text-[11px] text-gray-300 mb-5">
                Supported: Greenhouse, Ashby, Lever, Workday, and most career pages
              </p>

              <div className="flex items-center gap-3 p-3 rounded-xl bg-stone-blue-50/50 border border-stone-blue-100/50 mb-5">
                <Zap size={14} className="text-stone-blue shrink-0" />
                <p className="text-[12px] text-stone-blue-700 leading-relaxed">
                  Paste the URL and the pipeline handles everything: JD extraction, dual-scout contact search, email generation, and Gmail drafts.
                </p>
              </div>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg text-[13px] text-gray-500 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!url.trim()}
                  className="px-5 py-2 rounded-lg bg-stone-blue text-white text-[13px] font-medium hover:bg-stone-blue-dark transition-colors disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed"
                >
                  Start pipeline
                </button>
              </div>
            </>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-6"
            >
              <div className="w-12 h-12 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-3">
                <Zap size={20} className="text-green-600" />
              </div>
              <p className="text-[14px] font-medium text-gray-700">Pipeline started!</p>
              <p className="text-[12px] text-gray-400 mt-1">JD analysis and dual-scout search running...</p>
            </motion.div>
          )}
        </div>
      </motion.div>
    </div>
  )
}
