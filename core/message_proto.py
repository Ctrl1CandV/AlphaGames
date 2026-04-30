from protocol.constants import EnumCommonCommandCode

class MessageProto:
    """
    网络消息协议编解码器，处理消息包的编码和解码
    消息格式：[Head(1字节)][Command(1字节)][DataLength(2字节小端)][MessageData(N字节)]
    功能：支持消息编码、解码、快速获取头部信息，用于设备间通信协议解析
    """
    HEAD_LENGTH = 4

    def __init__(self, buffer=None, head=None, command=None, message_data=None):
        self.Head = 0
        self.Command = 0
        self.DataLength = 0
        self.MessageData = bytearray()  # 实际数据
        self.MoreData = bytearray()     # 更多补充数据

        # 缓冲区内有信息则接受并解码，没有信息则使用给出的信息进行编码
        if buffer is not None:
            self._decode(buffer)
        elif head is not None and command is not None:
            self._encode_new(head, command, message_data)

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

    def _encode_new(self, head, command, message_data):
        """ 编码函数 """
        if message_data is None:
            message_data = bytearray()
        self.Head = head
        self.Command = command
        self.MessageData = message_data
        self.DataLength = len(message_data) + self.HEAD_LENGTH

    def get_bytes(self):
        """ 将消息包转换为字节数据，用于网络传输 """
        length_bytes = self.DataLength.to_bytes(2, byteorder="little")
        result = bytearray()
        result.append(self.Head)
        result.append(self.Command)
        result.extend(length_bytes)
        result.extend(self.MessageData)
        return bytes(result)

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
        """ 静态方法，便捷的编码方式，使用固定的信息头 """
        if message_data is None:
            message_data = bytearray()
        msg = MessageProto(
            head=EnumCommonCommandCode.Head.value,
            command=command,
            message_data=message_data,
        )
        return msg.get_bytes()