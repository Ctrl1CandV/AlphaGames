from protocol.constants import (
    EnumChessFlag,
    EnumChessCmdType,
    EnumChessPosXFlag,
    EnumChessPosYFlag,
)

class ChessStepProto:
    """
    国际象棋走棋协议解析器
    功能：解析智能棋盘设备发送的6字节的二进制走棋数据包，转换为结构化的Python对象。
    支持走棋类型：普通移动 (Move)、王车易位 (Castling)、兵升变 (Promotion)、吃过路兵 (Enpassant)
    字段说明：
    - type: 走棋类型
    - color: 棋子颜色
    - chess: 棋子类型
    - start_x/start_y, end_x/end_y: 起始/目标位置
    - castling: 易位类型 (True=王翼, False=后翼)
    - newchess: 升变后的棋子类型
    - kill_pawn: 是否吃过路兵
    """
    def __init__(self, buffer):
        # 走棋协议至少需要六个字节
        if not buffer or len(buffer) < 6:
            raise ValueError(f"行棋数据长度不足: {len(buffer)}")

        self.type = None
        self.color = None
        self.chess = None       # 棋子类型
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.castling = None
        self.newchess = None
        self.kill_pawn = False

        # 当前行棋是否为特殊走棋
        if buffer[0] == EnumChessFlag.Special.value:
            self._special_chess(buffer)
        else:
            self._normal_chess(buffer)

    @staticmethod
    def _get_y_pos(flag_value):
        """ 将行坐标从十六进制转换为数字 """
        mapping = {
            EnumChessPosYFlag.Y1.value: 1,
            EnumChessPosYFlag.Y2.value: 2,
            EnumChessPosYFlag.Y3.value: 3,
            EnumChessPosYFlag.Y4.value: 4,
            EnumChessPosYFlag.Y5.value: 5,
            EnumChessPosYFlag.Y6.value: 6,
            EnumChessPosYFlag.Y7.value: 7,
            EnumChessPosYFlag.Y8.value: 8,
        }
        return mapping.get(flag_value, 0)

    @staticmethod
    def _is_name_legal(name):
        """ 验证棋子名称是否合法 """
        return name in {"K", "Q", "R", "B", "N", "P"}

    def _special_chess(self, buffer):
        """ 特殊走棋解析，其格式为[0x00, 颜色, bf2, bf3, bf4, bf5] """
        self.color = EnumChessFlag(buffer[1]).name.lower()
        bf2, bf3, bf4, bf5 = buffer[2], buffer[3], buffer[4], buffer[5]

        # 处理王车易位，格式为[0x00, 颜色, 0x4B, 易位类型, 易位类型, 0x52]
        if bf2 == 0x4b and bf5 == 0x52:
            self.type = EnumChessCmdType.Castling.name
            if bf3 == 0x67 and bf4 == 0x67:
                self.castling = True    # 王翼易位
            elif bf3 == 0x62 and bf4 == 0x62:
                self.castling = False   # 后翼易位
            else:
                self.type = EnumChessCmdType.Illegal.name
            return
        
        # 获取行棋的棋子类型
        if bf2 in [m.value for m in EnumChessFlag]:
            self.chess = EnumChessFlag(bf2).name

        if self._is_name_legal(self.chess):
            # 处理兵升变，格式为[0x00, 颜色, 兵标志, 起始列, 目标列, 升变棋子]
            self.start_x = EnumChessPosXFlag(bf3).name
            if self.color == "white":
                self.start_y = 7
                self.end_y = 8
            else:
                self.start_y = 2
                self.end_y = 1
            
            self.end_x = EnumChessPosXFlag(bf4).name
            self.newchess = EnumChessFlag(bf5).name
            if self._is_name_legal(self.newchess):
                self.type = EnumChessCmdType.Promotion.name
            else:
                self.type = EnumChessCmdType.Illegal.name   # 非法的兵升变
        else:
            # 处理吃过路兵，格式为[0x00, 颜色, 起始列, 起始行, 目标列, 目标行]
            self.type = EnumChessCmdType.Enpassant.name
            self.kill_pawn = True
            self.start_x = EnumChessPosXFlag(bf2).name
            self.start_y = self._get_y_pos(bf3)
            self.end_x = EnumChessPosXFlag(bf4).name
            self.end_y = self._get_y_pos(bf5)

    def _normal_chess(self, buffer):
        """ 普通走棋解析，格式为[颜色, 棋子类型, 起始列, 起始行, 目标列, 目标行] """
        self.type = EnumChessCmdType.Move.name
        self.color = EnumChessFlag(buffer[0]).name.lower()
        self.chess = EnumChessFlag(buffer[1]).name
        self.start_x = EnumChessPosXFlag(buffer[2]).name
        self.start_y = self._get_y_pos(buffer[3])
        self.end_x = EnumChessPosXFlag(buffer[4]).name
        self.end_y = self._get_y_pos(buffer[5])