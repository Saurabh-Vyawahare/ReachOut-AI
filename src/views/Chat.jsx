import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles, Wifi, WifiOff } from 'lucide-react'
import { api } from '../data/api'

const SUGGESTIONS = [
  'How many replies did I get this week?',
  'What happened with the latest pipeline?',
  'Show me all jobs waiting for emails',
  'Which scout is winning the standoff?',
  'Any follow-ups scheduled for tomorrow?',
]

function ChatMessage({ message, isBot }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      className={`flex gap-3 ${isBot ? '' : 'flex-row-reverse'}`}>
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
        isBot ? 'bg-stone-blue-50 text-stone-blue' : 'bg-gray-100 text-gray-500'}`}>
        {isBot ? <Bot size={14} /> : <User size={14} />}
      </div>
      <div className={`max-w-[85%] rounded-xl px-4 py-3 text-[13px] leading-relaxed ${
        isBot ? 'bg-white border border-border-light text-gray-600' : 'bg-stone-blue text-white'}`}>
        {message.split('\n').map((line, i) => {
          const formatted = line
            .replace(/\*\*(.*?)\*\*/g, '<strong class="font-medium text-gray-800">$1</strong>')
          return <p key={i} className={i > 0 ? 'mt-1.5' : ''} dangerouslySetInnerHTML={{ __html: formatted || '&nbsp;' }} />
        })}
      </div>
    </motion.div>
  )
}

function TypingIndicator() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex gap-3">
      <div className="w-7 h-7 rounded-lg bg-stone-blue-50 text-stone-blue flex items-center justify-center shrink-0"><Bot size={14} /></div>
      <div className="bg-white border border-border-light rounded-xl px-4 py-3 flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </motion.div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([
    { id: 0, text: 'Hey Saurabh! I can answer questions about your pipeline, reply status, standoff results, and more. What do you want to know?', isBot: true },
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isLive, setIsLive] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isTyping])

  // Check if backend is running
  useEffect(() => {
    api.getDashboard().then(() => setIsLive(true)).catch(() => setIsLive(false))
  }, [])

  const handleSend = async (text) => {
    const msg = text || input.trim()
    if (!msg) return
    setMessages(prev => [...prev, { id: Date.now(), text: msg, isBot: false }])
    setInput('')
    setIsTyping(true)

    try {
      if (isLive) {
        const data = await api.chat(msg)
        setMessages(prev => [...prev, { id: Date.now() + 1, text: data.response, isBot: true }])
      } else {
        await new Promise(r => setTimeout(r, 800))
        setMessages(prev => [...prev, {
          id: Date.now() + 1,
          text: `Backend not connected. Start the server with:\n\n\`cd ReachOut-AI && python server.py\`\n\nThen I'll answer with real pipeline data.`,
          isBot: true,
        }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { id: Date.now() + 1, text: `Error: ${e.message}`, isBot: true }])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-800">Assistant</h1>
            <p className="text-sm text-gray-400 mt-0.5">Powered by Claude Haiku — ask about your pipeline</p>
          </div>
          <div className={`flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full ${
            isLive ? 'bg-green-50 text-green-600' : 'bg-gray-100 text-gray-400'}`}>
            {isLive ? <Wifi size={11} /> : <WifiOff size={11} />}
            {isLive ? 'Live' : 'Offline'}
          </div>
        </div>
      </motion.div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-4 pb-4 min-h-0">
        {messages.map(msg => <ChatMessage key={msg.id} message={msg.text} isBot={msg.isBot} />)}
        <AnimatePresence>{isTyping && <TypingIndicator />}</AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {messages.length === 1 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="mb-4">
          <div className="flex items-center gap-1.5 mb-2">
            <Sparkles size={12} className="text-stone-blue" />
            <span className="text-[11px] text-gray-400 font-medium">Suggested questions</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((q, i) => (
              <button key={i} onClick={() => handleSend(q)}
                className="px-3 py-1.5 rounded-full border border-border-light text-[12px] text-gray-500 hover:bg-stone-blue-50 hover:text-stone-blue hover:border-stone-blue-200 transition-all cursor-pointer">
                {q}
              </button>
            ))}
          </div>
        </motion.div>
      )}

      <div className="border-t border-border-light pt-4 pb-2">
        <div className="flex items-center gap-3">
          <input type="text" value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSend()}
            placeholder="Ask about your pipeline, replies, standoff..."
            className="flex-1 px-4 py-2.5 rounded-xl border border-border-light bg-white text-[13px] text-gray-700 placeholder-gray-300 focus:outline-none focus:border-stone-blue-200 focus:ring-2 focus:ring-stone-blue-50 transition-all" />
          <button onClick={() => handleSend()} disabled={!input.trim()}
            className="w-10 h-10 rounded-xl bg-stone-blue text-white flex items-center justify-center hover:bg-stone-blue-dark transition-colors disabled:opacity-30 cursor-pointer disabled:cursor-not-allowed">
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
