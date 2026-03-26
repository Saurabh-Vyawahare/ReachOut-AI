import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Sidebar from './components/Sidebar'
import AddJobModal from './components/AddJobModal'
import Dashboard from './views/Dashboard'
import Pipeline from './views/Pipeline'
import Chat from './views/Chat'
import Landing from './views/Landing'
import Auth from './views/Auth'
import { signOut, getSession } from './data/supabase'

const fade = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 0.3 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
}

export default function App() {
  const [screen, setScreen] = useState('landing')
  const [view, setView] = useState('dashboard')
  const [showAddJob, setShowAddJob] = useState(false)
  const [selectedJobId, setSelectedJobId] = useState(null)
  const [authMode, setAuthMode] = useState('login')
  const [checkingSession, setCheckingSession] = useState(true)

  // Check for existing session on load
  useEffect(() => {
    getSession().then(session => {
      if (session) setScreen('app')
      setCheckingSession(false)
    }).catch(() => setCheckingSession(false))
  }, [])

  const handleNavigate = (target, jobId) => {
    setView(target)
    if (jobId) setSelectedJobId(jobId)
    else setSelectedJobId(null)
  }

  const handleAuth = () => setScreen('app')

  const handleLogout = async () => {
    await signOut()
    setScreen('landing')
    setView('dashboard')
  }

  const handleJobAdded = () => {
    setShowAddJob(false)
    // Switch to pipeline view to see the new job
    setView('pipeline')
  }

  if (checkingSession) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="w-8 h-8 border-2 border-stone-blue border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (screen === 'landing') {
    return (
      <AnimatePresence mode="wait">
        <motion.div key="landing" {...fade}>
          <Landing
            onLogin={() => { setAuthMode('login'); setScreen('auth') }}
            onSignup={() => { setAuthMode('signup'); setScreen('auth') }}
          />
        </motion.div>
      </AnimatePresence>
    )
  }

  if (screen === 'auth') {
    return (
      <AnimatePresence mode="wait">
        <motion.div key="auth" {...fade}>
          <Auth mode={authMode} onBack={() => setScreen('landing')} onAuth={handleAuth} />
        </motion.div>
      </AnimatePresence>
    )
  }

  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar active={view} onNavigate={handleNavigate} onAddJob={() => setShowAddJob(true)} onLogout={handleLogout} />
      <main className="ml-[220px] flex-1 p-6 max-w-[1200px]">
        <AnimatePresence mode="wait">
          {view === 'dashboard' && <Dashboard key="dash" onNavigate={handleNavigate} />}
          {view === 'pipeline' && <Pipeline key="pipe" selectedJobId={selectedJobId} />}
          {view === 'chat' && <Chat key="chat" />}
        </AnimatePresence>
      </main>
      <AddJobModal
        open={showAddJob}
        onClose={() => setShowAddJob(false)}
        onJobAdded={handleJobAdded}
      />
    </div>
  )
}
