from chess_ui import ChessBoardUI
import threading
import pygame
import socket
import chess
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

W, H = 800, 800
SERVER = ("127.0.0.1", 8480)

# 硬编码 SN 码 (与服务端通信时直接用的字节)
SN_CODE = bytes([0x49, 0x43, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39])

# 棋谱上传的 Tag 头(38字节)，用于 StepUpload 数据包前缀
TAG = bytes([0xE5, 0xD4, 0xFE, 0x00, 0x2F, 0x00, 0x21, 0x35,
             0x23, 0x59, 0xD8, 0xC6, 0xA3, 0xF5, 0x1F, 0xED,
             0x4A, 0x9C, 0x1F, 0x87] + [0x00] * 18)


def _mkpkt(cmd, data=b""):
    """封包: [0x39, cmd, len+4(2B LE), data]"""
    n = len(data) + 4
    return bytes([0x39, cmd, n & 0xFF, (n >> 8) & 0xFF]) + data


def _hex(b):
    return " ".join(f"{x:02X}" for x in b)


def _log(msg):
    print(f"[client] {msg}")

class ChessClient:
    def __init__(self):
        self.sock = None
        self.board = chess.Board()
        self.flip = False
        self.my_color = None
        self.playing = False
        self.sel = None
        self.legal = []
        self.running = False
        self.pending_move = None
        self.msgs = []
        self.lock = threading.Lock()
        self.ui = ChessBoardUI(W, H)
        self._mouse_was_down = False

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        self.sock.connect(SERVER)
        self.sock.settimeout(None)
        self.running = True
        threading.Thread(target=self._recv, daemon=True).start()

    def _recv(self):
        buf = bytearray()
        while self.running:
            try:
                data = self.sock.recv(65536)
                if not data:
                    break
            except Exception:
                break
            buf.extend(data)
            while len(buf) >= 4:
                total = int.from_bytes(buf[2:4], "little")
                if total == 0 or len(buf) < total:
                    break
                cmd = buf[1]
                body = bytes(buf[4:total])
                buf = buf[total:]
                with self.lock:
                    self.msgs.append((cmd, body))

    def send(self, cmd, data=b""):
        pkt = _mkpkt(cmd, data)
        try:
            self.sock.sendall(pkt)
            _log(f"发送 cmd=0x{cmd:02X}  {_hex(pkt)}")
        except Exception as e:
            _log(f"发送失败: {e}")

    def poll(self):
        with self.lock:
            m = self.msgs
            self.msgs = []
            return m

    def _dispatch(self, cmd, msg):
        _log(f"收到[{cmd}] {_hex(msg)}")

        if cmd == 0x01:  # SnCode 请求
            self.send(0x01, SN_CODE)

        elif cmd == 0x25:  # StepUpload 模式
            if len(msg) <= 1:
                self.send(0x25, bytes([0xC0]))
            elif self.playing and len(msg) >= 6:
                pass

        elif cmd == 0x26:  # AllUpload 模式
            if len(msg) <= 1:
                self.send(0x26, bytes([0xC0]))

        elif cmd == 0x21:  # NotifyOpenUpload
            if msg and msg[0] == 0xC0:
                self.send(0x20, bytes([0x14]))

        elif cmd == 0x50:  # Opening
            self.send(0x50, bytes([0xC0]))

        elif cmd == 0x53:  # BoardCamp
            if msg:
                if msg[0] == 0x56:
                    self.my_color = chess.WHITE
                    self.flip = False
                    _log("白方(先手)")
                else:
                    self.my_color = chess.BLACK
                    self.flip = True
                    _log("黑方(后手)")
                self.send(0x53, bytes([msg[0], 0xC0]))
                self.send(0x54, bytes([0xD0]))

        elif cmd == 0x20:  # EnableKey
            if msg and msg[0] == 0x07:
                _log("开始游戏!")
                self.send(0x20, bytes([0x07, 0xC0]))
                self.playing = True
            elif msg and msg[0] == 0x0A:
                _log("游戏结束")
                self.playing = False
                self.board.reset()

        elif cmd == 0x52:  # MoveOn — 对手走棋
            if len(msg) >= 6:
                raw = msg[-6:]
                self._parse_move(raw)

        elif cmd == 0x29:  # MoveVerify
            if msg and msg[0] == 0xA1:
                _log("行棋被拒(不合法)")
                self.pending_move = None
            elif msg and msg[0] == 0xA0:
                if self.pending_move:
                    self.board.push(chess.Move.from_uci(self.pending_move))
                    _log(f"我方走棋确认: {self.pending_move}")
                    self.pending_move = None

    def _parse_move(self, raw):
        try:
            from protocol.chess_step_proto import ChessStepProto
            from core.move_handler import binary_to_uci
            step = ChessStepProto(raw)
            uci = binary_to_uci(step)
            _log(f"对手走棋: {uci}")
            self.board.push(chess.Move.from_uci(uci))
        except Exception as e:
            _log(f"解析行棋失败(原始={_hex(raw)}): {e}")

    def send_move(self, uci):
        from core.move_handler import uci_to_binary
        move = chess.Move.from_uci(uci)
        if move not in self.board.legal_moves:
            return
        try:
            b = uci_to_binary(self.board, uci, move_color=self.board.turn)
        except Exception:
            return
        self.pending_move = uci
        self.send(0x25, TAG + b)

    def _handle_click(self):
        mouse_down = pygame.mouse.get_pressed()[0]
        if not self.playing or not mouse_down or self._mouse_was_down:
            self._mouse_was_down = mouse_down
            return
        self._mouse_was_down = True
        if self.board.turn != self.my_color:
            return
        sq = self.ui.screen_to_square(*pygame.mouse.get_pos(), self.flip)
        if self.sel is None:
            p = self.board.piece_at(sq)
            if p and p.color == self.my_color:
                self.sel = sq
                self.legal = [m.to_square for m in self.board.legal_moves
                              if m.from_square == sq]
        else:
            if sq == self.sel:
                self.sel = None
                self.legal = []
                return
            m = chess.Move(self.sel, sq)
            piece = self.board.piece_at(self.sel)
            to_rk = chess.square_rank(sq)
            promo = None
            if piece and piece.piece_type == chess.PAWN and to_rk in (0, 7):
                promo = self.ui.promotion_choice(lambda: self.running)
                if promo is None:
                    self.sel = None
                    self.legal = []
                    return
                m = chess.Move(self.sel, sq, promotion=promo)
            if m in self.board.legal_moves:
                self.send_move(m.uci())
            self.sel = None
            self.legal = []

    def run(self):
        _log("启动...")
        self.connect()

        self.ui.init()
        clock = pygame.time.Clock()

        while self.running:
            for cmd, msg in self.poll():
                self._dispatch(cmd, msg)

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_f:
                        self.flip = not self.flip
                    elif ev.key == pygame.K_r and self.playing:
                        self.send(0x20, bytes([0x0A]))

            self._handle_click()

            self.ui.draw(self.board, self.flip, self.sel, self.legal)
            self.ui.flip_display()
            clock.tick(60)

        if self.sock:
            self.sock.close()
        self.ui.quit()


if __name__ == "__main__":
    ChessClient().run()
