# AlphaGames

> 基于 Python 的国际象棋中台服务，连接物理棋盘与 Lichess 对战平台

## 功能

- **Web 注册 / 登录**：用户通过 Web 界面注册中台账号
- **棋盘绑定**：SN 码绑定物理棋盘，TCP 连接时自动关联用户
- **Lichess 绑定**：绑定 Lichess 账号及 API Token，支持在线验证
- **人机对战**：棋盘选择远程人机模式，Stockfish 引擎池走棋
- **人人对战**：棋盘选择远程人人模式，Lichess Board API 寻找对手并对弈
- **棋谱保存**：每局结束棋谱自动入库

## 技术栈

| 层 | 技术 |
|---|------|
| 语言 | Python 3.11+ |
| 并发 | asyncio + threading |
| 棋盘逻辑 | python-chess |
| AI | Stockfish（引擎池） |
| 人人对战 | berserk（Lichess Board API） |
| 数据库 | SQLAlchemy + aiomysql / pymysql |
| Web | Flask + Flask-Login |

## 运行

```bash
pip install -r requirements.txt
python main.py
# TCP 服务 :8480 + Flask Web :5000
```

模拟棋盘客户端：

```bash
cd client
python main.py
```

## 数据库表

| 表 | 用途 |
|----|------|
| `user` | 用户账号 |
| `device` | 棋盘 SN 码绑定 |
| `chessuser` | Lichess 账号绑定 |
| `chessrecord` | 对局棋谱 |
| `chessuploadmode` | 上传模式（预留） |

## 协议概览

TCP 二进制协议格式：`[0x39, cmd, len(2B LE), data]`

人机对战握手：

```
棋盘 → TCP 连接
中台 ← SnCode(0x01)
棋盘 → SN 码
中台 ← StepUpload(0x25)
棋盘 → Ok
中台 ← NotifyOpenUpload(0x21)
棋盘 → 人机模式(0x14)
中台 ← Opening(0x50) → BoardCamp → StartChess → PLAYING
```

## 项目结构

```
AlphaGames/
├── main.py           # 入口
├── config.py         # 全局配置
├── models.py         # ORM 模型
├── core/             # 基础设施 + 象棋逻辑
├── protocol/         # 协议常量 + 数据包
├── services/         # 业务逻辑
├── web/              # Flask Web
├── client/           # Pygame 仿真棋盘
└── utils/            # 日志
```
