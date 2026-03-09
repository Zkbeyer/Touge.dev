import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { RunResponse } from '../types/api'

export function useRun() {
  return useQuery<RunResponse>({
    queryKey: ['run'],
    queryFn: () => api.get<RunResponse>('/run'),
    // Poll every 30 seconds — ensures UI stays fresh between commits.
    // The GitHub webhook (POST /webhook/github) provides near-instant updates
    // on push; this polling acts as a safety net.
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,   // re-check whenever the user tabs back in
    staleTime: 15_000,
  })
}

export function useProcessRun() {
  const qc = useQueryClient()
  return useMutation<RunResponse>({
    mutationFn: () => api.post<RunResponse>('/run/process'),
    onSuccess: (data) => {
      qc.setQueryData(['run'], data)
    },
  })
}
