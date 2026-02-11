import React from 'react'
import { Table, Card, Input, Select, Space, Pagination, Spin, Button, Modal, Descriptions, Radio, DatePicker, message } from 'antd'
import type { RadioChangeEvent } from 'antd'
import { EyeOutlined, DownloadOutlined, SearchOutlined, FileOutlined, FolderOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { spiderAPI } from '../services/api'
import type { CrawledItem } from '../types'

const { RangePicker } = DatePicker

interface FileItem {
  name: string
  path: string
  size: number
  size_formatted: string
  extension: string
  modified_time: number
  modified_time_formatted: string
}

const DataDisplay: React.FC = () => {
  const [contentType, setContentType] = React.useState<'data' | 'files'>('data')
  const [spiderType, setSpiderType] = React.useState<string>('nhsa')
  const [dateRange, setDateRange] = React.useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([null, null])
  const [searchKeyword, setSearchKeyword] = React.useState('')
  
  const [items, setItems] = React.useState<CrawledItem[]>([])
  const [fileItems, setFileItems] = React.useState<FileItem[]>([])
  const [total, setTotal] = React.useState(0)
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(20)
  const [isLoading, setIsLoading] = React.useState(false)
  const [selectedItem, setSelectedItem] = React.useState<CrawledItem | null>(null)
  const [detailVisible, setDetailVisible] = React.useState(false)
  const [fileListVisible, setFileListVisible] = React.useState(false)
  const [currentFiles, setCurrentFiles] = React.useState<{name: string; path: string}[]>([])

  React.useEffect(() => {
    fetchData()
  }, [spiderType, contentType, dateRange, page, pageSize, searchKeyword])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      if (contentType === 'data') {
        const response = await spiderAPI.getData({
          type: spiderType,
          page,
          page_size: pageSize,
          keyword: searchKeyword || undefined,
          date_start: dateRange?.[0]?.format('YYYY-MM-DD') || undefined,
          date_end: dateRange?.[1]?.format('YYYY-MM-DD') || undefined,
        })
        if (response.success) {
          setItems(response.data || [])
          setTotal(response.total || 0)
          if ((response.total || 0) === 0 && (searchKeyword || dateRange)) {
            message.info('未找到符合条件的数据')
          }
        }
      } else {
        const response = await spiderAPI.getFiles({
          type: spiderType,
          page,
          page_size: pageSize,
          keyword: searchKeyword || undefined
        })
        if (response.success) {
          setFileItems((response.data as FileItem[]) || [])
          setTotal(response.total || 0)
          if ((response.total || 0) === 0 && searchKeyword) {
            message.info('未找到符合条件的数据')
          }
        }
      }
    } catch (error) {
      console.error('获取数据失败:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSpiderTypeChange = (value: string) => {
    setSpiderType(value)
    setDateRange([null, null])
    setSearchKeyword('')
    setPage(1)
  }

  const handleContentTypeChange = (e: RadioChangeEvent) => {
    setContentType(e.target.value as 'data' | 'files')
    setDateRange([null, null])
    setSearchKeyword('')
    setPage(1)
  }

  const handleSearch = () => {
    setPage(1)
  }

  const handlePageChange = (newPage: number, newPageSize?: number) => {
    setPage(newPage)
    if (newPageSize) {
      setPageSize(newPageSize)
    }
  }

  const showDetail = (item: CrawledItem) => {
    setSelectedItem(item)
    setDetailVisible(true)
  }

  const showFileList = async (item: CrawledItem) => {
    if (!item.item_id || (item.file_count || 0) === 0) return
    
    setIsLoading(true)
    try {
      const response = await spiderAPI.getFiles({
        type: spiderType,
        keyword: `${item.item_id}_`,
      })
      if (response.success) {
        const files = (response.data || []).map((f: FileItem) => ({
          name: f.name,
          path: f.path
        }))
        setCurrentFiles(files)
      } else {
        setCurrentFiles([])
      }
    } catch (error) {
      console.error('获取文件列表失败:', error)
      setCurrentFiles([])
    } finally {
      setIsLoading(false)
      setFileListVisible(true)
    }
  }

  const spiderOptions = [
    { value: 'nhsa', label: '国家医保局爬虫' },
    { value: 'wjw', label: '卫生健康委爬虫' },
  ]

  const dataColumns = [
    {
      title: 'ID',
      dataIndex: 'item_id',
      key: 'item_id',
      width: 140,
      render: (id: number) => id?.toString() || '-',
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: 350,
    },
    {
      title: '发布日期',
      dataIndex: 'publish_date',
      key: 'publish_date',
      width: 110,
    },
    {
      title: '链接',
      dataIndex: 'url',
      key: 'url',
      width: 80,
      render: (url: string) => (
        <Button 
          type="link" 
          size="small"
          href={url} 
          target="_blank"
        >
          访问
        </Button>
      ),
    },
    {
      title: '附件',
      dataIndex: 'file_count',
      key: 'file_count',
      width: 80,
      render: (count: number, record: CrawledItem) => {
        const fileCount = count || 0
        if (fileCount === 0) {
          return <span style={{ color: '#999' }}>0个</span>
        }
        return (
          <Button 
            type="link" 
            size="small"
            onClick={() => showFileList(record)}
          >
            {fileCount}个
          </Button>
        )
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: CrawledItem) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => showDetail(record)}
        >
          详情
        </Button>
      ),
    },
  ]

  const fileColumns = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record: FileItem) => (
        <Space>
          <FileOutlined />
          <a href={`/api/v1/spiders/download/?path=${encodeURIComponent(record.path)}`} target="_blank" rel="noopener noreferrer">
            {name}
          </a>
        </Space>
      ),
    },
    {
      title: '大小',
      dataIndex: 'size_formatted',
      key: 'size',
      width: 100,
    },
    {
      title: '修改时间',
      dataIndex: 'modified_time_formatted',
      key: 'modified_time',
      width: 180,
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: FileItem) => (
        <Button
          type="link"
          size="small"
          icon={<DownloadOutlined />}
          href={`/api/v1/spiders/download/?path=${encodeURIComponent(record.path)}`}
          target="_blank"
        >
          下载
        </Button>
      ),
    },
  ]

  const currentColumns = contentType === 'data' ? dataColumns : fileColumns as any
  const currentItems = contentType === 'data' ? items : fileItems

  return (
    <div className="data-page" style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 16 }}>数据展示</h2>
      
      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ display: 'flex', flexWrap: 'wrap' }}>
          <Radio.Group
            value={contentType}
            onChange={handleContentTypeChange}
            optionType="button"
            buttonStyle="solid"
          >
            <Radio.Button value="data"><FolderOutlined /> 数据</Radio.Button>
            <Radio.Button value="files"><FileOutlined /> 附件</Radio.Button>
          </Radio.Group>
          
          <Select
            placeholder="选择爬虫"
            style={{ width: 180 }}
            value={spiderType}
            onChange={handleSpiderTypeChange}
            options={spiderOptions}
          />
          
          {contentType === 'data' && (
            <RangePicker
              placeholder={['开始日期', '结束日期']}
              style={{ width: 260 }}
              value={dateRange}
              onChange={(dates) => {
                setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null])
                setPage(1)
              }}
            />
          )}
          
          <Input.Search
            placeholder={contentType === 'data' ? '搜索标题' : '搜索文件名'}
            style={{ width: 250 }}
            allowClear
            enterButton={<SearchOutlined />}
            value={searchKeyword}
            onChange={(e) => setSearchKeyword(e.target.value)}
            onSearch={handleSearch}
          />
        </Space>
      </Card>

      <Card className="data-table">
        {isLoading ? (
          <div className="loading-container">
            <Spin size="large" />
          </div>
        ) : (
          <>
            <Table
              dataSource={currentItems as any}
              columns={currentColumns}
              rowKey={(record: any) => record.item_id?.toString() || record.url}
              pagination={false}
            />
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Pagination
                current={page}
                pageSize={pageSize}
                total={total}
                onChange={handlePageChange}
                showSizeChanger
                showQuickJumper
                showTotal={(total) => `共 ${total} 条`}
              />
            </div>
          </>
        )}
      </Card>

      <Modal
        title="详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
          <Button key="open" type="primary" onClick={() => selectedItem && window.open(selectedItem.url, '_blank')}>
            打开原文
          </Button>,
        ]}
        width={800}
      >
        {selectedItem && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="ID">{selectedItem.item_id}</Descriptions.Item>
            <Descriptions.Item label="发布日期">{selectedItem.publish_date}</Descriptions.Item>
            <Descriptions.Item label="标题" span={2}>{selectedItem.title}</Descriptions.Item>
            <Descriptions.Item label="来源URL" span={2}>
              <a href={selectedItem.url} target="_blank" rel="noopener noreferrer">
                {selectedItem.url}
              </a>
            </Descriptions.Item>
            {selectedItem.data && (
              <Descriptions.Item label="其他数据" span={2}>
                <pre style={{ margin: 0, fontSize: 11, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                  {JSON.stringify(selectedItem.data, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      <Modal
        title="附件列表"
        open={fileListVisible}
        onCancel={() => setFileListVisible(false)}
        footer={[
          <Button key="close" onClick={() => setFileListVisible(false)}>
            关闭
          </Button>,
        ]}
        width={600}
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : currentFiles.length > 0 ? (
          <Descriptions column={1} bordered size="small">
            {currentFiles.map((file, index) => (
              <Descriptions.Item key={index} label={file.name}>
                <Button
                  type="link"
                  size="small"
                  icon={<DownloadOutlined />}
                  href={`/api/v1/spiders/download/?path=${encodeURIComponent(file.path)}`}
                  target="_blank"
                >
                  下载
                </Button>
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无附件
          </div>
        )}
      </Modal>
    </div>
  )
}

export default DataDisplay
