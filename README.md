# 登录验证码获取工具

一个本地使用的登录验证码获取工具，支持短信验证码登录、风控验证码校验、结果复制和本地历史记录保存。

## 功能

- 输入手机号发送短信验证码
- 遇到风控时可弹出腾讯验证码
- 登录成功后生成 `token_online#appid`
- 自动保存最近获取结果
- 支持一键复制和清除本地记录
- 支持 Python 运行、Docker 部署和桌面窗口启动

## 桌面窗口版

安装依赖后运行：

```bash
pip install -r requirements.txt pywebview
python desktop.py
```

桌面入口会打开独立窗口，不需要手动打开浏览器。

## Python 本地运行

```bash
pip install -r requirements.txt
python app.py
```

打开：

```text
http://127.0.0.1:5123
```

## Docker 部署

```bash
docker run -d \
  --name lianton_login \
  -p 5123:5123 \
  iguang9881/unicom_login:latest
```

打开：

```text
http://127.0.0.1:5123
```

## 自行构建 Docker 镜像

```bash
docker build -t iguang9881/unicom_login:latest .
docker push iguang9881/unicom_login:latest
```

## 环境变量

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Python 本地运行时监听地址。Docker 中默认为 `0.0.0.0`。 |
| `PORT` | `5123` | 服务端口。 |
| `FLASK_DEBUG` | `0` | 仅本地调试时可设为 `1`。 |
| `FLASK_SECRET_KEY` | 启动时随机生成 | 可选，用于固定 Flask 会话密钥。 |
| `OPEN_BROWSER` | 桌面版默认 `1` | 是否自动打开浏览器。桌面窗口入口不需要设置。 |

## 数据保存

登录成功后的结果会保存在本机：

```text
data/token_history.json
```

页面中的“清除记录”按钮会删除本地保存的结果。

## 注意

- 建议只在本机或内网使用，不要暴露到公网。
- 生成的登录态属于敏感信息，请勿公开分享。
- Docker 镜像和源码只负责本地工具运行，具体账号安全验证以运营商接口返回为准。
