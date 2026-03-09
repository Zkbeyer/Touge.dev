import { motion } from 'framer-motion'
import { useEffect } from 'react'
import { Toast as ToastType, useStore } from '../../store'
import { cn } from '../../lib/utils'

interface ToastProps {
  toast: ToastType
}

export function Toast({ toast }: ToastProps) {
  const removeToast = useStore((s) => s.removeToast)

  useEffect(() => {
    const t = setTimeout(() => removeToast(toast.id), 3500)
    return () => clearTimeout(t)
  }, [toast.id, removeToast])

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'px-4 py-2.5 rounded-card shadow-md text-sm font-body',
        toast.type === 'error' && 'bg-red text-white',
        toast.type === 'success' && 'bg-green text-white',
        toast.type === 'info' && 'bg-ink text-paper',
      )}
    >
      {toast.message}
    </motion.div>
  )
}
