import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Lootbox, OpenLootboxResult } from '../types/api'

export function useLootboxes() {
  return useQuery<Lootbox[]>({
    queryKey: ['inventory', 'lootboxes'],
    queryFn: () => api.get<Lootbox[]>('/inventory/lootboxes'),
  })
}

export function useOpenLootbox() {
  const qc = useQueryClient()
  return useMutation<OpenLootboxResult, Error, string>({
    mutationFn: (lootboxId) =>
      api.post<OpenLootboxResult>(`/inventory/lootboxes/${lootboxId}/open`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inventory'] })
      qc.invalidateQueries({ queryKey: ['garage'] })
      qc.invalidateQueries({ queryKey: ['run'] })
    },
  })
}
