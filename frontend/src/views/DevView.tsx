import { useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { Divider } from '../components/ui/Divider'
import { api } from '../lib/api'
import { useRun } from '../hooks/useRun'
import { useQueryClient } from '@tanstack/react-query'
import { useStore } from '../store'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <Divider label={title} />
      <div className="flex flex-wrap gap-2 mt-2">{children}</div>
    </div>
  )
}

export function DevView() {
  const { data: runData } = useRun()
  const qc = useQueryClient()
  const addToast = useStore((s) => s.addToast)
  const [stateDump, setStateDump] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const action = async (path: string, body?: unknown, method: 'POST' | 'GET' = 'POST') => {
    setLoading(true)
    try {
      const result = method === 'GET'
        ? await api.get(path)
        : await api.post(path, body)
      addToast('Done', 'success')
      qc.invalidateQueries()
      return result
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Error', 'error')
    } finally {
      setLoading(false)
    }
  }

  const getState = async () => {
    setLoading(true)
    try {
      const result = await api.get('/test/state')
      setStateDump(JSON.stringify(result, null, 2))
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Error', 'error')
    } finally {
      setLoading(false)
    }
  }

  const center = (
    <div className="h-full overflow-y-auto p-6">
      <div className="font-display text-display-xs text-ink mb-2">DEV PANEL</div>
      <p className="text-xs font-body text-ink3 mb-4">Test helpers. Debug only. Remove before production.</p>

      <Section title="Run">
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/process-day', { commits: 1 })} disabled={loading}>
          +1 Day (commit)
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/process-day', { commits: 0 })} disabled={loading}>
          +1 Day (miss)
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/force-crash')} disabled={loading}>
          Force Crash
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/skip-to-completion')} disabled={loading}>
          Skip to Completion
        </Button>
      </Section>

      <Section title="Fast Forward">
        {[5, 14, 30].map((n) => (
          <Button
            key={n}
            size="sm"
            variant="secondary"
            onClick={() => action('/test/run/fast-forward', { days: n })}
            disabled={loading}
          >
            FF {n} days
          </Button>
        ))}
      </Section>

      <Section title="Give Items">
        <Button size="sm" variant="secondary" onClick={() => action('/test/user/give-points', { amount: 500 })} disabled={loading}>
          +500 pts
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/user/give-points', { amount: 5000 })} disabled={loading}>
          +5k pts
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/user/give-gas', { amount: 3 })} disabled={loading}>
          +3 gas
        </Button>
        {['bronze', 'silver', 'gold', 'platinum'].map((tier) => (
          <Button
            key={tier}
            size="sm"
            variant="secondary"
            onClick={() => action('/test/inventory/give-lootbox', { tier, count: 1 })}
            disabled={loading}
          >
            {tier.charAt(0).toUpperCase() + tier.slice(1)} box
          </Button>
        ))}
      </Section>

      <Section title="State">
        <Button size="sm" variant="primary" onClick={getState} disabled={loading}>
          Dump State
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            if (window.confirm('Reset all game data?')) action('/test/user/reset')
          }}
          disabled={loading}
        >
          Reset Account
        </Button>
      </Section>

      {stateDump && (
        <div className="mt-4">
          <Divider label="State Dump" />
          <pre className="mt-2 p-3 bg-ink text-paper/80 text-[10px] font-mono rounded-card overflow-x-auto whitespace-pre-wrap">
            {stateDump}
          </pre>
        </div>
      )}
    </div>
  )

  return <AppShell user={runData?.user} center={center} />
}
