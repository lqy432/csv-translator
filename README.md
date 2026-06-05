# csv-translator

Product copy CSV translator for European languages. A Python CLI tool that
reads a CSV, translates English source text to DE/FR/IT/ES/NL using a JSON
dictionary, and writes back — with case matching, unit standardization,
and multi-line preservation.

## Features

- **Dictionary-based** — fast, offline, no API calls
- **Auto-detect columns** — no fixed column names required
- **Case matching** — ALL CAPS input → ALL CAPS output, Title Case → Title Case
- **Unit standardization** — fixes `65w` → `65 W`, `3.3kg` → `3.3 kg` (~60 units)
- **English optimization** — corrects title case for EN locale
- **Multi-line handling** — line breaks preserved in output
- **Zero dependencies** — Python standard library only

## Install

```bash
git clone https://github.com/lqy432/csv-translator.git
```

## Usage

```bash
python translate.py input.csv --in-place
```

| Option | Description |
|--------|-------------|
| `--in-place` | Overwrite input file (default: creates `xxx_translated.csv`) |
| `--source-col` | Source text column name (auto-detected if omitted) |
| `--target-col` | Output column name (auto-detected if omitted) |
| `--locale-col` | Locale column name (auto-detected if omitted) |
| `--output PATH` | Explicit output file path |

## Supported Locales

`DE` (German) · `FR` (French) · `IT` (Italian) · `ES` (Spanish) · `NL` (Dutch)

EN locale runs text optimization instead of translation.

## How It Works

```
CSV input → Auto-detect columns → Look up dictionary → Apply case → Fix units → Output
                                        ↓ (not found)
                                  Mark as [TODO:XX]
```

## Dictionary

Translations live in `references/translations.json`. New entries are picked up
automatically — no code changes needed.

```json
{
  "single_line": {
    "SOURCE TEXT": {
      "DE": "German",
      "FR": "French"
    }
  }
}
```

## Claude Code Skill

Also available as a Claude Code skill:

```
/csv-translator "file.csv" --in-place
```
