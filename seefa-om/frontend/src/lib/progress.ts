import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const API_BASE = 'http://austx-mdso-logs-02.chtrse.com/correlation-engine/api'

interface ProgressState {
  completedTutorials: Record<string, string[]> // userId -> tutorialIds (local cache)
  markComplete: (userId: string, tutorialId: string) => Promise<void>
  isComplete: (userId: string, tutorialId: string) => boolean
  getProgress: (userId: string, totalTutorials: number) => number
  loadProgress: (userId: string) => Promise<void>
}

export const useProgress = create<ProgressState>()(
  persist(
    (set, get) => ({
      completedTutorials: {},

      markComplete: async (userId: string, tutorialId: string) => {
        try {
          // Call backend API
          const response = await fetch(
            `${API_BASE}/auth/user/${userId}/tutorial/complete`,
            {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({ tutorial_id: tutorialId }),
            }
          )

          if (!response.ok) {
            throw new Error('Failed to mark tutorial complete')
          }

          // Update local state
          set((state) => {
            const userProgress = state.completedTutorials[userId] || []
            if (!userProgress.includes(tutorialId)) {
              return {
                completedTutorials: {
                  ...state.completedTutorials,
                  [userId]: [...userProgress, tutorialId]
                }
              }
            }
            return state
          })
        } catch (error) {
          console.error('Failed to mark tutorial complete:', error)
          throw error
        }
      },

      loadProgress: async (userId: string) => {
        try {
          const response = await fetch(
            `${API_BASE}/auth/user/${userId}/progress`
          )

          if (!response.ok) {
            throw new Error('Failed to load progress')
          }

          const progress = await response.json()
          const tutorialIds = progress.map((p: any) => p.tutorial_id)

          set((state) => ({
            completedTutorials: {
              ...state.completedTutorials,
              [userId]: tutorialIds
            }
          }))
        } catch (error) {
          console.error('Failed to load progress:', error)
        }
      },

      isComplete: (userId: string, tutorialId: string) => {
        const state = get()
        return state.completedTutorials[userId]?.includes(tutorialId) || false
      },

      getProgress: (userId: string, totalTutorials: number) => {
        const state = get()
        const completed = state.completedTutorials[userId]?.length || 0
        return Math.round((completed / totalTutorials) * 100)
      }
    }),
    { name: 'progress-storage' }
  )
)
