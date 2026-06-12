# 中华文明数字永生体 · Docker 部署配置

## 快速启动

```bash
# 构建镜像
docker build -t zhonghua-immortal:latest .

# 运行容器
docker run -d -p 8765:8765 --name zhonghua-immortal zhonghua-immortal:latest

# 查看日志
docker logs -f zhonghua-immortal
```

## Docker Compose 完整部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  immortal:
    build: .
    container_name: zhonghua-immortal
    ports:
      - "8765:8765"
    environment:
      - FLASK_ENV=production
      - API_PORT=8765
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8765/api/v1/健康"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: zhonghua-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - immortal
    restart: unless-stopped
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| API_PORT | 8765 | API服务端口 |
| FLASK_ENV | production | Flask环境 |
| LOG_LEVEL | INFO | 日志级别 |
| MAX_TRAJECTORY | 100 | 最大轨迹记录 |

## 资源限制

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## 健康检查

```bash
# 本地检查
curl http://localhost:8765/api/v1/健康

# 响应
{
  "状态": "正常",
  "版本": "1.0.0",
  "时间戳": "2026-04-14T..."
}
```

## 数据持久化

```bash
# 备份数据
docker exec zhonghua-immortal tar czf /tmp/backup.tar.gz /app/data

# 恢复数据
docker exec -i zhonghua-immortal tar xzf /tmp/backup.tar.gz -C /
```

## 扩展部署

```bash
# 水平扩展
docker-compose up -d --scale immortal=3

# 负载均衡配置
# 参见 nginx.conf
```
