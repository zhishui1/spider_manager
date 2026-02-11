import React from 'react'
import { Layout } from 'antd'
import { BugOutlined } from '@ant-design/icons'

const { Header } = Layout

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 24px',
  background: '#fff',
  boxShadow: '0 2px 8px rgba(0,0,0,0.09)',
}

const Logo: React.FC = () => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <BugOutlined style={{ fontSize: 24, color: '#1890ff' }} />
    <span style={{ fontSize: 18, fontWeight: 600 }}>爬虫管理平台</span>
  </div>
)

const StatusBar: React.FC = () => {
  const [time, setTime] = React.useState(new Date().toLocaleString())
  
  React.useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleString())
    }, 1000)
    return () => clearInterval(timer)
  }, [])
  
  return <span style={{ color: '#999' }}>{time}</span>
}

const HeaderComponent: React.FC = () => {
  return (
    <Header style={headerStyle}>
      <Logo />
      <StatusBar />
    </Header>
  )
}

export default HeaderComponent
