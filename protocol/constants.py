from enum import Enum

class EnumCommonCommandCode(Enum):
    """ 通用命令代码，包含数据头、SN序列码、版本代码和心跳包 """
    Head = 0x39
    SnCode = 0x01
    Version = 0x02
    HeartBeat = 0x7F

class EnumCommandCode(Enum):
    """ 具体命令代码 """
    # 棋谱上传相关代码：步进上传、全局上传、通知打开上传模式和通知关闭上传模式
    StepUpload, AllUpload, NotifyOpenUpload, NotifyCloseUpload = 0x25, 0x26, 0x21, 0x22
    
    # 游戏状态相关代码：开局，开始走棋，结束走棋，走棋进行中
    Opening, StartMove, EndMove, MoveOn = 0x50, 0x80, 0x81, 0x52

    # 状态相关代码：成功、失败和无效
    OkStatusCode, FailStatusCode, InvalidStatusCode = 0xc0, 0xc1, 0xcf

    # 对战模式相关代码：
    ManVsLocalMachine = 0x06
    ManVsRemoteMachine = 0x07
    ManVsRemoteMan = 0x08
    ManVsFaceMan = 0x09

    EnableKey = 0x20            # 启用按键
    MoveVerify = 0x29           # 移动验证
    BoardCamp = 0x53            # 棋盘阵营
    BoardLayout = 0x54          # 棋盘布局
    BoardLayoutComplete = 0xd0  # 棋盘布局完成
    MoveSucess = 0xa0           # 移动成功
    MoveFail = 0xa1             # 移动失败
    AudioFile = 0x48            # 音频文件
    TextResponse = 0x49         # 语音识别文本回复

class EnumChessCmdType(Enum):
    """ 国际象棋命令类型 """
    Move = 1
    Promotion = 2
    Castling = 3
    Enpassant = 4
    Illegal = 5

class EnumChessFlag(Enum):
    """
    棋子类型和颜色标志，依次为王、后、车、象、马和兵
    """
    K = 0x4b
    Q = 0x51
    R = 0x52
    B = 0x42
    N = 0x4e
    P = 0x50
    White = 0x56
    Black = 0x44
    Special = 0x00

class EnumOpenChessFlag(Enum):
    """ 开放棋子标志，包含颜色信息的更详细的棋子标志 """
    WhiteKing = 0x4b
    WhiteQueen = 0x51
    WhiteRook = 0x52
    WhiteBishop = 0x42
    WhiteKnight = 0x4e
    WhitePawn = 0x50
    BlackKing = 0xcb
    BlackQueen = 0xd1
    BlackRook = 0xd2
    BlackBishop = 0xc2
    BlackKnight = 0xce
    BlackPawn = 0xd0
    Empty = 0x00

class EnumChessPosXFlag(Enum):
    a = 0x01
    b = 0x02
    c = 0x03
    d = 0x04
    e = 0x05
    f = 0x06
    g = 0x07
    h = 0x08
class EnumChessPosYFlag(Enum):
    Y1 = 0x01
    Y2 = 0x02
    Y3 = 0x03
    Y4 = 0x04
    Y5 = 0x05
    Y6 = 0x06
    Y7 = 0x07
    Y8 = 0x08

class EnumKeyInfo(Enum):
    """
    按键信息，定义了设备按键的功能，依次为：
    开始下棋、暂停下棋、继续下棋、结束下棋、教学模式
    本地人机对战、远程人机对战、本地人人对战、远程人人对战
    """
    StartChess = 0x07
    PauseChess = 0x08
    ContinueChess = 0x09
    EndChess = 0x0a
    TeachMode = 0x12
    ManVsLocalMachine = 0x13
    ManVsRemoteMachine = 0x14
    ManVsRemoteMan = 0x15
    ManVsFaceMan = 0x16

TAG_HEADER_LENGTH = 38