import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { AppShell } from '../components/layout/AppShell'
import { MountainScene } from '../scene/MountainScene'
import { useRun, useProcessRun } from '../hooks/useRun'
import { Divider } from '../components/ui/Divider'
import { StatBlock } from '../components/ui/StatBlock'
import { ProgressBar } from '../components/ui/ProgressBar'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { fmtSeconds, fmtNum, capFirst } from '../lib/utils'
import { useStore } from '../store'
import { TodayChallengeDetail } from '../types/api'

// Colour per corner type
const CORNER_COLOURS: Record<string, string> = {
  hairpin: '#c8102e',
  chicane: '#e06b00',
  sweeper: '#d4a500',
}

// Human-readable segment badge
function SegmentBadge({ type }: { type: string }) {
  const colour = CORNER_COLOURS[type] ?? '#888'
  const label = type === 'straight' ? 'Straight' : capFirst(type)
  return (
    <span
      className="text-[10px] tracking-widest uppercase font-body px-1.5 py-0.5 rounded"
      style={{ background: colour + '22', color: colour, border: `1px solid ${colour}55` }}
    >
      {label}
    </span>
  )
}

function ChallengeRow({ c, dark = false }: { c: TodayChallengeDetail; dark?: boolean }) {
  const reqLabel = (c.requirement as Record<string, unknown>)?.label as string | undefined

  const categoryLabel =
    c.event_type === 'corner'
      ? `${capFirst(c.corner_type ?? '')} Corner`
      : `Weather · ${capFirst(c.weather_type ?? '')}`

  const detail =
    c.event_type === 'corner'
      ? c.time_save_seconds != null ? `−${c.time_save_seconds}s if cleared` : ''
      : c.penalty_seconds != null ? `+${c.penalty_seconds}s if failed` : ''

  const currentVal = c.current_value ?? 0
  const required = c.required_value

  const textPrimary = dark ? 'text-paper' : 'text-ink'
  const textSecondary = dark ? 'text-paper/50' : 'text-ink3'
  const textProgress = dark ? 'text-paper/60' : 'text-ink3'
  const metColor = dark ? '#4ade80' : '#166534'
  const unmetColor = dark ? '#f87171' : '#c8102e'

  return (
    <div className="flex items-center justify-between py-1.5">
      <div className="flex items-center gap-2 min-w-0">
        <div
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ background: c.met ? metColor : unmetColor }}
        />
        <div className="min-w-0">
          {reqLabel && (
            <span className={`text-sm font-body ${textPrimary} truncate block`}>{reqLabel}</span>
          )}
          <span className={`text-[10px] font-body ${textSecondary}`}>
            {categoryLabel}{detail ? ` · ${detail}` : ''}
          </span>
        </div>
      </div>
      <span className={`text-xs font-body ${textProgress} flex-shrink-0 ml-2`}>
        {currentVal} / {String(required)}
      </span>
    </div>
  )
}

function TelemetryPanel({ runData }: { runData: ReturnType<typeof useRun>['data'] }) {
  const { user, run, today_status: todayStatusRaw } = runData!
  const today_status = todayStatusRaw ?? { qualified: false, streak_applied: false, segment_advanced: false, has_challenges: false, all_challenges_met: false, challenges: [] }
  const processRun = useProcessRun()
  const addToast = useStore((s) => s.addToast)

  const handleProcess = async () => {
    try {
      const result = await processRun.mutateAsync()
      if (result.today_status.segment_advanced) {
        addToast('Segment cleared!', 'success')
      } else if (!result.today_status.qualified) {
        addToast('No qualifying activity yet today', 'error')
      } else {
        addToast('Challenges still pending — keep coding', 'error')
      }
      if (result.catchup_summary?.crashed) {
        addToast('CRASH — streak reset!', 'error')
      }
    } catch {
      addToast('Failed to check progress', 'error')
    }
  }

  const currentSeg = run?.current_segment
  const nextSeg =
    run && run.track.segment_layout
      ? run.track.segment_layout[run.segment_index] ?? null
      : null

  return (
    <div className="p-4 flex flex-col gap-3 h-full overflow-y-auto">
      {run && (
        <>
          <div>
            <div className="text-[10px] tracking-widest uppercase text-ink3 font-body mb-0.5">
              Track
            </div>
            <div className="font-display text-display-xs text-ink">
              {run.track.name.toUpperCase()}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge label={run.track.difficulty} type="default" />
              <span className="text-xs text-ink3 font-body">
                {run.track.length_days}d run
              </span>
            </div>
          </div>

          <Divider />

          {/* Current + next segment */}
          <div>
            <div className="text-[10px] tracking-widest uppercase text-ink3 font-body mb-1">
              Segment
            </div>
            {currentSeg ? (
              <div className="flex items-center gap-2">
                <SegmentBadge type={currentSeg.type} />
                <span className="text-xs font-body text-ink">{currentSeg.name}</span>
              </div>
            ) : (
              <span className="text-xs font-body text-ink3">At start line</span>
            )}
            {nextSeg && (
              <div className="flex items-center gap-2 mt-1 opacity-50">
                <span className="text-[10px] font-body text-ink3">Next:</span>
                <SegmentBadge type={nextSeg.type} />
                <span className="text-[10px] font-body text-ink3">{nextSeg.name}</span>
              </div>
            )}
          </div>

          <Divider />

          <div>
            <div className="text-[10px] tracking-widest uppercase text-ink3 font-body mb-1">
              Run Time
            </div>
            <div className="font-display text-display-lg" style={{ color: '#c47a0a' }}>
              {fmtSeconds(run.stopwatch_seconds)}
            </div>
          </div>

          <Divider />

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] tracking-widest uppercase text-ink3 font-body">
                Progress
              </span>
              <span className="text-xs font-body text-ink2">
                SEG {run.segment_index} / {run.track.length_days}
              </span>
            </div>
            <ProgressBar value={run.segment_index} max={run.track.length_days} />
            <div className="text-right text-[10px] text-ink3 font-body mt-0.5">
              {run.progress_percent}%
            </div>
          </div>

          <Divider />
        </>
      )}

      <div className="flex flex-col gap-2">
        <StatBlock label="Streak" value={user.streak} />
        <StatBlock label="Gas" value={user.gas} />
        <StatBlock label="Points" value={fmtNum(user.total_points)} accent />
      </div>

      {/* Today's status */}
      <Divider label="Today" />
      {today_status.segment_advanced ? (
        <div className="text-xs font-body text-ink3 text-center py-1">
          ✓ Day complete — keep coding tomorrow
        </div>
      ) : (
        <>
          {today_status.challenges.length > 0 && (
            <div className="divide-y divide-paper2">
              {today_status.challenges.map((c, i) => (
                <ChallengeRow key={i} c={c} dark={false} />
              ))}
            </div>
          )}
          <Button
            variant="primary"
            size="sm"
            onClick={handleProcess}
            disabled={processRun.isPending}
          >
            {processRun.isPending
              ? 'Checking...'
              : today_status.qualified
                ? 'Check Progress'
                : 'Sync Commits'}
          </Button>
        </>
      )}
    </div>
  )
}

export function RunView() {
  const { data, isLoading, error } = useRun()
  const addToast = useStore((s) => s.addToast)
  const [challengesOpen, setChallengesOpen] = useState(false)

  useEffect(() => {
    if (data?.catchup_summary?.crashed) {
      addToast('CRASH — streak reset to 0!', 'error')
    }
    if (data?.today_status.has_challenges && !data?.today_status.segment_advanced) {
      setChallengesOpen(true)
    }
  }, [data?.catchup_summary?.crashed, data?.today_status.has_challenges])

  if (isLoading) {
    return (
      <AppShell
        center={
          <div className="flex items-center justify-center h-full bg-scene-bg">
            <div className="font-display text-display-xs text-paper/40 animate-pulse">
              LOADING RUN...
            </div>
          </div>
        }
      />
    )
  }

  if (error || !data) {
    return (
      <AppShell
        center={
          <div className="flex items-center justify-center h-full text-red font-body text-sm">
            Failed to load run data.
          </div>
        }
      />
    )
  }

  const segPct = data.run ? data.run.progress_percent : 0
  const challenges = data.today_status.challenges

  return (
    <AppShell
      user={data.user}
      center={
        <div className="relative w-full h-full">
          <MountainScene progress={segPct} />

          {/* Challenge overlay — bottom of scene */}
          <AnimatePresence>
            {challengesOpen && challenges.length > 0 && !data.today_status.segment_advanced && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3 }}
                className="absolute bottom-0 left-0 right-0 overflow-hidden"
              >
                <div className="bg-scene-bg/95 backdrop-blur-lg border-t border-white/10 px-4 py-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] tracking-widest uppercase font-body text-paper/50">
                      Today&apos;s Challenges
                    </span>
                    <button
                      onClick={() => setChallengesOpen(false)}
                      className="text-paper/30 hover:text-paper/60 text-xs"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="divide-y divide-white/5">
                    {challenges.map((c, i) => (
                      <ChallengeRow key={i} c={c} dark={true} />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      }
      right={<TelemetryPanel runData={data} />}
    />
  )
}
