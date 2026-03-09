import { UserSummary } from '../../types/api'
import { NavRail } from './NavRail'
import { TopStrip } from './TopStrip'

interface AppShellProps {
  user?: UserSummary
  center: React.ReactNode
  right?: React.ReactNode
}

export function AppShell({ user, center, right }: AppShellProps) {
  return (
    <div className="flex flex-col h-full bg-paper overflow-hidden">
      <TopStrip user={user} />
      <div className="flex flex-1 overflow-hidden">
        <NavRail />
        <main className="flex-1 relative overflow-hidden">{center}</main>
        {right && (
          <aside
            className="border-l border-border bg-paper overflow-y-auto overflow-x-hidden flex-shrink-0"
            style={{ width: 280 }}
          >
            {right}
          </aside>
        )}
      </div>
    </div>
  )
}
