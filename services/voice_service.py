import hashlib
import hmac
import base64
import json
import aiohttp
import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode, quote

from config import Config


_OPENING_BOOK = {
    # ── 1.e4 e5 开放类开局 ──
    "e2e4 e7e5": "C20: 王兵开局",
    "e2e4 e7e5 f2f4": "C30: 王翼弃兵",
    "e2e4 e7e5 b1c3": "C25: 维也纳开局",
    "e2e4 e7e5 d2d4 e5d4": "C21: 中心开局",
    "e2e4 e7e5 f1c4": "C23: 象开局",
    "e2e4 e7e5 g1f3 g8f6": "C42: 俄罗斯防御",
    "e2e4 e7e5 g1f3 b8c6": "C40: 王马开局",
    "e2e4 e7e5 g1f3 b8c6 d2d4 e5d4 f3d4": "C44: 苏格兰开局",
    "e2e4 e7e5 g1f3 b8c6 f1c4": "C50: 意大利开局",
    "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5": "C50: 吉奥科钢琴开局",
    "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5 c2c3": "C50: 吉奥科钢琴中心攻击",
    "e2e4 e7e5 g1f3 b8c6 f1c4 g8f6": "C55: 双马防御",
    "e2e4 e7e5 g1f3 b8c6 f1b5": "C60: 西班牙开局",
    "e2e4 e7e5 g1f3 b8c6 f1b5 g8f6": "C65: 西班牙开局柏林防御",
    "e2e4 e7e5 g1f3 b8c6 f1b5 d7d6": "C62: 西班牙开局斯坦尼茨防御",
    "e2e4 e7e5 g1f3 b8c6 f1b5 f8c5": "C64: 西班牙开局古典变例",
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4": "C67: 西班牙开局摩洛哥弃兵",
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 f8e7": "C78: 西班牙开局封闭体系",
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 b7b5 a4b3 f8e7": "C88: 西班牙开局反马歇尔",
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 b7b5 a4b3 d7d5": "C89: 西班牙开局马歇尔弃兵",

    # ── 1.e4 c5 西西里防御 ──
    "e2e4 c7c5": "B20: 西西里防御",
    "e2e4 c7c5 c2c3": "B22: 阿拉平西西里",
    "e2e4 c7c5 b1c3": "B23: 封闭西西里",
    "e2e4 c7c5 g1f3 e7e6": "B40: 西西里法国变例",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3": "B56: 开放西西里",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6": "B90: 纳伊道夫西西里",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 g7g6": "B70: 龙式西西里",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 e7e6": "B80: 舍维宁根西西里",
    "e2e4 c7c5 g1f3 b8c6 d2d4 c5d4 f3d4 g8f6 b1c3 e7e5": "B32: 西西里拉布唐查",

    # ── 1.e4 e6 法兰西防御 ──
    "e2e4 e7e6": "C00: 法兰西防御",
    "e2e4 e7e6 d2d4 d7d5": "C01: 法兰西防御主线",
    "e2e4 e7e6 d2d4 d7d5 e4e5": "C02: 法兰西防御推进变例",
    "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6 e4e5": "C11: 法兰西防御推进变例",
    "e2e4 e7e6 d2d4 d7d5 b1c3 f8b4": "C15: 法兰西防御温纳韦尔变例",
    "e2e4 e7e6 d2d4 d7d5 b1c3 d5e4": "C13: 法兰西防御鲁宾斯坦变例",
    "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6": "C10: 法兰西防御古典变例",

    # ── 1.e4 c6 卡罗-卡恩防御 ──
    "e2e4 c7c6": "B10: 卡罗-卡恩防御",
    "e2e4 c7c6 d2d4 d7d5": "B12: 卡罗-卡恩主线",
    "e2e4 c7c6 d2d4 d7d5 e4e5": "B12: 卡罗-卡恩推进变例",
    "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4": "B18: 卡罗-卡恩古典变例",
    "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4 f8e7": "B19: 卡罗-卡恩古典主线",

    # ── 1.e4 其他半开放 ──
    "e2e4 d7d5": "B01: 斯堪的纳维亚防御",
    "e2e4 d7d5 e4d5 d8d5": "B01: 斯堪的纳维亚防御主线",
    "e2e4 g8f6": "B02: 阿廖欣防御",
    "e2e4 d7d6": "B07: 皮尔茨防御",
    "e2e4 d7d6 d2d4 g8f6 b1c3 g7g6": "B08: 皮尔茨防御古典变例",
    "e2e4 g7g6": "B06: 现代防御",

    # ── 1.d4 d5 后兵开局 ──
    "d2d4 d7d5": "D00: 后兵开局",
    "d2d4 d7d5 f1f4": "D00: 伦敦体系",
    "d2d4 d7d5 g1f3 g8f6 f1f4": "D00: 伦敦体系",
    "d2d4 d7d5 c2c4": "D06: 后翼弃兵",
    "d2d4 d7d5 c2c4 d5c4": "D20: 后翼弃兵接受变例",
    "d2d4 d7d5 c2c4 e7e6": "D30: 后翼弃兵拒绝变例",
    "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6": "D37: 后翼弃兵正统变例",
    "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6 c4d5 e6d5": "D36: 后翼弃兵兑换变例",
    "d2d4 d7d5 c2c4 e7e6 g1f3 g8f6 g2g3": "D37: 后翼弃兵卡塔兰体系",
    "d2d4 d7d5 c2c4 c7c6": "D10: 斯拉夫防御",
    "d2d4 d7d5 c2c4 c7c6 g1f3 g8f6 b1c3": "D15: 斯拉夫防御主线",
    "d2d4 d7d5 c2c4 c7c6 g1f3 g8f6 b1c3 e7e6": "D43: 半斯拉夫防御",
    "d2d4 d7d5 c2c4 c7c5": "D05: 正统后翼弃兵对称变例",

    # ── 1.d4 Nf6 印度防御 ──
    "d2d4 g8f6": "A45: 印度防御",
    "d2d4 g8f6 f1f4": "D00: 伦敦体系",
    "d2d4 g8f6 g1f3": "A46: 王马印度开局",
    "d2d4 g8f6 c2c4": "E20: 印度防御",
    "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6": "E90: 王翼印度防御",
    "d2d4 g8f6 c2c4 g7g6": "E60: 王翼印度防御",
    "d2d4 g8f6 c2c4 g7g6 g1f3 f8g7 g2g3 d7d6": "E60: 王翼印度防御费安凯托变例",
    "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4": "E20: 尼姆佐印度防御",
    "d2d4 g8f6 c2c4 e7e6 g1f3 b7b6": "E12: 后翼印度防御",
    "d2d4 g8f6 c2c4 e7e6 g2g3": "E00: 卡塔兰开局",
    "d2d4 g8f6 c2c4 c7c5 d4d5": "A56: 别诺尼防御",
    "d2d4 g8f6 c2c4 c7c5 d4d5 e7e6 b1c3 e6d5 c4d5 d7d6": "A60: 现代别诺尼",
    "d2d4 g8f6 c2c4 e7e5": "A51: 布达佩斯弃兵",

    # ── 1.c4 英国式开局 ──
    "c2c4": "A10: 英国式开局",
    "c2c4 e7e5": "A20: 英国式开局（反西西里）",
    "c2c4 g8f6": "A15: 英国式印度体系",
    "c2c4 c7c5": "A30: 英国式对称体系",
    "c2c4 e7e6 g1f3 d7d5 g2g3": "A13: 英国式卡塔兰体系",

    # ── 其他 ──
    "g1f3": "A04: 雷蒂开局",
    "f2f4": "A02: 伯德开局",
    "b2b3": "A01: 拉尔森开局",
    "b1c3": "A00: 杜尔金开局",
    "a2a3": "A00: 安德森开局",
    "g2g3": "A00: 本科开局",
    "e2e3": "A00: 金斯通弃兵",
    "d2d3": "A00: 马防体系",
}


class VoiceService:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("AlphaGames")

    @staticmethod
    def lookup_opening(moves):
        if not moves:
            return None
        for n in range(len(moves), 0, -1):
            key = " ".join(moves[:n])
            if key in _OPENING_BOOK:
                return _OPENING_BOOK[key]
        return None

    @staticmethod
    def _hmac_sha256(key, msg):
        return hmac.new(key.encode(), msg.encode(), hashlib.sha256).digest()

    def _build_xunfei_url(self, host, path, base_url):
        date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = self._hmac_sha256(Config.XUNFEI_API_SECRET, signature_origin)
        signature = base64.b64encode(signature_sha).decode()
        authorization_origin = (
            f'api_key="{Config.XUNFEI_API_KEY}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode()).decode()
        params = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
        return f"{base_url}?{urlencode(params)}"

    async def speech_to_text(self, audio_path):
        url = self._build_xunfei_url("ws-api.xfyun.cn", "/v2/iat", Config.XUNFEI_STT_URL)
        frame = {
            "common": {"app_id": Config.XUNFEI_APPID},
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "dwa": "wpgs",
                "ptt": 0,
            },
            "data": {
                "status": 0,
                "format": "audio/L16;rate=16000",
                "encoding": "raw",
            },
        }

        result_text = ""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    with open(audio_path, "rb") as f:
                        status = 0
                        while True:
                            chunk = f.read(1280)
                            if not chunk:
                                status = 2
                            frame["data"]["status"] = status
                            frame["data"]["audio"] = base64.b64encode(chunk).decode()
                            await ws.send_json(frame)
                            if not chunk:
                                break
                            if status == 0:
                                status = 1
                            await asyncio.sleep(0.04)

                    while True:
                        try:
                            msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                        except asyncio.TimeoutError:
                            break
                        code = msg.get("code", -1)
                        if code != 0:
                            self.logger.error(f"讯飞STT错误: {msg.get('message', '')}")
                            break
                        data = msg.get("data", {})
                        result_data = data.get("result", {})
                        ws_data = result_data.get("ws", [])
                        for item in ws_data:
                            cw = item.get("cw", [])
                            for w in cw:
                                result_text += w.get("w", "")
                        if data.get("status") == 2:
                            break
        except Exception as e:
            self.logger.error(f"语音识别异常: {e}")

        self.logger.info(f"语音识别结果: {result_text}")
        return result_text.strip()

    def parse_intent(self, text):
        t = text.lower()

        is_start = any(keyword in t for keyword in ("开始", "start", "game", "开局"))
        is_human = any(keyword in t for keyword in ("人人", "玩家对战", "玩家", "指定用户", "随机", "with human", "random", "human"))
        is_query_open = any(keyword in t for keyword in ("当前棋盘开局", "什么开局", "开局信息", "查询开局", "opening", "find opening"))
        is_query_move = any(keyword in t for keyword in ("当前局面", "局面", "局面信息", "现在局面", "board position", "position"))

        if is_query_open:
            return "query_opening"
        if is_query_move:
            return "query_moves"
        if is_start:
            if is_human:
                return "start_game_human"
            return "start_game_ai"
        return "chat"

    async def ai_chat(self, text):
        url = self._build_xunfei_url("spark-api.xf-yun.com", "/v1.1/chat", Config.XUNFEI_LLM_URL)
        request = {
            "header": {"app_id": Config.XUNFEI_LLM_APPID, "uid": "alpha_user"},
            "parameter": {
                "chat": {
                    "domain": "general",
                    "temperature": 0.5,
                    "max_tokens": 64,
                }
            },
            "payload": {
                "message": {
                    "text": [{"role": "user", "content": text}]
                }
            },
        }

        response_text = ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url) as ws:
                    await ws.send_json(request)
                    while True:
                        try:
                            msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
                        except asyncio.TimeoutError:
                            break
                        header = msg.get("header", {})
                        if header.get("code") != 0:
                            self.logger.error(f"LLM错误: {msg}")
                            break
                        payload = msg.get("payload", {})
                        choices = payload.get("choices", {})
                        text_list = choices.get("text", [])
                        for item in text_list:
                            response_text += item.get("content", "")
                        if choices.get("status") == 2:
                            break
        except Exception as e:
            self.logger.error(f"AI对话异常: {e}")

        self.logger.info(f"AI回复: {response_text}")
        return response_text.strip()

    async def text_to_speech(self, text):
        url = Config.ELEVENLABS_TTS_URL.format(voice_id=Config.ELEVENLABS_VOICE_ID)
        url += "?output_format=pcm_16000"
        headers = {
            "xi-api-key": Config.ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 1.0,
                "similarity_boost": 1.0,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status == 200:
                        return await resp.read()
        except Exception as e:
            self.logger.error(f"TTS异常: {e}")
        return None
