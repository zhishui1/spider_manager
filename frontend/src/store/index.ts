import { create } from 'zustand'
import type { SpiderStatus, SpiderStats, CrawledItem } from '../types'
import { spiderAPI } from '../services/api'

interface SpiderStore {
  statuses: Record<string, SpiderStatus>
  stats: Record<string, SpiderStats>
  isLoading: boolean
  error: string | null
  lastUpdated: string | null

  fetchStatus: (spiderType?: string) => Promise<void>
  fetchStats: (spiderType?: string) => Promise<void>
  controlSpider: (action: string, spiderType: string) => Promise<boolean>
  clearError: () => void
}

export const useSpiderStore = create<SpiderStore>((set, get) => ({
  statuses: {},
  stats: {},
  isLoading: false,
  error: null,
  lastUpdated: null,

  fetchStatus: async (spiderType) => {
    set({ isLoading: true, error: null })
    try {
      const response = await spiderAPI.getStatus(spiderType)
      if (response.success && response.data) {
        if (spiderType) {
          const statusData = response.data as SpiderStatus & SpiderStats
          set((state) => ({
            statuses: { ...state.statuses, [spiderType]: statusData },
            stats: { ...state.stats, [spiderType]: statusData },
            isLoading: false,
            lastUpdated: new Date().toISOString(),
          }))
        } else {
          const allStatus = response.data as Record<string, SpiderStatus & SpiderStats>
          const newStatuses: Record<string, SpiderStatus> = {}
          const newStats: Record<string, SpiderStats> = {}
          for (const [type, data] of Object.entries(allStatus)) {
            newStatuses[type] = data
            newStats[type] = data
          }
          set({
            statuses: newStatuses,
            stats: newStats,
            isLoading: false,
            lastUpdated: new Date().toISOString(),
          })
        }
      } else {
        set({ isLoading: false, error: response.error || '获取状态失败' })
      }
    } catch (error) {
      set({ error: '获取状态失败', isLoading: false })
    }
  },

  fetchStats: async (spiderType) => {
    try {
      const response = await spiderAPI.getStats(spiderType)
      if (response.success && response.stats) {
        const type = spiderType || 'nhsa'
        set((state) => ({
          stats: { ...state.stats, [type]: response.stats as SpiderStats },
        }))
      }
    } catch (error) {
      console.error('获取统计失败:', error)
    }
  },

  controlSpider: async (action, spiderType) => {
    set({ error: null })
    try {
      const response = await spiderAPI.controlSpider(action, spiderType)
      if (response.success) {
        await get().fetchStatus(spiderType)
        return true
      } else {
        set({ error: response.error || `${action}操作失败` })
        return false
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '操作失败'
      set({ error: errorMessage })
      return false
    }
  },

  clearError: () => {
    set({ error: null })
  },
}))

interface DataStore {
  items: CrawledItem[]
  total: number
  page: number
  pageSize: number
  isLoading: boolean
  error: string | null
  categories: string[]

  fetchData: (params?: {
    type?: string
    page?: number
    pageSize?: number
    category?: string
    keyword?: string
  }) => Promise<void>
  setPage: (page: number) => void
  setPageSize: (pageSize: number) => void
}

export const useDataStore = create<DataStore>((set, get) => ({
  items: [],
  total: 0,
  page: 1,
  pageSize: 20,
  isLoading: false,
  error: null,
  categories: [],

  fetchData: async (params) => {
    set({ isLoading: true, error: null })
    try {
      const { page, pageSize, ...rest } = get()
      const response = await spiderAPI.getData({
        type: params?.type || 'nhsa',
        page: params?.page || page,
        page_size: params?.pageSize || pageSize,
        ...rest,
        ...params,
      })
      if (response.success) {
        const data = response.data as CrawledItem[] || []
        const categories = [...new Set(data.map((item) => item.data?.category || '未知').filter(Boolean) as string[])]
        set({
          items: data,
          total: response.total || 0,
          page: response.page || 1,
          categories,
          isLoading: false,
        })
      } else {
        set({ error: response.error || '获取数据失败', isLoading: false })
      }
    } catch (error) {
      set({ error: '获取数据失败', isLoading: false })
    }
  },

  setPage: (page) => {
    set({ page })
    get().fetchData({ page })
  },

  setPageSize: (pageSize) => {
    set({ pageSize, page: 1 })
    get().fetchData({ pageSize: 1 })
  },
}))

interface LogStore {
  logs: Array<{
    timestamp?: string
    level: string
    message: string
    raw?: boolean
  }>
  isLoading: boolean
  error: string | null

  fetchLogs: (params: {
    type: string
    level?: string
    limit?: number
  }) => Promise<void>
  clearLogs: () => void
}

export const useLogStore = create<LogStore>((set) => ({
  logs: [],
  isLoading: false,
  error: null,

  fetchLogs: async (params) => {
    set({ isLoading: true, error: null })
    try {
      const response = await spiderAPI.getLogs(params)
      if (response.success) {
        set({
          logs: (response.logs as LogStore['logs']) || [],
          isLoading: false,
        })
      } else {
        set({ error: response.error || '获取日志失败', isLoading: false })
      }
    } catch (error) {
      set({ error: '获取日志失败', isLoading: false })
    }
  },

  clearLogs: () => {
    set({ logs: [] })
  },
}))

interface HealthStore {
  health: {
    redis_connected: boolean
    data_files: Record<string, { exists: boolean; size_mb: number }>
    file_dirs: Record<string, { file_count: number; html_count: number }>
    spiders: Record<string, { name: string; status: string; running: boolean }>
  } | null
  isLoading: boolean
  error: string | null
  lastChecked: string | null

  checkHealth: (spiderType?: string) => Promise<void>
}

export const useHealthStore = create<HealthStore>((set) => ({
  health: null,
  isLoading: false,
  error: null,
  lastChecked: null,

  checkHealth: async (spiderType) => {
    set({ isLoading: true, error: null, health: null })
    try {
      const response = await spiderAPI.checkHealth(spiderType)
      if (response.success && response.health) {
        set({
          health: response.health as HealthStore['health'],
          isLoading: false,
          lastChecked: response.timestamp || new Date().toISOString(),
        })
      } else {
        set({ error: response.error || '健康检查失败', isLoading: false, health: null })
      }
    } catch (error) {
      set({ error: '健康检查失败', isLoading: false, health: null })
    }
  },
}))
