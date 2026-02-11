# Spider Manager

爬虫管理平台 - 集中管理 wjw_crawler 和 nhsa_crawler

## 项目结构

```
spider_manager/
├── backend/           # Django后端
│   ├── spiders/      # 爬虫管理模块
│   ├── api/          # REST API
│   ├── tasks/        # 定时任务
│   └── models.py     # 数据库模型
├── frontend/         # React前端
│   └── src/
│       ├── components/  # 公共组件
│       ├── pages/       # 页面组件
│       ├── services/    # API服务
│       └── store/       # 状态管理
├── nhsa_crawler.py   # 国家医保局爬虫
├── wjw_crawler.py    # 卫生健康委爬虫
└── nhsa_data.json    # 医保局数据存储
```

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 2. 安装前端依赖并启动

```bash
cd frontend
npm install
npm run dev
```

### 3. 启动爬虫

```bash
# 启动医保局爬虫
python nhsa_crawler.py

# 启动卫健委爬虫
python wjw_crawler.py
```

## 功能特性

- 📊 **仪表盘** - 实时展示爬虫状态和数据统计
- 🕷️ **爬虫管理** - 启动、停止、暂停、恢复爬虫
- 📄 **数据展示** - 查看和筛选爬取的数据
- 📋 **日志管理** - 查看运行日志
- ⚡ **实时监控** - WebSocket状态推送
- ⏰ **定时任务** - 自动定时爬取

## 技术栈

- **前端**: React + TypeScript + Ant Design
- **后端**: Python + Django + Django REST Framework
- **实时通信**: WebSocket (Channels)
- **数据存储**: JSON + Redis
