'use client'

import { useMemo } from 'react'
import { useAuth } from '@clerk/nextjs'
import { ApiClient } from '@/lib/api-client'

export function useApiClient(): ApiClient {
  const { getToken } = useAuth()
  return useMemo(() => new ApiClient({ getToken }), [getToken])
}
