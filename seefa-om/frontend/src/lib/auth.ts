import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  username: string
  email: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      login: async (username: string, password: string) => {
        // Simple auth - in production, call backend API
        if (username && password) {
          const user = {
            id: Math.random().toString(36).substr(2, 9),
            username,
            email: `${username}@charter.com`
          }
          set({ user, isAuthenticated: true })
        }
      },
      logout: () => set({ user: null, isAuthenticated: false })
    }),
    { name: 'auth-storage' }
  )
)
