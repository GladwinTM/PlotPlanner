import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../app/AuthProvider'
import { getProfile, updateProfile } from '../services/api'
import type { ProfileUpdate } from '../types/profile'

/** Cache keys include the user id so profiles from different accounts can never mix. */
function useProfileKey() {
  const { session } = useAuth()
  return ['profile', session?.user.id ?? null] as const
}

export function useProfile() {
  const key = useProfileKey()
  return useQuery({ queryKey: key, queryFn: getProfile, enabled: key[1] !== null, retry: false })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  const key = useProfileKey()
  return useMutation({
    mutationFn: (changes: ProfileUpdate) => updateProfile(changes),
    onSuccess: (profile) => queryClient.setQueryData(key, profile),
  })
}
