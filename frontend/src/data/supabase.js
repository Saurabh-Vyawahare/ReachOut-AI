import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL || ''
const key = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

let supabase = null

if (url && key) {
  try {
    supabase = createClient(url, key)
  } catch (e) {
    console.warn('[Supabase] Init failed:', e.message)
  }
}

export { supabase }

export async function signInWithEmail(email, password) {
  if (!supabase) return { data: { user: { email } }, error: null }
  return await supabase.auth.signInWithPassword({ email, password })
}

export async function signUpWithEmail(email, password, name) {
  if (!supabase) return { data: { user: { email } }, error: null }
  return await supabase.auth.signUp({
    email, password,
    options: { data: { full_name: name } },
  })
}

export async function signInWithGoogle() {
  if (!supabase) return { data: null, error: { message: 'Local dev mode' } }
  return await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  })
}

export async function signOut() {
  if (supabase) await supabase.auth.signOut()
}

export async function getSession() {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session
}

export async function getAccessToken() {
  const session = await getSession()
  return session?.access_token || null
}
