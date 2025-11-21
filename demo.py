# download_zspms_relative.py   ← 直接保存成这个名字就行

import asyncio
import aiohttp
from pathlib import Path

# ==================== 关键改动：使用相对路径 ====================
BASE_DIR = Path(__file__).parent.resolve()  # 脚本所在目录
DATA_DIR = BASE_DIR / "zspms_data"
VOICES_DIR = DATA_DIR / "voices"

# 自动创建目录（如果不存在）
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 配置区（只改这里就行） ====================
CHARACTER = "薇拉·绯耀"  # 要下载的角色名
LANG = "中"  # 中 / 日 / 英 / 粤

# 语音条目列表（直接复制你页面里的顺序就行）
VOICE_LIST = [
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
    "必杀", "受伤", "危险警告", "力尽", "助战", "QTE", "战斗结束"
]


# ==============================================================

async def download_one(session, title: str):
    # 构造 wiki 重定向链接
    filename = f"文件:{CHARACTER} {LANG} {title}.mp3"
    url = f"https://wiki.biligame.com/zspms/Special:Redirect/file/{filename}"

    # 保存路径：zspms_data/voices/绯耀/构造体加入.mp3
    save_dir = VOICES_DIR / CHARACTER
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{title}.mp3"

    if save_path.exists():
        print(f"✔ 已存在 → {CHARACTER}/{title}.mp3")
        return

    try:
        async with session.get(url, allow_redirects=True, timeout=30) as resp:
            if resp.status == 200:
                save_path.write_bytes(await resp.read())
                print(f"✔ 下载成功 → {CHARACTER}/{title}.mp3")
            else:
                print(f"✘ 下载失败（{resp.status}） → {title}")
    except Exception as e:
        print(f"✘ 异常 → {title} | {e}")


async def main():
    print(f"开始下载 【{CHARACTER}】 {LANG}语语音，共 {len(VOICE_LIST)} 条")
    print(f"保存路径：{VOICES_DIR.relative_to(Path.cwd())}\\{CHARACTER}\\")

    async with aiohttp.ClientSession() as session:
        tasks = [download_one(session, t) for t in VOICE_LIST]
        await asyncio.gather(*tasks)

    print("全部完成！去 ./zspms_data/voices/ 里听吧～")


if __name__ == "__main__":
    asyncio.run(main())