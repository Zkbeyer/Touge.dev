import { useState } from 'react'
import { motion } from 'framer-motion'
import { AppShell } from '../components/layout/AppShell'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Divider } from '../components/ui/Divider'
import { useGarageCars, useGarageCosmetics, useSelectCar, useUpgradeCar, useTogglePerk } from '../hooks/useGarage'
import { useRun } from '../hooks/useRun'
import { OwnedCar } from '../types/api'
import { useStore } from '../store'
import { RARITY_COLORS } from '../design/tokens'
import { capFirst } from '../lib/utils'

function CarSilhouette({ rarity }: { rarity: string }) {
  const color = RARITY_COLORS[rarity] ?? '#a8a29e'
  return (
    <svg viewBox="0 0 200 100" fill="none" className="w-full max-w-xs">
      <g opacity="0.7">
        <ellipse cx="100" cy="72" rx="80" ry="8" fill={color} opacity="0.1" />
        <rect x="30" y="55" width="140" height="20" rx="4" fill={color} opacity="0.15" />
        <rect x="50" y="38" width="100" height="22" rx="8" fill={color} opacity="0.2" />
        <rect x="65" y="32" width="70" height="18" rx="6" fill={color} opacity="0.15" />
        <circle cx="55" cy="74" r="12" fill={color} opacity="0.3" />
        <circle cx="55" cy="74" r="7" fill="#1c1917" opacity="0.5" />
        <circle cx="145" cy="74" r="12" fill={color} opacity="0.3" />
        <circle cx="145" cy="74" r="7" fill="#1c1917" opacity="0.5" />
      </g>
    </svg>
  )
}

export function GarageView() {
  const { data: runData } = useRun()
  const { data: cars, isLoading, error } = useGarageCars()
  const { data: cosmetics } = useGarageCosmetics()
  const selectCar = useSelectCar()
  const upgradeCar = useUpgradeCar()
  const togglePerk = useTogglePerk()
  const addToast = useStore((s) => s.addToast)

  const [selectedId, setSelectedId] = useState<string | null>(null)

  const activeCar = selectedId
    ? cars?.find((c) => c.id === selectedId)
    : cars?.find((c) => c.id === runData?.user?.active_car_id) ?? cars?.[0]

  const handleSelect = async (car: OwnedCar) => {
    try {
      await selectCar.mutateAsync(car.id)
      addToast(`${car.car.name} selected`, 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Error', 'error')
    }
  }

  const handleUpgrade = async (car: OwnedCar) => {
    try {
      const result = await upgradeCar.mutateAsync(car.id)
      if (result.iconic_unlocked) addToast('ICONIC unlocked!', 'success')
      else addToast(`Upgraded to level ${result.new_level}`, 'success')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Not enough points', 'error')
    }
  }

  const handlePerkToggle = async (car: OwnedCar) => {
    try {
      await togglePerk.mutateAsync({ id: car.id, active: !car.perk_active })
      addToast(`Perk ${car.perk_active ? 'deactivated' : 'activated'}`, 'info')
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : 'Error', 'error')
    }
  }

  const center = (
    <div className="flex flex-col items-center justify-center w-full h-full" style={{ background: '#0d0c12' }}>
      {isLoading ? (
        <div className="font-display text-display-xs animate-pulse" style={{ color: '#f5f3ef', opacity: 0.4 }}>
          LOADING...
        </div>
      ) : error ? (
        <div className="font-display text-display-xs" style={{ color: '#c8102e' }}>
          FAILED TO LOAD
        </div>
      ) : activeCar ? (
        <motion.div
          key={activeCar.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center gap-6 text-center px-8"
        >
          <CarSilhouette rarity={activeCar.car.rarity} />
          <div>
            <div className="font-display text-display-md leading-none mb-1" style={{ color: '#f5f3ef' }}>
              {activeCar.car.name.toUpperCase()}
            </div>
            <div className="text-xs font-body" style={{ color: 'rgba(245,243,239,0.4)' }}>
              {activeCar.car.base_model}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge label={activeCar.car.rarity} type="rarity" />
            <span className="text-xs font-body" style={{ color: 'rgba(245,243,239,0.4)' }}>
              LVL {activeCar.upgrade_level} / {activeCar.car.max_upgrade_level}
            </span>
            {activeCar.iconic_unlocked && (
              <span className="text-[10px] font-body font-medium tracking-wider" style={{ color: '#c47a0a' }}>
                ICONIC
              </span>
            )}
          </div>
          {activeCar.car.perk && (
            <div className="text-xs font-body max-w-xs" style={{ color: 'rgba(245,243,239,0.6)' }}>
              <span className="uppercase tracking-wider text-[10px]" style={{ color: 'rgba(245,243,239,0.3)' }}>
                Perk ·{' '}
              </span>
              {activeCar.car.perk.name} — {activeCar.car.perk.description}
            </div>
          )}
        </motion.div>
      ) : (
        <div className="font-display text-display-xs" style={{ color: 'rgba(245,243,239,0.2)' }}>
          NO CAR
        </div>
      )}
    </div>
  )

  const right = (
    <div className="p-4">
      <div className="font-display text-display-xs text-ink mb-1">GARAGE</div>
      {runData?.user && (
        <div className="flex items-center gap-3 mb-3">
          <span className="text-xs font-body text-ink3">
            <span className="font-display text-sm text-ink">{runData.user.spendable_points}</span> sp
          </span>
          <span className="text-xs font-body text-ink3">
            <span className="font-display text-sm" style={{ color: '#c47a0a' }}>{runData.user.total_points}</span> total
          </span>
        </div>
      )}
      <div className="flex flex-col gap-1">
        {isLoading ? (
          <div className="text-xs text-ink3 font-body">Loading...</div>
        ) : error ? (
          <div className="text-xs text-red font-body">Failed to load garage</div>
        ) : !cars || cars.length === 0 ? (
          <div className="text-xs text-ink3 font-body">No cars owned</div>
        ) : (
          cars.map((car) => {
            const isActive = car.id === (selectedId ?? activeCar?.id)
            return (
              <button
                key={car.id}
                onClick={() => setSelectedId(car.id)}
                className="text-left p-2.5 rounded transition-all hover:bg-s2 relative"
                style={{
                  borderLeft: isActive ? '2px solid #c8102e' : '2px solid transparent',
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-body font-medium text-ink">{car.car.name}</span>
                  <Badge label={car.car.rarity} type="rarity" />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-body text-ink3">
                    LVL {car.upgrade_level}/{car.car.max_upgrade_level}
                  </span>
                  {car.car.perk && (
                    <span className="text-[10px] font-body text-blue">{car.car.perk.slug}</span>
                  )}
                </div>
                {isActive && (
                  <div className="flex gap-1.5 mt-2">
                    <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); handleSelect(car) }}>
                      Use
                    </Button>
                    {car.upgrade_level < car.car.max_upgrade_level ? (
                      <Button size="sm" variant="primary" onClick={(e) => { e.stopPropagation(); handleUpgrade(car) }}>
                        Upgrade
                      </Button>
                    ) : car.car.perk ? (
                      <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); handlePerkToggle(car) }}>
                        {car.perk_active ? 'Perk ON' : 'Perk OFF'}
                      </Button>
                    ) : null}
                  </div>
                )}
              </button>
            )
          })
        )}
      </div>

      {cosmetics && cosmetics.length > 0 && (
        <>
          <Divider label="Cosmetics" className="mt-4" />
          <div className="flex flex-col gap-1">
            {cosmetics.slice(0, 8).map((c) => (
              <div key={c.id} className="flex items-center justify-between py-1">
                <span className="text-xs font-body text-ink">{c.name}</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-body text-ink3">{capFirst(c.type)}</span>
                  <Badge label={c.rarity} type="rarity" />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )

  return <AppShell user={runData?.user} center={center} right={right} />
}
