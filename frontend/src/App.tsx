import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import SpiderManager from './pages/SpiderManager'
import DataDisplay from './pages/DataDisplay'
import LogViewer from './pages/LogViewer'

const { Content, Footer } = Layout

const App: React.FC = () => {
  return (
    <Layout className="site-layout">
      <Sidebar />
      <Layout>
        <Header />
        <Content className="site-layout-content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/spiders" element={<SpiderManager />} />
            <Route path="/data" element={<DataDisplay />} />
            <Route path="/logs" element={<LogViewer />} />
          </Routes>
        </Content>
        <Footer style={{ textAlign: 'center' }}>
          爬虫管理平台 © 2025 - 集中管理 wjw_crawler 和 nhsa_crawler
        </Footer>
      </Layout>
    </Layout>
  )
}

export default App
