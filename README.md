# CSV 多语言翻译 Skill

将 CSV 文件中产品文本自动翻译为 DE(德语) / FR(法语) / IT(意大利语) / ES(西班牙语) / NL(荷兰语)。

## 安装

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/你的用户名/csv-translator.git ~/.claude/skills/csv-translator
```

## 更新词典

```bash
cd ~/.claude/skills/csv-translator
git pull
```

## 使用

在 Claude Code 中：
```
/csv-translator "文件路径.csv" --in-place
```

或直接命令行：
```bash
python ~/.claude/skills/csv-translator/scripts/translate.py "文件.csv" --in-place
```

## 翻译规则

- **大小写匹配**：原文全大写 → 译文全大写，词首大写 → 词首大写
- **数字跳过**：纯数字（3, 20, 75...）自动留空
- **多行保留**：原文换行 → 译文对应换行
- **单位标准化**：Kg→kg, 65w→65 W, 180ML→180 ml

## 扩展词典

编辑 `references/translations.json`，提交 PR 即可与团队共享新翻译。
