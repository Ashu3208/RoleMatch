export type UserProfile = {
  id: string
  email: string | null
}

const apiUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

export async function getProfile(accessToken: string, signal: AbortSignal): Promise<UserProfile> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      signal,
    })
  } catch (error) {
    if (signal.aborted) throw error
    throw new Error('Unable to reach RoleMatch. Check that the backend is running.', { cause: error })
  }

  if (response.status === 401) {
    throw new Error('Your session could not be verified. Sign out and sign in again.')
  }
  if (response.status === 503) {
    throw new Error('Account verification is temporarily unavailable. Please try again.')
  }
  if (!response.ok) {
    throw new Error('Unable to load your profile. Please try again.')
  }

  const profile: unknown = await response.json()
  if (
    typeof profile !== 'object' || profile === null ||
    !('id' in profile) || typeof profile.id !== 'string' ||
    !('email' in profile) || (profile.email !== null && typeof profile.email !== 'string')
  ) {
    throw new Error('RoleMatch returned an invalid profile response.')
  }

  return {
    id: profile.id,
    email: typeof profile.email === 'string' ? profile.email : null,
  }
}
