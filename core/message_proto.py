from protocol.constants import EnumCommonCommandCode

class MessageProto:
    """
    网络消息协议编解码器，处理消息包的编码和解码
    消息格式：[Head(1字节)][Command(1字节)][DataLength(2字节小端)][MessageData(N字节)]
    功能：支持消息编码、解码、快速获取头部信息，用于设备间通信协议解析
    """
    HEAD_LENGTH = 4

    def __init__(self, buffer):
        self.Head = 0
        self.Command = 0
        self.DataLength = 0
        self.MessageData = bytearray()
        self.MoreData = bytearray()

        if buffer is not None:
            self._decode(buffer)

    def _decode(self, buffer):
        """ 解码函数 """
        if len(buffer) < self.HEAD_LENGTH:
            return

        self.Head, self.Command, length_bytes = buffer[0], buffer[1], buffer[2:4]
        self.DataLength = int.from_bytes(length_bytes, byteorder="little") - self.HEAD_LENGTH

        # 提取实际数据和其他数据（若有）
        if len(buffer) - self.HEAD_LENGTH >= self.DataLength:
            self.MessageData = buffer[self.HEAD_LENGTH : self.DataLength + self.HEAD_LENGTH]
        if len(buffer) - self.HEAD_LENGTH - self.DataLength > 0:
            self.MoreData = buffer[self.DataLength + self.HEAD_LENGTH :]

    def get_message(self):
        return bytes(self.MessageData)

    @staticmethod
    def get_head_info(buffer):
        """ 静态方法，快速提取信息包的头部信息 """
        if buffer and len(buffer) >= MessageProto.HEAD_LENGTH:
            head, command = buffer[0], buffer[1]
            data_length = int.from_bytes(buffer[2:4], byteorder="little")
            if data_length < MessageProto.HEAD_LENGTH:
                return 0, 0, 0
            return head, command, data_length
        return 0, 0, 0

    @staticmethod
    def encode(command, message_data):
        if message_data is None:
            message_data = bytearray()
        data_length = len(message_data) + MessageProto.HEAD_LENGTH
        result = bytearray()
        result.append(EnumCommonCommandCode.Head.value)
        result.append(command)
        result.extend(data_length.to_bytes(2, byteorder="little"))
        result.extend(message_data)
        return bytes(result)