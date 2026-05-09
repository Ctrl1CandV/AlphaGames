import logging
import chess

class ChessBoard:
    """
    国际象棋棋盘状态管理器
    功能：基于python-chess库管理棋盘状态和游戏逻辑
    主要方法：验证走棋合法性、更新棋盘状态、判断胜负平局、提供棋盘信息查询
    使用场景：游戏逻辑处理、走棋验证、状态展示
    """
    def __init__(self, logger=None):
        self.board = chess.Board()
        self.logger = logger or logging.getLogger("AlphaGames")
    
    # 重置棋盘到初始位置
    def reset(self):
        self.board = chess.Board()

    # 根据UCI字符串移动棋子
    def push_uci(self, uci_str):
        move = chess.Move.from_uci(uci_str)
        if move not in self.board.legal_moves:
            return False
        self.board.push(move)
        return True

    # 判断当前游戏是否结束
    def is_game_over(self):
        return self.board.is_game_over()

    # 返回对局结果
    def result(self):
        return self.board.result()

    # 返回当前棋盘的FEN表示，是一种用字符串表示国际象棋棋盘状态的标准格式
    def fen(self):
        return self.board.fen()

    # 返回当前轮到哪一方，True表示白方，False表示黑方
    def turn(self):
        return self.board.turn

    # 返回移动历史，以UCI字符串列表形式存储
    def move_stack(self):
        return [m.uci() for m in self.board.move_stack]

    # 返回当前所有合法移动的集合
    def legal_moves(self):
        return self.board.legal_moves

    # 返回指定方格上的棋子对象，如果该方格为空则返回None
    def piece_at(self, square):
        return self.board.piece_at(square)

    # 判断给定的UCI移动是否合法
    def is_legal(self, uci_str):
        try:
            move = chess.Move.from_uci(uci_str)
            return move in self.board.legal_moves
        except ValueError:
            return False

    ''' 
    分析UCI移动的类型，返回数据为(move_type, move)，特殊的移动有三类：
    castling，王车易位；promotion，兵的升变；enpassant，吃过路兵
    '''
    def get_uci_move_type(self, uci_str):
        move = chess.Move.from_uci(uci_str)
        piece = self.board.piece_at(move.from_square)
        target = self.board.piece_at(move.to_square)

        # 判断是否为易位
        if piece and piece.piece_type == chess.KING and abs(
            chess.square_file(move.from_square) - chess.square_file(move.to_square)
        ) >= 2:
            return "castling", move

        if piece and piece.piece_type == chess.PAWN:
            to_rank = chess.square_rank(move.to_square)
            if to_rank in (0, 7) and len(uci_str) == 5:
                return "promotion", move

            from_file = chess.square_file(move.from_square)
            to_file = chess.square_file(move.to_square)
            if from_file != to_file and target is None:
                return "enpassant", move

        return "move", move
