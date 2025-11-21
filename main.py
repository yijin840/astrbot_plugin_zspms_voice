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

        logger.info("[战双语音] ========== 开始初始化 ==========")

        data_dir_raw = StarTools.get_data_dir("astrbot_plugin_zspms_voice")
        logger.info(f"[战双语音] 原始数据目录类型: {type(data_dir_raw)}")
        logger.info(f"[战双语音] 原始数据目录值: {data_dir_raw}")

        self.data_dir = Path(str(data_dir_raw))
        logger.info(f"[战双语音] 转换后数据目录: {self.data_dir}")
        logger.info(f"[战双语音] 数据目录是否存在: {self.data_dir.exists()}")

        self.voices_dir = self.data_dir / "voices"
        logger.info(f"[战双语音] 语音缓存目录: {self.voices_dir}")

        try:
            self.voices_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[战双语音] ✅ 语音缓存目录创建成功")
        except Exception as e:
            logger.error(f"[战双语音] ❌ 创建语音缓存目录失败: {e}")

        plugin_root = self.data_dir.parent.parent / "plugins" / "astrbot_plugin_zspms_voice"
        logger.info(f"[战双语音] 插件根目录: {plugin_root}")
        logger.info(f"[战双语音] 插件根目录是否存在: {plugin_root.exists()}")

        voices_json_path = plugin_root / "voices.json"
        logger.info(f"[战双语音] voices.json完整路径: {voices_json_path}")
        logger.info(f"[战双语音] voices.json是否存在: {voices_json_path.exists()}")

        self.voice_list = []

        try:
            if voices_json_path.exists():
                with open(str(voices_json_path), "r", encoding="utf-8") as f:
                    self.voice_list = json.load(f)
                logger.info(f"[战双语音] ✅ 成功加载 {len(self.voice_list)} 个角色")
                # 仅打印前5个角色的标题以避免日志过长
                titles = [c.get("title", "未知") for c in self.voice_list[:5]]
                logger.info(f"[战双语音] 部分角色列表: {titles}")
            else:
                logger.error(f"[战双语音] ❌ voices.json文件不存在")
                logger.error(f"[战双语音] 请确保文件在: {voices_json_path}")
        except Exception as e:
            logger.error(f"[战双语音] ❌ 读取voices.json失败: {e}", exc_info=True)

        logger.info("[战双语音] ========== 初始化完成 ==========")

    async def download_and_send(self, event, file_name, character, title):
        logger.info(f"[战双语音] ---------- 开始处理语音 ----------")
        logger.info(f"[战双语音] 角色: {character}")
        logger.info(f"[战双语音] 标题: {title}")
        logger.info(f"[战双语音] 原始文件名: {file_name}")

        safe_character = re.sub(r'[\\/:*?"<>|]', '_', character)
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', title)
        logger.info(f"[战双语音] 安全角色名: {safe_character}")
        logger.info(f"[战双语音] 安全标题: {safe_title}")

        save_path = self.voices_dir / safe_character / f"{safe_title}.mp3"
        logger.info(f"[战双语音] 保存路径: {save_path}")
        logger.info(f"[战双语音] 父目录: {save_path.parent}")
        logger.info(f"[战双语音] 文件是否已存在: {save_path.exists()}")

        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"[战双语音] ✅ 父目录创建成功")
        except Exception as e:
            logger.error(f"[战双语音] ❌ 创建父目录失败: {e}")
            yield event.plain_result(f"创建目录失败: {e}")
            return

        if not save_path.exists():
            # --- START: 关键的路径修正逻辑（从您原来的代码中恢复） ---
            # 战双维基的 Special:Redirect/file 链接要求去掉文件名中的第一个“·”及其左边的内容。
            # 示例: "文件:蒲牢·华钟 中 问候.mp3" 必须变成 "文件:华钟 中 问候.mp3" 才能下载。

            download_path = file_name
            try:
                # 1. 分割文件名前缀（"文件:"）和文件名主体
                prefix, name_body = file_name.split(":", 1)

                # 2. 找到第一个 "·" 并只保留右侧内容
                if "·" in name_body:
                    _, right_part = name_body.split("·", 1)
                    # 重新组合路径
                    download_path = f"{prefix}:{right_part.strip()}"

            except Exception as e:
                # 如果分割失败，例如文件名中没有 ':', 仍然使用原始文件名
                logger.warning(f"[战双语音] 修正文件名失败，使用原始文件名: {e}")

            # 构造 URL
            download_path_encoded = download_path.replace(' ', '%20')
            url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{download_path_encoded}"
            logger.info(f"[战双语音] 修正后的下载路径: {download_path}")
            logger.info(f"[战双语音] 下载URL: {url}")
            # --- END: 关键的路径修正逻辑 ---

            yield event.plain_result(f"正在为你下载 {character} 的「{title}」...")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                try:
                    logger.info(f"[战双语音] 开始HTTP请求...")
                    # 可以在这里添加您的默认 Headers，如果您需要的话：
                    # headers = {"User-Agent": "YourPlugin/1.0"}
                    # async with session.get(url, headers=headers) as response:
                    async with session.get(url) as response:
                        logger.info(f"[战双语音] HTTP状态码: {response.status}")
                        logger.info(f"[战双语音] 响应头: {dict(response.headers)}")

                        if response.status == 200:
                            content = await response.read()
                            content_length = len(content)
                            logger.info(
                                f"[战双语音] 下载内容大小: {content_length} 字节 ({content_length / 1024:.2f} KB)")

                            try:
                                save_path.write_bytes(content)
                                logger.info(f"[战双语音] ✅ 文件写入成功: {save_path}")
                                logger.info(f"[战双语音] 文件大小验证: {save_path.stat().st_size} 字节")
                            except Exception as write_error:
                                logger.error(f"[战双语音] ❌ 文件写入失败: {write_error}")
                                yield event.plain_result(f"保存文件失败: {write_error}")
                                return
                        else:
                            logger.error(f"[战双语音] ❌ HTTP请求失败，状态码: {response.status}")
                            yield event.plain_result(f"下载失败(HTTP {response.status})，下次再试吧~")
                            return

                except aiohttp.ClientError as client_error:
                    logger.error(f"[战双语音] ❌ 网络请求异常(ClientError): {client_error}")
                    yield event.plain_result(f"网络请求失败: {client_error}")
                    return
                except Exception as e:
                    logger.error(f"[战双语音] ❌ 下载异常: {e}", exc_info=True)
                    yield event.plain_result(f"下载出错: {e}")
                    return
        else:
            logger.info(f"[战双语音] 文件已存在，跳过下载")

        logger.info(f"[战双语音] 准备发送语音文件: {save_path}")
        yield event.plain_result(f"来！{character} 的「{title}」~")

        try:
            # 确保 Record 类是可用的，并且路径是正确的字符串
            yield event.chain_result([Record.fromFileSystem(str(save_path))])
            logger.info(f"[战双语音] ✅ 语音发送成功")
        except Exception as send_error:
            logger.error(f"[战双语音] ❌ 语音发送失败: {send_error}")
            yield event.plain_result(f"发送语音失败: {send_error}")

        logger.info(f"[战双语音] ---------- 处理完成 ----------")

    @filter.command("zspms", alias=["战双语音", "zspms语音"])
    async def random_play(self, event: AstrMessageEvent):
        logger.info(f"[战双语音] 收到命令，触发随机播放")

        if not self.voice_list:
            logger.warning(f"[战双语音] 语音列表为空")
            yield event.plain_result("voices.json 没找到或加载失败！请检查插件目录")
            return
        available_chars = [
            char for char in self.voice_list
            if char.get("voices") and isinstance(char["voices"], list) and len(char["voices"]) > 0
        ]
        if not available_chars:
            logger.warning(f"[战双语音] 筛选后，没有可用的有语音的角色列表")
            yield event.plain_result("voices.json 中所有角色的语音列表都为空，无法播放！")
            return
        char = random.choice(available_chars)
        character = char.get("title", "未知角色")
        logger.info(f"[战双语音] 随机选中角色: {character}")

        voices = char.get("voices", [])
        if not voices:
            logger.warning(f"[战双语音] 角色 {character} 没有语音列表，跳过")
            yield event.plain_result(f"{character} 暂时没语音哦~ (请检查 voices.json)")
            return

        file_name = random.choice(voices)
        logger.info(f"[战双语音] 随机选中文件: {file_name}")

        # 尝试解析标题，假设格式是 "文件: [角色名] [语言] [标题].mp3" 或 "文件:[角色名·构造体名] [语言] [标题].mp3"
        # 简单地取空格后的第三个词开始作为标题
        try:
            # 找到第一个空格后的内容，然后找到第二个空格后的内容，作为标题的起始
            parts = file_name.split(" ", 2)
            if len(parts) > 2:
                title = parts[-1].replace(".mp3", "").strip()
            else:
                title = file_name.replace(".mp3", "").strip()
        except Exception:
            title = file_name.replace(".mp3", "").strip()

        logger.info(f"[战双语音] 解析标题: {title}")

        async for result in self.download_and_send(event, file_name, character, title):
            yield result
