import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabaseClient'

export function useAuth() {
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [pendingAction, setPendingAction] = useState<'sign-in' | 'sign-out' | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    let authChanged = false

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, nextSession) => {
        // getSession handles initial loading, including any initialization error.
        if (!active || event === 'INITIAL_SESSION') return

        authChanged = true
        setSession(nextSession)
        setIsLoading(false)
        if (event === 'SIGNED_IN' || event === 'SIGNED_OUT') {
          setPendingAction(null)
          setErrorMessage(null)
        }
      },
    )

    async function loadSession() {
      try {
        const { data, error } = await supabase.auth.getSession()

        // A later sign-in/sign-out event takes priority over this initial read.
        if (!active || authChanged) return
        if (error) throw error

        setSession(data.session)
      } catch (error) {
        if (!active || authChanged) return
        setErrorMessage(
          error instanceof Error ? error.message : 'Unable to restore your session.',
        )
      } finally {
        if (active && !authChanged) setIsLoading(false)
      }
    }

    void loadSession()

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  async function signInWithGoogle() {
    setErrorMessage(null)
    setPendingAction('sign-in')

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      })

      if (error) throw error
      // Keep the button disabled while the browser redirects to Google.
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Unable to start Google sign-in.',
      )
      setPendingAction(null)
    }
  }

  async function signOut() {
    setErrorMessage(null)
    setPendingAction('sign-out')

    try {
      const { error } = await supabase.auth.signOut({ scope: 'local' })
      if (error) throw error
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : 'Unable to sign out.',
      )
    } finally {
      setPendingAction(null)
    }
  }

  return {
    session,
    isLoading,
    pendingAction,
    errorMessage,
    signInWithGoogle,
    signOut,
  }
}
