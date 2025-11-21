# 文件名: main.py
# 战双帕弥什随机语音插件

import json
import random
import re
import os
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

        # voices.json 路径 - 使用多种方法确保路径正确
        try:
            # 方法1：尝试从 __file__ 获取
            if hasattr(__file__, '__str__'):
                plugin_dir = Path(str(__file__)).parent.resolve()
            else:
                plugin_dir = Path(__file__).parent.resolve()
        except:
            # 方法2：使用 context 或当前工作目录
            try:
                plugin_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            except:
                # 方法3：使用数据目录的父目录
                plugin_dir = self.data_dir.parent / "astrbot_plugin_zspms_voice"

        voices_path = plugin_dir / "voices.json"

        logger.info(f"插件目录: {plugin_dir}")
        logger.info(f"voices.json 路径: {voices_path}")

        if not voices_path.exists():
            logger.error(f"未找到 voices.json！应该在: {voices_path}")
            self.voice_list = []
        else:
            try:
                with open(str(voices_path), "r", encoding="utf-8") as f:
                    self.voice_list = json.load(f)
                logger.info(f"✅ 加载了 {len(self.voice_list)} 个角色语音列表，准备开冲！")
            except Exception as e:
                logger.exception("读取 voices.json 失败: %s", e)
                self.voice_list = []

    async def download_and_send(self, event, file_name, character, title):
        # 处理非法文件名字符
        safe_character = re.sub(r'[\\/:*?"<>|]', '_', character)
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)

        save_path = self.voices_dir / safe_character / f"{safe_title}.mp3"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        if not save_path.exists():
            url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{file_name.replace(' ', '%20')}"
            yield event.plain_result(f"正在为你下载 {character} 的「{title}」...")
            async with aiohttp.ClientSession() as s:
                try:
                    async with s.get(url, timeout=30) as r:
                        if r.status == 200:
                            save_path.write_bytes(await r.read())
                            logger.info(f"下载成功: {save_path}")
                        else:
                            yield event.plain_result(f"下载失败了(HTTP {r.status})，下次再试吧~")
                            return
                except Exception as e:
                    logger.error(f"下载异常: {e}")
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
        # 文件名最后部分去掉 .mp3 并去首尾空格
        title = file_name.split(" ", 2)[-1].replace(".mp3", "").strip()

        async for result in self.download_and_send(event, file_name, character, title):
            yield result