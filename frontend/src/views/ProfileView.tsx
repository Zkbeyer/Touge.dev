import { AppShell } from '../components/layout/AppShell'
import { Divider } from '../components/ui/Divider'
import { StatBlock } from '../components/ui/StatBlock'
import { useProfile } from '../hooks/useProfile'
import { useRun } from '../hooks/useRun'
import { fmtNum } from '../lib/utils'

export function ProfileView() {
  const { data: runData } = useRun()
  const { data: profile, isLoading } = useProfile()

  const center = (
    <div className="h-full overflow-y-auto p-8 max-w-2xl mx-auto">
      {isLoading || !profile ? (
        <div className="text-xs text-ink3 font-body">Loading...</div>
      ) : (
        <>
          <div className="mb-8">
            <div className="font-display text-display-md text-ink leading-none mb-1">
              {(profile.display_name ?? profile.github_username).toUpperCase()}
            </div>
            <div className="text-sm font-body text-ink2">@{profile.github_username}</div>
            {profile.leetcode_validated && profile.leetcode_username && (
              <div className="text-xs font-body text-ink3 mt-0.5">
                LeetCode: {profile.leetcode_username}
              </div>
            )}
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <StatBlock label="Streak" value={profile.streak} />
            <StatBlock label="Best" value={profile.longest_streak} />
            <StatBlock label="Gas" value={profile.gas} />
            <StatBlock label="Points" value={fmtNum(profile.total_points)} accent />
          </div>

          <Divider label="Lifetime Stats" />

          <div className="flex flex-col divide-y divide-border">
            {[
              ['Runs Completed', profile.lifetime_stats.total_runs_completed],
              ['Days Qualified', profile.lifetime_stats.total_days_qualified],
              ['Gas Used', profile.lifetime_stats.total_gas_used],
              ['Crashes', profile.lifetime_stats.total_crashes],
              ['Corner Saves', profile.lifetime_stats.total_corner_saves],
              ['Weather Survived', profile.lifetime_stats.total_weather_survived],
              //['Ghost Wins', profile.lifetime_stats.total_ghost_wins], // ghost removed
              ['Lootboxes Opened', profile.lifetime_stats.total_lootboxes_opened],
              ['Cars Owned', profile.lifetime_stats.total_cars_owned],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex items-center justify-between py-2">
                <span className="text-sm font-body text-ink2">{label}</span>
                <span className="font-display text-display-xs text-ink">{val}</span>
              </div>
            ))}
          </div>

          {profile.personal_bests.length > 0 && (
            <>
              <Divider label="Personal Bests" className="mt-4" />
              <div className="flex flex-col divide-y divide-border">
                {profile.personal_bests.map((pb) => (
                  <div key={pb.track_id} className="flex items-center justify-between py-2">
                    <span className="text-sm font-body text-ink">{pb.track_name}</span>
                    <span
                      className="font-display text-display-xs"
                      style={{ color: '#c47a0a' }}
                    >
                      {pb.best_formatted}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )

  return <AppShell user={runData?.user} center={center} />
}
