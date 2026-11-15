import { StrictMode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import type { AuthChangeEvent, Session } from '@supabase/supabase-js'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const auth = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  signInWithOAuth: vi.fn(),
  signOut: vi.fn(),
}))

vi.mock('./lib/supabaseClient', () => ({ supabase: { auth } }))

const savedSession: Session = {
  access_token: 'test-access-token',
  refresh_token: 'test-refresh-token',
  expires_in: 3600,
  token_type: 'bearer',
  user: {
    id: 'test-user',
    email: 'applicant@example.com',
    aud: 'authenticated',
    app_metadata: {},
    user_metadata: {},
    created_at: '2026-11-15T00:00:00Z',
  },
}

const fetchProfile = vi.fn()

function renderApp(path = '/') {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

let notifyAuthChange: (event: AuthChangeEvent, session: Session | null) => void
let unsubscribe: ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.resetAllMocks()
  vi.stubGlobal('fetch', fetchProfile)
  fetchProfile.mockResolvedValue(new Response(JSON.stringify({
    id: 'verified-user-id', email: 'verified@example.com',
  }), { status: 200 }))
  unsubscribe = vi.fn()
  auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
  auth.onAuthStateChange.mockImplementation((callback) => {
    notifyAuthChange = callback
    return { data: { subscription: { unsubscribe } } }
  })
  auth.signInWithOAuth.mockResolvedValue({ error: null })
  auth.signOut.mockResolvedValue({ error: null })
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('authentication', () => {
  it('shows loading until the saved session has been checked', async () => {
    renderApp()

    expect(screen.getByRole('status').textContent).toBe('Checking your session…')
    expect(screen.queryByRole('button')).toBeNull()
    await screen.findByRole('button', { name: 'Continue with Google' })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('restores the saved user on mount and after remounting', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    const firstMount = renderApp()

    await screen.findByText('Signed in as applicant@example.com')
    expect(screen.queryByRole('button', { name: 'Continue with Google' })).toBeNull()
    firstMount.unmount()

    renderApp()
    await screen.findByText('Signed in as applicant@example.com')
    expect(auth.getSession).toHaveBeenCalledTimes(2)
  })

  it('starts Google OAuth and prevents repeated clicks while redirecting', async () => {
    renderApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Continue with Google' }))

    await waitFor(() => {
      expect(auth.signInWithOAuth).toHaveBeenCalledWith({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/` },
      })
    })
    const button = screen.getByRole('button', { name: 'Redirecting to Google…' }) as HTMLButtonElement
    expect(button.disabled).toBe(true)
  })

  it('shows OAuth errors and allows retrying', async () => {
    auth.signInWithOAuth.mockResolvedValue({ error: new Error('Provider unavailable') })
    renderApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Continue with Google' }))

    expect((await screen.findByRole('alert')).textContent).toBe('Provider unavailable')
    const button = screen.getByRole('button', { name: 'Continue with Google' }) as HTMLButtonElement
    expect(button.disabled).toBe(false)
  })

  it('reflects auth changes and signs out of this browser session', async () => {
    auth.signOut.mockImplementation(async () => {
      notifyAuthChange('SIGNED_OUT', null)
      return { error: null }
    })
    renderApp()
    await screen.findByRole('button', { name: 'Continue with Google' })

    act(() => notifyAuthChange('SIGNED_IN', savedSession))
    expect(screen.getByText('Signed in as applicant@example.com')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    await screen.findByRole('button', { name: 'Continue with Google' })
    expect(auth.signOut).toHaveBeenCalledWith({ scope: 'local' })
    expect(screen.queryByText('Signed in as applicant@example.com')).toBeNull()
  })

  it('keeps the signed-in view when sign-out fails', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    auth.signOut.mockRejectedValue(new Error('Network unavailable'))
    renderApp()
    fireEvent.click(await screen.findByRole('button', { name: 'Sign out' }))

    expect((await screen.findByRole('alert')).textContent).toBe('Network unavailable')
    expect(screen.getByText('Signed in as applicant@example.com')).toBeTruthy()
    const button = screen.getByRole('button', { name: 'Sign out' }) as HTMLButtonElement
    expect(button.disabled).toBe(false)
  })

  it('reports session-loading errors and offers sign-in', async () => {
    auth.getSession.mockResolvedValue({
      data: { session: null }, error: new Error('Session expired'),
    })
    renderApp()

    expect((await screen.findByRole('alert')).textContent).toBe('Session expired')
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeTruthy()
  })

  it('does not restore an old session after a newer sign-out event', async () => {
    let resolveSession!: (value: { data: { session: Session }; error: null }) => void
    auth.getSession.mockReturnValue(new Promise((resolve) => { resolveSession = resolve }))
    renderApp()

    act(() => notifyAuthChange('SIGNED_OUT', null))
    await act(async () => {
      resolveSession({ data: { session: savedSession }, error: null })
    })

    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeTruthy()
    expect(screen.queryByText('Signed in as applicant@example.com')).toBeNull()
  })

  it('cleans up subscriptions during StrictMode checks and on unmount', async () => {
    const view = render(<StrictMode><MemoryRouter><App /></MemoryRouter></StrictMode>)
    await screen.findByRole('button', { name: 'Continue with Google' })

    expect(auth.onAuthStateChange).toHaveBeenCalledTimes(2)
    expect(unsubscribe).toHaveBeenCalledTimes(1)
    view.unmount()
    expect(unsubscribe).toHaveBeenCalledTimes(2)
  })
})

describe('navigation and profile', () => {
  it('shows navigation and does not fetch profile information on the home page', async () => {
    renderApp()
    await screen.findByRole('button', { name: 'Continue with Google' })

    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Sign in' }).getAttribute('href')).toBe('/')
    expect(screen.getByRole('link', { name: 'Profile' }).getAttribute('href')).toBe('/profile')
    expect(fetchProfile).not.toHaveBeenCalled()
  })

  it('fetches profile information with the bearer token when navigating to Profile', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    renderApp()
    await screen.findByRole('button', { name: 'Sign out' })
    fireEvent.click(screen.getByRole('link', { name: 'Profile' }))

    await screen.findByText('verified@example.com')
    expect(screen.getByText('verified-user-id')).toBeTruthy()
    expect(fetchProfile).toHaveBeenCalledWith(
      expect.stringMatching(/\/me$/),
      expect.objectContaining({
        headers: { Authorization: 'Bearer test-access-token' },
        signal: expect.any(AbortSignal),
      }),
    )
    expect(screen.getByRole('link', { name: 'Profile' }).getAttribute('aria-current')).toBe('page')
    expect(screen.queryByRole('button', { name: 'Sign out' })).toBeNull()
  })

  it('supports opening the profile route directly with a saved session', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    renderApp('/profile')

    await screen.findByText('verified@example.com')
    expect(fetchProfile).toHaveBeenCalledTimes(1)
  })

  it('asks signed-out users to sign in without calling the backend', async () => {
    renderApp('/profile')

    await screen.findByText('Sign in to view your profile')
    expect(fetchProfile).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('link', { name: 'Go to sign in' }))
    await screen.findByRole('button', { name: 'Continue with Google' })
  })

  it('shows a loading state and ignores late profile responses after sign-out', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    let finishRequest!: (response: Response) => void
    fetchProfile.mockReturnValue(new Promise((resolve) => { finishRequest = resolve }))
    renderApp('/profile')
    await screen.findByText('Loading your profile…')
    const signal = fetchProfile.mock.calls[0][1].signal as AbortSignal

    act(() => notifyAuthChange('SIGNED_OUT', null))
    expect(signal.aborted).toBe(true)
    await act(async () => {
      finishRequest(new Response(JSON.stringify({ id: 'old-user', email: 'old@example.com' })))
    })
    expect(screen.getByText('Sign in to view your profile')).toBeTruthy()
    expect(screen.queryByText('old@example.com')).toBeNull()
  })

  it('sends an updated token after the session refreshes', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    renderApp('/profile')
    await screen.findByText('verified@example.com')
    fetchProfile.mockResolvedValue(new Response(JSON.stringify({
      id: 'verified-user-id', email: 'verified@example.com',
    })))

    act(() => notifyAuthChange('TOKEN_REFRESHED', { ...savedSession, access_token: 'refreshed-token' }))

    await waitFor(() => expect(fetchProfile).toHaveBeenLastCalledWith(
      expect.stringMatching(/\/me$/),
      expect.objectContaining({ headers: { Authorization: 'Bearer refreshed-token' } }),
    ))
  })

  it('shows authentication and service errors without displaying profile data', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    fetchProfile.mockResolvedValue(new Response('{}', { status: 401 }))
    renderApp('/profile')

    expect((await screen.findByRole('alert')).textContent).toContain('Sign out and sign in again')
    expect(screen.queryByText('verified-user-id')).toBeNull()

    fetchProfile.mockResolvedValue(new Response('{}', { status: 503 }))
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect((await screen.findByRole('alert')).textContent).toContain('temporarily unavailable')
  })

  it('allows retrying after a network failure', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    fetchProfile.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    renderApp('/profile')

    expect((await screen.findByRole('alert')).textContent).toContain('backend is running')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await screen.findByText('verified@example.com')
    expect(screen.queryByRole('alert')).toBeNull()
  })
})
