import React from 'react'
import { Row, Col, Card, Statistic, Spin } from 'antd'
import { PlayCircleOutlined, PauseCircleOutlined, StopOutlined, ReloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { useSpiderStore } from '../store'

const Dashboard: React.FC = () => {
  const { statuses, stats, fetchStatus, controlSpider, isLoading } = useSpiderStore()
  
  React.useEffect(() => {
    fetchStatus()
    // 自动轮询刷新已注释
    // const interval = setInterval(() => {
    //   fetchStatus()
    // }, 5000)
    // return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return '#52c41a'
      case 'paused': return '#faad14'
      case 'error': return '#ff4d4f'
      default: return '#d9d9d9'
    }
  }

  const getSpiderInfo = (spiderType: string): { name: string; color: string } => {
    switch (spiderType) {
      case 'nhsa': return { name: '国家医保局爬虫', color: '#1890ff' }
      case 'wjw': return { name: '卫生健康委爬虫', color: '#52c41a' }
      case 'flkgov': return { name: '国家法律法规数据库爬虫', color: '#722ed1' }
      default: return { name: spiderType, color: '#666' }
    }
  }

  const fileTypeChartOption = () => {
    const allFileTypes: Record<string, number> = {}
    Object.values(stats).forEach(s => {
      if (s.file_types) {
        Object.entries(s.file_types).forEach(([ext, count]) => {
          allFileTypes[ext] = (allFileTypes[ext] || 0) + (count as number)
        })
      }
    })
    
    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} 个 ({d}%)' },
      legend: { top: '5%', left: 'center' },
      series: [
        {
          name: '文件类型',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: { show: false, position: 'center' },
          emphasis: {
            label: { show: true, fontSize: 16, fontWeight: 'bold' },
          },
          data: Object.entries(allFileTypes).map(([name, value]) => ({ name, value })),
        },
      ],
    }
  }

  const totalData = Object.values(stats).reduce((sum, s) => sum + (s.total_items || 0), 0)
  const totalFiles = Object.values(stats).reduce((sum, s) => sum + (s.file_count || 0), 0)
  const runningSpiders = Object.values(statuses).filter(s => s.running).length

  return (
    <div className="dashboard-page" style={{ padding: 16 }}>
      <h2 style={{ marginBottom: 16 }}>仪表盘</h2>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="运行中的爬虫"
              value={runningSpiders}
              suffix={`/ ${Object.keys(statuses).length || 0}`}
              valueStyle={{ color: runningSpiders > 0 ? '#52c41a' : '#999' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="总数据量"
              value={totalData}
              suffix="条"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card className="stat-card">
            <Statistic
              title="下载文件"
              value={totalFiles}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="状态概览" extra={<span style={{ color: '#999' }}>共 {Object.keys(statuses).length} 个爬虫</span>}>
            {isLoading ? (
              <div className="loading-container" style={{ padding: 40 }}>
                <Spin size="large" />
              </div>
            ) : (
              <Row gutter={[12, 12]}>
                {Object.entries(statuses).map(([type, status]) => {
                  const info = getSpiderInfo(type)
                  
                  return (
                    <Col xs={24} sm={12} key={type}>
                      <Card
                        size="small"
                        style={{ 
                          borderLeft: `3px solid ${info.color}`,
                          transition: 'all 0.3s',
                        }}
                        bodyStyle={{ padding: 16 }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ 
                                display: 'inline-block',
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                backgroundColor: getStatusColor(status.status),
                              }} />
                              <span style={{ fontWeight: 500, fontSize: 15 }}>{info.name}</span>
                            </div>
                            <div style={{ marginTop: 4, fontSize: 12, color: '#999' }}>
                              {status.running ? '运行中' : status.status === 'paused' ? '已暂停' : '空闲'}
                              {status.pid && <span> · PID: {status.pid}</span>}
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: 8 }}>
                            <PlayCircleOutlined 
                              onClick={() => controlSpider('start', type)}
                              style={{ 
                                fontSize: 20, 
                                color: status.running ? '#52c41a40' : '#52c41a',
                                cursor: status.running ? 'not-allowed' : 'pointer'
                              }}
                              title="启动"
                            />
                            <PauseCircleOutlined 
                              onClick={() => controlSpider('pause', type)}
                              style={{ 
                                fontSize: 20, 
                                color: !status.running ? '#faad1440' : '#faad14',
                                cursor: !status.running ? 'not-allowed' : 'pointer'
                              }}
                              title="暂停"
                            />
                            <StopOutlined 
                              onClick={() => controlSpider('stop', type)}
                              style={{ 
                                fontSize: 20, 
                                color: !status.running ? '#ff4d4f40' : '#ff4d4f',
                                cursor: !status.running ? 'not-allowed' : 'pointer'
                              }}
                              title="停止"
                            />
                            <ReloadOutlined 
                              onClick={() => { fetchStatus(type); }}
                              style={{ fontSize: 20, cursor: 'pointer' }}
                              title="刷新"
                            />
                          </div>
                        </div>
                        
                        <Row gutter={16}>
                          <Col span={12}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ fontSize: 20, fontWeight: 600, color: '#333' }}>
                                {status.total_items || 0}
                              </div>
                              <div style={{ fontSize: 12, color: '#999' }}>数据量</div>
                            </div>
                          </Col>
                          <Col span={12}>
                            <div style={{ textAlign: 'center' }}>
                              <div style={{ fontSize: 20, fontWeight: 600, color: '#333' }}>
                                {status.file_count || 0}
                              </div>
                              <div style={{ fontSize: 12, color: '#999' }}>文件</div>
                            </div>
                          </Col>
                        </Row>
                        
                        {status.date_range?.latest && (
                          <div style={{ marginTop: 8, fontSize: 11, color: '#bbb', textAlign: 'center' }}>
                            更新: {status.date_range.latest}
                          </div>
                        )}
                      </Card>
                    </Col>
                  )
                })}
              </Row>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <div className="chart-container">
            <h3>文件类型分布</h3>
            {Object.keys(stats).length > 0 ? (
              <ReactECharts option={fileTypeChartOption()} style={{ height: 300 }} />
            ) : (
              <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                暂无数据
              </div>
            )}
          </div>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
