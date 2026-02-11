import axios from 'axios'
import type { SpiderStatus, SpiderStats, CrawledItem, LogEntry, APIResponse } from '../types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const spiderAPI = {
  async getStatus(spiderType?: string): Promise<APIResponse<SpiderStatus | Record<string, SpiderStatus>>> {
    try {
      const url = spiderType ? `/spiders/status/?type=${spiderType}` : '/spiders/status/'
      const response = await api.get(url)
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '获取状态失败',
      }
    }
  },

  async controlSpider(action: string, spiderType: string): Promise<APIResponse<{ message: string }>> {
    try {
      const response = await api.post('/spiders/control/', {
        action,
        spider_type: spiderType,
      })
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '操作失败',
      }
    }
  },

  async getData(params?: {
    type?: string
    page?: number
    page_size?: number
    keyword?: string
    date_start?: string
    date_end?: string
    sort_field?: string
    sort_order?: string
  }): Promise<APIResponse<CrawledItem[]> & { total?: number; page?: number; page_size?: number }> {
    try {
      const response = await api.get('/spiders/data/', { params })
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '获取数据失败',
        data: [],
        total: 0,
      }
    }
  },

  async getFiles(params?: {
    type?: string
    page?: number
    page_size?: number
    keyword?: string
  }): Promise<APIResponse<{ name: string; path: string; size: number; size_formatted: string; extension: string; modified_time: number; modified_time_formatted: string }[]> & { total?: number; page?: number; page_size?: number }> {
    try {
      const response = await api.get('/spiders/files/', { params })
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '获取文件列表失败',
        data: [],
        total: 0,
      }
    }
  },

  async getLogs(params: {
    type: string
    level?: string
    keyword?: string
    limit?: number
    offset?: number
  }): Promise<APIResponse<LogEntry[]>> {
    try {
      const response = await api.get('/spiders/logs/', { params })
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '获取日志失败',
        logs: [],
      }
    }
  },

  async getStats(spiderType?: string): Promise<APIResponse<SpiderStats>> {
    try {
      const url = spiderType ? `/spiders/stats/?type=${spiderType}` : '/spiders/stats/'
      const response = await api.get(url)
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '获取统计失败',
      }
    }
  },

  async checkHealth(spiderType?: string): Promise<
    APIResponse<{
      redis_connected: boolean
      data_files: Record<string, { exists: boolean; size_mb: number }>
      file_dirs: Record<string, { file_count: number; html_count: number }>
      spiders: Record<string, { name: string; status: string; running: boolean }>
    }> & { timestamp?: string; healthy?: boolean }
  > {
    try {
      const url = spiderType ? `/spiders/health/?type=${spiderType}` : '/spiders/health/'
      const response = await api.get(url)
      return response.data
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '健康检查失败',
        health: null,
      }
    }
  },
}

export default api
