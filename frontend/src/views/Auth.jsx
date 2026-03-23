import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, ArrowLeft, Mail, Lock, User, Loader2 } from 'lucide-react'
import { signInWithEmail, signUpWithEmail, signInWithGoogle } from '../data/supabase'

const container = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.15 } } }
const item = { hidden: { y: 16, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { duration: 0.45, ease: 'easeOut' } } }

function GlassInput({ icon: Icon, ...props }) {
  return (
    <div className="relative rounded-xl border border-gray-200 bg-gray-50/50 transition-colors focus-within:border-stone-blue/40 focus-within:bg-stone-blue-50/20">
      <Icon size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-300" />
      <input {...props} className="w-full bg-transparent text-[14px] text-gray-700 py-3.5 pl-11 pr-4 rounded-xl focus:outline-none placeholder-gray-400" />
    </div>
  )
}

function PasswordInput({ ...props }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative rounded-xl border border-gray-200 bg-gray-50/50 transition-colors focus-within:border-stone-blue/40 focus-within:bg-stone-blue-50/20">
      <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-300" />
      <input {...props} type={show ? 'text' : 'password'} className="w-full bg-transparent text-[14px] text-gray-700 py-3.5 pl-11 pr-12 rounded-xl focus:outline-none placeholder-gray-400" />
      <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 transition-colors cursor-pointer">
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48">
      <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/>
      <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"/>
      <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0124 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/>
      <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 01-4.087 5.571l6.19 5.238C36.971 39.801 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/>
    </svg>
  )
}

const STATS = [
  { value: '~40s', label: 'URL to drafts' },
  { value: '32%', label: 'Reply rate' },
  { value: '7', label: 'AI agents' },
]

export default function Auth({ mode: initialMode = 'login', onBack, onAuth }) {
  const [mode, setMode] = useState(initialMode)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    const form = new FormData(e.target)
    const email = form.get('email')
    const password = form.get('password')
    const name = form.get('name')

    try {
      if (mode === 'login') {
        const { error } = await signInWithEmail(email, password)
        if (error) { setError(error.message); setLoading(false); return }
      } else {
        const { error } = await signUpWithEmail(email, password, name)
        if (error) { setError(error.message); setLoading(false); return }
      }
      onAuth?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogle = async () => {
    setError('')
    const { error } = await signInWithGoogle()
    if (error) {
      // If Supabase not configured, just proceed (local dev)
      if (error.message.includes('not configured')) {
        onAuth?.()
      } else {
        setError(error.message)
      }
    }
  }

  return (
    <div className="min-h-screen flex">
      <div className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          <motion.div variants={container} initial="hidden" animate="visible" key={mode}>
            <motion.button variants={item} onClick={onBack}
              className="flex items-center gap-1.5 text-[13px] text-gray-400 hover:text-gray-600 transition-colors mb-8 cursor-pointer">
              <ArrowLeft size={14} /> Back to home
            </motion.button>

            <motion.div variants={item} className="flex items-center gap-2.5 mb-8">
              <div className="w-9 h-9 rounded-lg bg-stone-blue flex items-center justify-center">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M3 8L7 4L11 8L7 12Z" fill="#fff"/>
                  <path d="M8 3L12 7L8 11" stroke="#fff" strokeWidth="1.5" fill="none"/>
                </svg>
              </div>
              <span className="text-[16px] font-semibold text-gray-800 tracking-tight">ReachOut AI</span>
            </motion.div>

            <motion.h1 variants={item} className="text-3xl font-semibold text-gray-900 tracking-tight">
              {mode === 'login' ? 'Welcome back' : 'Create your account'}
            </motion.h1>
            <motion.p variants={item} className="mt-2 text-[14px] text-gray-500">
              {mode === 'login'
                ? 'Sign in to access your outreach dashboard'
                : 'Start automating your cold outreach in minutes'}
            </motion.p>

            <motion.div variants={item} className="mt-8">
              <button onClick={handleGoogle}
                className="w-full flex items-center justify-center gap-3 border border-gray-200 rounded-xl py-3.5 text-[14px] text-gray-700 font-medium hover:bg-gray-50 transition-colors cursor-pointer">
                <GoogleIcon /> Continue with Google
              </button>
            </motion.div>

            {error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="mt-3 p-3 rounded-xl bg-red-50 border border-red-100 text-[13px] text-red-600">
                {error}
              </motion.div>
            )}

            <motion.div variants={item} className="relative my-6">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
              <div className="relative flex justify-center"><span className="px-3 text-[12px] text-gray-400 bg-white">Or continue with email</span></div>
            </motion.div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <AnimatePresence mode="wait">
                {mode === 'signup' && (
                  <motion.div key="name" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}>
                    <GlassInput icon={User} type="text" placeholder="Full name" name="name" />
                  </motion.div>
                )}
              </AnimatePresence>
              <motion.div variants={item}><GlassInput icon={Mail} type="email" placeholder="Email address" name="email" /></motion.div>
              <motion.div variants={item}><PasswordInput placeholder="Password" name="password" /></motion.div>

              {mode === 'login' && (
                <motion.div variants={item} className="flex items-center justify-between text-[13px]">
                  <label className="flex items-center gap-2 cursor-pointer text-gray-600">
                    <input type="checkbox" className="rounded border-gray-300 accent-stone-blue" />
                    Keep me signed in
                  </label>
                  <button type="button" className="text-stone-blue hover:underline cursor-pointer">Forgot password?</button>
                </motion.div>
              )}

              <motion.div variants={item}>
                <button type="submit" disabled={loading}
                  className="w-full py-3.5 rounded-xl bg-stone-blue text-white font-medium text-[14px] hover:bg-stone-blue-dark transition-colors cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2">
                  {loading && <Loader2 size={16} className="animate-spin" />}
                  {mode === 'login' ? 'Sign in' : 'Create account'}
                </button>
              </motion.div>
            </form>

            <motion.p variants={item} className="mt-6 text-center text-[13px] text-gray-500">
              {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
              <button onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
                className="text-stone-blue font-medium hover:underline cursor-pointer">
                {mode === 'login' ? 'Create one' : 'Sign in'}
              </button>
            </motion.p>
          </motion.div>
        </div>
      </div>

      <div className="hidden lg:block flex-1 relative p-4">
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.2 }}
          className="absolute inset-4 rounded-3xl overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #1E3350 0%, #2E4A70 40%, #4A6FA5 100%)',
          }}
        >
          <div className="absolute inset-0 opacity-[0.04]" style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
            backgroundSize: '24px 24px',
          }} />

          <div className="relative h-full flex flex-col items-center justify-center p-12 text-white">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="text-center"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/10 text-[11px] font-medium text-white/80 mb-6">
                <Zap size={11} /> Multi-agent architecture
              </div>
              <h2 className="text-2xl font-semibold tracking-tight">7 AI agents.<br />Zero hallucinations.</h2>
              <p className="mt-3 text-[14px] text-white/60 max-w-sm leading-relaxed">
                Dual-scout standoff, quality gates, and business-day follow-ups — all automated from a single URL.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="mt-10 flex gap-4"
            >
              {STATS.map((s, i) => (
                <div key={i} className="px-5 py-3.5 rounded-2xl bg-white/8 border border-white/10 text-center backdrop-blur-sm">
                  <div className="text-xl font-semibold">{s.value}</div>
                  <div className="text-[11px] text-white/50 mt-0.5">{s.label}</div>
                </div>
              ))}
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1 }}
              className="mt-10 flex items-center gap-3"
            >
              <div className="flex -space-x-2">
                {[
                  'bg-amber-400', 'bg-rose-400', 'bg-emerald-400', 'bg-blue-400'
                ].map((bg, i) => (
                  <div key={i} className={`w-7 h-7 rounded-full ${bg} border-2 border-stone-blue-800 flex items-center justify-center text-[9px] font-bold text-white`}>
                    {['SV', 'AI', 'ML', 'DS'][i]}
                  </div>
                ))}
              </div>
              <p className="text-[12px] text-white/50">Trusted by data scientists</p>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
