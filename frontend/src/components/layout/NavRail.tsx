import { NavLink } from 'react-router-dom'
import { KanjiAccent } from '../decorative/KanjiAccent'

const NAV_ITEMS = [
  { path: '/', icon: '●', label: 'RUN', exact: true },
  { path: '/garage', icon: '□', label: 'GAR', exact: false },
  { path: '/inventory', icon: '⬡', label: 'BOX', exact: false },
  { path: '/profile', icon: '○', label: 'DRV', exact: false },
  { path: '/settings', icon: '◈', label: 'SET', exact: false },
  { path: '/dev', icon: '⚙', label: 'DEV', exact: false },
]

export function NavRail() {
  return (
    <nav
      className="flex flex-col items-center py-3 gap-1 border-r border-border-mid bg-s1"
      style={{ width: 64, flexShrink: 0 }}
    >
      <div className="mb-4 mt-1">
        <KanjiAccent size={28} opacity={0.3} />
      </div>

      <div className="flex flex-col gap-1 flex-1 w-full px-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.exact}
            className="relative flex flex-col items-center justify-center py-2.5 w-full rounded transition-all duration-150 hover:bg-s2 active:scale-[0.97]"
            style={({ isActive }) => ({ color: isActive ? '#c8102e' : '#6b6560' })}
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <div className="absolute left-0 top-2 bottom-2 w-0.5 bg-red rounded-r" />
                )}
                <span className="text-base leading-none">{item.icon}</span>
                <span className="text-[9px] font-body font-medium tracking-widest mt-0.5">
                  {item.label}
                </span>
              </>
            )}
          </NavLink>
        ))}
      </div>

    </nav>
  )
}
