import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { ProfileResponse } from '../types/api'

export function useProfile() {
  return useQuery<ProfileResponse>({
    queryKey: ['profile'],
    queryFn: () => api.get<ProfileResponse>('/profile'),
  })
}
