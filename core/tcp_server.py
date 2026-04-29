from services.chess_service import ChessService
import asyncio
import logging

class TcpServer:
    """
    异步TCP服务器，监听指定端口，处理客户端连接并转发给ChessService处理
    功能：启动/停止服务器，接受客户端连接，为每个连接创建独立的处理任务
    特点：基于asyncio实现高并发，支持多客户端同时连接
    """
    def __init__(self, host="0.0.0.0", port=8480, logger=None):
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger("AlphaGames")
        self._server = None

    async def start(self):
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
        )
        addr = self._server.sockets[0].getsockname()
        self.logger.info(f"TCP服务器已启动 {addr}")

    # 处理服务器连接
    async def _handle_client(self, reader, writer):
        peer = writer.get_extra_info("peername")
        try:
            self.logger.info(f"新连接: {peer}")
            chess_service = ChessService(reader, writer, logger=self.logger)
            await chess_service.handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception as e:
            self.logger.error(f"处理客户端异常: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            self.logger.info(f"连接断开: {peer}")


    async def stop(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self.logger.info("TCP服务器已关闭")
