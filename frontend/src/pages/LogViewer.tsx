import React from 'react'
import { Card, Select, Space, Button, Tag, Row, Col, Statistic, Input, Pagination } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { spiderAPI } from '../services/api'
import type { LogEntry } from '../types'

const { Option } = Select

interface LogStats {
  links: number
  details: number
  download: number
  error: number
  total: number
}

const LogViewer: React.FC = () => {
  const [logs, setLogs] = React.useState<LogEntry[]>([])
  const [isLoading, setIsLoading] = React.useState(false)
  const [spiderType, setSpiderType] = React.useState<string>('nhsa')
  const [logType, setLogType] = React.useState<string>('all')
  const [keyword, setKeyword] = React.useState<string>('')
  const [stats, setStats] = React.useState<LogStats>({ links: 0, details: 0, download: 0, error: 0, total: 0 })
  const logContainerRef = React.useRef<HTMLDivElement>(null)
  const [currentPage, setCurrentPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(100)
  const [totalLogs, setTotalLogs] = React.useState(0)

  const spiderOptions = [
    { value: 'nhsa', label: '国家医保局爬虫', name: 'NHSA' },
    { value: 'wjw', label: '卫生健康委爬虫', name: 'WJW' },
    { value: 'flkgov', label: '国家法律法规数据库爬虫', name: 'FLKGOV' },
  ]

  const fetchLogs = async () => {
    setIsLoading(true)
    try {
      const offset = (currentPage - 1) * pageSize
      const response = await spiderAPI.getLogs({
        type: spiderType,
        level: logType !== 'all' ? logType : undefined,
        limit: pageSize,
        offset: offset,
      })
      if (response.success && response.logs) {
        setLogs((response.logs as LogEntry[]) || [])
        setTotalLogs(response.total || 0)
        calculateStats(response.logs as LogEntry[])
      }
    } catch (error) {
      console.error('获取日志失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const calculateStats = (logList: LogEntry[]) => {
    const newStats = { links: 0, details: 0, download: 0, error: 0, total: logList.length }
    logList.forEach(log => {
      const msg = log.message || ''
      const level = log.level?.toLowerCase() || ''
      
      if (level === 'error' || msg.includes('[错误]') || msg.includes('失败')) {
        newStats.error++
      } else if (msg.includes('翻页') || msg.includes('栏目') || msg.includes('入队') || msg.includes('链接收集')) {
        newStats.links++
      } else if (msg.includes('详情') || msg.includes('Crawl success') || msg.includes('已爬取')) {
        newStats.details++
      } else if (msg.includes('下载') || msg.includes('Download')) {
        newStats.download++
      }
    })
    setStats(newStats)
  }

  React.useEffect(() => {
    setCurrentPage(1)
    fetchLogs()
  }, [spiderType, logType])

  React.useEffect(() => {
    fetchLogs()
  }, [currentPage, pageSize])

  React.useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const getLogColor = (logLevel: string) => {
    switch (logLevel.toLowerCase()) {
      case 'debug': return '#6a9955'
      case 'info': return '#d4d4d4'
      case 'warning': return '#cca700'
      case 'error': return '#f14c4c'
      default: return '#d4d4d4'
    }
  }

  const getLogBgColor = (message: string, level: string) => {
    const msg = message || ''
    if (level.toLowerCase() === 'error' || msg.includes('[错误]') || msg.includes('失败')) {
      return 'rgba(241, 76, 76, 0.1)'
    }
    if (msg.includes('[成功]') || msg.includes('Crawl success') || msg.includes('[下载] 成功')) {
      return 'rgba(106, 153, 85, 0.1)'
    }
    if (msg.includes('[翻页]') || msg.includes('入队:')) {
      return 'rgba(86, 156, 214, 0.1)'
    }
    if (msg.includes('[详情]')) {
      return 'rgba(206, 145, 120, 0.1)'
    }
    return 'transparent'
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('zh-CN')
    } catch {
      return ''
    }
  }

  const getSpiderName = (type: string) => {
    return spiderOptions.find(s => s.value === type)?.name || type.toUpperCase()
  }

  return (
    <div className="log-page" style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 16 }}>日志管理</h2>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="翻页/链接" value={stats.links} valueStyle={{ color: '#569cd6' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="详情爬取" value={stats.details} valueStyle={{ color: '#ce9178' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="文件下载" value={stats.download} valueStyle={{ color: '#6a9955' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="错误" value={stats.error} valueStyle={{ color: '#f14c4c' }} />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ display: 'flex', flexWrap: 'wrap' }}>
          <span>爬虫项目：</span>
          <Select value={spiderType} onChange={setSpiderType} style={{ width: 180 }}>
            {spiderOptions.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
          
          <span>日志类型：</span>
          <Select value={logType} onChange={setLogType} style={{ width: 140 }}>
            <Option value="all">全部日志</Option>
            <Option value="links">翻页/链接</Option>
            <Option value="details">详情爬取</Option>
            <Option value="download">文件下载</Option>
            <Option value="error">错误日志</Option>
          </Select>
          
          <Input.Search
            placeholder="搜索日志内容"
            style={{ width: 200 }}
            allowClear
            enterButton={<SearchOutlined />}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={() => fetchLogs()}
          />
          
          <Button icon={<ReloadOutlined />} onClick={fetchLogs} loading={isLoading}>
            刷新
          </Button>
        </Space>
      </Card>

      <Card>
        <div style={{ marginBottom: 8, color: '#999', fontSize: 12 }}>
          共 {stats.total} 条日志 | 当前爬虫: {getSpiderName(spiderType)} | 筛选: {logType === 'all' ? '全部' : logType}
        </div>
        <div className="log-viewer" ref={logContainerRef} style={{ 
          maxHeight: '600px', 
          overflow: 'auto', 
          background: '#1e1e1e', 
          padding: '12px',
          borderRadius: '4px',
          fontFamily: 'Consolas, Monaco, "Courier New", monospace',
          fontSize: '13px',
          lineHeight: '1.6'
        }}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>加载中...</div>
          ) : logs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>暂无日志</div>
          ) : (
            logs.map((log, index) => {
              const msg = log.message || ''
              const bgColor = getLogBgColor(msg, log.level || 'info')
              
              return (
                <div 
                  key={index} 
                  className={`log-entry ${log.level || 'info'}`}
                  style={{ 
                    padding: '4px 8px', 
                    marginBottom: '2px',
                    backgroundColor: bgColor,
                    borderRadius: '2px',
                    color: '#d4d4d4'
                  }}
                >
                  <span style={{ color: '#569cd6', marginRight: 8 }}>
                    {formatTimestamp(log.timestamp || '')}
                  </span>
                  <Tag 
                    color={getLogColor(log.level || 'info')} 
                    style={{ marginRight: 8, fontSize: '10px', padding: '0 4px' }}
                  >
                    {(log.level || 'INFO').toUpperCase()}
                  </Tag>
                  <span style={{ color: '#d4d4d4' }}>{msg}</span>
                </div>
              )
            })
          )}
        </div>
        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end' }}>
          <Pagination
            current={currentPage}
            pageSize={pageSize}
            total={totalLogs}
            onChange={(page, size) => {
              setCurrentPage(page)
              setPageSize(size)
            }}
            showSizeChanger
            showQuickJumper
            pageSizeOptions={[50, 100, 200, 500]}
            showTotal={(total) => `共 ${total} 条日志`}
          />
        </div>
      </Card>
    </div>
  )
}

export default LogViewer
