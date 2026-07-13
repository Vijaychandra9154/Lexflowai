import { useState } from 'react'
import { useRouter } from 'next/router'

export default function Login() {
  const router = useRouter()
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const endpoint = mode === 'login' ? '/api/token' : '/api/signup'
    const body = mode === 'login'
      ? { email, password }
      : { email, password, full_name: fullName }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const text = await res.text()
      let data
      try { data = JSON.parse(text) } catch { throw new Error(text || `Server error (${res.status})`) }
      if (!res.ok) throw new Error(data.detail || `Server error (${res.status})`)
      localStorage.setItem('lexflow_token', data.access_token)
      router.push('/')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <header>
        <div className="logo">⚖️ LexFlow AI <span className="logo-badge">MVP</span></div>
        <div className="header-right"><span>Legal Draft Assistant</span></div>
      </header>

      <div className="main" style={{ maxWidth: 420, paddingTop: 80 }}>
        <div className="page-title" style={{ fontSize: 26 }}>
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </div>
        <div className="page-sub">
          {mode === 'login'
            ? 'Access your LexFlow AI workspace'
            : 'Start drafting legal documents in seconds'}
        </div>

        <div className="card" style={{ marginTop: 24 }}>
          <form onSubmit={submit}>
            {mode === 'signup' && (
              <div style={{ marginBottom: 14 }}>
                <label className="label">Full Name</label>
                <input
                  className="context-input"
                  type="text"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  placeholder="Your full name"
                  required
                />
              </div>
            )}
            <div style={{ marginBottom: 14 }}>
              <label className="label">Email</label>
              <input
                className="context-input"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label className="label">Password</label>
              <input
                className="context-input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                minLength={6}
              />
            </div>

            {error && <div className="error-box" style={{ marginBottom: 14 }}>{error}</div>}

            <button className="btn-generate" type="submit" disabled={loading}>
              {loading && <div className="spinner" />}
              <span>{loading ? 'Please wait...' : mode === 'login' ? 'Sign in' : 'Create account'}</span>
              <div className="gold-line" />
            </button>
          </form>

          <div className="divider" style={{ margin: '20px 0' }} />

          <div style={{ textAlign: 'center', fontSize: 13, color: 'var(--muted)' }}>
            {mode === 'login' ? (
              <>Don&apos;t have an account?{' '}
                <button onClick={() => { setMode('signup'); setError('') }}
                  style={{ background: 'none', border: 'none', color: 'var(--gold)', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 }}>
                  Sign up
                </button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button onClick={() => { setMode('login'); setError('') }}
                  style={{ background: 'none', border: 'none', color: 'var(--gold)', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', fontSize: 13 }}>
                  Sign in
                </button>
              </>
            )}
          </div>
        </div>

        <div className="footer-note" style={{ marginTop: 24, textAlign: 'center' }}>
          By continuing, you agree that AI-generated drafts are for reference only and require review by a qualified advocate.
        </div>
      </div>
    </>
  )
}
