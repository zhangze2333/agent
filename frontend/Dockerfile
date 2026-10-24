# ───── 阶段一：用 Node 把 Vue 项目打包成静态文件 ─────
FROM node:22-alpine AS build
WORKDIR /app

# 先只复制依赖清单再安装：只要 package.json 没变，
# Docker 会缓存这一层，下次构建几秒完成（镜像层缓存的经典用法）
COPY package.json package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com

COPY . .
RUN npm run build

# ───── 阶段二：把打包产物放进 nginx，对外提供服务 ─────
# 最终镜像里没有 Node、没有源码，只有 nginx + 静态文件（约 50MB）
FROM nginx:alpine

# 容器版 nginx 配置：/api 反代到 compose 网络里的 api 服务（见同目录 nginx.docker.conf）
COPY nginx.docker.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
