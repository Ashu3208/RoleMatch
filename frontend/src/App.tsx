import { useAuth } from './hooks/useAuth'

function App() {
  const {
    session,
    isLoading,
    pendingAction,
    errorMessage,
    signInWithGoogle,
    signOut,
  } = useAuth()

  return (
    <main>
      <h1>RoleMatch</h1>

      {isLoading ? (
        <p role="status">Checking your session…</p>
      ) : session ? (
        <>
          <p>Signed in as {session.user.email ?? session.user.id}</p>
          <button type="button" onClick={signOut} disabled={pendingAction !== null}>
            {pendingAction === 'sign-out' ? 'Signing out…' : 'Sign out'}
          </button>
        </>
      ) : (
        <button type="button" onClick={signInWithGoogle} disabled={pendingAction !== null}>
          {pendingAction === 'sign-in' ? 'Redirecting to Google…' : 'Continue with Google'}
        </button>
      )}

      {errorMessage && <p role="alert">{errorMessage}</p>}
    </main>
  )
}

export default App
