import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useStore } from './store'
import { ToastStack } from './components/ui/ToastStack'
import { LoginView } from './views/LoginView'
import { RunView } from './views/RunView'
import { GarageView } from './views/GarageView'
import { InventoryView } from './views/InventoryView'
import { ProfileView } from './views/ProfileView'
import { SettingsView } from './views/SettingsView'
import { DevView } from './views/DevView'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function AuthGuard() {
  const { token, setToken } = useStore()
  const location = useLocation()

  const params = new URLSearchParams(location.search)
  const urlToken = params.get('token')

  useEffect(() => {
    if (urlToken) {
      setToken(urlToken)
      window.history.replaceState({}, '', location.pathname)
    }
  }, [urlToken, setToken, location.pathname])

  // No token at all → login
  if (!token && !urlToken) return <Navigate to="/login" replace />

  // URL token present but not yet in store → wait for the effect above
  // This prevents children from mounting and firing API calls before the
  // token is set in Zustand
  if (urlToken && !token) return null

  return <Outlet />
}

export function App() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <div className="h-full">
          <Routes>
            <Route path="/login" element={<LoginView />} />
            <Route element={<AuthGuard />}>
              <Route path="/" element={<RunView />} />
              <Route path="/garage" element={<GarageView />} />
              <Route path="/inventory" element={<InventoryView />} />
              <Route path="/profile" element={<ProfileView />} />
              <Route path="/settings" element={<SettingsView />} />
              <Route path="/dev" element={<DevView />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          <ToastStack />
        </div>
      </QueryClientProvider>
    </BrowserRouter>
  )
}
