import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Zap, ShieldCheck, Mail, BarChart3, ArrowRight } from 'lucide-react'

function GithubIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
    </svg>
  )
}

const container = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.12, delayChildren: 0.3 } } }
const item = { hidden: { y: 24, opacity: 0 }, visible: { y: 0, opacity: 1, transition: { duration: 0.6, ease: 'easeOut' } } }

const FEATURES = [
  { icon: Zap, title: 'Dual-scout standoff', desc: 'Grok and SerpAPI compete in parallel. A neutral validator picks the best contacts — no hallucinations.', color: '#EA580C' },
  { icon: ShieldCheck, title: 'Quality gate', desc: 'Every email scored 1-10 by AI. Below 7? Auto-rejected and regenerated with specific feedback.', color: '#0D9488' },
  { icon: Mail, title: 'Smart dispatch', desc: 'Round-robin across 4 Gmail accounts with daily caps. Anti-spam by design.', color: '#4A6FA5' },
  { icon: BarChart3, title: 'Live dashboard', desc: 'Pipeline status, standoff tracker, Gmail health, quality scores, and reply monitoring — all real-time.', color: '#8B5CF6' },
]

const WORKFLOW_NODES = [
  { label: 'JD URL', color: '#6366F1', x: 0 },
  { label: 'JD Analyzer', color: '#8B5CF6', x: 1 },
  { label: 'Dual Scouts', color: '#EA580C', x: 2 },
  { label: 'Validator', color: '#0D9488', x: 3 },
  { label: 'Composer', color: '#DC2626', x: 4 },
  { label: 'Gmail', color: '#4A6FA5', x: 5 },
]

function MiniWorkflow() {
  const [activeIdx, setActiveIdx] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setActiveIdx(i => (i + 1) % WORKFLOW_NODES.length), 1200)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex items-center gap-2 overflow-x-auto py-2 px-1">
      {WORKFLOW_NODES.map((n, i) => (
        <div key={i} className="flex items-center gap-2 shrink-0">
          <div className={`px-3 py-2 rounded-xl border text-[11px] font-medium transition-all duration-500 ${
            i <= activeIdx
              ? 'bg-white border-gray-200 shadow-sm text-gray-700'
              : 'bg-gray-50 border-gray-100 text-gray-300'
          }`}
            style={i <= activeIdx ? { borderColor: n.color + '40', boxShadow: `0 0 12px ${n.color}15` } : {}}
          >
            <div className="w-1.5 h-1.5 rounded-full mb-1 mx-auto transition-colors duration-500"
              style={{ background: i <= activeIdx ? n.color : '#E5E7EB' }} />
            {n.label}
          </div>
          {i < WORKFLOW_NODES.length - 1 && (
            <div className="w-6 h-[1.5px] transition-colors duration-500"
              style={{ background: i < activeIdx ? n.color + '60' : '#E5E7EB' }} />
          )}
        </div>
      ))}
    </div>
  )
}

export default function Landing({ onLogin, onSignup }) {
  return (
    <div className="min-h-screen bg-white overflow-hidden">
      <motion.header
        initial={{ y: -40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 md:px-12 h-16 bg-white/80 backdrop-blur-sm border-b border-gray-100"
      >
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-stone-blue flex items-center justify-center">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8L7 4L11 8L7 12Z" fill="#fff"/>
              <path d="M8 3L12 7L8 11" stroke="#fff" strokeWidth="1.5" fill="none"/>
            </svg>
          </div>
          <span className="text-[15px] font-semibold text-gray-800 tracking-tight">ReachOut AI</span>
        </div>
        <nav className="hidden md:flex items-center gap-6">
          <a href="#features" className="text-sm text-gray-500 hover:text-gray-800 transition-colors">Features</a>
          <a href="#workflow" className="text-sm text-gray-500 hover:text-gray-800 transition-colors">How it works</a>
          <a href="https://github.com/Saurabh-Vyawahare/ReachOut-AI" target="_blank" rel="noreferrer" className="text-sm text-gray-500 hover:text-gray-800 transition-colors flex items-center gap-1.5">
            <GithubIcon size={14} /> GitHub
          </a>
        </nav>
        <div className="flex items-center gap-3">
          <button onClick={onLogin} className="text-sm text-gray-600 hover:text-gray-800 transition-colors cursor-pointer">Sign in</button>
          <button onClick={onSignup}
            className="text-sm font-medium text-white bg-stone-blue hover:bg-stone-blue-dark px-4 py-2 rounded-lg transition-colors cursor-pointer">
            Get started
          </button>
        </div>
      </motion.header>

      <section className="pt-32 pb-20 px-6 md:px-12 max-w-5xl mx-auto">
        <motion.div variants={container} initial="hidden" animate="visible" className="text-center">
          <motion.div variants={item} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-stone-blue-50 border border-stone-blue-100 text-stone-blue text-[12px] font-medium mb-6">
            <Zap size={12} /> Multi-agent cold email automation
          </motion.div>

          <motion.h1 variants={item} className="text-4xl md:text-6xl font-semibold text-gray-900 leading-tight tracking-tight">
            Paste a job URL.
            <br />
            <span className="text-stone-blue">Get personalized drafts.</span>
          </motion.h1>

          <motion.p variants={item} className="mt-6 text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">
            ReachOut AI finds the right contacts, writes JD-matched emails, and creates Gmail drafts — all from a single URL. Dual-scout standoff ensures zero hallucinated contacts.
          </motion.p>

          <motion.div variants={item} className="mt-10 flex items-center justify-center gap-4">
            <button onClick={onSignup}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-stone-blue text-white font-medium hover:bg-stone-blue-dark transition-colors cursor-pointer">
              Start for free <ArrowRight size={16} />
            </button>
            <a href="https://github.com/Saurabh-Vyawahare/ReachOut-AI" target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-gray-200 text-gray-600 font-medium hover:bg-gray-50 transition-colors">
              <GithubIcon size={16} /> View source
            </a>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.7 }}
          id="workflow"
          className="mt-16 rounded-2xl border border-gray-200 bg-gray-50/50 p-6"
        >
          <div className="text-[11px] font-medium text-gray-400 uppercase tracking-widest mb-4">Live pipeline preview</div>
          <MiniWorkflow />
          <div className="mt-4 grid grid-cols-3 gap-3 text-center text-[12px]">
            <div className="p-3 rounded-xl bg-white border border-gray-100">
              <div className="text-lg font-semibold text-gray-800">~40s</div>
              <div className="text-gray-400 mt-0.5">URL to drafts</div>
            </div>
            <div className="p-3 rounded-xl bg-white border border-gray-100">
              <div className="text-lg font-semibold text-success">32%</div>
              <div className="text-gray-400 mt-0.5">Reply rate</div>
            </div>
            <div className="p-3 rounded-xl bg-white border border-gray-100">
              <div className="text-lg font-semibold text-stone-blue">$0.03</div>
              <div className="text-gray-400 mt-0.5">Per company</div>
            </div>
          </div>
        </motion.div>
      </section>

      <section id="features" className="py-20 px-6 md:px-12 bg-gray-50/50 border-t border-gray-100">
        <div className="max-w-5xl mx-auto">
          <motion.div initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-semibold text-gray-900 tracking-tight">Built different</h2>
            <p className="mt-3 text-gray-500 max-w-lg mx-auto">Not another mail merge. A multi-agent system where AI agents validate each other's work.</p>
          </motion.div>
          <div className="grid md:grid-cols-2 gap-4">
            {FEATURES.map((f, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="p-5 rounded-2xl bg-white border border-gray-100 hover:border-gray-200 transition-colors"
              >
                <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
                  style={{ background: f.color + '12', color: f.color }}>
                  <f.icon size={18} />
                </div>
                <h3 className="text-[15px] font-medium text-gray-800">{f.title}</h3>
                <p className="mt-1.5 text-[13px] text-gray-500 leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 px-6 md:px-12 text-center">
        <h2 className="text-2xl md:text-3xl font-semibold text-gray-900 tracking-tight">Ready to automate your outreach?</h2>
        <p className="mt-3 text-gray-500">Paste a URL. Get drafts. Send. Get replies.</p>
        <button onClick={onSignup}
          className="mt-8 inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-stone-blue text-white font-medium hover:bg-stone-blue-dark transition-colors cursor-pointer text-[15px]">
          Get started free <ArrowRight size={16} />
        </button>
      </section>

      <footer className="border-t border-gray-100 py-6 px-6 md:px-12 text-center text-[12px] text-gray-400">
        Built by Saurabh Vyawahare — ReachOut AI v2.0
      </footer>
    </div>
  )
}
