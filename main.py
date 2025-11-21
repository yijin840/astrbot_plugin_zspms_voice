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

        # voices.json 路径（仅局部变量，防止被框架覆盖）
        plugin_dir = Path(__file__).parent.resolve()
        voices_path = plugin_dir / "voices.json"
        voices_path = Path(voices_path)  # 强制 Path

        print("json_path:", voices_path)
        print("json_path type:", type(voices_path))

        if not voices_path.exists():
            logger.error("未找到 voices.json！请放在插件目录下")
            self.voice_list = []
        else:
            try:
                with voices_path.open("r", encoding="utf-8") as f:
                    self.voice_list = json.load(f)
                logger.info(f"加载了 {len(self.voice_list)} 个角色语音列表，准备开冲！")
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
                        else:
                            yield event.plain_result("下载失败了，下次再试吧~")
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

        await self.download_and_send(event, file_name, character, title)
