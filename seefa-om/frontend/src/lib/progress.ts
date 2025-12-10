import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ProgressState {
  completedTutorials: Record<string, string[]> // userId -> tutorialIds
  markComplete: (userId: string, tutorialId: string) => void
  isComplete: (userId: string, tutorialId: string) => boolean
  getProgress: (userId: string, totalTutorials: number) => number
}

export const useProgress = create<ProgressState>()(
  persist(
    (set, get) => ({
      completedTutorials: {},
      markComplete: (userId: string, tutorialId: string) => {
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
