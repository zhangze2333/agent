# K8s 入门指南（从本项目出发理解 Kubernetes）

> 一句话定义：**Kubernetes 是"服务器集群的操作系统"**。
> 你有一堆机器（Node），k8s 把它们池化成一个资源池，你声明"我要跑什么"，
> 它负责找机器、启动、挂了重启、流量分发、滚动升级。

## 一、你已经会用 k8s 的一半了（概念映射表）

你把项目部署到服务器时做的事情，k8s 全都有对应概念——只是从"一台机器手动做"
升级成"一百台机器自动做"：

| 你在单机上手做的 | k8s 里的对应物 | 升级了什么 |
|---|---|---|
| systemd 的 agent-api.service | **Pod**（容器的封装） | 一个 Pod = 一个或多个容器，k8s 的最小调度单位 |
| `Restart=always` 崩溃自动拉起 | **自愈（Self-healing）** | Pod 挂了自动重建，还能跨机器迁移 |
| systemd 开机自启 | **Deployment**（声明"我要 2 个副本常驻"） | 副本数声明式管理，机器挂了自动在别的机器补 |
| `systemctl restart`（停机更新） | **滚动更新（Rolling Update）** | 新版本逐个替换旧版本，用户无感知，可一键回滚 |
| 手动 scp 传代码 | **镜像（Image）+ 镜像仓库** | 代码打成 Docker 镜像，任何机器拉下来就能跑 |
| nginx：静态文件 + /api 转发 8010 | **Service + Ingress** | Service=一组 Pod 的固定访问入口；Ingress=七层路由（就是集群级的 nginx） |
| 你的那一台服务器 | **Node**（集群里的一台机器） | 3 台、30 台、300 台对你是透明的 |
| 安全组放行端口 | **NetworkPolicy**（可选） | 集群内的网络访问控制 |

看懂这张表，你就懂了 k8s 存在的意义：**把"运维一台机器的经验"自动化地放大到整个集群**。

## 二、学习顺序：千万别跳过 Docker

k8s 调度的基本单位是**容器**，不先懂 Docker 直接学 k8s 会寸步难行。推荐路线：

```
① Docker：把我们的应用打成镜像，本机 docker run 跑起来     （1-2 天）
② Docker Compose：一条命令同时起"前端+后端+数据库"        （半天）
③ minikube/kind：在自己电脑上跑一个单节点 k8s 集群玩       （1 天）
④ kubectl + 三个 YAML：把我们的应用部署上去                （2-3 天）
⑤ 云上的托管 k8s（ACK/TKE/百度云 CCE）：以后公司真用时再学  （用到再学）
```

## 三、我们项目的 k8s 长什么样（预习代码）

把现在的单机部署"翻译"成 k8s，核心就是三个 YAML（真实可用，学完 Docker 后即可用）：

```yaml
# deployment-api.yaml —— 后端（对应你的 systemd 服务）
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-api
spec:
  replicas: 2                     # 跑 2 个副本（单机时 systemd 只能跑 1 个）
  selector:
    matchLabels: { app: agent-api }
  template:
    metadata:
      labels: { app: agent-api }
    spec:
      containers:
        - name: api
          image: your-dockerhub/agent-api:v1   # Docker 镜像（第一步要学的东西）
          ports: [{ containerPort: 8010 }]
          env:
            - name: ZHIPU_API_KEY
              valueFrom:
                secretKeyRef: { name: agent-secrets, key: zhipu-key }  # 密钥也进集群管理
          resources:
            requests: { memory: "128Mi", cpu: "100m" }  # 声明资源占用，调度器据此选机器
---
# service-api.yaml —— 后端的稳定访问入口（IP 会漂移，Service 名字不变）
apiVersion: v1
kind: Service
metadata:
  name: agent-api-svc
spec:
  selector: { app: agent-api }    # 自动找到所有带这个标签的 Pod，负载均衡
  ports: [{ port: 80, targetPort: 8010 }]
```

前端则是「静态文件打镜像 + Ingress 做路由」，等价于你 nginx 配置里那段
`location /` 和 `location /api/`。

日常操作就这几条命令（对比你现在的 systemctl）：

```bash
kubectl get pods                          # 看 all 服务状态（= systemctl status）
kubectl logs -f deploy/agent-api          # 看日志（= journalctl -u agent-api -f）
kubectl apply -f deployment-api.yaml      # 部署/更新（= scp + systemctl restart）
kubectl rollout undo deploy/agent-api     # 一键回滚上一个版本
kubectl scale deploy/agent-api --replicas=5   # 一行扩到 5 个副本
```

## 四、诚实的建议：你什么时候才真的需要它

| 信号 | 说明 |
|---|---|
| 服务器 ≥ 3 台，手动部署开始出错 | k8s 的自动化才开始值回票价 |
| 微服务数量 ≥ 5 个 | 服务发现、负载均衡、独立扩缩变成刚需 |
| 发布频繁、需要灰度/快速回滚 | 滚动更新 + 声明式配置的价值 |
| 团队 ≥ 3 个后端 | 统一的部署语言，避免"我机器上能跑" |

**你现在的情况（一个应用、一台服务器、自己学习）完全够不上这些信号**，
systemd + nginx 就是教科书级方案。所以学习姿势应该是：**在本地沙盒里学**，
不要把生产服务器折腾成 k8s 实验田。

## 五、动手第一步（想做的时候从这里开始）

1. 本地装 Docker Desktop（Windows 下基于 WSL2），或轻量的 Podman
2. 给本项目写两个 Dockerfile（前端多阶段构建：node 打包 → nginx 托管；后端：python:3.12-slim）
3. `docker compose up` 一条命令在本地把全套跑起来
4. 再装 minikube，把 compose 翻译成上面那几个 YAML
5. 每一步我都会带着做、讲原理

> 学习资料：Docker 官方 get-started、https://kubernetes.io/zh-cn/docs/tutorials/
> （官方中文教程的"Hello Minikube"就是第 4 步）
