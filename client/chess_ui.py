import pygame
import chess

class PieceRenderer:
    """ 使用pygame将每个棋子绘制出来 """
    SS = 2

    def __init__(self, square_size: int):
        self.s = square_size
        self.cache: dict = {}
        self._build()

    def get(self, piece_type: int, color: bool) -> pygame.Surface:
        return self.cache[(piece_type, color)]

    def _v(self, r: float) -> int:
        return int(r * self.s)

    def _pt(self, x: float, y: float) -> tuple:
        return (int(x * self.s), int(y * self.s))

    def _pts(self, lst):
        return [(int(x * self.s), int(y * self.s)) for x, y in lst]

    def _base(self, surf, stroke, fill):
        pygame.draw.ellipse(surf, stroke,
                            (self._v(.16), self._v(.85), self._v(.68), self._v(.10)))
        pygame.draw.ellipse(surf, fill,
                            (self._v(.19), self._v(.86), self._v(.62), self._v(.07)))

    def _build(self):
        configs = {
            chess.WHITE: {"fill": (255, 252, 240), "stroke": (70, 65, 55)},
            chess.BLACK: {"fill": (55, 50, 45),    "stroke": (170, 160, 145)},
        }
        draw_fn = {
            chess.PAWN:   self._pawn,
            chess.KNIGHT: self._knight,
            chess.BISHOP: self._bishop,
            chess.ROOK:   self._rook,
            chess.QUEEN:  self._queen,
            chess.KING:   self._king,
        }
        for color, c in configs.items():
            for pt, fn in draw_fn.items():
                big = self.s * self.SS
                big_surf = pygame.Surface((big, big), pygame.SRCALPHA)
                saved = self.s
                self.s = big
                fn(big_surf, c["fill"], c["stroke"])
                self.s = saved
                surf = pygame.transform.smoothscale(big_surf, (self.s, self.s))
                self.cache[(pt, color)] = surf

    def _pawn(self, surf, fill, stroke):
        self._base(surf, stroke, fill)
        pygame.draw.polygon(surf, stroke, self._pts(
            [(.40, .48), (.60, .48), (.68, .85), (.32, .85)]))
        pygame.draw.polygon(surf, fill, self._pts(
            [(.43, .50), (.57, .50), (.65, .83), (.35, .83)]))
        pygame.draw.ellipse(surf, stroke,
                            (self._v(.36), self._v(.43), self._v(.28), self._v(.08)))
        pygame.draw.ellipse(surf, fill,
                            (self._v(.38), self._v(.44), self._v(.24), self._v(.05)))
        pygame.draw.circle(surf, stroke, self._pt(.50, .35), self._v(.14))
        pygame.draw.circle(surf, fill,   self._pt(.50, .35), self._v(.11))

    def _rook(self, surf, fill, stroke):
        self._base(surf, stroke, fill)
        lw = max(1, self.s // 50)
        pygame.draw.rect(surf, stroke,
                         (self._v(.26), self._v(.36), self._v(.48), self._v(.50)))
        pygame.draw.rect(surf, fill,
                         (self._v(.29), self._v(.38), self._v(.42), self._v(.46)))
        pygame.draw.rect(surf, stroke,
                         (self._v(.20), self._v(.30), self._v(.60), self._v(.08)))
        pygame.draw.rect(surf, fill,
                         (self._v(.23), self._v(.32), self._v(.54), self._v(.04)))
        bw = self._v(.15)
        for x in (.20, .425, .65):
            pygame.draw.rect(surf, stroke,
                             (self._v(x), self._v(.17), bw, self._v(.15)))
            pygame.draw.rect(surf, fill,
                             (self._v(x) + lw, self._v(.19), bw - 2 * lw, self._v(.11)))

    def _knight(self, surf, fill, stroke):
        self._base(surf, stroke, fill)
        outer = [
            (.28, .86), (.28, .52), (.22, .38), (.26, .22),
            (.36, .12), (.50, .08), (.62, .16), (.70, .30),
            (.64, .40), (.58, .48), (.66, .56), (.68, .86)]
        inner = [
            (.31, .84), (.31, .53), (.25, .40), (.29, .24),
            (.38, .15), (.50, .11), (.60, .18), (.67, .31),
            (.62, .40), (.57, .48), (.64, .56), (.65, .84)]
        pygame.draw.polygon(surf, stroke, self._pts(outer))
        pygame.draw.polygon(surf, fill,   self._pts(inner))
        pygame.draw.polygon(surf, stroke, self._pts(
            [(.38, .16), (.42, .08), (.48, .14)]))
        pygame.draw.polygon(surf, fill, self._pts(
            [(.39, .15), (.43, .10), (.47, .14)]))
        pygame.draw.circle(surf, stroke, self._pt(.46, .28), self._v(.035))
        pygame.draw.circle(surf, fill,   self._pt(.46, .28), self._v(.02))
        pygame.draw.circle(surf, stroke, self._pt(.66, .33), self._v(.02))

    def _bishop(self, surf, fill, stroke):
        self._base(surf, stroke, fill)
        lw = max(1, self.s // 50)
        pygame.draw.polygon(surf, stroke, self._pts(
            [(.36, .38), (.64, .38), (.72, .85), (.28, .85)]))
        pygame.draw.polygon(surf, fill, self._pts(
            [(.39, .40), (.61, .40), (.69, .83), (.31, .83)]))
        pygame.draw.ellipse(surf, stroke,
                            (self._v(.32), self._v(.36), self._v(.36), self._v(.08)))
        pygame.draw.ellipse(surf, fill,
                            (self._v(.34), self._v(.37), self._v(.32), self._v(.05)))
        pygame.draw.polygon(surf, stroke, self._pts(
            [(.50, .10), (.36, .42), (.64, .42)]))
        pygame.draw.polygon(surf, fill, self._pts(
            [(.50, .14), (.39, .40), (.61, .40)]))
        pygame.draw.circle(surf, stroke, self._pt(.50, .10), self._v(.05))
        pygame.draw.circle(surf, fill,   self._pt(.50, .10), self._v(.035))
        pygame.draw.line(surf, stroke,
                         self._pt(.50, .22), self._pt(.50, .42), lw)

    def _queen(self, surf, fill, stroke):
        self._base(surf, stroke, fill)
        pygame.draw.polygon(surf, stroke, self._pts(
            [(.28, .42), (.72, .42), (.78, .85), (.22, .85)]))
        pygame.draw.polygon(surf, fill, self._pts(
            [(.31, .44), (.69, .44), (.75, .83), (.25, .83)]))
        pygame.draw.rect(surf, stroke,
                         (self._v(.28), self._v(.50), self._v(.44), self._v(.04)))
        pygame.draw.rect(surf, fill,
                         (self._v(.30), self._v(.51), self._v(.40), self._v(.02)))
        for i, x in enumerate((.26, .38, .50, .62, .74)):
            tip = .10 if i % 2 == 0 else .22
            pygame.draw.polygon(surf, stroke, self._pts(
                [(x - .045, .42), (x, tip), (x + .045, .42)]))
            pygame.draw.polygon(surf, fill, self._pts(
                [(x - .025, .41), (x, tip + .04), (x + .025, .41)]))
        for x in (.26, .50, .74):
            pygame.draw.circle(surf, stroke, self._pt(x, .10), self._v(.045))
            pygame.draw.circle(surf, fill,   self._pt(x, .10), self._v(.03))

    def _king(self, surf, fill, stroke):
        self._base(surf, stroke, fill)
        lw = max(2, self.s // 40)
        pygame.draw.polygon(surf, stroke, self._pts(
            [(.28, .40), (.72, .40), (.78, .85), (.22, .85)]))
        pygame.draw.polygon(surf, fill, self._pts(
            [(.31, .42), (.69, .42), (.75, .83), (.25, .83)]))
        pygame.draw.rect(surf, stroke,
                         (self._v(.24), self._v(.38), self._v(.52), self._v(.06)))
        pygame.draw.rect(surf, fill,
                         (self._v(.27), self._v(.39), self._v(.46), self._v(.04)))
        cw = self._v(.09)
        cx = self._v(.50)
        pygame.draw.rect(surf, stroke,
                         (cx - cw // 2, self._v(.06), cw, self._v(.34)))
        pygame.draw.rect(surf, fill,
                         (cx - cw // 2 + lw, self._v(.08), cw - 2 * lw, self._v(.30)))
        ch = self._v(.09)
        pygame.draw.rect(surf, stroke,
                         (self._v(.36), self._v(.14), self._v(.28), ch))
        pygame.draw.rect(surf, fill,
                         (self._v(.38), self._v(.14) + lw, self._v(.24), ch - 2 * lw))

class ChessBoardUI:
    """
    负责所有pygame窗口操作，包括如下操作
    1. 窗口创建与销毁 2. 棋盘绘制 3. 屏幕坐标 → 棋盘格转换 4. 兵升变 UI
    """

    LIGHT_COLOR = (240, 217, 181)
    DARK_COLOR  = (181, 136, 99)
    BG_COLOR    = (30, 30, 30)
    SEL_COLOR   = (186, 202, 68, 160)
    LEGAL_COLOR = (145, 190, 109, 120)

    def __init__(self, width: int = 800, height: int = 800, title: str = "AlphaGames Board"):
        self.W = width
        self.H = height
        self.title = title
        self.sq = width // 8
        self.piece_renderer: PieceRenderer | None = None
        self.win: pygame.Surface | None = None
        self.font: pygame.font.Font | None = None

    def init(self):
        """ 初始化pygame、创建窗口、加载字体、预渲染棋子 """
        pygame.init()
        self.win = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption(self.title)
        self.font = self._load_font(int(self.sq * 0.6))
        self.piece_renderer = PieceRenderer(self.sq)

    def quit(self):
        pygame.quit()

    def draw(self, board: chess.Board, flip: bool,
            sel: int | None = None, legal: list[int] | None = None):
        """
        绘制完整棋盘画面，参数含义：
        - param board:  python-chess Board 对象
        - param flip:   是否翻转棋盘（黑方视角）
        - param sel:    当前选中的格子索引，None 表示未选中
        - param legal:  当前选中棋子的合法目标格列表
        """
        if legal is None:
            legal = []
        win = self.win
        sq = self.sq

        win.fill(self.BG_COLOR)

        # 棋盘格
        for r in range(8):
            for c in range(8):
                color = self.LIGHT_COLOR if (r + c) % 2 == 0 else self.DARK_COLOR
                pygame.draw.rect(win, color, (c * sq, r * sq, sq, sq))

        # 选中格高亮
        if sel is not None:
            col, row = self._square_to_screen(sel, flip)
            s = pygame.Surface((sq, sq), pygame.SRCALPHA)
            s.fill(self.SEL_COLOR)
            win.blit(s, (col * sq, row * sq))

        # 合法走法指示
        for sq_to in legal:
            col, row = self._square_to_screen(sq_to, flip)
            s = pygame.Surface((sq, sq), pygame.SRCALPHA)
            pygame.draw.circle(s, self.LEGAL_COLOR,
                               (sq // 2, sq // 2), sq // 6)
            win.blit(s, (col * sq, row * sq))

        # 棋子
        for square in chess.SQUARES:
            p = board.piece_at(square)
            if p is None:
                continue
            piece_surf = self.piece_renderer.get(p.piece_type, p.color)
            col, row = self._square_to_screen(square, flip)
            win.blit(piece_surf, (col * sq, row * sq))

    def flip_display(self):
        """刷新 pygame 显示。"""
        pygame.display.flip()

    def screen_to_square(self, x: int, y: int, flip: bool) -> int:
        """屏幕像素坐标 → 棋盘格索引 (0-63)。"""
        c, r = x // self.sq, y // self.sq
        f = 7 - c if flip else c
        rk = r if flip else 7 - r
        return chess.square(f, rk)

    def _square_to_screen(self, square: int, flip: bool) -> tuple[int, int]:
        """棋盘格索引 → 屏幕 (col, row)。"""
        f = chess.square_file(square)
        rk = chess.square_rank(square)
        col = 7 - f if flip else f
        row = rk if flip else 7 - rk
        return col, row


    def promotion_choice(self, running_check) -> int | None:
        """
        弹出升变选择界面，返回 chess.QUEEN / ROOK / BISHOP / KNIGHT
        若用户关闭窗口或点击空白则返回 None
        """
        choices = [
            (chess.QUEEN,  "Q"),
            (chess.ROOK,   "R"),
            (chess.BISHOP, "B"),
            (chess.KNIGHT, "N"),
        ]
        btn_w = self.W // 4
        btn_h = 100
        btn_y = self.H - btn_h

        while running_check():
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    return None
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = ev.pos
                    if btn_y <= my <= self.H:
                        i = mx // btn_w
                        if 0 <= i < len(choices):
                            return choices[i][0]
                    return None

            for i, (_, nm) in enumerate(choices):
                rx = i * btn_w
                pygame.draw.rect(self.win, (255, 255, 255),
                                 (rx, btn_y, btn_w, btn_h))
                t = self.font.render(nm, True, (0, 0, 0))
                self.win.blit(t, t.get_rect(
                    center=(rx + btn_w // 2, btn_y + btn_h // 2)))

            pygame.display.flip()

        return None

    @staticmethod
    def _load_font(sz: int) -> pygame.font.Font:
        for nm in ["arial", "segoeui", "tahoma", "microsoftsansserif", None]:
            try:
                if nm is None:
                    return pygame.font.Font(None, sz)
                return pygame.font.SysFont(nm, sz)
            except Exception:
                continue
        return pygame.font.Font(None, sz)
