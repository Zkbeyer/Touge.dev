import { useState, useRef, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { useLootboxes, useOpenLootbox } from '../hooks/useInventory'
import { useRun } from '../hooks/useRun'
import { OpenLootboxResult } from '../types/api'
import { useStore } from '../store'
import { TIER_COLORS } from '../design/tokens'
import { capFirst } from '../lib/utils'

function TierGem({ tier }: { tier: string }) {
  const color = TIER_COLORS[tier] ?? '#a8a29e'
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <polygon
        points="18,2 32,10 32,26 18,34 4,26 4,10"
        fill={color}
        fillOpacity="0.15"
        stroke={color}
        strokeWidth="1.5"
      />
      <polygon
        points="18,8 26,13 26,23 18,28 10,23 10,13"
        fill={color}
        fillOpacity="0.3"
      />
      <polygon
        points="18,12 22,15 22,21 18,24 14,21 14,15"
        fill={color}
        fillOpacity="0.6"
      />
    </svg>
  )
}

function LootboxCanvas({ onComplete }: { onComplete: () => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    let frame = 0
    let raf: number

    const draw = () => {
      ctx.clearRect(0, 0, 300, 300)
      const cx = 150
      const cy = 150
      const t = frame / 60

      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(t * 0.5)

      ctx.beginPath()
      ctx.rect(-40, -40, 80, 80)
      ctx.strokeStyle = `rgba(196,122,10,${0.8 - t * 0.2})`
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.fillStyle = `rgba(196,122,10,${0.15 - t * 0.03})`
      ctx.fillRect(-40, -40, 80, 80)

      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + t * 2
        const r = 60 + Math.sin(t * 3 + i) * 8
        const px = Math.cos(angle) * r
        const py = Math.sin(angle) * r
        ctx.beginPath()
        ctx.arc(px, py, 3, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(200,16,46,${0.7 - t * 0.1})`
        ctx.fill()
      }

      ctx.restore()

      frame++
      if (frame < 120) {
        raf = requestAnimationFrame(draw)
      } else {
        onComplete()
      }
    }

    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [onComplete])

  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={300}
      className="mx-auto"
    />
  )
}

function RewardReveal({ result, onDismiss }: { result: OpenLootboxResult; onDismiss: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center gap-4 text-center"
    >
      <div className="text-[10px] tracking-widest uppercase text-ink3 font-body">
        {result.type === 'car' ? 'New Car!' : result.type === 'duplicate_points' ? 'Duplicate — converted' : 'Points'}
      </div>
      {result.car_name && (
        <div className="font-display text-display-md text-ink">
          {result.car_name.toUpperCase()}
        </div>
      )}
      {result.points && (
        <div className="font-display text-display-lg" style={{ color: '#c47a0a' }}>
          +{result.points} PTS
        </div>
      )}
      <Badge label={result.rarity} type="rarity" />
      <Button variant="secondary" onClick={onDismiss}>Close</Button>
    </motion.div>
  )
}

export function InventoryView() {
  const { data: runData } = useRun()
  const { data: lootboxes, isLoading } = useLootboxes()
  const openLootbox = useOpenLootbox()
  const addToast = useStore((s) => s.addToast)

  const [opening, setOpening] = useState<string | null>(null)
  const [animating, setAnimating] = useState(false)
  const [result, setResult] = useState<OpenLootboxResult | null>(null)

  const handleOpen = async (id: string) => {
    setOpening(id)
    setAnimating(true)
    setResult(null)
  }

  const handleAnimComplete = async () => {
    if (!opening) return
    try {
      const res = await openLootbox.mutateAsync(opening)
      setResult(res)
      setAnimating(false)
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Failed to open', 'error')
      setOpening(null)
      setAnimating(false)
    }
  }

  const handleDismiss = () => {
    setOpening(null)
    setResult(null)
    setAnimating(false)
  }

  const center = (
    <div className="relative flex-1 p-6 overflow-y-auto">
      <div className="font-display text-display-xs text-ink mb-4">
        LOOTBOXES
        <span className="ml-3 text-sm font-body text-ink3 normal-case">
          {lootboxes?.length ?? 0} unopened
        </span>
      </div>

      {isLoading ? (
        <div className="text-xs text-ink3 font-body">Loading...</div>
      ) : lootboxes?.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="font-display text-display-sm text-ink3 mb-2">EMPTY</div>
          <p className="text-xs font-body text-ink3">Complete runs to earn lootboxes</p>
        </div>
      ) : (
        <div
          className="grid gap-3"
          style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }}
        >
          {lootboxes?.map((lb) => (
            <div
              key={lb.id}
              className="bg-s1 border border-border rounded-card p-4 flex flex-col items-center gap-3"
            >
              <TierGem tier={lb.tier} />
              <Badge label={lb.tier} type="tier" />
              <div className="text-[10px] font-body text-ink3">
                {new Date(lb.created_at).toLocaleDateString()}
              </div>
              <Button
                size="sm"
                variant="primary"
                onClick={() => handleOpen(lb.id)}
                className="w-full"
              >
                Open
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  return (
    <>
      <AppShell user={runData?.user} center={center} />

      <AnimatePresence>
        {opening && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-paper rounded-card border border-border p-8 flex flex-col items-center gap-4 min-w-[320px]"
            >
              {animating ? (
                <>
                  <div className="text-[10px] tracking-widest uppercase font-body text-ink3 mb-2">
                    Opening {capFirst(lootboxes?.find(l => l.id === opening)?.tier ?? '')}...
                  </div>
                  <LootboxCanvas onComplete={handleAnimComplete} />
                </>
              ) : result ? (
                <RewardReveal result={result} onDismiss={handleDismiss} />
              ) : null}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
