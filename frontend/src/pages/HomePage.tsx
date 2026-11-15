import type { Session } from '@supabase/supabase-js'

type HomePageProps = {
  session: Session | null
  pendingAction: 'sign-in' | 'sign-out' | null
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

export function HomePage({ session, pendingAction, signInWithGoogle, signOut }: HomePageProps) {
  return (
    <>
      <h1>Your account</h1>
      {session ? (
        <>
          <p>Signed in as {session.user.email ?? session.user.id}</p>
          <button type="button" onClick={signOut} disabled={pendingAction !== null}>
            {pendingAction === 'sign-out' ? 'Signing out…' : 'Sign out'}
          </button>
        </>
      ) : (
        <>
          <p>Sign in to access your RoleMatch account</p>
          <button type="button" onClick={signInWithGoogle} disabled={pendingAction !== null}>
            {pendingAction === 'sign-in' ? 'Redirecting to Google…' : 'Continue with Google'}
          </button>
        </>
      )}
    </>
  )
}
