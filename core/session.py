from core.message_proto import MessageProto
import logging

class BaseSession:
    """
    TCP连接会话基类，封装网络连接的读写操作和日志记录。
    功能：发送数据包、关闭连接、记录带对端地址的日志。
    特点：异步操作、自动日志前缀、异常处理，为上层业务提供简洁接口。
    """
    def __init__(self, reader, writer, logger=None):
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info("peername")
        self.logger = logger or logging.getLogger("AlphaGames")
        self._connected = True

    def _log(self, msg, level="info"):
        prefix = f"[{self.peer}]"
        getattr(self.logger, level)(f"{prefix} {msg}")

    def _hex_str(self, data):
        return " ".join(f"{b:02X}" for b in data)

    async def send_data(self, command, data):
        if not self._connected:
            return bytes([0x00, 0x00, 0x00, 0x00])
        packet = MessageProto.encode(command, data)
        try:
            self.writer.write(packet)
            await self.writer.drain()
            self._log(f"发送 命令=0x{command:02X} 数据={self._hex_str(packet)}")
            return packet
        except Exception:
            self._connected = False
            return bytes([0x00, 0x00, 0x00, 0x00])

    async def close(self):
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception:
            pass
