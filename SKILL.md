---
name: csv-translator
description: Translate CSV product text columns across DE/FR/IT/ES/NL with case matching, multi-line preservation, unit standardization. Use when user needs to fill a Translated Text column in a CSV or translate product copy across European languages.
user-invocable: true
argument-hint: <csv_file_path> [--source-col C] [--target-col D] [--locale-col B]
---

# CSV 多语言翻译 Skill

将 CSV 文件中产品文本自动翻译为 DE(德语) / FR(法语) / IT(意大利语) / ES(西班牙语) / NL(荷兰语)。

## 使用方式

```
/csv-translator <csv_file_path>
```

可选参数：
- `--source-col`：源文本列名（默认 `Source Text`）
- `--target-col`：翻译输出列名（默认 `Translated Text`）
- `--locale-col`：语言代码列名（默认 `Locale`）
- `--in-place`：原地更新文件（默认生成 `<原名>_translated.csv`）
- `--output <path>`：指定输出路径

示例：
```
/csv-translator "a:\_Graphic Design\电商\CESHI\0t\0001111.csv" --in-place
```

## 翻译规则

脚本执行时自动应用以下规则：

1. **大小写匹配**：D 列译文与 C 列原文大小写一致
   - `POWERFUL` → `LEISTUNGSSTARK`
   - `Powerful` → `Leistungsstark`
   - `powerful` → `leistungsstark`

2. **数字跳过**：纯数字（如 `3`、`20`、`75`）的 D 列留空

3. **多行保留**：C 列内有换行的文本，D 列译文在对应位置换行
   ```
   AUTOMATIC CHAIN          AUTOMATISCHE
   LUBRICATION          →   KETTENSCHMIERUNG
   ```

4. **单位标准化**：所有计量单位遵循通用规范
   - `Kg` → `kg`
   - `65w` → `65 W`
   - `180ML` → `180 ml`
   - 欧洲语言使用逗号作小数点：`3,3 kg`

5. **语言代码**：B 列 `DE`→德语 `FR`→法语 `IT`→意大利语 `ES`→西班牙语 `NL`→荷兰语

## 处理新文本

当遇到翻译词典中没有的新源文本时：
1. 脚本会在 D 列填入 `[TODO:<locale>]` 标记
2. 脚本输出未翻译文本列表
3. 你应利用语言知识逐条翻译新文本
4. 翻译后，建议将新条目添加到 `references/translations.json` 中以备复用

翻译新文本时请遵循相同的规则（大小写匹配、单位标准化、多行保留）。

## 扩展翻译词典

编辑 `references/translations.json`：
- `single_line`：单行源文本的翻译
- `multi_line`：多行源文本的翻译（换行用 `\n` 表示）

添加新条目后脚本自动生效，无需修改代码。

## 脚本位置

核心脚本：`scripts/translate.py`
翻译词典：`references/translations.json`
