# AlphaGames — 项目上下文

> 最后更新：2026-04-29

## 技术栈

| 层 | 技术 |
|---|------|
| 语言 | Python 3.11+ |
| 并发 | asyncio（单线程异步） |
| 通信 | TCP 二进制协议，[0x39, cmd, len(2B LE), data] |
| 棋盘 | python-chess |
| AI | Stockfish 子进程（引擎池，最大 4 个） |
| 客户端 | Pygame（纯 pygame 渲染，无 cairosvg） |
| 日志 | logging + TimedRotatingFileHandler（按天切割） |
| 数据库 | SQLAlchemy + aiomysql（**暂未启用**） |

## 项目结构

```
AlphaGames/
├── main.py              # 入口
├── config.py            # 配置
├── models.py            # ORM 模型（未启用）
├── requirements.txt
├── stockfish-windows-x86-64-avx2.exe
├── chess_core/          # 棋盘 + 引擎 + 协议转换
├── core/                # TCP服务器 + 编解码 + 会话 + DB引擎
├── protocol/            # 常量 + 行棋协议 + 开局协议
├── services/            # 对弈状态机 + DB服务
├── utils/               # 日志
└── client/              # Pygame 仿真棋盘
```

## 当前开发阶段

**TCP 人机对弈已跑通**。棋盘客户端可连接中台，完成握手、选择人机模式、对弈、投降，Stockfish 引擎池正常运行。

尚未实现：
- 人人对战 / 其他模式
- 数据库写入（代码已保留，调用已移除）
- 语音识别

## 关键决策

### 1. `chess/` 目录改名为 `chess_core/`
**原因**：pip 的库也叫 `chess`，Python 导入时项目目录优先级最高，`import chess.pgn` 找到了本地空包而非 pip 库。

### 2. 客户端 Pygame 跑主线程，TCP 收发放后台线程
**原因**：Windows 下 Pygame 必须在主线程调用 `init()`/`set_mode()`。旧 PygameBoard 反过来导致窗口永不显示。

### 3. Stockfish 使用全局引擎池而非逐会话绑定
**原因**：一个 Stockfish 子进程 ~50MB，逐会话绑定在 100 并发时需 5GB。池上限 4 个，走棋时借用、用完归还、异常时销毁。

### 4. 客户端不本地 push 棋盘，等 MoveVerify 确认
**原因**：本地先 push 后如果服务端拒绝走棋，两端棋盘永久失步。改为 `pending_move` 机制。

### 5. 命令码硬编码而非枚举类
**客户端 `main.py` 直接写 `cmd == 0x20` 而非引用 `EnumCommandCode`，避免跨项目 import 出错。

### 6. 暂时绕过数据库
**原因**：当前只需跑通对弈，不想增加网络依赖。`models.py`、`database.py`、`db_service.py` 保留备用。

### 7. 棋子用字母 KQRBNP + 白色描边
**原因**：Unicode 棋子 ♔♕ 在非标准 Windows 系统上渲染为方块。字母保证任意字体可用，描边保证深浅格均可读。

## 已解决的问题

| # | 问题 | 解决方案 |
|---|------|----------|
| 1 | `chess.pgn` 找不到 | 重命名 `chess/` → `chess_core/` |
| 2 | `python-chess` 版本不存在 | 改用 `chess>=1.9.0` |
| 3 | 双方连接后无窗口弹出 | Pygame 主线程 + TCP 后台线程 |
| 4 | 服务端 `AttributeError: SnCode` | 补 `EnumCommonCommandCode` 导入 |
| 5 | 棋子全部叠在左上角 | 变量名 `sq` 冲突，改为 `square` |
| 6 | 点击绿点不走棋 | `uci_to_binary` 兼容 `chess.Board` 和 `ChessBoard` |
| 7 | 投降后疯狂循环刷屏 | 客户端不再回发 EndChess；服务端加状态守卫 |
| 8 | 客户端关闭后服务端刷屏报错 | `send_data` 加 `_connected` 哨兵；`tcp_server` 消化连接异常 |
| 9 | 走棋后其他棋子无法点击 | 改为 pending_move 等 MoveVerify 确认再 push |
| 10 | Stockfish 池坏引擎回收 | 异常时 `quit()` 而非 `release()` |
| 11 | Stockfish 卡死无超时 | `asyncio.wait_for(..., 10s)` |
| 12 | `TimedRotatingFileHandler` 启动报错 | `extMatch` 改为 `re.compile(...)` |

## 协议握手流程

```
客户端 → TCP连接
中台 → SnCode(0x01)
客户端 → SN码
中台 → StepUpload(0x25)
客户端 → Ok
中台 → NotifyOpenUpload(0x21)
客户端 → 人机对战(0x14)
中台 → Opening(0x50)
客户端 → Ok
中台 → BoardCamp(0x53, 随机黑白)
客户端 → Ok → BoardLayout(BoardLayoutComplete)
中台 → StartChess → 进入 PLAYING
```
