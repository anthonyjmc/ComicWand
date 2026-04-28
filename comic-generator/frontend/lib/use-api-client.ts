'use client'

import { useMemo } from 'react'
import { useAuth } from '@clerk/nextjs'
import { ApiClient } from '@/lib/api-client'

export function useApiClient(): ApiClient {
  const { getToken } = useAuth()
  const clerkJwtTemplate = process.env.NEXT_PUBLIC_CLERK_JWT_TEMPLATE

  return useMemo(
    () =>
      new ApiClient({
        getToken: async () => {
          if (!clerkJwtTemplate) return getToken()
          return getToken({ template: clerkJwtTemplate })
        },
      }),
    [getToken, clerkJwtTemplate]
  )
}
