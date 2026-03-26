import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Link, Loader2, Check, AlertCircle, MapPin, Briefcase, Building2 } from 'lucide-react'
import { api } from '../data/api'

export default function AddJobModal({ open, onClose, onJobAdded }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async () => {
    if (!url.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await api.addJob(url.trim())
      setResult(data)
      setUrl('')
      // Notify parent to refresh after short delay
      setTimeout(() => {
        onJobAdded?.()
        onClose()
        setResult(null)
      }, 2500)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !loading) handleSubmit()
    if (e.key === 'Escape') onClose()
  }

  if (!open) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div>
              <h2 className="text-lg font-semibold text-gray-800">Add Job</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                Paste a JD link — we'll extract info & find contacts
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X size={18} className="text-gray-400" />
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-5">
            {/* URL input */}
            <div className="relative">
              <Link size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="https://jobs.lever.co/company/position..."
                className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:border-[#4A6FA5] focus:ring-2 focus:ring-[#4A6FA5]/10 transition-all"
                autoFocus
                disabled={loading}
              />
            </div>

            {/* Supported platforms hint */}
            <p className="text-[10px] text-gray-400 mt-2 ml-1">
              Supports Greenhouse, Lever, Ashby, Workday, LinkedIn, and direct company pages
            </p>

            {/* Error */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 mt-3 px-3 py-2 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600"
              >
                <AlertCircle size={14} />
                {error}
              </motion.div>
            )}

            {/* Success result */}
            {result && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 p-4 bg-green-50 border border-green-100 rounded-xl"
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-6 h-6 rounded-full bg-green-500 text-white flex items-center justify-center">
                    <Check size={14} />
                  </div>
                  <span className="text-sm font-semibold text-green-700">Job added!</span>
                </div>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2 text-green-700">
                    <Building2 size={12} /> <span className="font-medium">{result.company}</span>
                  </div>
                  <div className="flex items-center gap-2 text-green-600">
                    <Briefcase size={12} /> {result.job_title}
                  </div>
                  <div className="flex items-center gap-2 text-green-600">
                    <MapPin size={12} /> {result.location || 'Remote'}
                  </div>
                </div>
                <p className="text-[10px] text-green-500 mt-2">
                  Scouts dispatched — contacts will appear in Pipeline shortly
                </p>
              </motion.div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-6 py-4 bg-gray-50/80 border-t border-gray-100">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!url.trim() || loading}
              className="flex items-center gap-2 px-5 py-2 bg-[#4A6FA5] text-white text-sm font-medium rounded-lg hover:bg-[#3d5f8f] disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <><Loader2 size={14} className="animate-spin" /> Analyzing...</>
              ) : (
                'Add & Find Contacts'
              )}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
