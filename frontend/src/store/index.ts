import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Toast {
  id: string
  message: string
  type: 'info' | 'success' | 'error'
}

interface State {
  token: string | null
  toasts: Toast[]

  setToken: (token: string) => void
  clearToken: () => void
  addToast: (message: string, type?: Toast['type']) => void
  removeToast: (id: string) => void
}

export const useStore = create<State>()(
  persist(
    (set) => ({
      token: null,
      toasts: [],

      setToken: (token) => set({ token }),
      clearToken: () => set({ token: null }),

      addToast: (message, type = 'info') =>
        set((s) => ({
          toasts: [
            ...s.toasts,
            { id: `${Date.now()}-${Math.random()}`, message, type },
          ],
        })),
      removeToast: (id) =>
        set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
    }),
    {
      name: 'touge-store',
      partialize: (s) => ({ token: s.token }),
    },
  ),
)
