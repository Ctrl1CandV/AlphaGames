from protocol.constants import (
    EnumChessFlag,
    EnumChessPosXFlag,
)
import chess

def _pos_to_byte(pos_str, file_only=False):
    """ 将棋盘位置字符串转换为字节值 """
    if not pos_str or len(pos_str) < 2:
        return 0

    file_char = pos_str[0]
    file_byte = EnumChessPosXFlag[file_char].value

    # 返回格式中是否需要Y坐标
    if file_only:
        return file_byte
    rank = int(pos_str[1])
    return file_byte, rank

def binary_to_uci(step):
    """ 将二进制格式的走棋步骤转换为UCI格式字符串 """
    color = step.color
    start_x = step.start_x
    start_y = step.start_y
    end_x = step.end_x
    end_y = step.end_y
    chess_type = step.type.lower()

    if chess_type == "castling":
        if color == "white":
            return "e1g1" if step.castling else "e1c1"
        else:
            return "e8g8" if step.castling else "e8c8"

    if chess_type == "promotion":
        new = step.newchess.lower() if step.newchess else "q"
        return f"{start_x}{start_y}{end_x}{end_y}{new}"

    if chess_type == "enpassant":
        return f"{start_x}{start_y}{end_x}{end_y}"

    return f"{start_x}{start_y}{end_x}{end_y}"

def uci_to_binary(board, uci_str, move_color=None):
    """ 将UCI格式字符串转换为二进制字节序列 """
    move = chess.Move.from_uci(uci_str)
    b = board.board if hasattr(board, 'board') else board
    piece = b.piece_at(move.from_square)
    target = b.piece_at(move.to_square)
    from_file = chess.square_file(move.from_square)
    to_rank = chess.square_rank(move.to_square)
    to_file = chess.square_file(move.to_square)

    if move_color is not None:
        player_is_white = move_color == chess.WHITE
    else:
        player_is_white = b.turn == chess.WHITE
    color_byte = EnumChessFlag.White.value if player_is_white else EnumChessFlag.Black.value

    # 处理王车易位
    if piece and piece.piece_type == chess.KING and abs(from_file - to_file) >= 2:
        is_short = to_file == 6
        castling_bytes = bytes([0x67, 0x67]) if is_short else bytes([0x62, 0x62])
        # 特殊标志 + 颜色 + 王标志 + 易位类型 + 车标志
        return (
            bytes([EnumChessFlag.Special.value])
            + bytes([color_byte])
            + bytes([0x4B])
            + castling_bytes
            + bytes([0x52])
        )

    # 处理兵升变
    if piece and piece.piece_type == chess.PAWN and to_rank in (0, 7) and len(uci_str) == 5:
        promo_char = uci_str[4].upper()
        promo_piece = EnumChessFlag[promo_char].value
        piece_byte = EnumChessFlag.P.value
        start_x_byte = _pos_to_byte(uci_str[:2], file_only=True)
        end_x_byte = _pos_to_byte(uci_str[2:4], file_only=True)
        # 特殊标志 + 颜色 + 兵标志 + 起始列 + 目标列 + 升变棋子
        return (
            bytes([EnumChessFlag.Special.value])
            + bytes([color_byte])
            + bytes([piece_byte])
            + bytes([start_x_byte])
            + bytes([end_x_byte])
            + bytes([promo_piece])
        )

    """ 处理吃过路兵，判断逻辑为行棋的必须是兵，同时目标格子与当前不同列且是空缺，此外这一步是合法的 """
    if piece and piece.piece_type == chess.PAWN and from_file != to_file and target is None:
        start_x_byte, start_y_byte = _pos_to_byte(uci_str[:2])
        end_x_byte, end_y_byte = _pos_to_byte(uci_str[2:4])
        # 特殊标志 + 颜色 + 起始列 + 起始行 + 目标列 + 目标行
        return (
            bytes([EnumChessFlag.Special.value])
            + bytes([color_byte])
            + bytes([start_x_byte])
            + bytes([start_y_byte])
            + bytes([end_x_byte])
            + bytes([end_y_byte])
        )

    # 普通移动，需要返回颜色 + 棋子类型 + 起始列 + 起始行 + 目标列 + 目标行
    piece_char = piece.symbol().upper() if piece else "P"
    piece_byte = EnumChessFlag[piece_char].value
    start_x_byte, start_y_byte = _pos_to_byte(uci_str[:2])
    end_x_byte, end_y_byte = _pos_to_byte(uci_str[2:4])
    return (
        bytes([color_byte])
        + bytes([piece_byte])
        + bytes([start_x_byte])
        + bytes([start_y_byte])
        + bytes([end_x_byte])
        + bytes([end_y_byte])
    )