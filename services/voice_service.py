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


class VoiceService:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("AlphaGames")

    @staticmethod
    def _hmac_sha256(key, msg):
        return hmac.new(key.encode(), msg.encode(), hashlib.sha256).digest()

    def _build_xunfei_stt_url(self):
        host = "ws-api.xfyun.cn"
        path = "/v2/iat"
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
        return f"{Config.XUNFEI_STT_URL}?{urlencode(params)}"

    def _build_xunfei_llm_url(self):
        host = "spark-api.xf-yun.com"
        path = "/v1.1/chat"
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
        return f"{Config.XUNFEI_LLM_URL}?{urlencode(params)}"

    async def speech_to_text(self, audio_path):
        url = self._build_xunfei_stt_url()
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

        if is_start:
            if is_human:
                return "start_game_human"
            return "start_game_ai"
        if is_query_open:
            return "query_opening"
        if is_query_move:
            return "query_moves"
        return "chat"

    async def ai_chat(self, text):
        url = self._build_xunfei_llm_url()
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
