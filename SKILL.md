---
name: csv-translator
description: Translate CSV product text columns across DE/FR/IT/ES/NL with case matching, multi-line preservation, unit standardization. Auto-detects columns by content. Supports EN optimization. Use when user needs to fill a Translated Text column or translate product copy across European languages.
user-invocable: true
argument-hint: <csv_file_path> [--in-place]
---

# CSV 多语言翻译 Skill

将 CSV 文件中产品文本翻译为 DE(德语) / FR(法语) / IT(意大利语) / ES(西班牙语) / NL(荷兰语)。EN(英语) 目标语言时对原文做大小写和单位优化。

## 使用方式

```
/csv-translator <csv_file_path> --in-place
```

脚本自动识别 CSV 中哪列是原文、哪列是语种代码、哪列是译文输出，**不需要固定列名**。

可选参数：
- `--source-col NAME`：手动指定原文列名
- `--target-col NAME`：手动指定译文列名
- `--locale-col NAME`：手动指定语种列名
- `--in-place`：原地更新文件
- `--output PATH`：指定输出路径

## 翻译规则

| 规则 | 说明 |
|------|------|
| 大小写匹配 | 原文全大写→译文全大写，词首大写→词首大写 |
| 词首大写 | EN 按英文规则（介词连词小写），其他语言每词首字母大写 |
| 数字跳过 | 纯数字（3, 20, 75...）留空 |
| 多行保留 | 原文换行→译文对应换行 |
| 单位标准化 | 覆盖所有常用计量单位（见下方） |

## EN 目标语言

不翻译，只优化：
- 修正大小写：`Easy To Use` → `Easy to Use`
- 标准化单位：`65w Charger` → `65 W Charger`
- 全大写原文保持不变

## 支持的语种代码

`DE` `FR` `IT` `ES` `NL` `EN` `PT` `PL` `RU` `JA` `ZH` `KO` 等 50+

## 单位标准化

脚本内置 ~60 个常用单位的标准化形式。

| 类别 | 单位 |
|------|------|
| 长度 | mm cm m km in ft yd mi |
| 重量 | mg g kg t oz lb |
| 体积 | ml cl L gal |
| 功率 | W kW MW HP |
| 电压/电流 | V kV A mA Ah mAh Wh kWh |
| 频率 | Hz kHz MHz GHz |
| 压强 | Pa hPa kPa MPa bar PSI |
| 力/扭矩 | N kN Nm |
| 速度 | m/s km/h mph |
| 时间 | s ms min h |
| 温度 | °C °F |
| 其他 | % dB RPM |

规则：
- 数字与单位分离加空格：`20CM` → `20 cm`
- 单位大小写修正：`KG` → `kg`，`W` 保持 `W`
- 欧洲语言小数点用逗号：`3.3 kg` → `3,3 kg`

## 处理新文本

遇到词典中没有的源文本时，脚本会在 D 列填入 `[TODO:语言代码]` 并打印未翻译列表。将其加入 `references/translations.json` 即可。

## 文件结构

```
csv-translator/
├── SKILL.md
├── scripts/translate.py
└── references/translations.json
```
