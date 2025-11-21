# # 文件名: __init__.py
# # 放在文件夹 astrbot_plugin_zspms_voice/ 下即可直接加载
#
# import json
# import random
# from pathlib import Path
# from typing import List, Optional, Dict, Tuple
#
# import aiohttp
# from astrbot.api import logger
# from astrbot.api.all import *
# from astrbot.api.event import filter, AstrMessageEvent
# from astrbot.api.star import StarTools
# from astrbot.core.config.astrbot_config import AstrBotConfig
#
#
# @register("astrbot_plugin_zspms_voice", "yijin840", "战双帕弥什全构造体语音插件（中日英粤+涂装）", "1.0.0")
# class ZSPMSPlugin(Star):
#     DEFAULT_HEADERS = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
#         "Referer": "https://wiki.biligame.com/zspms/",
#     }
#
#     VOICE_DESCRIPTIONS = [
#         "构造体加入", "升级", "晋升", "进化", "技能升级", "武器装备",
#         "编入队伍", "设为队长", "任务完成1",
#         "日常问候1", "日常问候2", "日常问候3", "日常问候4", "日常问候5",
#         "日常问候6", "日常问候7", "日常问候8", "日常问候9", "日常问候10",
#         "日常问候11", "日常问候12", "日常问候13", "日常问候14", "日常问候15",
#         "信赖提升1", "信赖提升2", "信赖提升3", "信赖提升4", "信赖提升5",
#         "信赖提升6", "信赖提升7", "信赖提升8", "信赖提升9", "信赖提升10",
#         "信赖提升11", "信赖提升12", "信赖提升13", "信赖提升14", "信赖提升15", "信赖提升16",
#         "空闲1", "空闲2", "空闲3", "空闲4", "空闲5",
#         "链接时间过长1", "链接时间过长2", "链接时间过长3", "链接时间过长4", "连接时间过长5",
#         "链接接入1", "链接接入2", "链接接入3", "链接接入4", "链接接入5",
#         "链接接入6", "链接接入7", "链接接入8",
#         "摇晃1", "摇晃2", "摇晃3",
#         "快速点击1", "快速点击2", "快速点击3",
#         "活跃度已满", "战斗开始", "战斗1", "战斗2", "战斗3",
#         "必杀", "受伤", "危险警告", "力尽", "助战", "QTE", "战斗结束",
#         "涂装专属语音",
#     ]
#
#     LANG_MAP = {"中": "cn"}
#
#     def __init__(self, context: Context, config: AstrBotConfig):
#         super().__init__(context)
#         logger.info("战双帕弥什语音插件正在初始化...")
#
#         # 修复路径问题：使用插件自己的 data 目录
#         self.data_dir = StarTools.get_data_dir("astrbot_plugin_zspms_voice")
#         self.voices_dir = self.data_dir / "voices"
#         self.assets_dir = self.data_dir / "assets"
#         self.plugin_dir = Path(__file__).parent.resolve()
#
#         # 强制创建目录 + 打印日志
#         for d in [self.data_dir, self.voices_dir, self.assets_dir]:
#             d.mkdir(parents=True, exist_ok=True)
#             logger.info(f"[战双语音] 创建目录: {d}")
#
#         self.voice_index: Dict[str, List[str]] = {}
#         self._load_config(config)
#         self.scan_voice_files()
#
#         logger.info(f"[战双语音] 初始化完成！语音将保存在: {self.voices_dir}")
#
#     def _load_config(self, config: AstrBotConfig):
#         self.config = config
#         self.auto_download = self.config.get("auto_download", True)
#         self.auto_download_coating = self.config.get("auto_download_coating", True)
#
#         self.language_list = ["cn"]
#         self.default_language_rank = self.config.get("default_language_rank", "1234")
#         self.auto_download_language = self.config.get("auto_download_language", "12")
#
#         self.lang_name = {"cn": "中文"}
#
#         # 自动生成配置模板
#         schema = {
#             "auto_download": {"description": "未找到语音时自动下载", "type": "bool", "default": True},
#             "auto_download_coating": {"description": "自动下载涂装语音", "type": "bool", "default": True},
#             "default_language_rank": {"type": "string", "description": "语言优先级 1中文 2日语 3英语 4粤语",
#                                       "default": "1234"},
#             "auto_download_language": {"type": "string", "description": "自动下载的语言（填数字组合）", "default": "12"},
#         }
#         schema_path = self.data_dir / "_conf_schema.json"
#         if not schema_path.exists():
#             schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=4), encoding="utf-8")
#             logger.info("[战双语音] 已自动创建 _conf_schema.json")
#
#     def scan_voice_files(self):
#         self.voice_index.clear()
#         if not self.voices_dir.exists():
#             logger.warning("[战双语音] voices 目录不存在，已自动创建")
#             return
#         for char_dir in self.voices_dir.iterdir():
#             if not char_dir.is_dir():
#                 continue
#             char_name = char_dir.name
#             langs = []
#             for lang_dir in char_dir.iterdir():
#                 if lang_dir.is_dir() and any(f.suffix == ".mp3" for f in lang_dir.iterdir()):
#                     langs.append(lang_dir.name)
#             if langs:
#                 self.voice_index[char_name] = langs
#                 if (char_dir / "cn" / "涂装专属语音.mp3").exists():
#                     self.voice_index[f"{char_name}涂装"] = ["cn"]
#         logger.info(f"[战双语音] 扫描完成，发现 {len(self.voice_index)} 个构造体")
#
#     async def download_single_voice(self, character: str, title: str, lang: str) -> bool:
#         # 正确的文件名格式：文件:角色名 [语言] 标题.mp3
#         lang_text = {"cn": "中"}[lang]
#         if title == "涂装专属语音":
#             filename = f"文件:{character} 涂装语音.mp3"  # 涂装固定这样
#         else:
#             filename = f"文件:{character} {lang_text} {title}.mp3"
#
#         prefix, name = filename.split(":", 1)
#         # 只处理第一个“·”左右的内容
#         left, right = name.split("·", 1)
#         # 拼回结果
#         path = f"{prefix}:{right.strip()}"
#
#         url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{path.replace(' ', '%20')}"
#
#         save_dir = self.voices_dir / character / lang
#         save_dir.mkdir(parents=True, exist_ok=True)
#         save_path = save_dir / f"{title}.mp3"
#
#         if save_path.exists():
#             logger.info(f"[战双语音] 已存在: {save_path}")
#             return True
#
#         async with aiohttp.ClientSession(headers=self.DEFAULT_HEADERS) as session:
#             logger.info(f"[战双语音] 正在下载: {url}")
#             try:
#                 async with session.get(url, timeout=30) as resp:
#                     if resp.status == 200:
#                         data = await resp.read()
#                         save_path.write_bytes(data)
#                         logger.info(f"[战双语音] 下载成功！保存到: {save_path}")
#                         return True
#                     else:
#                         logger.info(f"[战双语音] 下载失败 (状态码 {resp.status})")
#             except Exception as e:
#                 logger.info(f"[战双语音] 请求异常: {e}")
#
#         logger.warning(f"[战双语音] 下载失败: {character} - {title} ({lang})")
#         return False
#
#     async def fetch_character_voices(self, character: str) -> Tuple[bool, str]:
#         logger.info(f"[战双语音] 开始下载角色: {character}")
#         success_count = 0
#         for i in self.auto_download_language:
#             try:
#                 lang = self.language_list[int(i) - 1]
#             except:
#                 continue
#             logger.info(f"[战双语音] 下载 {character} 的 {self.lang_name[lang]} 语音...")
#             for title in self.VOICE_DESCRIPTIONS:
#                 if title == "涂装专属语音" and not self.auto_download_coating:
#                     continue
#                 if await self.download_single_voice(character, title, lang):
#                     success_count += 1
#                 if title == "涂装专属语音":
#                     break
#         self.scan_voice_files()
#         return True, f"成功下载 {success_count} 条语音"
#
#     def get_best_lang(self, character: str) -> str:
#         for rank in self.default_language_rank:
#             try:
#                 lang = self.language_list[int(rank) - 1]
#                 if character in self.voice_index and lang in self.voice_index[character]:
#                     return lang
#             except:
#                 continue
#         return "cn" if character in self.voice_index else "nodownload"
#
#     def get_voice_path(self, character: str, title: str, lang: str) -> Optional[Path]:
#         if character.endswith("涂装"):
#             path = self.voices_dir / character.replace("涂装", "") / "cn" / "涂装专属语音.mp3"
#         else:
#             path = self.voices_dir / character / lang / f"{title}.mp3"
#         return path if path.exists() else None
#
#     @filter.command("zspms", alias=["战双语音", "zspms语音"])
#     async def zspms_handler(self, event: AstrMessageEvent, character: str = None, extra: str = None,
#                             voice_name: str = None, language: str = None):
#         self.scan_voice_files()
#
#         is_coating = False
#         if extra and "涂装" in extra:
#             is_coating = True
#             if character:
#                 character = f"{character}涂装"
#
#         if not character:
#             if not self.voice_index:
#                 yield event.plain_result("还没有缓存任何语音，快用 /zspms_fetch 下载吧~")
#                 return
#             character = random.choice(list(self.voice_index.keys()))
#
#         lang = "cn"
#         if language and language.lower() in self.LANG_MAP:
#             lang = self.LANG_MAP[language.lower()]
#         else:
#             lang = self.get_best_lang(character)
#
#         if lang == "nodownload":
#             if not self.auto_download:
#                 yield event.plain_result(f"未找到《{character}》的语音，自动下载已关闭")
#                 return
#             yield event.plain_result(f"未找到，正在自动下载《{character.replace('涂装', '')}》语音...")
#             ok, msg = await self.fetch_character_voices(character.replace("涂装", ""))
#             if not ok:
#                 yield event.plain_result(f"下载失败：{msg}")
#                 return
#             lang = self.get_best_lang(character)
#
#         if not voice_name or voice_name in ["0", "随机"]:
#             if is_coating:
#                 voice_name = "涂装专属语音"
#             else:
#                 voice_name = random.choice(self.VOICE_DESCRIPTIONS)
#
#         yield event.plain_result(f"正在播放 {character} 的语音：{voice_name} ({self.lang_name.get(lang, lang)})")
#
#         path = self.get_voice_path(character, voice_name, lang)
#         if not path:
#             yield event.plain_result("该语音暂时不存在哦~")
#             return
#
#         async for msg in self.send_voice_message(event, str(path)):
#             yield msg
#
#     @filter.command("zspms_list", alias=["战双语音列表", "zspms列表"])
#     async def list_handler(self, event: AstrMessageEvent):
#         self.scan_voice_files()
#         if not self.voice_index:
#             yield event.plain_result("还没有缓存任何语音，使用 /zspms_fetch [角色名] 下载吧")
#             return
#
#         lines = ["【战双帕弥什 已缓存构造体】\n"]
#         for name, langs in sorted(self.voice_index.items()):
#             lang_str = "".join(f"[{self.lang_name.get(l, l)}]" for l in langs)
#             coating = " ✨涂装" if name.endswith("涂装") else ""
#             lines.append(f"• {name}{coating}  {lang_str}")
#
#         yield event.plain_result("\n".join(lines) + f"\n\n总数：{len(self.voice_index)} 个")
#
#     @filter.command("zspms_fetch", alias=["战双下载语音", "下载战双语音"])
#     async def fetch_handler(self, event: AstrMessageEvent, character: str):
#         yield event.plain_result(f"正在下载《{character}》的语音，请稍等...")
#         ok, msg = await self.fetch_character_voices(character)
#         yield event.plain_result("✔ 下载完成！" if ok else f"✘ 下载失败：{msg}")
#
#     async def send_voice_message(self, event: AstrMessageEvent, voice_path: str):
#         try:
#             chain = [Record.fromFileSystem(voice_path)]
#             yield event.chain_result(chain)
#         except Exception as e:
#             yield event.plain_result(f"发送语音失败：{e}")
