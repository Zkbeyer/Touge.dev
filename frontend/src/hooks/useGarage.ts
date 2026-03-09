import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Cosmetic, OwnedCar, UpgradeResponse } from '../types/api'

export function useGarageCars() {
  return useQuery<OwnedCar[]>({
    queryKey: ['garage', 'cars'],
    queryFn: () => api.get<OwnedCar[]>('/garage/cars'),
  })
}

export function useGarageCosmetics() {
  return useQuery<Cosmetic[]>({
    queryKey: ['garage', 'cosmetics'],
    queryFn: () => api.get<Cosmetic[]>('/garage/cosmetics'),
  })
}

export function useSelectCar() {
  const qc = useQueryClient()
  return useMutation<unknown, Error, string>({
    mutationFn: (carOwnershipId) =>
      api.post(`/garage/cars/${carOwnershipId}/select`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['garage'] })
      qc.invalidateQueries({ queryKey: ['run'] })
    },
  })
}

export function useUpgradeCar() {
  const qc = useQueryClient()
  return useMutation<UpgradeResponse, Error, string>({
    mutationFn: (carOwnershipId) =>
      api.post<UpgradeResponse>(`/garage/cars/${carOwnershipId}/upgrade`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['garage'] })
      qc.invalidateQueries({ queryKey: ['run'] })
    },
  })
}

export function useTogglePerk() {
  const qc = useQueryClient()
  return useMutation<unknown, Error, { id: string; active: boolean }>({
    mutationFn: ({ id, active }) =>
      api.post(`/garage/cars/${id}/perk`, { active }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['garage'] })
    },
  })
}
