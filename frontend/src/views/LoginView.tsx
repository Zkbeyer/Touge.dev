import { TopoLines } from '../components/decorative/TopoLines'
import { KanjiAccent } from '../components/decorative/KanjiAccent'

export function LoginView() {
  return (
    <div className="relative flex items-center justify-center h-full overflow-hidden bg-paper">
      <TopoLines className="absolute inset-0 w-full h-full text-ink3/30 pointer-events-none" />

      <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-40">
        <KanjiAccent size={320} opacity={0.055} />
      </div>

      <div className="relative z-10 flex flex-col items-center text-center px-8 max-w-sm">
        <div className="font-display text-display-xl text-ink mb-2 leading-none">
          TOUGE.DEV
        </div>
        <p className="font-body text-sm text-ink2 mb-1 tracking-wide">
          Gamified Coding Streak
        </p>
        <p className="font-body text-xs text-ink3 mb-10">
          Drive your commit streak up the mountain pass
        </p>

        <a
          href="/auth/github"
          className="inline-flex items-center gap-3 bg-ink text-paper px-6 py-3 rounded-btn font-body font-medium text-sm hover:bg-ink/90 transition-all duration-150 active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-red"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.482 0-.237-.008-.866-.013-1.7-2.782.603-3.369-1.342-3.369-1.342-.454-1.155-1.11-1.463-1.11-1.463-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.087 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.029-2.683-.103-.253-.446-1.27.098-2.647 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.377.202 2.394.1 2.647.64.699 1.028 1.592 1.028 2.683 0 3.842-2.339 4.687-4.566 4.935.359.309.678.919.678 1.852 0 1.336-.012 2.415-.012 2.743 0 .267.18.579.688.481C19.138 20.163 22 16.418 22 12c0-5.523-4.477-10-10-10z" />
          </svg>
          Continue with GitHub
        </a>

        <div className="mt-12 font-display text-[11px] tracking-[0.3em] text-ink3">
          峠 MOUNTAIN PASS STREAK
        </div>
      </div>
    </div>
  )
}
