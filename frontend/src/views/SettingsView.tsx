import { useState, useEffect } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { Divider } from '../components/ui/Divider'
import { api } from '../lib/api'
import { useRun } from '../hooks/useRun'
import { useStore } from '../store'
import { UserResponse } from '../types/api'

export function SettingsView() {
  const { data: runData } = useRun()
  const addToast = useStore((s) => s.addToast)
  const [username, setUsername] = useState('')
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [lcValidated, setLcValidated] = useState(false)
  const [currentLc, setCurrentLc] = useState<string | null>(null)
  const [debugDump, setDebugDump] = useState<string | null>(null)
  const [debugLoading, setDebugLoading] = useState(false)

  useEffect(() => {
    api.get<UserResponse>('/auth/me')
      .then((u) => {
        setLcValidated(u.leetcode_validated)
        setCurrentLc(u.leetcode_username)
        setUsername(u.leetcode_username ?? '')
      })
      .catch(() => {})
  }, [])

  const handleSave = async () => {
    if (!username.trim()) return
    setSaving(true)
    try {
      await api.put('/settings/leetcode', { username: username.trim() })
      addToast('LeetCode username saved and validated', 'success')
      setLcValidated(true)
      setCurrentLc(username.trim())
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Validation failed — check username', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleDebug = async () => {
    const target = username.trim() || currentLc
    if (!target) {
      addToast('Enter a username to debug', 'error')
      return
    }
    setDebugLoading(true)
    try {
      const result = await api.get<{ base_url: string; username: string; results: Record<string, unknown> }>(
        `/settings/leetcode/debug?username=${encodeURIComponent(target)}`
      )
      setDebugDump(JSON.stringify(result, null, 2))
    } catch (e: unknown) {
      setDebugDump(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setDebugLoading(false)
    }
  }

  const handleRemove = async () => {
    setRemoving(true)
    try {
      await api.delete('/settings/leetcode')
      addToast('LeetCode removed', 'info')
      setLcValidated(false)
      setCurrentLc(null)
      setUsername('')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Remove failed', 'error')
    } finally {
      setRemoving(false)
    }
  }

  const center = (
    <div className="h-full flex items-start justify-center p-8">
      <div className="w-full max-w-sm">
        <div className="font-display text-display-xs text-ink mb-6">SETTINGS</div>

        <Divider label="LeetCode (Optional)" />

        <div className="flex flex-col gap-3 mt-3">
          <p className="text-xs font-body text-ink3">
            Connect your LeetCode account to count solved problems toward your daily streak.
          </p>

          {lcValidated && currentLc && (
            <div className="flex items-center gap-2 text-xs font-body">
              <div className="w-1.5 h-1.5 rounded-full bg-green" />
              <span className="text-ink2">Connected: {currentLc}</span>
            </div>
          )}

          <label className="text-xs font-body text-ink2" htmlFor="lc-input">
            LeetCode Username
          </label>
          <input
            id="lc-input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            placeholder="your-leetcode-username"
            className="w-full px-3 py-2 text-sm font-body bg-s1 border border-border rounded-btn text-ink placeholder-ink3 focus:outline-none focus:border-border-mid"
          />

          <div className="flex gap-2">
            <Button
              variant="primary"
              onClick={handleSave}
              disabled={saving || !username.trim()}
            >
              {saving ? 'Validating...' : 'Save & Validate'}
            </Button>
            {currentLc && (
              <Button
                variant="secondary"
                onClick={handleRemove}
                disabled={removing}
              >
                {removing ? '...' : 'Remove'}
              </Button>
            )}
          </div>

          <div className="mt-4">
            <Divider label="Debug" />
            <div className="mt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleDebug}
                disabled={debugLoading || (!username.trim() && !currentLc)}
              >
                {debugLoading ? 'Fetching...' : 'Fetch Raw API Response'}
              </Button>
            </div>
            {debugDump && (
              <pre className="mt-2 p-3 bg-ink text-paper/80 text-[10px] font-mono rounded-card overflow-x-auto whitespace-pre-wrap">
                {debugDump}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  )

  return <AppShell user={runData?.user} center={center} />
}
