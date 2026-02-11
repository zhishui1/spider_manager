import React from 'react'
import { Card, Row, Col, Button, Space, Divider, message, Progress, Tag, Alert } from 'antd'
import {
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useSpiderStore } from '../store'
import type { SpiderStatus } from '../types'

const SpiderManager: React.FC = () => {
  const { statuses, error, clearError, fetchStatus, controlSpider } = useSpiderStore()

  React.useEffect(() => {
    fetchStatus()
  }, [])

  const handleControl = async (action: string, spiderType: string) => {
    clearError()
    const actionNames: Record<string, string> = {
      start: '启动',
      stop: '停止',
      pause: '暂停',
      resume: '恢复'
    }
    const success = await controlSpider(action, spiderType)
    if (success) {
      message.success(`${actionNames[action]}成功`)
    } else {
      message.error(`${actionNames[action]}失败: ${error || '未知错误'}`)
    }
  }

  const getSpiderConfig = (spiderType: string) => {
    switch (spiderType) {
      case 'nhsa':
        return {
          name: '国家医保局爬虫',
          description: '爬取国家医疗保障局官网的政策法规、通知公告等数据',
          categories: ['政策法规', '政策解读', '通知公告', '建议提案'],
          color: '#1890ff',
        }
      case 'wjw':
        return {
          name: '卫生健康委爬虫',
          description: '爬取卫生健康委员会官网的相关数据',
          categories: ['新闻动态', '政策文件', '公告公示'],
          color: '#52c41a',
        }
      case 'flkgov':
        return {
          name: '国家法律法规数据库爬虫',
          description: '爬取国家法律法规数据库的法律法规数据',
          categories: ['法律法规'],
          color: '#722ed1',
        }
      default:
        return { name: spiderType, description: '', categories: [], color: '#666' }
    }
  }

  const renderSpiderControl = (spiderType: string, status: SpiderStatus) => {
    const config = getSpiderConfig(spiderType)
    const getStatusTag = () => {
      if (status.running) {
        return <Tag color="success">运行中</Tag>
      }
      if (status.status === 'paused') {
        return <Tag color="warning">已暂停</Tag>
      }
      if (status.status === 'error') {
        return <Tag color="error">异常</Tag>
      }
      return <Tag color="default">空闲</Tag>
    }

    const getReasonDisplay = () => {
      if (!status.reason || status.running) return null

      const reasonMap: Record<string, string> = {
        completed: '爬取完成',
        user_stopped: '用户停止',
        too_many_errors: '因错误停止（连续失败）'
      }

      const reasonText = reasonMap[status.reason] || status.reason
      return (
        <div style={{ marginTop: 8 }}>
          <Tag color="blue">{reasonText}</Tag>
        </div>
      )
    }

    const progress = status.progress
    const crawled = parseInt(progress?.crawled || '0')
    const total = parseInt(progress?.total || '0')
    const progressPercent = total > 0 ? Math.round((crawled / total) * 100) : 0

    return (
      <Card key={spiderType} style={{ marginBottom: 16, borderLeft: `4px solid ${config.color}` }}>
        <Card.Meta
          title={
            <Space>
              {config.name}
              {getStatusTag()}
              {status.pid && <Tag>PID: {status.pid}</Tag>}
              {getReasonDisplay()}
            </Space>
          }
          description={config.description}
          style={{ marginBottom: 16 }}
        />

        {status.status === 'error' && (
          <Alert
            message="爬虫运行异常"
            description={status.redis_status || '请检查日志获取详细信息'}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Divider>状态概览</Divider>

        <Row gutter={[12, 12]}>
          <Col xs={12} sm={8} md={4}>
            <Card size="small" bodyStyle={{ padding: '12px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>当前状态</div>
              <div style={{ 
                fontSize: 16, 
                fontWeight: 600,
                color: status.running ? '#52c41a' : '#999'
              }}>
                {status.running ? '运行中' : '空闲'}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small" bodyStyle={{ padding: '12px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>已收集链接</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#1890ff' }}>
                {status.links_collected || 0}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small" bodyStyle={{ padding: '12px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>待爬取链接</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#faad14' }}>
                {status.pending_links || 0}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small" bodyStyle={{ padding: '12px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>已爬取链接</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#52c41a' }}>
                {status.details_crawled || 0}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card size="small" bodyStyle={{ padding: '12px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>文件数量</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#722ed1' }}>
                {status.file_count || 0}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={8} md={4}>
            <Card 
              size="small" 
              bodyStyle={{ padding: '12px 8px', textAlign: 'center' }}
              style={{ borderColor: (status.error_count || 0) > 0 ? '#ff4d4f' : undefined }}
            >
              <div style={{ fontSize: 11, color: '#999', marginBottom: 4 }}>错误数量</div>
              <div style={{ 
                fontSize: 16, 
                fontWeight: 600, 
                color: (status.error_count || 0) > 0 ? '#ff4d4f' : '#52c41a' 
              }}>
                {status.error_count || 0}
              </div>
            </Card>
          </Col>
        </Row>

        {status.running && progressPercent > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 12, color: '#666' }}>
                爬取进度: {crawled} / {total}
              </span>
              <span style={{ fontSize: 12, color: '#666' }}>
                {progress?.current_category || '进行中...'}
              </span>
            </div>
            <Progress percent={progressPercent} status="active" strokeColor={config.color} />
          </div>
        )}

        <Divider>控制面板</Divider>

        <Row gutter={16}>
          <Col xs={24} md={16}>
            <Space size="middle" wrap>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleControl('start', spiderType)}
                disabled={status.running}
                size="large"
              >
                启动
              </Button>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={() => handleControl('stop', spiderType)}
                disabled={!status.running}
                size="large"
              >
                停止
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  fetchStatus(spiderType)
                }}
                size="large"
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col xs={24} md={8}>
            <div style={{ textAlign: 'right' }}>
              <span style={{ color: '#999', fontSize: 12 }}>
                最后更新: {status.last_update ? new Date(status.last_update).toLocaleString() : '-'}
              </span>
            </div>
          </Col>
        </Row>

      </Card>
    )
  }

  return (
    <div className="spider-manager-page" style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 16 }}>爬虫管理</h2>

      {error && (
        <Alert
          message="操作失败"
          description={error}
          type="error"
          showIcon
          closable
          onClose={clearError}
          style={{ marginBottom: 16 }}
        />
      )}

      {Object.keys(statuses).length === 0 ? (
        <Card>
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无爬虫状态数据，请刷新页面
          </div>
        </Card>
      ) : (
        Object.entries(statuses).map(([type, status]) => renderSpiderControl(type, status))
      )}
    </div>
  )
}

export default SpiderManager
