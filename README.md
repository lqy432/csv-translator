# CSV 多语言翻译

产品文案 CSV → DE/FR/IT/ES/NL 自动翻译。

## 安装

**前提：** 电脑需安装 [Python 3](https://www.python.org/downloads/) 和 [Git](https://git-scm.com/downloads)。

```bash
# 克隆到 Claude Code 技能目录
git clone https://github.com/lqy432/csv-translator.git ~/.claude/skills/csv-translator
```

克隆后重启 Claude Code 即可生效。

## 使用

在 Claude Code 中输入：

```
/csv-translator "文件路径.csv" --in-place
```

| 参数 | 说明 |
|------|------|
| `--in-place` | 直接覆盖原文件，不加则生成 `xxx_translated.csv` |
| `--output 路径` | 指定输出文件位置 |

也可以在终端直接运行：

```bash
python ~/.claude/skills/csv-translator/scripts/translate.py "文件.csv" --in-place
```

### CSV 格式要求

| 列 | 内容 | 示例 |
|----|------|------|
| Locale | 语言代码 | DE / FR / IT / ES / NL |
| Source Text | 原文 | POWERFUL DRIVE SYSTEM |
| Translated Text | 译文（自动填入） | 留空即可 |

## 更新

```bash
cd ~/.claude/skills/csv-translator && git pull
```
