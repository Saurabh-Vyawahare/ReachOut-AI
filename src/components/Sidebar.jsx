import { LayoutDashboard, GitBranch, MessageCircle, Plus, Settings } from 'lucide-react'

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'pipeline', label: 'Pipeline', icon: GitBranch },
  { key: 'chat', label: 'Assistant', icon: MessageCircle },
]

export default function Sidebar({ active, onNavigate, onAddJob }) {
  return (
    <aside className="w-[220px] h-screen bg-stone-blue-900 text-white flex flex-col fixed left-0 top-0 z-50">
      <div className="px-5 py-6 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-stone-blue flex items-center justify-center">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 8L7 4L11 8L7 12Z" fill="#fff"/>
            <path d="M8 3L12 7L8 11" stroke="#fff" strokeWidth="1.5" fill="none"/>
          </svg>
        </div>
        <span className="text-[15px] font-medium tracking-tight">ReachOut AI</span>
      </div>

      <button
        onClick={onAddJob}
        className="mx-4 mb-6 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-stone-blue hover:bg-stone-blue-light transition-colors text-sm font-medium cursor-pointer"
      >
        <Plus size={15} />
        Add job URL
      </button>

      <nav className="flex-1 px-3">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon
          const isActive = active === item.key
          return (
            <button
              key={item.key}
              onClick={() => onNavigate(item.key)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg mb-1 text-sm transition-all cursor-pointer
                ${isActive
                  ? 'bg-white/12 text-white font-medium'
                  : 'text-white/55 hover:bg-white/6 hover:text-white/80'
                }`}
            >
              <Icon size={17} strokeWidth={isActive ? 2 : 1.5} />
              {item.label}
            </button>
          )
        })}
      </nav>

      <div className="px-3 pb-5">
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-white/40 hover:bg-white/6 hover:text-white/60 transition-all cursor-pointer">
          <Settings size={17} strokeWidth={1.5} />
          Settings
        </button>
        <div className="mt-4 px-3 text-[11px] text-white/25">
          v2.0 — Multi-agent architecture
        </div>
      </div>
    </aside>
  )
}
