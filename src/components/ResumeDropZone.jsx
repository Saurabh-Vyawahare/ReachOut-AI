import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { FileUp, CheckCircle2, File, Loader2 } from 'lucide-react'

export default function ResumeDropZone({ job }) {
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [attached, setAttached] = useState(false)
  const inputRef = useRef(null)

  const draftsReady = job.stages.drafts.status === 'done'
  const contactCount = job.contacts.filter(c => c.email).length

  const handleFile = (f) => {
    if (!f || !f.name.toLowerCase().endsWith('.pdf')) return
    setFile(f)
    setUploading(true)
    setTimeout(() => {
      setUploading(false)
      setAttached(true)
    }, 1800)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    handleFile(f)
  }

  const onDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  if (!draftsReady) return null

  return (
    <div className="mt-3">
      <div className="text-[11px] font-medium text-gray-400 mb-2 flex items-center gap-1.5">
        <FileUp size={12} />
        Resume attachment
      </div>

      {!attached ? (
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={() => setDragOver(false)}
          onClick={() => inputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all ${
            dragOver
              ? 'border-stone-blue bg-stone-blue-50/50 scale-[1.01]'
              : uploading
              ? 'border-amber-300 bg-amber-50/30'
              : 'border-gray-200 hover:border-stone-blue-200 hover:bg-stone-blue-50/20'
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => handleFile(e.target.files[0])}
          />

          {uploading ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-2">
              <Loader2 size={20} className="mx-auto text-stone-blue animate-spin mb-2" />
              <p className="text-[12px] text-stone-blue font-medium">
                Attaching to {contactCount} draft{contactCount !== 1 ? 's' : ''}...
              </p>
              <p className="text-[11px] text-gray-400 mt-0.5">{file?.name}</p>
            </motion.div>
          ) : (
            <>
              <FileUp size={18} className={`mx-auto mb-1.5 ${dragOver ? 'text-stone-blue' : 'text-gray-300'}`} />
              <p className="text-[12px] text-gray-500">
                {dragOver ? 'Drop resume here' : 'Drag resume PDF or click to browse'}
              </p>
              <p className="text-[10px] text-gray-300 mt-0.5">
                Attaches to all {contactCount} {job.company} drafts
              </p>
            </>
          )}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2.5 p-3 rounded-xl bg-green-50 border border-green-200"
        >
          <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center shrink-0">
            <CheckCircle2 size={15} className="text-green-600" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[12px] font-medium text-green-700 flex items-center gap-1.5">
              <File size={11} />
              {file?.name}
            </div>
            <div className="text-[11px] text-green-600 mt-0.5">
              Attached to {contactCount} draft{contactCount !== 1 ? 's' : ''} for {job.company}
            </div>
          </div>
          <button
            onClick={() => { setFile(null); setAttached(false) }}
            className="text-[11px] text-green-600 hover:text-green-800 font-medium cursor-pointer"
          >
            Replace
          </button>
        </motion.div>
      )}
    </div>
  )
}
