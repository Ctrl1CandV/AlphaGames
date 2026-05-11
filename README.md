# AlphaGames

> 基于 Python 的国际象棋中台服务，连接物理棋盘、Lichess 对战平台与 Stockfish AI 引擎

## 功能

- **Web 用户系统**：注册、登录，管理员后台统一管理
- **棋盘设备绑定**：SN 码绑定物理棋盘，自动识别最近绑定用户
- **Lichess 账号绑定**：Web 端绑定 Lichess 账号及 API Token
- **上传模式切换**：步步上传 / 整局上传，Web 端可切换
- **对局配置**：AI 等级（1-8）、颜色偏好（白/黑/随机）、时间控制
- **本地人机对战**：Stockfish 引擎池走棋，根据配置动态调整难度
- **Lichess 人机对战**：通过 Lichess Board API 挑战指定等级 AI
- **Lichess 人人对战**：Lichess Board API 寻找对手并自动对弈
- **语音交互**：讯飞 STT 语音识别 + 大模型对话 + ElevenLabs TTS 语音合成
- **棋谱管理**：对局结束后棋谱自动入库，管理员可查看

## 技术栈

| 层 | 技术 |
|---|------|
| 语言 | Python 3.11+ |
| 并发 | asyncio + threading |
| 棋盘逻辑 | python-chess |
| AI 引擎 | Stockfish（多实例引擎池） |
| Lichess | berserk（Board API + 事件流） |
| 数据库 | SQLAlchemy (async + sync) + MySQL |
| Web | Flask + Flask-Login |
| 语音 | 讯飞 STT / LLM + ElevenLabs TTS |

## 部署（Linux 服务器）

### 环境要求

- **系统**：Ubuntu 20.04+ / Debian 11+ / CentOS 7+
- **Python**：3.11+
- **MySQL**：8.0+
- **Stockfish**：16+（引擎）

### 1. 安装系统依赖

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip mysql-server stockfish

# CentOS 7+ / RHEL（需先启用 EPEL）
sudo yum install -y epel-release
sudo yum install -y python3.11 python3.11-pip mysql-server
# Stockfish 通常需从源码编译，或下载预编译二进制
wget https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64.tar
tar -xvf stockfish-ubuntu-x86-64.tar
sudo cp stockfish/stockfish-ubuntu-x86-64 /usr/local/bin/stockfish
```

### 2. 配置 MySQL

```bash
# 启动 MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# 创建数据库和用户
sudo mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS alpha_platform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'alpha'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON alpha_platform.* TO 'alpha'@'localhost';
FLUSH PRIVILEGES;
EOF
```

### 3. 部署项目

```bash
# 克隆项目
git clone <your-repo-url> /opt/AlphaGames
cd /opt/AlphaGames

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 修改配置

编辑 `config.py`，对照 Linux 环境修改以下配置：

```python
# Stockfish 路径（Linux 下通常是这个位置）
STOCKFISH_PATH = "/usr/games/stockfish"
# 或自行安装的位置
# STOCKFISH_PATH = "/usr/local/bin/stockfish"

# 数据库连接（改成上面创建的数据库用户密码）
DB_URL = "mysql+aiomysql://alpha:your_strong_password@127.0.0.1:3306/alpha_platform"

# 修改为生产环境的密钥（必须改！）
SECRET_KEY = "生成一个随机字符串替换这里"

# Flask 监听地址改为 0.0.0.0 以允许外部访问
FLASK_HOST = "0.0.0.0"
```

### 5. 首次启动验证

```bash
# 确保在虚拟环境中
source venv/bin/activate
python main.py
```

首次运行会自动创建所有数据库表和管理员账号：
- **Web 管理**：`http://<服务器IP>:5000`
- **管理员登录**：账号 `admin`，密码 `admin`（**上线后立即修改**）
- **TCP 服务**：监听 `0.0.0.0:8480`，供棋盘设备连接

验证无误后 `Ctrl+C` 停止。

### 6. 配置 systemd 服务（生产环境）

创建服务文件：

```bash
sudo tee /etc/systemd/system/alphagames.service <<EOF
[Unit]
Description=AlphaGames Chess Middleware
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/AlphaGames
ExecStart=/opt/AlphaGames/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=append:/opt/AlphaGames/logs/stdout.log
StandardError=append:/opt/AlphaGames/logs/stderr.log

[Install]
WantedBy=multi-user.target
EOF
```

```bash
# 重载并启动
sudo systemctl daemon-reload
sudo systemctl enable alphagames
sudo systemctl start alphagames

# 查看运行状态
sudo systemctl status alphagames
```

### 常用运维命令

```bash
# 查看实时日志
tail -f /opt/AlphaGames/logs/tcp.log

# 重启/停止服务
sudo systemctl restart alphagames
sudo systemctl stop alphagames

# 查看服务日志
sudo journalctl -u alphagames -f
```

## 数据库表

| 表 | 用途 |
|----|------|
| `user` | 用户账号 |
| `admin` | 管理员账号 |
| `device` | 棋盘 SN 码绑定（支持多用户绑定，取最近一次） |
| `chessuser` | Lichess 账号绑定 |
| `chessuploadmode` | 棋盘上传模式（步步/整局） |
| `gameconfig` | 对局配置（颜色/AI等级/时间/加秒） |
| `chessrecord` | 对局棋谱 |

## 协议概览

TCP 二进制协议格式：`[0x39, cmd, len(2B LE), data]`

### 连接认证

```
棋盘 → TCP 连接
中台 ← SnCode(0x01) 请求
棋盘 → SN 码
中台 ← 下发上传模式 (0x25/0x26)
棋盘 → 确认
中台 ← NotifyOpenUpload(0x21)
棋盘 → 按键选择模式
```

### 模式按键

| 模式 | 按键值 | 说明 |
|------|--------|------|
| 本地人机 | 0x13 | Stockfish 引擎 |
| Lichess 人机 | 0x14 | Lichess Board API 挑战 AI |
| Lichess 人人 | 0x15 | Lichess Board API 匹配对手 |
| 快乐对弈 | 0x16 | 同本地人机 |

### 走棋数据

StepUpload 格式：`[38 字节 TAG] + [6 字节走棋数据]`

6 字节普通走棋：`[颜色, 棋子类型, 起始列, 起始行, 目标列, 目标行]`

## 项目结构

```
AlphaGames/
├── main.py                  # 入口（DB初始化 + Flask + TCP）
├── config.py                # 全局配置
├── models.py                # SQLAlchemy ORM 模型
├── requirements.txt         # 依赖
├── core/
│   ├── tcp_server.py        # TCP 服务端 + KeepAlive
│   ├── session.py           # TCP 会话基类（收发/编解码）
│   ├── database.py          # 数据库初始化 + 默认管理员
│   ├── engine.py            # Stockfish 引擎池 + 动态技能等级
│   ├── board.py             # python-chess 棋盘封装
│   ├── message_proto.py     # 二进制协议编解码
│   └── move_handler.py      # UCI ↔ 6字节走棋互转
├── protocol/
│   ├── constants.py         # 全部协议枚举常量
│   ├── chess_step_proto.py  # 6字节走棋协议解析
│   └── chess_opening_proto.py  # 开局数据包构建
├── services/
│   ├── chess_service.py     # 核心业务（协议分发/开局/走棋/结束）
│   ├── lichess_service.py   # Lichess Board API 封装（匹配/挑战/状态流）
│   ├── voice_service.py     # 语音服务（STT/LLM/TTS）
│   └── db_service.py        # 数据库访问层
├── web/
│   ├── __init__.py          # Flask 应用工厂
│   ├── auth.py              # 用户注册/登录
│   ├── admin.py             # 管理员后台
│   ├── device.py            # 设备绑定 + 模式切换
│   ├── lichess.py           # Lichess 绑定
│   ├── game_config.py       # 对局配置
│   ├── static/style.css     # 暗色主题样式
│   └── templates/           # Jinja2 模板
└── utils/
    └── logger.py            # 日志配置
```
