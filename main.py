# 文件名: main.py
# 战双帕弥什随机语音插件

import json
import random
import re
from pathlib import Path

import aiohttp
from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import StarTools, Star


@register("astrbot_plugin_zspms_voice", "yijin840", "战双帕弥什随机语音（一键即播）", "1.0.0")
class ZSPMSPlugin(Star):
    def __init__(self, context, config):
        super().__init__(context)

        # 插件数据目录
        self.data_dir = StarTools.get_data_dir("astrbot_plugin_zspms_voice")
        self.voices_dir = self.data_dir / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)

        # 直接从 StarTools 获取插件根目录
        # AstrBot 的插件根目录就是 data/plugins/插件名称/
        plugin_root = self.data_dir.parent.parent / "plugins" / "astrbot_plugin_zspms_voice"
        voices_path = plugin_root / "voices.json"

        logger.info(f"[战双语音] 数据目录: {self.data_dir}")
        logger.info(f"[战双语音] 插件根目录: {plugin_root}")
        logger.info(f"[战双语音] voices.json路径: {voices_path}")

        self.voice_list = []

        if voices_path.exists():
            try:
                with open(voices_path, "r", encoding="utf-8") as f:
                    self.voice_list = json.load(f)
                logger.info(f"[战双语音] ✅ 加载了 {len(self.voice_list)} 个角色语音列表")
            except Exception as e:
                logger.error(f"[战双语音] ❌ 读取 voices.json 失败: {e}")
        else:
            logger.error(f"[战双语音] ❌ 未找到 voices.json，路径: {voices_path}")

    async def download_and_send(self, event, file_name, character, title):
        # 处理非法文件名字符
        safe_character = re.sub(r'[\\/:*?"<>|]', '_', character)
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)

        save_path = self.voices_dir / safe_character / f"{safe_title}.mp3"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if not save_path.exists():
            url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{file_name.replace(' ', '%20')}"
            yield event.plain_result(f"正在为你下载 {character} 的「{title}」...")

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content = await response.read()
                            save_path.write_bytes(content)
                            logger.info(f"[战双语音] 下载成功: {save_path}")
                        else:
                            yield event.plain_result(f"下载失败(HTTP {response.status})，下次再试吧~")
                            return
                except Exception as e:
                    logger.error(f"[战双语音] 下载异常: {e}")
                    yield event.plain_result("下载出错了，稍后再试哦~")
                    return

        yield event.plain_result(f"来！{character} 的「{title}」~")
        yield event.chain_result([Record.fromFileSystem(str(save_path))])

    @filter.command("zspms", alias=["战双语音", "zspms语音"])
    async def random_play(self, event: AstrMessageEvent):
        if not self.voice_list:
            yield event.plain_result("voices.json 没找到或加载失败！请检查插件目录")
            return

        char = random.choice(self.voice_list)
        character = char.get("title", "未知角色")

        if not char.get("voices"):
            yield event.plain_result(f"{character} 暂时没语音哦~")
            return

        file_name = random.choice(char["voices"])
        title = file_name.split(" ", 2)[-1].replace(".mp3", "").strip()

        async for result in self.download_and_send(event, file_name, character, title):
            yield result