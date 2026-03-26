import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown, ChevronUp, Upload, Send, Pencil, Trash2,
  Plus, Loader2, Check, AlertCircle, RefreshCw, User,
  FileText, X, Zap, Search, Mail, Shield, Inbox, Eye,
  Linkedin, ClipboardPaste, Copy
} from 'lucide-react'
import { api } from '../data/api'

/* ─── Pipeline stage config ─── */
const STAGES = [
  { key: 'jd', label: 'JD Analysis', icon: FileText },
  { key: 'scouts', label: 'Scouts', icon: Search },
  { key: 'contacts', label: 'Contacts', icon: User },
  { key: 'emails', label: 'Emails', icon: Mail },
  { key: 'quality', label: 'Quality', icon: Shield },
  { key: 'drafts', label: 'Drafts', icon: Inbox },
  { key: 'sent', label: 'Sent', icon: Send },
]

function getStageIndex(status) {
  const s = (status || '').toUpperCase()
  if (['FIND', 'SCOUTING'].includes(s)) return 1
  if (['CONTACTS_FOUND', 'CONTACTS'].includes(s)) return 2
  if (s === 'READY') return 3
  if (s === 'COMPOSING') return 3
  if (s === 'QG_CHECK') return 4
  if (s === 'DRAFTS_READY') return 5
  if (['SENT', 'FU1', 'FU2', 'REPLIED', 'DONE'].includes(s)) return 6
  return 0
}

function getStatusColor(status) {
  const s = (status || '').toUpperCase()
  if (s === 'REPLIED') return 'bg-emerald-100 text-emerald-700 border-emerald-200'
  if (['SENT', 'FU1', 'FU2'].includes(s)) return 'bg-green-50 text-green-700 border-green-200'
  if (s === 'DRAFTS_READY') return 'bg-blue-50 text-blue-700 border-blue-200'
  if (['FIND', 'SCOUTING'].includes(s)) return 'bg-amber-50 text-amber-700 border-amber-200'
  if (['CONTACTS_FOUND', 'CONTACTS', 'READY'].includes(s)) return 'bg-purple-50 text-purple-700 border-purple-200'
  return 'bg-gray-50 text-gray-600 border-gray-200'
}

function getStatusMessage(status) {
  const s = (status || '').toUpperCase()
  if (['FIND', 'SCOUTING'].includes(s)) return 'Scouts searching for contacts...'
  if (['CONTACTS_FOUND', 'CONTACTS'].includes(s)) return 'Contacts found — paste emails & hit GO'
  if (s === 'READY') return 'Ready — paste emails & hit GO'
  if (s === 'COMPOSING') return 'Writing personalized emails...'
  if (s === 'QG_CHECK') return 'Quality gate checking...'
  if (s === 'DRAFTS_READY') return 'Drafts ready — review in Gmail'
  if (s === 'SENT') return 'Sent — monitoring replies'
  if (s === 'FU1') return 'Follow-up 1 sent'
  if (s === 'FU2') return 'Follow-up 2 sent'
  if (s === 'REPLIED') return 'Reply received!'
  return 'Pending'
}

function initials(name) {
  if (!name) return '??'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

const AVATAR_COLORS = [
  'bg-blue-100 text-blue-700',
  'bg-emerald-100 text-emerald-700',
  'bg-purple-100 text-purple-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
]

/* ─── Pipeline Progress Bar ─── */
function PipelineProgress({ currentStage, isAnimating }) {
  return (
    <div className="flex items-center gap-0 w-full mb-5">
      {STAGES.map((stage, i) => {
        const Icon = stage.icon
        const completed = i < currentStage
        const active = i === currentStage
        const upcoming = i > currentStage
        return (
          <div key={stage.key} className="flex items-center flex-1">
            <div className="flex flex-col items-center flex-1">
              <motion.div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs transition-all duration-500 ${
                  completed
                    ? 'bg-[#4A6FA5] text-white'
                    : active
                    ? 'bg-[#4A6FA5]/20 text-[#4A6FA5] ring-2 ring-[#4A6FA5] ring-offset-1'
                    : 'bg-gray-100 text-gray-400'
                }`}
                animate={active && isAnimating ? { scale: [1, 1.15, 1] } : {}}
                transition={{ repeat: Infinity, duration: 1.2 }}
              >
                {completed ? <Check size={14} /> : <Icon size={14} />}
              </motion.div>
              <span
                className={`text-[10px] mt-1 font-medium ${
                  completed || active ? 'text-[#4A6FA5]' : 'text-gray-400'
                }`}
              >
                {stage.label}
              </span>
            </div>
            {i < STAGES.length - 1 && (
              <div
                className={`h-0.5 w-full min-w-[12px] mt-[-12px] transition-all duration-500 ${
                  i < currentStage ? 'bg-[#4A6FA5]' : 'bg-gray-200'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ─── Contact Card ─── */
function ContactCard({ contact, index, onUpdate, onRemove, editable }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(contact.name || '')
  const [email, setEmail] = useState(contact.email || '')
  const [saving, setSaving] = useState(false)
  const emailRef = useRef(null)

  useEffect(() => {
    setName(contact.name || '')
    setEmail(contact.email || '')
  }, [contact.name, contact.email])

  const handleSave = async () => {
    setSaving(true)
    try {
      await onUpdate(index, name, email)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  const handleEmailChange = async (e) => {
    const val = e.target.value
    setEmail(val)
    // Auto-save email when it looks complete
    if (val.includes('@') && val.includes('.')) {
      try {
        await onUpdate(index, name, val)
      } catch (err) {
        console.error('Auto-save failed:', err)
      }
    }
  }

  const handleEmailBlur = async () => {
    if (email !== (contact.email || '')) {
      try {
        await onUpdate(index, name, email)
      } catch (err) {
        console.error('Save failed:', err)
      }
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ delay: index * 0.1 }}
      className="bg-white border border-gray-100 rounded-xl p-3 group hover:border-[#4A6FA5]/20 transition-all"
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${AVATAR_COLORS[index % AVATAR_COLORS.length]}`}>
          {initials(name)}
        </div>

        <div className="flex-1 min-w-0">
          {/* Name */}
          {editing ? (
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="text-sm font-semibold text-gray-800 w-full border-b border-[#4A6FA5] outline-none bg-transparent pb-0.5"
              placeholder="Contact name"
              autoFocus
            />
          ) : (
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-semibold text-gray-800 truncate">{name || 'Unknown'}</span>
              <button
                onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(name) }}
                className="p-0.5 hover:bg-gray-100 rounded transition-colors"
                title="Copy name"
              >
                <Copy size={11} className="text-gray-400" />
              </button>
              <a
                href={`https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(name)}`}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="p-0.5 hover:bg-blue-50 rounded transition-colors"
                title={`Search ${name} on LinkedIn`}
              >
                <Linkedin size={12} className="text-[#0077B5]" />
              </a>
              {editable && (
                <button
                  onClick={() => setEditing(true)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-gray-100 rounded"
                >
                  <Pencil size={11} className="text-gray-400" />
                </button>
              )}
            </div>
          )}

          {/* Email input */}
          {editable ? (
            <input
              ref={emailRef}
              value={email}
              onChange={handleEmailChange}
              onBlur={handleEmailBlur}
              onKeyDown={(e) => e.key === 'Enter' && emailRef.current?.blur()}
              className={`text-xs w-full mt-1.5 px-2.5 py-1.5 rounded-lg border outline-none transition-all ${
                email
                  ? 'border-green-200 bg-green-50/50 text-green-700'
                  : 'border-gray-200 bg-gray-50 text-gray-500 focus:border-[#4A6FA5] focus:bg-white'
              }`}
              placeholder="Paste email from Apollo..."
            />
          ) : (
            <span className={`text-xs mt-0.5 block ${email ? 'text-[#4A6FA5]' : 'text-gray-400 italic'}`}>
              {email || 'No email'}
            </span>
          )}

          {/* Edit actions */}
          {editing && (
            <div className="flex gap-1.5 mt-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="text-[10px] px-2.5 py-1 bg-[#4A6FA5] text-white rounded-md hover:bg-[#3d5f8f] disabled:opacity-50 flex items-center gap-1"
              >
                {saving ? <Loader2 size={10} className="animate-spin" /> : <Check size={10} />}
                Save
              </button>
              <button
                onClick={() => { setEditing(false); setName(contact.name || ''); }}
                className="text-[10px] px-2.5 py-1 bg-gray-100 text-gray-600 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {/* Remove button */}
        {editable && !editing && (
          <button
            onClick={() => onRemove(index)}
            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-red-50 rounded text-gray-400 hover:text-red-500"
          >
            <Trash2 size={12} />
          </button>
        )}
      </div>
    </motion.div>
  )
}

/* ─── Resume Drop Zone ─── */
function ResumeDropZone({ file, onFile, onClear }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f && f.name.toLowerCase().endsWith('.pdf')) onFile(f)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => !file && inputRef.current?.click()}
      className={`relative border-2 border-dashed rounded-xl p-3 text-center cursor-pointer transition-all ${
        dragging
          ? 'border-[#4A6FA5] bg-[#4A6FA5]/5'
          : file
          ? 'border-green-200 bg-green-50/50'
          : 'border-gray-200 hover:border-[#4A6FA5]/40 hover:bg-gray-50/50'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
      />
      {file ? (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-green-600" />
            <span className="text-xs font-medium text-green-700 truncate max-w-[180px]">{file.name}</span>
            <span className="text-[10px] text-green-500">({(file.size / 1024).toFixed(0)} KB)</span>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onClear() }}
            className="p-1 hover:bg-red-100 rounded transition-colors"
          >
            <X size={12} className="text-red-500" />
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1 py-1">
          <Upload size={18} className={dragging ? 'text-[#4A6FA5]' : 'text-gray-400'} />
          <span className="text-xs text-gray-500">
            Drop resume PDF here <span className="text-gray-400">or click</span>
          </span>
        </div>
      )}
    </div>
  )
}

/* ─── Single Job Card ─── */
function JobCard({ job, onRefresh }) {
  const [expanded, setExpanded] = useState(false)
  const [contacts, setContacts] = useState(job.contacts || [])
  const [resumeFile, setResumeFile] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [genStage, setGenStage] = useState('')
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [scouting, setScouting] = useState(false)
  const [showApolloInput, setShowApolloInput] = useState(false)
  const [apolloText, setApolloText] = useState('')
  const [analyzingApollo, setAnalyzingApollo] = useState(false)

  const stageIndex = getStageIndex(job.status)
  const isEditable = !['SENT', 'FU1', 'FU2', 'REPLIED', 'DONE'].includes(job.status?.toUpperCase())
  const hasEmails = contacts.some((c) => c.email)
  const allEmailsFilled = contacts.length > 0 && contacts.every((c) => c.email)
  const canGo = contacts.length > 0 && hasEmails && isEditable && !generating
  const needsMoreContacts = contacts.length < 3 && contacts.length > 0 && isEditable

  useEffect(() => {
    setContacts(job.contacts || [])
  }, [job.contacts])

  const handleUpdateContact = async (index, name, email) => {
    try {
      await api.updateContact(job.row, index + 1, name, email)
      setContacts((prev) => prev.map((c, i) => (i === index ? { ...c, name, email } : c)))
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRemoveContact = async (index) => {
    try {
      await api.removeContact(job.row, index + 1)
      setContacts((prev) => prev.filter((_, i) => i !== index))
    } catch (err) {
      setError(err.message)
    }
  }

  const handleAddContact = async () => {
    if (contacts.length >= 3) return
    const name = prompt('Enter contact name:')
    if (!name) return
    try {
      await api.addContact(job.row, name)
      setContacts((prev) => [...prev, { name, email: '' }])
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRunScouts = async () => {
    setScouting(true)
    setError(null)
    try {
      await api.runScouts(job.row)
      setSuccess('Scouts dispatched! Refresh in ~30s to see contacts.')
      setTimeout(() => { setSuccess(null); onRefresh() }, 5000)
    } catch (err) {
      setError(err.message)
    } finally {
      setScouting(false)
    }
  }

  const handleAnalyzeApollo = async () => {
    if (!apolloText.trim()) return
    setAnalyzingApollo(true)
    setError(null)
    try {
      const result = await api.analyzeApollo(job.row, apolloText.trim())
      setSuccess(result.message || 'Contacts added from Apollo list!')
      setApolloText('')
      setShowApolloInput(false)
      setTimeout(() => { setSuccess(null); onRefresh() }, 3000)
    } catch (err) {
      setError(err.message)
    } finally {
      setAnalyzingApollo(false)
    }
  }

  const handleGo = async () => {
    setGenerating(true)
    setError(null)
    setSuccess(null)

    const stages = ['Composing emails...', 'Quality check...', 'Creating drafts...']
    for (const msg of stages) {
      setGenStage(msg)
      await new Promise((r) => setTimeout(r, 800))
    }

    try {
      const result = await api.generateDrafts(job.row, resumeFile)
      setGenStage('')
      setSuccess(result.message || 'Drafts created! Check your Gmail.')
      setTimeout(() => { setSuccess(null); onRefresh() }, 4000)
    } catch (err) {
      setGenStage('')
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <motion.div
      layout
      className={`bg-white rounded-2xl border transition-all overflow-hidden ${
        expanded ? 'border-[#4A6FA5]/20 shadow-lg shadow-[#4A6FA5]/5' : 'border-gray-100 hover:border-gray-200 shadow-sm'
      }`}
    >
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center gap-4 text-left"
      >
        {/* Status dot */}
        <div
          className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
            job.status?.toUpperCase() === 'REPLIED'
              ? 'bg-emerald-500'
              : ['SENT', 'FU1', 'FU2'].includes(job.status?.toUpperCase())
              ? 'bg-green-500'
              : ['FIND', 'SCOUTING'].includes(job.status?.toUpperCase())
              ? 'bg-amber-500 animate-pulse'
              : generating
              ? 'bg-blue-500 animate-pulse'
              : 'bg-gray-300'
          }`}
        />

        {/* Company info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-800">{job.company}</span>
            <span className="text-gray-400">—</span>
            <span className="text-sm text-gray-500 truncate">{job.job_title}</span>
          </div>
          <span className="text-xs text-gray-400">
            {job.location || 'Remote'} · {getStatusMessage(job.status)}
          </span>
        </div>

        {/* Status badge */}
        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${getStatusColor(job.status)}`}>
          {job.status || 'PENDING'}
        </span>

        {/* Contact count */}
        <span className="text-xs text-gray-400">{contacts.length} contacts</span>

        {/* Expand icon */}
        {expanded ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-gray-50">
              {/* Pipeline progress */}
              <div className="pt-4">
                <PipelineProgress currentStage={stageIndex} isAnimating={generating || scouting} />
              </div>

              {/* Error/Success banners */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="flex items-center gap-2 px-3 py-2 mb-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600"
                  >
                    <AlertCircle size={14} />
                    {error}
                    <button onClick={() => setError(null)} className="ml-auto"><X size={12} /></button>
                  </motion.div>
                )}
                {success && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="flex items-center gap-2 px-3 py-2 mb-3 bg-green-50 border border-green-100 rounded-lg text-xs text-green-600"
                  >
                    <Check size={14} />
                    {success}
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
                {/* Left: Details + Actions */}
                <div className="lg:col-span-2 space-y-4">
                  {/* Job details */}
                  <div className="bg-gray-50/80 rounded-xl p-4 space-y-2.5">
                    <DetailRow label="Status" value={job.status} />
                    <DetailRow label="Gmail account" value={job.gmail_used || 'Auto-assigned'} />
                    <DetailRow label="Sent date" value={job.sent_date || '—'} />
                    <DetailRow label="Scout winner" value={job.scout_winner || '—'} />
                    <DetailRow label="Quality score" value={job.quality_score || '—'} />
                    <DetailRow label="Notes" value={job.notes || '—'} />
                  </div>

                  {/* Resume upload */}
                  {isEditable && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 mb-1.5 block">Resume (attached to drafts)</label>
                      <ResumeDropZone file={resumeFile} onFile={setResumeFile} onClear={() => setResumeFile(null)} />
                    </div>
                  )}

                  {/* Action buttons */}
                  {isEditable && (
                    <div className="space-y-2">
                      {/* Run scouts button (if no contacts yet) */}
                      {contacts.length === 0 && (
                        <button
                          onClick={handleRunScouts}
                          disabled={scouting}
                          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-500 text-white rounded-xl font-medium text-sm hover:bg-amber-600 disabled:opacity-60 transition-all"
                        >
                          {scouting ? (
                            <><Loader2 size={16} className="animate-spin" /> Scouts searching...</>
                          ) : (
                            <><Search size={16} /> Find Contacts</>
                          )}
                        </button>
                      )}

                      {/* Apollo paste area - when Grok found < 3 contacts */}
                      {needsMoreContacts && (
                        <div className="space-y-2">
                          <button
                            onClick={() => setShowApolloInput(!showApolloInput)}
                            className="w-full flex items-center justify-center gap-2 px-4 py-2 border border-dashed border-[#4A6FA5]/30 text-[#4A6FA5] rounded-xl text-sm hover:bg-[#4A6FA5]/5 transition-all"
                          >
                            <ClipboardPaste size={14} />
                            {showApolloInput ? 'Hide' : `Paste Apollo contacts (need ${3 - contacts.length} more)`}
                          </button>
                          {showApolloInput && (
                            <div className="space-y-2">
                              <textarea
                                value={apolloText}
                                onChange={(e) => setApolloText(e.target.value)}
                                placeholder="Paste the Apollo.io contact list here — Claude will pick the best matches for this role..."
                                className="w-full h-32 px-3 py-2 border border-gray-200 rounded-xl text-xs focus:outline-none focus:border-[#4A6FA5] focus:ring-2 focus:ring-[#4A6FA5]/10 resize-none"
                              />
                              <button
                                onClick={handleAnalyzeApollo}
                                disabled={!apolloText.trim() || analyzingApollo}
                                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-[#4A6FA5] text-white rounded-xl text-sm hover:bg-[#3d5f8f] disabled:opacity-50 transition-all"
                              >
                                {analyzingApollo ? (
                                  <><Loader2 size={14} className="animate-spin" /> Analyzing...</>
                                ) : (
                                  <><Search size={14} /> Find Best Contacts</>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      )}

                      {/* GO button */}
                      {contacts.length > 0 && (
                        <button
                          onClick={handleGo}
                          disabled={!canGo}
                          className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold text-sm transition-all ${
                            canGo
                              ? 'bg-[#4A6FA5] text-white hover:bg-[#3d5f8f] shadow-md shadow-[#4A6FA5]/20 hover:shadow-lg'
                              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                          }`}
                        >
                          {generating ? (
                            <><Loader2 size={16} className="animate-spin" /> {genStage}</>
                          ) : (
                            <><Zap size={16} /> {allEmailsFilled ? 'GO — Generate Drafts' : 'Paste emails to enable'}</>
                          )}
                        </button>
                      )}

                      {!allEmailsFilled && contacts.length > 0 && (
                        <p className="text-[10px] text-gray-400 text-center">
                          Paste at least one email from Apollo to enable GO
                        </p>
                      )}
                    </div>
                  )}
                </div>

                {/* Right: Contacts */}
                <div className="lg:col-span-3">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-700">Contacts</h3>
                    {isEditable && contacts.length < 3 && (
                      <button
                        onClick={handleAddContact}
                        className="flex items-center gap-1 text-[11px] text-[#4A6FA5] hover:text-[#3d5f8f] font-medium"
                      >
                        <Plus size={12} /> Add contact
                      </button>
                    )}
                  </div>

                  {contacts.length === 0 ? (
                    <div className="text-center py-8 bg-gray-50/50 rounded-xl border border-dashed border-gray-200">
                      <User size={24} className="mx-auto text-gray-300 mb-2" />
                      <p className="text-sm text-gray-400">No contacts yet</p>
                      <p className="text-xs text-gray-400 mt-1">
                        {['FIND', 'SCOUTING'].includes(job.status?.toUpperCase())
                          ? 'Scouts are searching...'
                          : 'Click "Find Contacts" or add manually'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <AnimatePresence mode="popLayout">
                        {contacts.map((contact, i) => (
                          <ContactCard
                            key={`${contact.name}-${i}`}
                            contact={contact}
                            index={i}
                            editable={isEditable}
                            onUpdate={handleUpdateContact}
                            onRemove={handleRemoveContact}
                          />
                        ))}
                      </AnimatePresence>
                    </div>
                  )}

                  {/* Reply info */}
                  {job.reply_from && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="mt-3 p-3 bg-emerald-50 border border-emerald-100 rounded-xl"
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-emerald-500 text-white flex items-center justify-center">
                          <Check size={12} />
                        </div>
                        <div>
                          <span className="text-xs font-semibold text-emerald-700">Reply from</span>
                          <span className="text-xs text-emerald-600 ml-1">{job.reply_from}</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function DetailRow({ label, value }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-gray-400">{label}</span>
      <span className="text-gray-700 font-medium text-right truncate max-w-[60%]">{value}</span>
    </div>
  )
}

/* ─── Main Pipeline View ─── */
export default function Pipeline() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const pollRef = useRef(null)

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.getPipeline()
      setJobs(data.jobs || [])
    } catch (err) {
      console.error('Pipeline fetch failed:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchJobs()
    // Poll every 15 seconds for updates
    pollRef.current = setInterval(fetchJobs, 15000)
    return () => clearInterval(pollRef.current)
  }, [fetchJobs])

  const filtered = jobs.filter((j) => {
    const s = (j.status || '').toUpperCase()
    if (filter === 'all') return true
    if (filter === 'active') return !['SENT', 'FU1', 'FU2', 'REPLIED', 'DONE'].includes(s)
    if (filter === 'sent') return ['SENT', 'FU1', 'FU2'].includes(s)
    if (filter === 'replied') return s === 'REPLIED'
    return true
  })

  const counts = {
    all: jobs.length,
    active: jobs.filter((j) => !['SENT', 'FU1', 'FU2', 'REPLIED', 'DONE'].includes(j.status?.toUpperCase())).length,
    sent: jobs.filter((j) => ['SENT', 'FU1', 'FU2'].includes(j.status?.toUpperCase())).length,
    replied: jobs.filter((j) => j.status?.toUpperCase() === 'REPLIED').length,
  }

  return (
    <div>
      {/* Header */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">Pipeline</h1>
            <p className="text-sm text-gray-400 mt-0.5">
              Interactive workflow — find contacts, paste emails, generate drafts
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchJobs}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw size={16} className="text-gray-400" />
            </button>
            <span className="text-xs text-[#4A6FA5] font-medium bg-[#4A6FA5]/5 px-2.5 py-1 rounded-full">
              ◆ {jobs.length} jobs
            </span>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 mt-4 bg-gray-100/80 p-1 rounded-xl w-fit">
          {[
            { key: 'all', label: 'All' },
            { key: 'active', label: 'Active' },
            { key: 'sent', label: 'Sent' },
            { key: 'replied', label: 'Replied' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-all ${
                filter === key
                  ? 'bg-white text-[#4A6FA5] shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label} <span className="text-gray-400 ml-0.5">({counts[key]})</span>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Job list */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-[#4A6FA5]" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Inbox size={32} className="mx-auto mb-2" />
          <p className="text-sm">No jobs in this view</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((job) => (
            <JobCard key={job.id} job={job} onRefresh={fetchJobs} />
          ))}
        </div>
      )}
    </div>
  )
}
