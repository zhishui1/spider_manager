import React from 'react'
import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  ControlOutlined,
  TableOutlined,
  FileTextOutlined,
} from '@ant-design/icons'

const { Sider } = Layout

const sidebarStyle: React.CSSProperties = {
  overflow: 'auto',
  height: '100vh',
  position: 'fixed',
  left: 0,
  top: 0,
  bottom: 0,
}

const menuItems = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/spiders',
    icon: <ControlOutlined />,
    label: '爬虫管理',
  },
  {
    key: '/data',
    icon: <TableOutlined />,
    label: '数据展示',
  },
  {
    key: '/logs',
    icon: <FileTextOutlined />,
    label: '日志管理',
  },
]

const Sidebar: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Sider width={250} style={sidebarStyle} theme="light">
      <div className="logo" style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid #f0f0f0' }}>
        <span style={{ fontSize: 16, fontWeight: 600, color: '#1890ff' }}>Spider Manager</span>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ borderRight: 0 }}
      />
    </Sider>
  )
}

export default Sidebar
