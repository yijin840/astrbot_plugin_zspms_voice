# 文件名: __init__.py
# 放在文件夹 astrbot_plugin_zspms_voice/ 下即可直接加载

import os
import json
import asyncio
import random
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple

import aiohttp
from bs4 import BeautifulSoup
from PIL import Image as PILImage, ImageDraw, ImageFont

from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.api.star import StarTools
from astrbot.api import logger


@register("astrbot_plugin_zspms_voice", "yijin840", "战双帕弥什全构造体语音插件（中日英粤+涂装）", "1.0.0")
class ZSPMSPlugin(Star):
    # ==================== 配置 ====================
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://wiki.biligame.com/zspms/",
    }

    # 战双标准语音条目（和游戏内顺序一致，含涂装专属最后一条）
    VOICE_DESCRIPTIONS = [
        "构造体加入", "升级", "晋升", "进化", "技能升级", "武器装备",
        "编入队伍", "设为队长", "任务完成1",
        "日常问候1", "日常问候2", "日常问候3", "日常问候4", "日常问候5",
        "日常问候6", "日常问候7", "日常问候8", "日常问候9", "日常问候10",
        "日常问候11", "日常问候12", "日常问候13", "日常问候14", "日常问候15",
        "信赖提升1", "信赖提升2", "信赖提升3", "信赖提升4", "信赖提升5",
        "信赖提升6", "信赖提升7", "信赖提升8", "信赖提升9", "信赖提升10",
        "信赖提升11", "信赖提升12", "信赖提升13", "信赖提升14", "信赖提升15", "信赖提升16",
        "空闲1", "空闲2", "空闲3", "空闲4", "空闲5",
        "链接时间过长1", "链接时间过长2", "链接时间过长3", "链接时间过长4", "连接时间过长5",
        "链接接入1", "链接接入2", "链接接入3", "链接接入4", "链接接入5",
        "链接接入6", "链接接入7", "链接接入8",
        "摇晃1", "摇晃2", "摇晃3",
        "快速点击1", "快速点击2", "快速点击3",
        "活跃度已满", "战斗开始", "战斗1", "战斗2", "战斗3",
        "必杀", "受伤", "危险警告", "力尽", "助战", "QTE", "战斗结束",
        "涂装专属语音",  # 最后一项专门给涂装用
    ]

    LANG_MAP = {"中": "cn", "cn": "cn", "日": "jp", "jp": "jp", "英": "en", "en": "en", "粤": "yue", "yue": "yue"}

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        logger.info("战双帕弥什语音插件正在初始化...")

        self.data_dir = StarTools.get_data_dir("zspms_data")
        self.voices_dir = self.data_dir / "voices"
        self.assets_dir = self.data_dir / "assets"
        self.plugin_dir = Path(__file__).parent.resolve()

        for d in [self.data_dir, self.voices_dir, self.assets_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.voice_index: Dict[str, List[str]] = {}  # {角色名: [cn, jp, ...]}
        self._load_config(config)
        self.scan_voice_files()

    def _load_config(self, config: AstrBotConfig):
        self.config = config
        self.auto_download = self.config.get("auto_download", True)
        self.auto_download_coating = self.config.get("auto_download_coating", True)

        # 语言优先级 1中文 2日语 3英语 4粤语几乎没人用，放最后
        self.language_list = ["cn", "jp", "en", "yue"]
        self.default_language_rank = self.config.get("default_language_rank", "1234")
        self.auto_download_language = self.config.get("auto_download_language", "12")

        self.lang_name = {"cn": "中文", "jp": "日语", "en": "英语", "yue": "粤语"}

        # 配置 schema（第一次加载会自动生成）
        schema = {
            "auto_download": {"description": "未找到语音时自动下载", "type": "bool", "default": True},
            "auto_download_coating": {"description": "自动下载涂装语音", "type": "bool", "default": True},
            "default_language_rank": {"type": "string", "description": "语言优先级 1中文 2日语 3英语 4粤语",
                                      "default": "1234"},
            "auto_download_language": {"type": "string", "description": "自动下载的语言（填数字）", "default": "12"},
        }
        schema_path = self.data_dir / "_conf_schema.json"
        if not schema_path.exists():
            schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=4), encoding="utf-8")

    # ==================== 索引管理 ====================
    def scan_voice_files(self):
        self.voice_index.clear()
        if not self.voices_dir.exists():
            return
        for char_dir in self.voices_dir.iterdir():
            if not char_dir.is_dir():
                continue
            char_name = char_dir.name
            langs = []
            for lang_dir in char_dir.iterdir():
                if lang_dir.is_dir() and any(f.suffix == ".mp3" for f in lang_dir.iterdir()):
                    langs.append(lang_dir.name)
            if langs:
                self.voice_index[char_name] = langs
                # 涂装特殊处理
                if (char_dir / "coating").exists():
                    self.voice_index[f"{char_name}涂装"] = ["cn"]  # 涂装语音只有中文
        logger.info(f"扫描完成，共缓存 {len(self.voice_index)} 个构造体语音")

    # ==================== 下载核心 ====================
    async def download_single_voice(self, character: str, title: str, lang: str) -> bool:
        """使用 wiki 重定向链接下载单条语音"""
        filename = f"文件:{character} {self.lang_name[lang]} {title}.mp3"
        url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{filename.replace(' ', '%20')}"

        save_dir = self.voices_dir / character / lang
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{title}.mp3"

        if save_path.exists():
            return True

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self.DEFAULT_HEADERS, timeout=20) as resp:
                    if resp.status == 200:
                        save_path.write_bytes(await resp.read())
                        return True
            except:
                pass
        return False

    async def fetch_character_voices(self, character: str) -> Tuple[bool, str]:
        """下载某个构造体的全部语音（根据配置自动选语言 + 涂装）"""
        success_count = 0
        async with aiohttp.ClientSession() as session:
            # 先下载普通语音
            for lang_code in self.language_list:
                if lang_code not in [self.language_list[int(i) - 1] for i in self.auto_download_language]:
                    continue
                for title in self.VOICE_DESCRIPTIONS[:-1]:  # 除了最后一项涂装专属
                    if await self.download_single_voice(character, title, lang_code):
                        success_count += 1

            # 再下载涂装语音（如果开启）
            if self.auto_download_coating:
                if await self.download_single_voice(character, "涂装专属语音", "cn"):
                    success_count += 1
                    (self.voices_dir / character / "coating").mkdir(exist_ok=True)
                    (self.voices_dir / character / "coating" / "coating" / "涂装专属语音.mp3").symlink_to(
                        f"../../cn/涂装专属语音.mp3"
                    )

        self.scan_voice_files()
        return True, f"成功下载 {success_count} 条语音"

    # ==================== 语言选择 ====================
    def get_best_lang(self, character: str) -> str:
        """按配置优先级返回可用语言"""
        for rank in self.default_language_rank:
            try:
                lang = self.language_list[int(rank) - 1]
                if character in self.voice_index and lang in self.voice_index[character]:
                    return lang
            except:
                continue
        return "cn" if character in self.voice_index else "nodownload"

    # ==================== 路径获取 ====================
    def get_voice_path(self, character: str, title: str, lang: str) -> Optional[Path]:
        if character.endswith("涂装"):
            # 涂装语音只有中文，且文件名固定为“涂装专属语音.mp3”
            path = self.voices_dir / character.replace("涂装", "") / "cn" / "涂装专属语音.mp3"
        else:
            path = self.voices_dir / character / lang / f"{title}.mp3"
        return path if path.exists() else None

    # ==================== 命令处理 ====================
    @filter.command("zspms", alias=["战双语音", "zspms语音"])
    async def zspms_handler(self, event: AstrMessageEvent, character: str = None, extra: str = None,
                            voice_name: str = None, language: str = None):
        """主命令：播放语音"""
        self.scan_voice_files()

        # 处理涂装参数
        is_coating = False
        if extra and "涂装" in extra:
            is_coating = True
            if character:
                character = f"{character}涂装"

        if not character:
            if not self.voice_index:
                yield event.plain_result("还没有缓存任何语音，快用 /zspms_fetch 下载吧~")
                return
            character = random.choice(list(self.voice_index.keys()))

        # 语言处理
        lang = "cn"
        if language and language.lower() in self.LANG_MAP:
            lang = self.LANG_MAP[language.lower()]
        else:
            lang = self.get_best_lang(character)

        if lang == "nodownload":
            if not self.auto_download:
                yield event.plain_result(f"未找到《{character}》的语音，自动下载已关闭")
                return
            yield event.plain_result(f"未找到，正在自动下载《{character}》语音...")
            ok, msg = await self.fetch_character_voices(character.replace("涂装", ""))
            if not ok:
                yield event.plain_result(f"下载失败：{msg}")
                return
            lang = self.get_best_lang(character)

        # 语音名处理
        if not voice_name or voice_name in ["0", "随机"]:
            if is_coating:
                voice_name = "涂装专属语音"
            else:
                voice_name = random.choice(self.VOICE_DESCRIPTIONS)

        # 发送
        yield event.plain_result(f"正在播放 {character} 的语音：{voice_name} ({self.lang_name.get(lang, lang)})")
        path = self.get_voice_path(character, voice_name, lang)
        if not path:
            yield event.plain_result("该语音暂时不存在哦~")
            return

        async for msg in self.send_voice_message(event, str(path)):
            yield msg

    @filter.command("zspms_list", alias=["战双语音列表", "zspms列表"])
    async def list_handler(self, event: AstrMessageEvent):
        """列出所有已缓存的构造体"""
        self.scan_voice_files()
        if not self.voice_index:
            yield event.plain_result("还没有缓存任何语音，使用 /zspms_fetch [角色名] 下载吧")
            return

        lines = ["【战双帕弥什 已缓存构造体】\n"]
        for name, langs in sorted(self.voice_index.items()):
            lang_str = "".join(f"[{self.lang_name.get(l, l)}]" for l in langs)
            coating = " ✨涂装" if name.endswith("涂装") else ""
            lines.append(f"• {name}{coating}  {lang_str}")

        yield event.plain_result("\n".join(lines) + f"\n\n总数：{len(self.voice_index)} 个")

    @filter.command("zspms_fetch", alias=["战双下载语音", "下载战双语音"])
    async def fetch_handler(self, event: AstrMessageEvent, character: str):
        """手动下载某个构造体的全部语音"""
        yield event.plain_result(f"正在下载《{character}》的语音，请稍等...")
        ok, msg = await self.fetch_character_voices(character)
        yield event.plain_result("✔ 下载完成！" if ok else f"✘ 下载失败：{msg}")

    # ==================== 工具函数 ====================
    async def send_voice_message(self, event: AstrMessageEvent, voice_path: str):
        try:
            chain = [Record.fromFileSystem(voice_path)]
            yield event.chain_result(chain)
        except Exception as e:
            yield event.plain_result(f"发送语音失败：{e}")
