export interface SpiderStatus {
  status: string
  running: boolean
  paused?: boolean
  pid?: number
  exit_code?: number
  redis_status?: string
  reason?: string
  version?: number
  progress?: {
    crawled?: string
    total?: string
    current_category?: string
    errors?: string
    updated_at?: string
  }
  error_count?: number
  links_collected?: number
  details_crawled?: number
  pending_links?: number
  total_items?: number
  categories?: Record<string, number>
  date_range?: {
    earliest?: string
    latest?: string
  }
  file_count?: number
  last_update?: string
  spider_name?: string
  spider_type?: string
}

export interface SpiderStats {
  total_items: number
  categories: Record<string, number>
  date_range: {
    earliest?: string
    latest?: string
  }
  file_count: number
  file_types?: Record<string, number>
  html_count?: number
  crawled_count?: number
  visited_urls?: number
  last_update?: string
}

export interface CrawledItem {
  item_id?: number
  title: string
  publish_date: string
  url: string
  data?: Record<string, unknown>
  file_count?: number
}

export interface CrawledFile {
  name: string
  path: string
  size: number
  size_formatted: string
  extension: string
  modified_time: number
  modified_time_formatted: string
}

export interface LogEntry {
  timestamp?: string
  level: string
  message: string
  url?: string
  type?: string
  raw?: boolean
  extra?: Record<string, unknown>
}

export interface APIResponse<T> {
  success: boolean
  data?: T
  stats?: T
  logs?: LogEntry[]
  health?: unknown
  error?: string
  total?: number
  page?: number
  page_size?: number
  timestamp?: string
  healthy?: boolean
  message?: string
}

export interface SpiderControlRequest {
  action: 'start' | 'stop' | 'pause' | 'resume'
  spider_type: string
}

export interface HealthInfo {
  redis_connected: boolean
  data_files: Record<string, { exists: boolean; size_mb: number }>
  file_dirs: Record<string, { file_count: number; html_count: number }>
  spiders: Record<string, { name: string; status: string; running: boolean }>
}
