#!/usr/bin/env python3
"""
CSV Product Text Translator
============================
Translates product copy in CSV files across DE/FR/IT/ES/NL languages.
Features: case matching, multi-line preservation, unit standardization,
number skipping, and extensible JSON-based translation dictionary.

Usage:
    python translate.py <csv_path> [options]

Options:
    --source-col NAME    Source text column name (default: "Source Text")
    --target-col NAME    Translation output column name (default: "Translated Text")
    --locale-col NAME    Locale code column name (default: "Locale")
    --in-place           Overwrite input file instead of creating a new one
    --output PATH        Specify output file path explicitly
    --dict PATH          Path to translations.json (auto-detected if omitted)
"""

import csv
import re
import os
import sys
import json
import argparse


# ============================================================
# Helpers
# ============================================================

def normalize_text(text):
    """Collapse all whitespace to single spaces, strip."""
    if text is None:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def has_newlines(text):
    """Check if text contains newline characters."""
    if text is None:
        return False
    return '\n' in text or '\r' in text


def is_pure_number(text):
    """Check if text is purely a number (integer, decimal, or comma-decimal)."""
    normalized = normalize_text(text)
    if not normalized:
        return False
    return bool(re.match(r'^[\d.,]+$', normalized))


def get_case_type(text):
    """
    Determine case type: 'allcaps', 'title', or 'mixed'.
    Handles multi-line text correctly.
    """
    alpha_only = re.sub(r'[^a-zA-Z]', '', text)
    if not alpha_only:
        return 'mixed'

    if alpha_only == alpha_only.upper():
        return 'allcaps'

    flat_text = text.replace('\n', ' ').replace('\r', ' ')
    words = flat_text.split()
    if not words:
        return 'mixed'

    alpha_words = [w for w in words if re.search(r'[a-zA-Z]', w)]
    if not alpha_words:
        return 'mixed'

    all_title = all(re.match(r'^[A-Z]', w) for w in alpha_words)
    return 'title' if all_title else 'mixed'


def apply_case(translation, case_type):
    """Apply case type to translation. Handles multi-line text line by line."""
    if '\n' in translation:
        lines = translation.split('\n')
        return '\n'.join(apply_case(line, case_type) for line in lines)

    if case_type == 'allcaps':
        return translation.upper()
    elif case_type == 'title':
        words = translation.split()
        result = []
        for w in words:
            if w:
                result.append(w[0].upper() + w[1:] if len(w) > 1 else w.upper())
        return ' '.join(result)
    else:
        return translation


# ============================================================
# Translation engine
# ============================================================

class Translator:
    """Loads translations from JSON and provides lookup with case matching."""

    def __init__(self, dict_path):
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.single = data.get('single_line', {})
        self.multi = data.get('multi_line', {})
        self.supported_locales = self._detect_locales(data)
        self.untranslated = []

    def _detect_locales(self, data):
        locales = set()
        for section in [data.get('single_line', {}), data.get('multi_line', {})]:
            for source, translations in section.items():
                locales.update(translations.keys())
        return sorted(locales)

    def translate(self, source_text, locale):
        """
        Translate source_text to the given locale.
        Returns (translation, is_missing) tuple.
        """
        normalized = normalize_text(source_text)

        # Numbers → leave empty
        if is_pure_number(normalized):
            return "", False

        # Try multi-line translation first
        if has_newlines(source_text):
            clean_source = source_text.replace('\r\n', '\n').replace('\r', '\n')
            base = self.multi.get(clean_source, {}).get(locale)
            if base is not None:
                case_type = get_case_type(source_text)
                return apply_case(base, case_type), False

        # Fall back to single-line translation
        base = self.single.get(normalized, {}).get(locale)
        if base is not None:
            case_type = get_case_type(source_text)
            return apply_case(base, case_type), False

        # Missing translation
        self.untranslated.append((normalized, locale))
        return f"[TODO:{locale}]", True

    def report(self):
        """Return list of unique untranslated (source, locale) pairs."""
        seen = set()
        unique = []
        for src, loc in self.untranslated:
            key = (src, loc)
            if key not in seen:
                seen.add(key)
                unique.append(key)
        return unique


# ============================================================
# CSV processing
# ============================================================

def find_dict_path():
    """Auto-detect translations.json relative to this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Try references/ alongside scripts/
    path = os.path.join(os.path.dirname(script_dir), 'references', 'translations.json')
    if os.path.exists(path):
        return path
    # Try relative to cwd
    path = os.path.join(os.getcwd(), 'references', 'translations.json')
    if os.path.exists(path):
        return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Translate CSV product text across European languages.'
    )
    parser.add_argument('csv_path', help='Path to input CSV file')
    parser.add_argument('--source-col', default='Source Text',
                        help='Source text column name (default: "Source Text")')
    parser.add_argument('--target-col', default='Translated Text',
                        help='Target translation column name (default: "Translated Text")')
    parser.add_argument('--locale-col', default='Locale',
                        help='Locale code column name (default: "Locale")')
    parser.add_argument('--in-place', action='store_true',
                        help='Overwrite the input file')
    parser.add_argument('--output', default=None,
                        help='Output file path (overrides default naming)')
    parser.add_argument('--dict', default=None,
                        help='Path to translations.json (auto-detected if omitted)')

    args = parser.parse_args()

    # Find translation dictionary
    dict_path = args.dict or find_dict_path()
    if not dict_path or not os.path.exists(dict_path):
        print("ERROR: Cannot find translations.json.")
        print("  Specify with --dict or place it in references/translations.json")
        sys.exit(1)

    print(f"Translation dictionary: {dict_path}")

    # Load translations
    translator = Translator(dict_path)
    print(f"Supported locales: {', '.join(translator.supported_locales)}")

    # Read CSV
    csv_path = args.csv_path
    if not os.path.exists(csv_path):
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter=',')
        rows = list(reader)

    if not rows:
        print("ERROR: No rows found in CSV!")
        sys.exit(1)

    header = rows[0]
    print(f"Header: {header}")
    print(f"Data rows: {len(rows) - 1}")

    # Find column indices by header name
    try:
        col_locale = header.index(args.locale_col)
        col_source = header.index(args.source_col)
        col_target = header.index(args.target_col)
    except ValueError as e:
        print(f"ERROR: Column not found in header: {e}")
        print(f"  Available columns: {header}")
        sys.exit(1)

    print(f"Columns: locale={header[col_locale]}, "
          f"source={header[col_source]}, "
          f"target={header[col_target]}")

    # Process rows
    processed = 0
    multiline_count = 0
    missing_count = 0
    number_skipped = 0

    for i in range(1, len(rows)):
        row = rows[i]

        if not row or all(cell.strip() == '' for cell in row):
            continue

        # Ensure row has enough columns
        while len(row) <= col_source:
            row.append('')

        locale = row[col_locale].strip() if len(row) > col_locale else ''
        source_text = row[col_source] if len(row) > col_source else ''

        if not locale or not source_text:
            continue

        translation, is_missing = translator.translate(source_text, locale)

        if is_missing:
            missing_count += 1
            row[col_target] = translation
        elif translation == "":
            # Number or empty
            row[col_target] = ""
            if is_pure_number(normalize_text(source_text)):
                number_skipped += 1
        else:
            row[col_target] = translation
            processed += 1
            if has_newlines(source_text):
                multiline_count += 1

    # Determine output path
    if args.output:
        output_path = args.output
    elif args.in_place:
        output_path = csv_path
    else:
        base, ext = os.path.splitext(csv_path)
        output_path = f"{base}_translated{ext}"

    # Write output
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=',', lineterminator='\n')
        writer.writerows(rows)

    # Summary
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Total rows processed : {len(rows) - 1}")
    print(f"Translations filled   : {processed} ({multiline_count} multi-line)")
    print(f"Numbers skipped       : {number_skipped}")
    print(f"Missing translations  : {missing_count}")
    print(f"Output                : {output_path}")

    # Report untranslated
    untranslated = translator.report()
    if untranslated:
        print(f"\n{'='*50}")
        print(f"UNTRANSLATED TEXTS ({len(untranslated)} unique)")
        print(f"{'='*50}")
        for src, loc in untranslated:
            print(f"  [{loc}] {src}")
        print(f"\n  Add translations to references/translations.json")
        print(f"  under 'single_line' or 'multi_line' as appropriate.")

    print()


if __name__ == '__main__':
    main()
