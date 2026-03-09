import { AnimatePresence } from 'framer-motion'
import { useStore } from '../../store'
import { Toast } from './Toast'

export function ToastStack() {
  const toasts = useStore((s) => s.toasts)
  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 items-end pointer-events-none">
      <AnimatePresence mode="popLayout">
        {toasts.map((t) => (
          <Toast key={t.id} toast={t} />
        ))}
      </AnimatePresence>
    </div>
  )
}
