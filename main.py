# 文件名: __init__.py  (或 main.py 都行)
# 战双帕弥什 · 极简随机语音插件

import json
import random
from pathlib import Path

import aiohttp
from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import StarTools


@register("astrbot_plugin_zspms_voice", "yijin840", "战双帕弥什随机语音（一键即播）", "1.0.0")
class ZSPMSPlugin(Star):
    def __init__(self, context, config):
        super().__init__(context)

        self.data_dir = StarTools.get_data_dir("astrbot_plugin_zspms_voice")
        self.voices_dir = self.data_dir / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)

        plugin_dir = Path(__file__).parent.resolve()
        json_path = plugin_dir / "voices.json"
        print(json_path)
        if not json_path.exists():
            logger.error("未找到 voices.json！请放在插件目录下")
            self.voice_list = []
        else:
            self.voice_list = json.load(open(json_path, "r", encoding="utf-8"))
            logger.info(f"加载 {len(self.voice_list)} 个角色语音列表，准备开冲！")

    async def download_and_send(self, event, file_name, character, title):
        save_path = self.voices_dir / character / f"{title}.mp3"
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
                except:
                    yield event.plain_result("下载出错了，稍后再试哦~")
                    return

        yield event.plain_result(f"来！{character} 的「{title}」~")
        yield event.chain_result([Record.fromFileSystem(str(save_path))])

    @filter.command("zspms")
    async def random_play(self, event: AstrMessageEvent):
        if not self.voice_list == []:
            yield event.plain_result("voices.json 没找到！请检查插件目录")
            return

        char = random.choice(self.voice_list)
        character = char["title"]
        if not char["voices"]:
            yield event.plain_result(f"{character} 暂时没语音哦~")
            return

        file_name = random.choice(char["voices"])
        title = file_name.split(" ", 2)[-1].replace(".mp3", "")  # 提取标题

        await self.download_and_send(event, file_name, character, title)
