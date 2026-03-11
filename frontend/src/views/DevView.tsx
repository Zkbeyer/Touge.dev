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
  const [commitDump, setCommitDump] = useState<string | null>(null)
  const [lcDump, setLcDump] = useState<string | null>(null)
  const [eventPoolDump, setEventPoolDump] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [segmentInput, setSegmentInput] = useState(0)
  const [injectCommits, setInjectCommits] = useState(0)
  const [injectEasy, setInjectEasy] = useState(0)
  const [injectMedium, setInjectMedium] = useState(0)
  const [injectHard, setInjectHard] = useState(0)

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

  const getEventPool = async () => {
    setLoading(true)
    try {
      const result = await api.get('/test/events/pool')
      setEventPoolDump(JSON.stringify(result, null, 2))
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Error', 'error')
    } finally {
      setLoading(false)
    }
  }

  const getCommitDebug = async () => {
    setLoading(true)
    try {
      const result = await api.get('/test/activity/github-debug') as {
        date: string
        user_timezone: string
        cached_activity: { commit_count: number | null; fetched_at: string | null; is_finalized: boolean | null }
        live_github: { commit_count: number | null; error: string | null; push_events: unknown[] }
      }
      // Format a readable summary
      const lines = [
        `Date: ${result.date} (${result.user_timezone})`,
        ``,
        `── Cached in DB ──`,
        `  commit_count : ${result.cached_activity.commit_count ?? 'none'}`,
        `  fetched_at   : ${result.cached_activity.fetched_at ?? 'never'}`,
        `  is_finalized : ${result.cached_activity.is_finalized ?? 'n/a'}`,
        ``,
        `── Live from GitHub API ──`,
        `  commit_count : ${result.live_github.commit_count ?? 'n/a'}`,
        result.live_github.error ? `  error        : ${result.live_github.error}` : '',
        ``,
        `── Push Events ──`,
        ...result.live_github.push_events.map((e: unknown) => {
          const ev = e as Record<string, unknown>
          if (ev.error) return `  ERROR: ${ev.error}`
          const commits = (ev.commits as { sha: string; message: string; author: string }[]) ?? []
          return [
            `  ${ev.repo}  (${ev.pushed_at_local})`,
            ...commits.map((c) => `    [${c.sha}] ${c.author}: ${c.message}`),
          ].join('\n')
        }),
      ].filter((l) => l !== '').join('\n')
      setCommitDump(lines)
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Error', 'error')
    } finally {
      setLoading(false)
    }
  }

  const getLcDebug = async () => {
    setLoading(true)
    try {
      const result = await api.get('/test/activity/leetcode-debug') as {
        date: string
        user_timezone: string
        leetcode_username: string | null
        leetcode_validated: boolean
        cached_activity: { lc_easy: number | null; lc_medium: number | null; lc_hard: number | null; lc_total: number | null; fetched_at: string | null; is_finalized: boolean | null }
        live_leetcode: { submission_count: number; error: string | null; submissions: { title: string; difficulty: string; submitted_at_local: string; lang: string; status: string }[] }
      }
      const lines = [
        `Date: ${result.date} (${result.user_timezone})`,
        `LC user: ${result.leetcode_username ?? 'not set'} (validated: ${result.leetcode_validated})`,
        ``,
        `── Cached in DB ──`,
        `  easy   : ${result.cached_activity.lc_easy ?? 'none'}`,
        `  medium : ${result.cached_activity.lc_medium ?? 'none'}`,
        `  hard   : ${result.cached_activity.lc_hard ?? 'none'}`,
        `  total  : ${result.cached_activity.lc_total ?? 'none'}`,
        `  fetched_at   : ${result.cached_activity.fetched_at ?? 'never'}`,
        `  is_finalized : ${result.cached_activity.is_finalized ?? 'n/a'}`,
        ``,
        `── Live from LeetCode API ──`,
        `  accepted today : ${result.live_leetcode.submission_count}`,
        result.live_leetcode.error ? `  error          : ${result.live_leetcode.error}` : '',
        ``,
        `── Accepted Submissions ──`,
        ...result.live_leetcode.submissions.map((s) =>
          `  [${s.difficulty.padEnd(6)}] ${s.title}  (${s.lang})  ${s.submitted_at_local}`
        ),
        result.live_leetcode.submissions.length === 0 && !result.live_leetcode.error
          ? '  (none today)'
          : '',
      ].filter((l) => l !== '').join('\n')
      setLcDump(lines)
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
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/advance-date')} disabled={loading}>
          +1 Day (skip)
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/process-day', { commits: 0, lc_easy: 1 })} disabled={loading}>
          +1 Day (LC Easy)
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/process-day', { commits: 0, lc_medium: 1 })} disabled={loading}>
          +1 Day (LC Med)
        </Button>
        <Button size="sm" variant="secondary" onClick={() => action('/test/run/process-day', { commits: 0, lc_hard: 1 })} disabled={loading}>
          +1 Day (LC Hard)
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

      <Section title="Segment">
        {[0, 5, 10, 15].map((n) => (
          <Button
            key={n}
            size="sm"
            variant="secondary"
            onClick={() => action('/test/run/set-segment', { segment_index: n })}
            disabled={loading}
          >
            Seg {n}
          </Button>
        ))}
        <div className="flex items-center gap-1">
          <input
            type="number"
            min={0}
            value={segmentInput}
            onChange={(e) => setSegmentInput(Number(e.target.value))}
            className="w-14 px-2 py-1 text-xs font-mono bg-paper border border-ink3/30 rounded text-ink text-center"
          />
          <Button
            size="sm"
            variant="secondary"
            onClick={() => action('/test/run/set-segment', { segment_index: segmentInput })}
            disabled={loading}
          >
            Set
          </Button>
        </div>
      </Section>

      <Section title="Events">
        <Button size="sm" variant="primary" onClick={getEventPool} disabled={loading}>
          View Event Pool
        </Button>
        {(['fog', 'rain', 'night_run'] as const).map((wt) => (
          <Button
            key={wt}
            size="sm"
            variant="secondary"
            onClick={() => action('/test/events/force-weather', { weather_type: wt })}
            disabled={loading}
          >
            Force: {wt.replace('_', ' ')}
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
        {[0, 7, 30].map((n) => (
          <Button
            key={n}
            size="sm"
            variant="secondary"
            onClick={() => action('/test/user/set-streak', { streak: n })}
            disabled={loading}
          >
            Streak {n}
          </Button>
        ))}
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

      <Section title="Inject Activity">
        <div className="flex items-center gap-2 flex-wrap">
          {([
            ['commits', injectCommits, setInjectCommits],
            ['lc_easy', injectEasy, setInjectEasy],
            ['lc_med', injectMedium, setInjectMedium],
            ['lc_hard', injectHard, setInjectHard],
          ] as [string, number, (n: number) => void][]).map(([label, val, setter]) => (
            <label key={label} className="flex flex-col items-center gap-0.5">
              <span className="text-[9px] font-mono text-ink3 uppercase">{label}</span>
              <input
                type="number"
                min={0}
                value={val}
                onChange={(e) => setter(Number(e.target.value))}
                className="w-14 px-2 py-1 text-xs font-mono bg-paper border border-ink3/30 rounded text-ink text-center"
              />
            </label>
          ))}
          <Button
            size="sm"
            variant="secondary"
            onClick={() => action('/test/activity/inject', {
              commits: injectCommits,
              lc_easy: injectEasy,
              lc_medium: injectMedium,
              lc_hard: injectHard,
            })}
            disabled={loading}
          >
            Inject (no process)
          </Button>
        </div>
      </Section>

      <Section title="GitHub Activity">
        <Button size="sm" variant="primary" onClick={getCommitDebug} disabled={loading}>
          Fetch Commits (live)
        </Button>
      </Section>

      <Section title="LeetCode Activity">
        <Button size="sm" variant="primary" onClick={getLcDebug} disabled={loading}>
          Fetch Submissions (live)
        </Button>
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

      {commitDump && (
        <div className="mt-4">
          <Divider label="GitHub Commits" />
          <pre className="mt-2 p-3 bg-ink text-paper/80 text-[10px] font-mono rounded-card overflow-x-auto whitespace-pre-wrap">
            {commitDump}
          </pre>
        </div>
      )}

      {lcDump && (
        <div className="mt-4">
          <Divider label="LeetCode Submissions" />
          <pre className="mt-2 p-3 bg-ink text-paper/80 text-[10px] font-mono rounded-card overflow-x-auto whitespace-pre-wrap">
            {lcDump}
          </pre>
        </div>
      )}

      {eventPoolDump && (
        <div className="mt-4">
          <Divider label="Event Pool" />
          <pre className="mt-2 p-3 bg-ink text-paper/80 text-[10px] font-mono rounded-card overflow-x-auto whitespace-pre-wrap">
            {eventPoolDump}
          </pre>
        </div>
      )}

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
