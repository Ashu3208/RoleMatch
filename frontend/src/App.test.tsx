import { StrictMode } from 'react'
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

let notifyAuthChange: (event: AuthChangeEvent, session: Session | null) => void
let unsubscribe: ReturnType<typeof vi.fn>

beforeEach(() => {
  vi.resetAllMocks()
  unsubscribe = vi.fn()
  auth.getSession.mockResolvedValue({ data: { session: null }, error: null })
  auth.onAuthStateChange.mockImplementation((callback) => {
    notifyAuthChange = callback
    return { data: { subscription: { unsubscribe } } }
  })
  auth.signInWithOAuth.mockResolvedValue({ error: null })
  auth.signOut.mockResolvedValue({ error: null })
})

afterEach(cleanup)

describe('authentication', () => {
  it('shows loading until the saved session has been checked', async () => {
    render(<App />)

    expect(screen.getByRole('status').textContent).toBe('Checking your session…')
    expect(screen.queryByRole('button')).toBeNull()
    await screen.findByRole('button', { name: 'Continue with Google' })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('restores the saved user on mount and after remounting', async () => {
    auth.getSession.mockResolvedValue({ data: { session: savedSession }, error: null })
    const firstMount = render(<App />)

    await screen.findByText('Signed in as applicant@example.com')
    expect(screen.queryByRole('button', { name: 'Continue with Google' })).toBeNull()
    firstMount.unmount()

    render(<App />)
    await screen.findByText('Signed in as applicant@example.com')
    expect(auth.getSession).toHaveBeenCalledTimes(2)
  })

  it('starts Google OAuth and prevents repeated clicks while redirecting', async () => {
    render(<App />)
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
    render(<App />)
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
    render(<App />)
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
    render(<App />)
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
    render(<App />)

    expect((await screen.findByRole('alert')).textContent).toBe('Session expired')
    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeTruthy()
  })

  it('does not restore an old session after a newer sign-out event', async () => {
    let resolveSession!: (value: { data: { session: Session }; error: null }) => void
    auth.getSession.mockReturnValue(new Promise((resolve) => { resolveSession = resolve }))
    render(<App />)

    act(() => notifyAuthChange('SIGNED_OUT', null))
    await act(async () => {
      resolveSession({ data: { session: savedSession }, error: null })
    })

    expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeTruthy()
    expect(screen.queryByText('Signed in as applicant@example.com')).toBeNull()
  })

  it('cleans up subscriptions during StrictMode checks and on unmount', async () => {
    const view = render(<StrictMode><App /></StrictMode>)
    await screen.findByRole('button', { name: 'Continue with Google' })

    expect(auth.onAuthStateChange).toHaveBeenCalledTimes(2)
    expect(unsubscribe).toHaveBeenCalledTimes(1)
    view.unmount()
    expect(unsubscribe).toHaveBeenCalledTimes(2)
  })
})
