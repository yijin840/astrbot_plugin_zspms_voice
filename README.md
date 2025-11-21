# astrbot_plugin_zspms_voice

战双帕弥什全构造体语音插件 for AstrBot

[![版本](https://img.shields.io/badge/版本-v1.0.0-blue)](.) [![AstrBot](https://img.shields.io/badge/AstrBot-插件-green)](https://github.com/Soulter/AstrBot) [![战双帕弥什](https://img.shields.io/badge/游戏-战双帕弥什-ff69b4)](https://grayravens.com)

> 支持中文语音 + 涂装专属语音  
> 自动下载、优先级语言、随机播放、图片列表一应俱全  
> 数据来源：战双帕弥什官方 wiki（明文直链，永不失效）

## 功能列表

| 命令                       | 功能说明                        |
|--------------------------|-----------------------------|
| `/zspms 露娜·银冕 戳一下`       | 播放露娜·银冕的「戳一下」语音             |
| `/zspms 露娜·银冕 涂装 涂装专属语音` | 播放该涂装的专属语音（目前只有中文）          |
| `/zspms 0 信赖触摸`          | 不写角色名 = 随机一个已缓存的构造体播放「信赖触摸」 |
| `/zspms_list`            | 查看所有已缓存的构造体和支持的语言（含涂装标记）    |
| `/zspms_fetch 绯耀`        | 手动下载绯耀的全语言语音（根据配置自动中/日）     |

## 安装方法

1. 将整个 `astrbot_plugin_zspms_voice` 文件夹放入 AstrBot 的 `plugins/` 目录
2. 重启 AstrBot 或发送 `/reload`
3. 第一次使用会自动生成配置和 `zspms_data/` 文件夹

## 数据存放位置（相对路径）
