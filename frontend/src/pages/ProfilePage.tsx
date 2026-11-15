import { useEffect, useState } from 'react'
import { getProfile } from '../lib/api'
import type { UserProfile } from '../lib/api'

type ProfilePageProps = {
  accessToken: string
}

type ProfileState =
  | { status: 'loading' }
  | { status: 'success'; profile: UserProfile }
  | { status: 'error'; message: string }

export function ProfilePage({ accessToken }: ProfilePageProps) {
  const [state, setState] = useState<ProfileState>({ status: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function loadProfile() {
      try {
        const profile = await getProfile(accessToken, controller.signal)
        if (!controller.signal.aborted) setState({ status: 'success', profile })
      } catch (error) {
        if (!controller.signal.aborted) {
          setState({
            status: 'error',
            message: error instanceof Error ? error.message : 'Unable to load your profile.',
          })
        }
      }
    }

    void loadProfile()
    return () => controller.abort()
  }, [accessToken, attempt])

  function retry() {
    setState({ status: 'loading' })
    setAttempt((value) => value + 1)
  }

  return (
    <>
      <h1>Your profile</h1>
      {state.status === 'loading' && <p role="status">Loading your profile…</p>}
      {state.status === 'error' && (
        <>
          <p role="alert">{state.message}</p>
          <button type="button" onClick={retry}>Try again</button>
        </>
      )}
      {state.status === 'success' && (
        <dl className="profile-details">
          <div>
            <dt>Email</dt>
            <dd>{state.profile.email ?? 'Not provided'}</dd>
          </div>
          <div>
            <dt>User ID</dt>
            <dd className="user-id">{state.profile.id}</dd>
          </div>
        </dl>
      )}
    </>
  )
}
