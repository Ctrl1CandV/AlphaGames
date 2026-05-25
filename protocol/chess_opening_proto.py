from protocol.constants import EnumOpenChessFlag

def build_opening_data():
    """ 构建国际象棋开局棋盘的二进制数据包，用于智能棋盘设备初始化或通信协议 """
    # 固定头部包括协议表示头、棋盘类型标识和未定义区域
    head = bytes([0x79, 0x55])
    chess_type = bytes([0xc8])
    undefined_area = bytes([0x00])
    # 棋盘配置包括行数、列数和数据总长度
    row_number = bytes([0x08])
    column_number = bytes([0x08])
    data_length = (74).to_bytes(2, byteorder="little")
    # 结束符
    end = bytes([0x00, 0x00])

    # 初始棋盘的状态
    row1 = bytes([
        EnumOpenChessFlag.BlackRook.value,
        EnumOpenChessFlag.BlackKnight.value,
        EnumOpenChessFlag.BlackBishop.value,
        EnumOpenChessFlag.BlackQueen.value,
        EnumOpenChessFlag.BlackKing.value,
        EnumOpenChessFlag.BlackBishop.value,
        EnumOpenChessFlag.BlackKnight.value,
        EnumOpenChessFlag.BlackRook.value,
    ])
    row2 = bytes([EnumOpenChessFlag.BlackPawn.value] * 8)
    row3 = bytes([EnumOpenChessFlag.Empty.value] * 8)
    row4 = bytes([EnumOpenChessFlag.Empty.value] * 8)
    row5 = bytes([EnumOpenChessFlag.Empty.value] * 8)
    row6 = bytes([EnumOpenChessFlag.Empty.value] * 8)
    row7 = bytes([EnumOpenChessFlag.WhitePawn.value] * 8)
    row8 = bytes([
        EnumOpenChessFlag.WhiteRook.value,
        EnumOpenChessFlag.WhiteKnight.value,
        EnumOpenChessFlag.WhiteBishop.value,
        EnumOpenChessFlag.WhiteQueen.value,
        EnumOpenChessFlag.WhiteKing.value,
        EnumOpenChessFlag.WhiteBishop.value,
        EnumOpenChessFlag.WhiteKnight.value,
        EnumOpenChessFlag.WhiteRook.value,
    ])

    return (
        head + data_length + undefined_area
        + chess_type + row_number + column_number
        + end
        + row1 + row2 + row3 + row4 + row5 + row6 + row7 + row8
    )
