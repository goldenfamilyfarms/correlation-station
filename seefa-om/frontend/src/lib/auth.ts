import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_BASE = 'http://austx-mdso-logs-02.chtrse.com/correlation-engine/api'

interface User {
  id: string
  username: string
  email: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        try {
          const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Login failed')
          }

          const user = await response.json()
          set({ user, isAuthenticated: true })
        } catch (error) {
          console.error('Login error:', error)
          throw error
        }
      },

      register: async (username: string, email: string, password: string) => {
        try {
          const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, email, password }),
          })

          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail || 'Registration failed')
          }

          const user = await response.json()
          set({ user, isAuthenticated: true })
        } catch (error) {
          console.error('Registration error:', error)
          throw error
        }
      },

      logout: () => set({ user: null, isAuthenticated: false })
    }),
    { name: 'auth-storage' }
  )
)
