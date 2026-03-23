import { CheckCircle2, XCircle } from 'lucide-react'

const NODE_W = 148
const NODE_H = 64
const GAP_X = 36
const GAP_Y = 32

const NODES = [
  { key: 'trigger', label: 'URL trigger', sub: 'Apps Script', x: 0, y: 1, iconColor: '#6366F1', iconBg: '#EEF2FF',
    icon: (
      <g transform="translate(3,3)"><rect x="1" y="3" width="10" height="8" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.3"/><path d="M1 5.5L6 8.5L11 5.5" fill="none" stroke="currentColor" strokeWidth="1.3"/></g>
    )},
  { key: 'jd_analyze', label: 'JD analyzer', sub: 'Haiku', x: 1, y: 1, iconColor: '#8B5CF6', iconBg: '#F5F3FF',
    icon: (
      <g transform="translate(3,3)"><rect x="2" y="1" width="8" height="10" rx="1" fill="none" stroke="currentColor" strokeWidth="1.3"/><path d="M4.5 4.5h3M4.5 7h2" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round"/></g>
    )},
  { key: 'scout_grok', label: 'Grok scout', sub: 'Web + X search', x: 2, y: 0, iconColor: '#EA580C', iconBg: '#FFF7ED',
    icon: (
      <g transform="translate(3,3)"><polygon points="6,1 11,5.5 9,11 3,11 1,5.5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><circle cx="6" cy="6" r="1.5" fill="currentColor"/></g>
    )},
  { key: 'scout_serpapi', label: 'SerpAPI scout', sub: 'Google + Haiku', x: 2, y: 2, iconColor: '#2563EB', iconBg: '#EFF6FF',
    icon: (
      <g transform="translate(3,3)"><circle cx="5.5" cy="5.5" r="4" fill="none" stroke="currentColor" strokeWidth="1.3"/><line x1="8.5" y1="8.5" x2="11" y2="11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></g>
    )},
  { key: 'validator', label: 'Validator', sub: 'Neutral judge', x: 3, y: 1, iconColor: '#0D9488', iconBg: '#F0FDFA',
    icon: (
      <g transform="translate(3,3)"><path d="M6 1L10 4V8.5C10 10 8 11.5 6 12C4 11.5 2 10 2 8.5V4L6 1Z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><path d="M4.2 6.2L5.5 7.5L7.8 5" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></g>
    )},
  { key: 'email_find', label: 'Email finder', sub: 'Hunter + Apollo', x: 4, y: 1, iconColor: '#D97706', iconBg: '#FFFBEB',
    icon: (
      <g transform="translate(3,3)"><circle cx="6" cy="4.5" r="2.5" fill="none" stroke="currentColor" strokeWidth="1.3"/><path d="M1.5 11C1.5 8.5 3.5 7 6 7C8.5 7 10.5 8.5 10.5 11" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></g>
    )},
  { key: 'composer', label: 'Composer', sub: 'Sonnet 4.6', x: 5, y: 1, iconColor: '#DC2626', iconBg: '#FEF2F2',
    icon: (
      <g transform="translate(3,3)"><path d="M8.5 1.5L10.5 3.5L4 10H2V8L8.5 1.5Z" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><line x1="7" y1="3" x2="9" y2="5" stroke="currentColor" strokeWidth="1.1"/></g>
    )},
  { key: 'quality_gate', label: 'Quality gate', sub: 'Score 1-10', x: 6, y: 1, iconColor: '#CA8A04', iconBg: '#FEFCE8',
    icon: (
      <g transform="translate(3,3)"><path d="M6 1L7.5 4.5L11 5L8.5 7.5L9 11L6 9.5L3 11L3.5 7.5L1 5L4.5 4.5Z" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></g>
    )},
  { key: 'dispatcher', label: 'Gmail dispatch', sub: '4 accounts', x: 7, y: 1, iconColor: '#4A6FA5', iconBg: '#EEF3F9',
    icon: (
      <g transform="translate(3,3)"><rect x="1" y="3" width="10" height="7" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.3"/><path d="M1 4L6 7.5L11 4" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></g>
    )},
  { key: 'monitor', label: 'Reply monitor', sub: '3 biz days', x: 8, y: 1, iconColor: '#BE185D', iconBg: '#FDF2F8',
    icon: (
      <g transform="translate(3,3)"><circle cx="6" cy="6" r="5" fill="none" stroke="currentColor" strokeWidth="1.3"/><path d="M6 3V6.5L8 8" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></g>
    )},
]

const EDGES = [
  ['trigger', 'jd_analyze'],
  ['jd_analyze', 'scout_grok'],
  ['jd_analyze', 'scout_serpapi'],
  ['scout_grok', 'validator'],
  ['scout_serpapi', 'validator'],
  ['validator', 'email_find'],
  ['email_find', 'composer'],
  ['composer', 'quality_gate'],
  ['quality_gate', 'dispatcher'],
  ['dispatcher', 'monitor'],
]

function getJobStageStatus(job, stageKey) {
  const s = job.stages
  switch (stageKey) {
    case 'trigger': return 'done'
    case 'jd_analyze': return s.scout.status === 'pending' ? 'pending' : 'done'
    case 'scout_grok':
    case 'scout_serpapi':
      if (s.scout.status === 'pending') return 'pending'
      if (s.scout.status === 'running') return 'running'
      if (s.scout.status === 'error') return 'error'
      return 'done'
    case 'validator': return s.validate.status === 'done' ? 'done' : s.validate.status === 'pending' ? 'pending' : 'running'
    case 'email_find':
      if (s.emails.status === 'pending') return 'pending'
      if (s.emails.status === 'waiting') return 'warning'
      return 'done'
    case 'composer': return s.compose.status === 'done' ? 'done' : s.compose.status === 'pending' ? 'pending' : 'running'
    case 'quality_gate':
      if (s.compose.status === 'pending') return 'pending'
      return 'done'
    case 'dispatcher': return s.drafts.status === 'done' ? 'done' : 'pending'
    case 'monitor':
      if (s.monitor.status === 'pending') return 'pending'
      if (s.monitor.status === 'review') return 'warning'
      if (s.monitor.status === 'sent') return s.monitor.repliedCount > 0 ? 'success' : 'running'
      if (s.monitor.status === 'fu1' || s.monitor.status === 'fu2') return 'running'
      return 'done'
    default: return 'pending'
  }
}

function getStatusDetail(job, stageKey) {
  const s = job.stages
  switch (stageKey) {
    case 'trigger': return new Date(job.addedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    case 'jd_analyze': return s.scout.status !== 'pending' ? 'Skills mapped' : ''
    case 'scout_grok':
      if (s.scout.status === 'error') return 'API timeout'
      if (s.scout.status === 'running') return 'Searching...'
      return s.scout.time || ''
    case 'scout_serpapi':
      if (s.scout.status === 'error') return '0 results'
      if (s.scout.status === 'running') return 'Searching...'
      return s.scout.time || ''
    case 'validator': return s.validate.status === 'done' ? (s.validate.winner === 'grok' ? 'Grok won' : 'SerpAPI won') : ''
    case 'email_find':
      if (s.emails.status === 'waiting') return `${s.emails.found}/${s.emails.total} found`
      if (s.emails.status === 'done') return `${s.emails.found} verified`
      return ''
    case 'composer': return s.compose.status === 'done' ? `${s.compose.score}/10` : ''
    case 'quality_gate':
      if (s.compose.status === 'done' && s.compose.attempts > 1) return `Retried ${s.compose.attempts}x`
      return s.compose.status === 'done' ? 'All passed' : ''
    case 'dispatcher': return s.drafts.status === 'done' ? 'Drafts ready' : ''
    case 'monitor':
      if (s.monitor.repliedCount > 0) return `${s.monitor.repliedCount} reply!`
      if (s.monitor.status === 'fu1') return 'FU1 sent'
      if (s.monitor.status === 'sent') return `${s.monitor.daysLeft}d left`
      if (s.monitor.status === 'review') return 'Review'
      return ''
    default: return ''
  }
}

const STATUS_THEME = {
  done:    { ring: '#86EFAC', badge: '#DCFCE7', badgeText: '#166534', glow: 'rgba(34,197,94,0.08)' },
  running: { ring: '#93C5FD', badge: '#DBEAFE', badgeText: '#1E40AF', glow: 'rgba(59,130,246,0.08)' },
  warning: { ring: '#FDE68A', badge: '#FEF3C7', badgeText: '#92400E', glow: 'rgba(245,158,11,0.08)' },
  error:   { ring: '#FCA5A5', badge: '#FEE2E2', badgeText: '#991B1B', glow: 'rgba(239,68,68,0.08)' },
  pending: { ring: '#E5E7EB', badge: '#F3F4F6', badgeText: '#9CA3AF', glow: 'transparent' },
  success: { ring: '#6EE7B7', badge: '#D1FAE5', badgeText: '#065F46', glow: 'rgba(16,185,129,0.08)' },
}

export default function WorkflowCanvas({ job }) {
  const padX = 28
  const padY = 24
  const totalW = 9 * (NODE_W + GAP_X) - GAP_X + padX * 2
  const totalH = 3 * (NODE_H + GAP_Y) - GAP_Y + padY * 2

  function pos(node) {
    return { x: padX + node.x * (NODE_W + GAP_X), y: padY + node.y * (NODE_H + GAP_Y) }
  }

  const nodeMap = {}
  NODES.forEach(n => { nodeMap[n.key] = { ...n, pos: pos(n) } })

  return (
    <div className="overflow-x-auto pb-1" style={{ scrollbarWidth: 'thin' }}>
      <svg width={totalW} height={totalH} viewBox={`0 0 ${totalW} ${totalH}`} style={{ minWidth: totalW, display: 'block' }}>
        <defs>
          {['#86EFAC','#93C5FD','#E5E7EB','#FDE68A','#FCA5A5'].map((c, i) => (
            <marker key={i} id={`ah${i}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M2 1.5L8 5L2 8.5" fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </marker>
          ))}
          <filter id="nodeShadow" x="-8%" y="-8%" width="116%" height="124%">
            <feDropShadow dx="0" dy="1" stdDeviation="2.5" floodOpacity="0.06"/>
          </filter>
          <filter id="glowGreen"><feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#22c55e" floodOpacity="0.15"/></filter>
          <filter id="glowBlue"><feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#3b82f6" floodOpacity="0.15"/></filter>
          <filter id="glowAmber"><feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#f59e0b" floodOpacity="0.15"/></filter>
          <filter id="glowRed"><feDropShadow dx="0" dy="0" stdDeviation="3" floodColor="#ef4444" floodOpacity="0.15"/></filter>
        </defs>

        {EDGES.map(([fromKey, toKey], i) => {
          const from = nodeMap[fromKey]
          const to = nodeMap[toKey]
          const fromStatus = getJobStageStatus(job, fromKey)
          const toStatus = getJobStageStatus(job, toKey)
          const active = fromStatus === 'done' || fromStatus === 'success'
          const isRunning = toStatus === 'running'
          const isWarn = toStatus === 'warning' || toStatus === 'error'

          const x1 = from.pos.x + NODE_W
          const y1 = from.pos.y + NODE_H / 2
          const x2 = to.pos.x
          const y2 = to.pos.y + NODE_H / 2

          const stroke = isWarn ? '#FDE68A' : active ? '#86EFAC' : isRunning ? '#93C5FD' : '#E5E7EB'
          const markerIdx = isWarn ? 3 : active ? 0 : isRunning ? 1 : 2

          const straight = Math.abs(y1 - y2) < 2
          const d = straight
            ? null
            : `M${x1} ${y1} C${x1 + (x2 - x1) * 0.45} ${y1}, ${x2 - (x2 - x1) * 0.45} ${y2}, ${x2} ${y2}`

          return (
            <g key={i}>
              {straight
                ? <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={stroke} strokeWidth="2" markerEnd={`url(#ah${markerIdx})`} />
                : <path d={d} fill="none" stroke={stroke} strokeWidth="2" markerEnd={`url(#ah${markerIdx})`} />
              }
              {isRunning && straight && (
                <circle r="3" fill="#3b82f6">
                  <animateMotion dur="1.2s" repeatCount="indefinite" path={`M${x1},${y1} L${x2},${y2}`} />
                </circle>
              )}
              {isRunning && !straight && (
                <circle r="3" fill="#3b82f6">
                  <animateMotion dur="1.2s" repeatCount="indefinite" path={d} />
                </circle>
              )}
            </g>
          )
        })}

        {(() => {
          const from = nodeMap['quality_gate']
          const to = nodeMap['composer']
          const hasRetried = job.stages.compose.attempts > 1
          const qgDone = getJobStageStatus(job, 'quality_gate') !== 'pending'
          if (!qgDone) return null
          const x1 = from.pos.x + NODE_W / 2
          const y1 = from.pos.y + NODE_H
          const x2 = to.pos.x + NODE_W / 2
          const y2 = to.pos.y + NODE_H
          const loopY = y1 + 26
          return (
            <g opacity={hasRetried ? 0.9 : 0.25}>
              <path d={`M${x1} ${y1} L${x1} ${loopY} L${x2} ${loopY} L${x2} ${y2}`}
                fill="none" stroke={hasRetried ? '#FDE68A' : '#E5E7EB'} strokeWidth="1.5" strokeDasharray="5 4"
                markerEnd={hasRetried ? 'url(#ah3)' : 'url(#ah2)'}/>
              <rect x={(x1 + x2) / 2 - 28} y={loopY + 4} width="56" height="16" rx="8" fill={hasRetried ? '#FEF3C7' : '#F9FAFB'} stroke={hasRetried ? '#FDE68A' : '#E5E7EB'} strokeWidth="0.5"/>
              <text x={(x1 + x2) / 2} y={loopY + 15} textAnchor="middle" fontSize="8" fontWeight="500" fill={hasRetried ? '#92400E' : '#9CA3AF'} fontFamily="DM Sans, sans-serif">
                Retry &lt; 7
              </text>
            </g>
          )
        })()}

        {NODES.map((node) => {
          const status = getJobStageStatus(job, node.key)
          const detail = getStatusDetail(job, node.key)
          const theme = STATUS_THEME[status] || STATUS_THEME.pending
          const { x, y } = pos(node)
          const isPending = status === 'pending'
          const glowFilter = status === 'done' || status === 'success' ? 'url(#glowGreen)'
            : status === 'running' ? 'url(#glowBlue)'
            : status === 'warning' ? 'url(#glowAmber)'
            : status === 'error' ? 'url(#glowRed)' : 'url(#nodeShadow)'

          return (
            <g key={node.key} opacity={isPending ? 0.4 : 1} style={{ transition: 'opacity 0.3s' }}>
              <rect x={x} y={y} width={NODE_W} height={NODE_H} rx={12} fill="#FFFFFF"
                stroke={theme.ring} strokeWidth={isPending ? 1 : 1.8}
                filter={isPending ? 'url(#nodeShadow)' : glowFilter}/>

              {status === 'running' && (
                <rect x={x} y={y} width={NODE_W} height={NODE_H} rx={12} fill="none"
                  stroke={theme.ring} strokeWidth="2.5" opacity="0.4">
                  <animate attributeName="opacity" values="0.4;0.1;0.4" dur="1.8s" repeatCount="indefinite"/>
                </rect>
              )}

              <circle cx={x + 22} cy={y + NODE_H / 2} r={16} fill={isPending ? '#F9FAFB' : node.iconBg} stroke={isPending ? '#E5E7EB' : node.iconColor} strokeWidth="1" strokeOpacity="0.3"/>

              <g color={isPending ? '#D1D5DB' : node.iconColor} transform={`translate(${x + 10}, ${y + NODE_H / 2 - 8})`}>
                {status === 'running' ? (
                  <g transform="translate(5,2)">
                    <circle cx="6" cy="6" r="4.5" fill="none" stroke={node.iconColor} strokeWidth="1.5" strokeDasharray="10 18" strokeLinecap="round">
                      <animateTransform attributeName="transform" type="rotate" from="0 6 6" to="360 6 6" dur="0.8s" repeatCount="indefinite"/>
                    </circle>
                  </g>
                ) : status === 'error' ? (
                  <g transform="translate(3,2)"><circle cx="6" cy="6" r="5" fill="none" stroke="#EF4444" strokeWidth="1.3"/><path d="M4.2 4.2L7.8 7.8M7.8 4.2L4.2 7.8" stroke="#EF4444" strokeWidth="1.3" strokeLinecap="round"/></g>
                ) : (
                  node.icon
                )}
              </g>

              <text x={x + 44} y={y + 20} fontSize="11.5" fontWeight="600" fill={isPending ? '#9CA3AF' : '#1F2937'} fontFamily="DM Sans, sans-serif">
                {node.label}
              </text>
              <text x={x + 44} y={y + 33} fontSize="9.5" fill={isPending ? '#D1D5DB' : '#9CA3AF'} fontFamily="DM Sans, sans-serif">
                {node.sub}
              </text>

              {detail && !isPending && (
                <g>
                  <rect x={x + 44} y={y + 40} width={detail.length * 5.8 + 12} height={16} rx={8}
                    fill={theme.badge} stroke={theme.ring} strokeWidth="0.5"/>
                  <text x={x + 50} y={y + 51} fontSize="8.5" fontWeight="600" fill={theme.badgeText} fontFamily="DM Sans, sans-serif">
                    {detail}
                  </text>
                </g>
              )}

              {(status === 'done' || status === 'success') && (
                <g transform={`translate(${x + NODE_W - 14}, ${y + 4})`}>
                  <circle cx="6" cy="6" r="7" fill="#DCFCE7" stroke="#86EFAC" strokeWidth="1"/>
                  <path d="M3.5 6L5.5 8L8.5 4.5" fill="none" stroke="#16A34A" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                </g>
              )}

              {status === 'error' && (
                <g transform={`translate(${x + NODE_W - 14}, ${y + 4})`}>
                  <circle cx="6" cy="6" r="7" fill="#FEE2E2" stroke="#FCA5A5" strokeWidth="1"/>
                  <path d="M4 4L8 8M8 4L4 8" fill="none" stroke="#DC2626" strokeWidth="1.3" strokeLinecap="round"/>
                </g>
              )}

              {status === 'warning' && (
                <g transform={`translate(${x + NODE_W - 14}, ${y + 4})`}>
                  <circle cx="6" cy="6" r="7" fill="#FEF3C7" stroke="#FDE68A" strokeWidth="1"/>
                  <path d="M6 4V7" stroke="#D97706" strokeWidth="1.4" strokeLinecap="round"/><circle cx="6" cy="9" r="0.7" fill="#D97706"/>
                </g>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
