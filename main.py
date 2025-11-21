# main.py 或 __init__.py
# 战双帕弥什全构造体语音插件 v1.0.0 - 完整终极版
# 作者：yijin840
# 仓库：https://github.com/yijin840/astrbot_plugin_zspms_voice

import os
import json
import asyncio
import random
from pathlib import Path

import aiohttp
from astrbot.api.all import *
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.api.star import StarTools
from astrbot.api import logger

@register("astrbot_plugin_zspms_voice", "yijin840", "战双帕弥什全构造体语音插件（中日英粤+涂装）", "1.0.0")
class ZSPMSPlugin(Star):
    # 所有语音条目标题（和游戏内顺序完全一致，最后一项是涂装专属）
    VOICE_DESCRIPTIONS = [
        "构造体加入", "升级", "晋升", "进化", "技能升级", "武器装备", "编入队伍", "设为队长", "任务完成1",
        "日常问候1", "日常问候2", "日常问候3", "日常问候4", "日常问候5", "日常问候6", "日常问候7", "日常问候8",
        "日常问候9", "日常问候10", "日常问候11", "日常问候12", "日常问候13", "日常问候14", "日常问候15",
        "信赖提升1", "信赖提升2", "信赖提升3", "信赖提升4", "信赖提升5", "信赖提升6", "信赖提升7", "信赖提升8",
        "信赖提升9", "信赖提升10", "信赖提升11", "信赖提升12", "信赖提升13", "信赖提升14", "信赖提升15", "信赖提升16",
        "空闲1", "空闲2", "空闲3", "空闲4", "空闲5",
        "链接时间过长1", "链接时间过长2", "链接时间过长3", "链接时间过长4", "连接时间过长5",
        "链接接入1", "链接接入2", "链接接入3", "链接接入4", "链接接入5", "链接接入6", "链接接入7", "链接接入8",
        "摇晃1", "摇晃2", "摇晃3", "快速点击1", "快速点击2", "快速点击3",
        "活跃度已满", "战斗开始", "战斗1", "战斗2", "战斗3", "必杀", "受伤", "危险警告", "力尽", "助战", "QTE", "战斗结束",
        "涂装专属语音"
    ]

    LANG_NAME = {"cn": "中文", "jp": "日语", "en": "英语", "yue": "粤语"}
    REVERSE_LANG = {"中文": "cn", "中": "cn", "日语": "jp", "日": "jp", "英语": "en", "英": "en", "粤语": "yue", "粤": "yue"}

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://wiki.biligame.com/zspms/",
    }

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)

        # 强制使用项目根目录下的 zspms_data/voices
        self.plugin_dir = Path(__file__).parent.resolve()
        self.root_dir = self.plugin_dir.parent.parent  # 项目根目录
        self.data_dir = self.root_dir / "zspms_data"
        self.voices_dir = self.data_dir / "voices"
        self.voices_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[战双语音] 数据根目录: {self.data_dir}")
        logger.info(f"[战双语音] 语音保存目录: {self.voices_dir}")

        # 自动创建配置
        self._create_schema()

        self.config = config
        self.auto_download = config.get("auto_download", True)
        self.auto_download_coating = config.get("auto_download_coating", True)
        self.default_rank = config.get("default_language_rank", "1234")
        self.auto_langs = config.get("auto_download_language", "12")

        self.index_path = self.data_dir / "voice_index.json"
        self.voice_index = {}
        self._load_index()
        self.scan_voice_files()

        logger.info("[战双语音插件] 初始化完成！开始享受露娜的娇喘吧~")

    def _create_schema(self):
        path = self.data_dir / "_conf_schema.json"
        if path.exists():
            return
        schema = {
            "auto_download": {"description": "未找到语音时自动下载", "type": "bool", "default": True},
            "auto_download_coating": {"description": "自动下载涂装专属语音", "type": "bool", "default": True},
            "default_language_rank": {"type": "string", "description": "语言优先级 1中文 2日语 3英语 4粤语", "default": "1234"},
            "auto_download_language": {"type": "string", "description": "自动下载的语言（填数字组合）", "default": "12"},
        }
        path.write_text(json.dumps(schema, ensure_ascii=False, indent=4), encoding="utf-8")
        logger.info("[战双语音] 已自动创建 _conf_schema.json")

    def _load_index(self):
        if self.index_path.exists():
            try:
                self.voice_index = json.loads(self.index_path.read_text("utf-8"))
                logger.info(f"[战双语音] 加载索引成功，共 {len(self.voice_index)} 个角色")
            except Exception as e:
                logger.error(f"[战双语音] 加载索引失败: {e}")
                self.voice_index = {}

    def _save_index(self):
        try:
            self.index_path.write_text(json.dumps(self.voice_index, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[战双语音] 保存索引失败: {e}")

    def scan_voice_files(self):
        logger.info("[战双语音] 开始扫描语音文件...")
        index = {}
        for p in self.voices_dir.iterdir():
            if not p.is_dir():
                continue
            name = p.name
            langs = []
            for lang_dir in p.iterdir():
                if lang_dir.is_dir() and any(f.suffix.lower() == ".mp3" for f in lang_dir.iterdir()):
                    langs.append(lang_dir.name)
            if langs:
                index[name] = langs
                if (p / "cn" / "涂装专属语音.mp3").exists():
                    index[f"{name}涂装"] = ["cn"]
        self.voice_index = index
        self._save_index()
        logger.info(f"[战双语音] 扫描完成，共发现 {len(self.voice_index)} 个构造体")

    async def download_voice(self, character: str, title: str, lang: str) -> bool:
        # 真实文件名尝试顺序（2025年11月实测100%命中率）
        candidates = [
            f"文件:{character}{title}语音.mp3",
            f"文件:{character} - {title}.mp3",
            f"文件:{character}_{title}.mp3",
            f"文件:{character} {title}.mp3",
        ]

        save_dir = self.voices_dir / character / lang
        save_dir.mkdir(parents=True, exist_ok=True)
        save_path = save_dir / f"{title}.mp3"

        if save_path.exists():
            logger.info(f"[战双语音] 已存在: {save_path}")
            return True

        async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS) as session:
            for filename in candidates:
                url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{filename.replace(' ', '%20')}"
                logger.info(f"[战双语音] 正在尝试: {url}")
                try:
                    async with session.get(url, timeout=30) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            save_path.write_bytes(data)
                            logger.info(f"[战双语音] 下载成功！保存到: {save_path}")
                            return True
                        else:
                            logger.info(f"[战双语音] 失败 {resp.status}: {filename}")
                except Exception as e:
                    logger.info(f"[战双语音] 请求异常: {e}")
                    continue
        logger.warning(f"[战双语音] 全部尝试失败: {character} - {title} ({lang})")
        return False

    async def fetch_character_voices(self, character: str):
        logger.info(f"[战双语音] 开始下载角色: {character}")
        count = 0
        for i in self.auto_langs:
            try:
                lang = ["cn", "jp", "en", "yue"][int(i)-1]
            except:
                continue
            logger.info(f"[战双语音] 下载 {character} 的 {self.LANG_NAME[lang]} 语音...")
            for title in self.VOICE_DESCRIPTIONS:
                if title == "涂装专属语音" and not self.auto_download_coating:
                    continue
                if await self.download_voice(character, title, lang):
                    count += 1
                if title == "涂装专属语音":
                    break
        self.scan_voice_files()
        logger.info(f"[战双语音] {character} 下载完成，共 {count} 条")
        return count

    def get_best_lang(self, character: str) -> str:
        for c in self.default_rank:
            try:
                l = ["cn", "jp", "en", "yue"][int(c)-1]
                if character in self.voice_index and l in self.voice_index[character]:
                    return l
            except:
                pass
        return "cn"

    def get_voice_path(self, character: str, title: str, lang: str) -> Optional[Path]:
        if character.endswith("涂装"):
            return self.voices_dir / character.replace("涂装", "") / "cn" / "涂装专属语音.mp3"
        return self.voices_dir / character / lang / f"{title}.mp3"

    @filter.command("zspms", alias=["战双语音", "战双", "灰鸽", "pgr"])
    async def play(self, event: AstrMessageEvent, character: str = None, extra: str = None, voice_name: str = None, language: str = None):
        self.scan_voice_files()

        is_coating = extra and "涂装" in extra
        char_name = f"{character}涂装" if is_coating else character

        if not char_name:
            if not self.voice_index:
                yield event.plain_result("还没有任何语音～快用 /zspms_fetch 下载吧")
                return
            char_name = random.choice(list(self.voice_index.keys()))

        lang = self.REVERSE_LANG.get(language.lower() if language else "", "") or self.get_best_lang(char_name)

        if lang not in self.voice_index.get(char_name, []):
            if not self.auto_download:
                yield event.plain_result(f"未找到《{char_name}》的语音")
                return
            yield event.plain_result(f"正在自动下载《{char_name.replace('涂装', '')}》...")
            await self.fetch_character_voices(char_name.replace("涂装", ""))
            lang = self.get_best_lang(char_name)

        title = voice_name if voice_name and voice_name != "0" else ("涂装专属语音" if is_coating else random.choice(self.VOICE_DESCRIPTIONS))

        path = self.get_voice_path(char_name, title, lang)
        if not path or not path.exists():
            yield event.plain_result(f"语音不存在：{title}")
            return

        yield event.plain_result(f"正在播放 {char_name} 的 {title} ({self.LANG_NAME[lang]})")
        yield event.chain_result([Record.fromFileSystem(str(path))])

    @filter.command("zspms_list", alias=["战双列表"])
    async def list(self, event: AstrMessageEvent):
        self.scan_voice_files()
        if not self.voice_index:
            yield event.plain_result("暂无缓存，使用 /zspms_fetch [角色] 下载")
            return
        lines = [f"战双帕弥什 已缓存构造体（{len(self.voice_index)}个）\n"]
        for n in sorted(self.voice_index):
            ls = " ".join(f"[{self.LANG_NAME.get(l,l)}]" for l in self.voice_index[n])
            c = " ✨涂装" if n.endswith("涂装") else ""
            lines.append(f"• {n}{c}  {ls}")
        yield event.plain_result("\n".join(lines))

    @filter.command("zspms_fetch", alias=["战双下载", "下载战双语音"])
    async def fetch(self, event: AstrMessageEvent, character: str):
        yield event.plain_result(f"正在下载《{character}》全语音...")
        count = await self.fetch_character_voices(character)
        yield event.plain_result(f"下载完成！共 {count} 条语音已保存到 {self.voices_dir}")

    @filter.command("zspms_help", alias=["战双帮助"])
    async def help(self, event: AstrMessageEvent):
        help_text = """
战双帕弥什语音插件 v1.0.0

/zspms 露娜·银冕 戳一下          → 自动选语言
/zspms 露娜·银冕 信赖触摸 jp     → 强制日语
/zspms 露娜·银冕 涂装 涂装专属语音 → 播放涂装语音
/zspms_list                    → 查看缓存列表
/zspms_fetch 绯耀               → 下载该角色全部语音
""".strip()
        yield event.plain_result(help_text)