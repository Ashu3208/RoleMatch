import { Link, Route, Routes } from 'react-router-dom'
import { Navbar } from './components/Navbar'
import { useAuth } from './hooks/useAuth'
import { HomePage } from './pages/HomePage'
import { ProfilePage } from './pages/ProfilePage'

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
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Navbar isSignedIn={session !== null} />
      <main id="main-content" className="page-content">
        {isLoading ? (
          <p role="status">Checking your session…</p>
        ) : (
          <Routes>
            <Route path="/" element={(
              <HomePage
                session={session}
                pendingAction={pendingAction}
                signInWithGoogle={signInWithGoogle}
                signOut={signOut}
              />
            )} />
            <Route path="/profile" element={session ? (
              <ProfilePage key={session.user.id} accessToken={session.access_token} />
            ) : (
              <>
                <h1>Your profile</h1>
                <p>Sign in to view your profile</p>
                <Link to="/">Go to sign in</Link>
              </>
            )} />
            <Route path="*" element={(
              <>
                <h1>Page not found</h1>
                <Link to="/">Go to your account</Link>
              </>
            )} />
          </Routes>
        )}
        {errorMessage && <p role="alert">{errorMessage}</p>}
      </main>
    </>
  )
}

export default App
