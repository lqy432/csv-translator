#!/usr/bin/env python3
"""
CSV Product Text Translator v2
===============================
Auto-detects columns by content. Translates across DE/FR/IT/ES/NL, optimizes
English text. Features: case matching per locale, multi-line preservation,
comprehensive unit standardization, number skipping.

Usage:
    python translate.py <csv_path> [options]
"""

import csv
import re
import os
import sys
import json
import argparse


# ============================================================
# Constants
# ============================================================

# Recognized locale codes (ISO 639-1 + some common variants)
KNOWN_LOCALES = {
    'DE', 'FR', 'IT', 'ES', 'NL', 'EN', 'PT', 'PL', 'RU', 'JA', 'ZH',
    'KO', 'AR', 'TR', 'SV', 'DA', 'NO', 'FI', 'CS', 'HU', 'RO', 'BG',
    'EL', 'HE', 'TH', 'VI', 'ID', 'MS', 'HI', 'BN', 'UK', 'SR', 'HR',
    'SK', 'SL', 'LT', 'LV', 'ET', 'IS', 'MT', 'GA', 'CY', 'EU', 'CA',
    'GL', 'SW', 'FA', 'HE', 'UR', 'TA', 'TE', 'MR', 'GU', 'KN', 'ML',
    'PA', 'BN', 'SI', 'LO', 'KM', 'MY', 'AM', 'NE',
    # Common regional variants
    'EN-US', 'EN-GB', 'PT-BR', 'PT-PT', 'ZH-CN', 'ZH-TW',
    'ES-MX', 'ES-ES', 'FR-CA', 'FR-FR', 'DE-DE', 'DE-AT', 'DE-CH',
    'NL-NL', 'NL-BE', 'IT-IT', 'IT-CH',
}

# Unit standardization map (lowercase key -> correct SI form)
# Pattern: number + optional-space + unit_alias -> number + space + correct_unit
UNIT_STANDARD = {
    # Length
    'mm': 'mm', 'cm': 'cm', 'm': 'm', 'km': 'km',
    'in': 'in', 'inch': 'in', 'inches': 'in',
    'ft': 'ft', 'feet': 'ft', 'yd': 'yd', 'mi': 'mi',
    # Weight
    'mg': 'mg', 'g': 'g', 'kg': 'kg', 't': 't',
    'oz': 'oz', 'lb': 'lb', 'lbs': 'lb',
    # Volume
    'ml': 'ml', 'cl': 'cl', 'l': 'L', 'gal': 'gal',
    # Power
    'w': 'W', 'kw': 'kW', 'mw': 'MW', 'hp': 'HP',
    # Electricity
    'v': 'V', 'kv': 'kV', 'a': 'A', 'ma': 'mA',
    'ah': 'Ah', 'mah': 'mAh', 'wh': 'Wh', 'kwh': 'kWh',
    # Frequency
    'hz': 'Hz', 'khz': 'kHz', 'mhz': 'MHz', 'ghz': 'GHz',
    # Pressure
    'pa': 'Pa', 'hpa': 'hPa', 'kpa': 'kPa', 'mpa': 'MPa',
    'bar': 'bar', 'psi': 'PSI',
    # Force / Torque
    'n': 'N', 'kn': 'kN', 'nm': 'Nm',
    # Speed
    'm/s': 'm/s', 'km/h': 'km/h', 'mph': 'mph',
    # Time
    's': 's', 'sec': 's', 'ms': 'ms',
    'min': 'min', 'mins': 'min', 'h': 'h', 'hr': 'hr', 'hrs': 'hr',
    # Temperature
    'c': '°C', 'f': '°F',
    # Other
    '%': '%', 'db': 'dB', 'rpm': 'RPM',
    # Angle
    'deg': '°',
}

# English minor words that should be lowercase in title case
# (prepositions, conjunctions, articles of 4 chars or fewer)
EN_MINOR_WORDS = {
    'a', 'an', 'the',
    'and', 'but', 'or', 'nor', 'for', 'so', 'yet',
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
    'up', 'off', 'out', 'per', 'via', 'into', 'onto', 'upon',
    'down', 'over', 'near', 'past',
    'as', 'if', 'not', 'than', 'that', 'this', 'each', 'some',
    'its', 'it',
}

# European locales (use comma as decimal separator: 3,3 kg)
EU_LOCALES = {'DE', 'FR', 'IT', 'ES', 'NL', 'PT', 'PL', 'RU', 'SV', 'DA',
              'NO', 'FI', 'CS', 'HU', 'RO', 'BG', 'EL', 'SK', 'SL', 'LT',
              'LV', 'ET', 'HR', 'SR', 'UK'}

# Locale-specific character sets — if source text contains these, it's likely
# already translated into that locale (used for skip-already-translated check).
LOCALE_SIGNATURE_CHARS = {
    'DE': set('äöüßÄÖÜ'),
    'FR': set('éèêëàâîïôûùçÉÈÊËÀÂÎÏÔÛÙÇ'),
    'IT': set('àèéìòùÀÈÉÌÒÙ'),
    'ES': set('áéíóúüñÁÉÍÓÚÜÑ¿¡'),
    'NL': set('éèëïêÉÈËÏÊ'),
}


# ============================================================
# Helpers
# ============================================================

def normalize_text(text):
    if text is None:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def has_newlines(text):
    if text is None:
        return False
    return '\n' in text or '\r' in text


def is_pure_number(text):
    normalized = normalize_text(text)
    if not normalized:
        return False
    return bool(re.match(r'^[\d.,]+$', normalized))


def is_mostly_ascii(text, threshold=0.9):
    """Check if text is mostly ASCII (suggests English source)."""
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return ascii_count / len(text) >= threshold


# ============================================================
# Unit standardization
# ============================================================

def _build_unit_pattern():
    """Build regex pattern matching number+unit combinations."""
    all_units = sorted(UNIT_STANDARD.keys(), key=len, reverse=True)
    escaped = [re.escape(u) for u in all_units]
    # Match: number (optional decimal) + optional space + unit
    # Captures: (full_match, number, unit_raw)
    pattern = r'(\d+(?:[.,]\d+)?)\s*(' + '|'.join(escaped) + r')(?![a-zA-Z])'
    return re.compile(pattern, re.IGNORECASE)


_UNIT_PATTERN = _build_unit_pattern()


def standardize_units(text, locale=None):
    """
    Fix unit formatting in text.
    - Separate number and unit with space
    - Fix unit case to standard form
    - EU locales: use comma as decimal separator
    """
    def replacer(m):
        number = m.group(1)
        unit_raw = m.group(2)
        standard_unit = UNIT_STANDARD.get(unit_raw.lower(), unit_raw)

        # Decimal separator
        if locale and locale.upper() in EU_LOCALES:
            number = number.replace('.', ',')

        return f'{number} {standard_unit}'

    return _UNIT_PATTERN.sub(replacer, text)


# ============================================================
# Case detection and application
# ============================================================

def _is_unit_word(w):
    """Check if a word is a known unit abbreviation (should be ignored for case detection)."""
    clean = w.strip('()[]{}"\',.;:!?')
    # Strip leading digits (e.g. "3.3kg" -> "kg")
    clean = re.sub(r'^[\d.,]+', '', clean)
    return clean.lower() in UNIT_STANDARD if clean else False


def get_case_type(text):
    """Determine case type: 'allcaps', 'title', or 'mixed'.
    Unit abbreviations (kg, cm, etc.) are ignored for case detection
    since they are always lowercase in standard form."""
    alpha_only = re.sub(r'[^a-zA-Z]', '', text)
    if not alpha_only:
        return 'mixed'

    if alpha_only == alpha_only.upper():
        return 'allcaps'

    flat_text = text.replace('\n', ' ').replace('\r', ' ')
    words = flat_text.split()
    if not words:
        return 'mixed'

    # Filter out number+unit words like "3.3kg" (units are naturally lowercase)
    alpha_words = [w for w in words
                   if re.search(r'[a-zA-Z]', w)
                   and not re.match(r'^[\d.,]', w)]
    if not alpha_words:
        return 'mixed'

    all_title = all(re.match(r'^[A-Z]', w) for w in alpha_words)
    return 'title' if all_title else 'mixed'


def apply_case(translation, case_type, locale=None):
    """
    Apply case type to translation, with per-locale title case rules.
    - allcaps: always uppercase (all languages)
    - title:
        EN: English rules (minor words lowercase)
        others: every word capitalized (product label convention)
    - mixed: keep as-is
    """
    if '\n' in translation:
        lines = translation.split('\n')
        return '\n'.join(apply_case(line, case_type, locale) for line in lines)

    if case_type == 'allcaps':
        return translation.upper()

    elif case_type == 'title':
        words = translation.split()
        result = []
        is_en = locale and locale.upper() == 'EN'

        for i, w in enumerate(words):
            if not w:
                result.append(w)
                continue

            is_first = (i == 0)
            is_last = (i == len(words) - 1)

            if is_en:
                # English title case: protect unit abbreviations, lowercase minor words
                if _is_unit_word(w):
                    result.append(w)
                    continue
                clean = w.strip('()[]{}"\',.;:!?')
                if (not is_first and not is_last
                        and clean.lower() in EN_MINOR_WORDS
                        and len(clean) <= 4):
                    result.append(w.lower())
                else:
                    result.append(w[0].upper() + w[1:] if len(w) > 1 else w.upper())
            else:
                # Non-EN product labels: every word capitalized (standard convention)
                result.append(w[0].upper() + w[1:] if len(w) > 1 else w.upper())

        return ' '.join(result)

    else:
        return translation


# ============================================================
# EN text optimization
# ============================================================

def optimize_en_text(source_text):
    """
    Optimize English source text without translation.
    1. Standardize units
    2. Fix title case (lowercase minor words)
    3. Re-standardize units (title-casing may have broken them)
    """
    text = standardize_units(source_text, locale='EN')
    case_type = get_case_type(source_text)
    text = apply_case(text, case_type, locale='EN')
    if case_type == 'title':
        text = standardize_units(text, locale='EN')
    return text


# ============================================================
# Auto column detection
# ============================================================

def _sample_rows(rows, n=10):
    """Get the first n data rows (skip header)."""
    data = rows[1:] if len(rows) > 1 else []
    return data[:min(n, len(data))]


def detect_columns(rows):
    """
    Auto-detect column roles.
    Primary: match header names against keyword sets.
    Fallback: content-based heuristics.
    Returns (locale_col, source_col, target_col) indices.
    """
    header = rows[0] if rows else []
    if not header:
        return None, None, None

    # === Primary: header name matching ===
    LOCALE_KEYWORDS = ['locale', 'language', 'lang', '语种', '语言']
    SOURCE_KEYWORDS = ['source text', 'source', '原文', '源文本', '源文字']
    TARGET_KEYWORDS = ['translat', 'target', '译文', '翻译', '译文输出', '结果']

    def _matches(h, keywords):
        lower = h.strip().lower()
        return any(kw in lower for kw in keywords)

    locale_col = source_col = target_col = None

    for i, h in enumerate(header):
        if locale_col is None and _matches(h, LOCALE_KEYWORDS):
            locale_col = i
        elif source_col is None and _matches(h, SOURCE_KEYWORDS):
            source_col = i
        elif target_col is None and _matches(h, TARGET_KEYWORDS):
            target_col = i

    if locale_col is not None and source_col is not None and target_col is not None:
        return locale_col, source_col, target_col

    # === Fallback: content-based detection ===
    sample = _sample_rows(rows)
    if not sample:
        return None, None, None

    num_cols = max(len(row) for row in sample) if sample else 0
    if num_cols == 0:
        return None, None, None

    # Score each column
    locale_score = [0] * num_cols
    empty_score = [0] * num_cols
    english_score = [0] * num_cols
    number_score = [0] * num_cols
    sample_count = [0] * num_cols

    for row in sample:
        for i in range(min(len(row), num_cols)):
            val = row[i].strip() if i < len(row) else ''
            sample_count[i] += 1

            if not val:
                empty_score[i] += 1
                continue

            # Locale check
            if val.upper() in KNOWN_LOCALES:
                locale_score[i] += 1

            # Number check
            if is_pure_number(val):
                number_score[i] += 1

            # English check
            if is_mostly_ascii(val) and val.upper() not in KNOWN_LOCALES and not is_pure_number(val):
                english_score[i] += 1

    # Normalize to ratios
    for i in range(num_cols):
        n = max(sample_count[i], 1)
        locale_score[i] /= n
        empty_score[i] /= n
        english_score[i] /= n
        number_score[i] /= n

    # Find locale column: highest locale score (must be > 0.5)
    locale_col = max(range(num_cols), key=lambda i: locale_score[i])
    if locale_score[locale_col] < 0.5:
        locale_col = None

    # Find target column: combine content (empty score) with header hints
    TARGET_KEYWORDS_FALLBACK = ['translat', 'target', '翻译', '译文', '结果']
    candidates = [i for i in range(num_cols) if i != locale_col]
    if candidates:
        def target_score(i):
            score = empty_score[i]
            h = header[i].lower() if header and i < len(header) else ''
            if any(kw in h for kw in TARGET_KEYWORDS_FALLBACK):
                score += 1.0
            return score

        target_col = max(candidates, key=target_score)
        if empty_score[target_col] < 0.3 and not any(
            kw in (header[target_col].lower() if header and target_col < len(header) else '')
            for kw in TARGET_KEYWORDS_FALLBACK
        ):
            target_col = min(candidates, key=lambda i: english_score[i] + locale_score[i])
    else:
        target_col = None

    # Find source column: highest english score, not locale or target
    remaining = [i for i in range(num_cols) if i != locale_col and i != target_col]
    if remaining:
        source_col = max(remaining, key=lambda i: english_score[i])
    else:
        source_col = None

    return locale_col, source_col, target_col


def print_detected_columns(header, locale_col, source_col, target_col):
    """Print auto-detected column mapping."""
    names = []
    for role, col in [('Locale', locale_col), ('Source', source_col), ('Target', target_col)]:
        if col is not None and col < len(header):
            names.append(f'{role}="{header[col]}"')
        else:
            names.append(f'{role}=?')
    print(f"Columns: {', '.join(names)}")


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
        self.already_count = 0
        # Reverse index: locale -> set of known translation strings (lowercased)
        self._reverse_index = self._build_reverse_index(data)

    def _detect_locales(self, data):
        locales = set()
        for section in [data.get('single_line', {}), data.get('multi_line', {})]:
            for source, translations in section.items():
                locales.update(translations.keys())
        return sorted(locales)

    def _build_reverse_index(self, data):
        """Build reverse index: for each locale, collect all known translations.
        Used to detect if source text is already a translation (skip, don't re-translate)."""
        index = {}
        for section in [data.get('single_line', {}), data.get('multi_line', {})]:
            for source, translations in section.items():
                for loc, text in translations.items():
                    if loc not in index:
                        index[loc] = set()
                    # Store normalized form for fuzzy matching
                    index[loc].add(normalize_text(text).lower())
        return index

    def is_already_translated(self, source_text, locale):
        """
        Check if source_text appears to already be in the target locale.
        Uses two signals:
        1. Reverse dictionary lookup — source matches a known translation
        2. Character signature — source contains locale-specific characters
        """
        locale_upper = locale.upper()

        # Signal 1: reverse dictionary match
        normalized_lower = normalize_text(source_text).lower()
        known = self._reverse_index.get(locale_upper, set())
        if normalized_lower in known:
            return True

        # Signal 2: locale-specific character signature
        sig_chars = LOCALE_SIGNATURE_CHARS.get(locale_upper, set())
        if sig_chars and any(c in source_text for c in sig_chars):
            return True

        return False

    def _apply_translation(self, base, source_text, locale_upper):
        """Standardize units, apply case, then re-standardize for title case."""
        base = standardize_units(base, locale_upper)
        case_type = get_case_type(source_text)
        result = apply_case(base, case_type, locale_upper)
        # Re-standardize after title-casing (fixes "Ml" -> "ml", "Kg" -> "kg", etc.)
        if case_type == 'title':
            result = standardize_units(result, locale_upper)
        return result

    def translate(self, source_text, locale):
        """
        Translate source_text to the given locale.
        Returns (translation, is_missing) tuple.
        """
        normalized = normalize_text(source_text)

        # Numbers -> leave empty
        if is_pure_number(normalized):
            return "", False

        locale_upper = locale.upper()

        # EN/UK: optimize text, don't translate
        if locale_upper in ('EN', 'UK'):
            return optimize_en_text(source_text), False

        # Already translated? Source text is already in target locale -> skip
        if self.is_already_translated(source_text, locale):
            self.already_count += 1
            return source_text, False

        # Multi-line lookup first
        if has_newlines(source_text):
            clean_source = source_text.replace('\r\n', '\n').replace('\r', '\n')
            base = self.multi.get(clean_source, {}).get(locale_upper)
            if base is not None:
                return self._apply_translation(base, source_text, locale_upper), False

        # Single-line lookup
        base = self.single.get(normalized, {}).get(locale_upper)
        if base is not None:
            return self._apply_translation(base, source_text, locale_upper), False

        # Missing
        self.untranslated.append((normalized, locale_upper, has_newlines(source_text)))
        return f"[TODO:{locale_upper}]", True

    def report(self):
        seen = set()
        unique = []
        for src, loc, is_multiline in self.untranslated:
            key = (src, loc)
            if key not in seen:
                seen.add(key)
                unique.append((src, loc, is_multiline))
        return unique


# ============================================================
# CSV processing
# ============================================================

def find_dict_path():
    """Auto-detect translations.json relative to this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(os.path.dirname(script_dir), 'references', 'translations.json')
    if os.path.exists(path):
        return path
    path = os.path.join(os.getcwd(), 'references', 'translations.json')
    if os.path.exists(path):
        return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Translate CSV product text across European languages.'
    )
    parser.add_argument('csv_path', help='Path to input CSV file')
    parser.add_argument('--source-col', default=None,
                        help='Source text column name (auto-detected if omitted)')
    parser.add_argument('--target-col', default=None,
                        help='Target translation column name (auto-detected if omitted)')
    parser.add_argument('--locale-col', default=None,
                        help='Locale code column name (auto-detected if omitted)')
    parser.add_argument('--in-place', action='store_true',
                        help='Overwrite the input file')
    parser.add_argument('--output', default=None,
                        help='Output file path')
    parser.add_argument('--dict', default=None,
                        help='Path to translations.json (auto-detected if omitted)')
    parser.add_argument('--missing-json', default=None,
                        help='Output untranslated entries as JSON to the given path')

    args = parser.parse_args()

    # Find dictionary
    dict_path = args.dict or find_dict_path()
    if not dict_path or not os.path.exists(dict_path):
        print("ERROR: Cannot find translations.json.")
        print("  Specify with --dict or place it in references/translations.json")
        sys.exit(1)

    print(f"Dictionary: {dict_path}")

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
        print("ERROR: No rows found!")
        sys.exit(1)

    header = rows[0]
    print(f"Header: {header}")
    print(f"Data rows: {len(rows) - 1}")

    # Determine column indices
    if args.locale_col and args.source_col and args.target_col:
        # Manual override
        try:
            col_locale = header.index(args.locale_col)
            col_source = header.index(args.source_col)
            col_target = header.index(args.target_col)
        except ValueError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        print(f"Columns (manual): Locale=\"{args.locale_col}\", "
              f"Source=\"{args.source_col}\", Target=\"{args.target_col}\"")
    else:
        # Auto-detect
        col_locale, col_source, col_target = detect_columns(rows)
        if col_locale is None or col_source is None or col_target is None:
            print("ERROR: Could not auto-detect columns. "
                  "Use --locale-col, --source-col, --target-col to specify.")
            sys.exit(1)
        print_detected_columns(header, col_locale, col_source, col_target)

    # Process
    processed = 0
    multiline_count = 0
    missing_count = 0
    number_skipped = 0
    en_optimized = 0

    for i in range(1, len(rows)):
        row = rows[i]

        if not row or all(cell.strip() == '' for cell in row):
            continue

        while len(row) <= max(col_locale, col_source, col_target):
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
            row[col_target] = ""
            if is_pure_number(normalize_text(source_text)):
                number_skipped += 1
        else:
            row[col_target] = translation
            processed += 1
            if has_newlines(source_text):
                multiline_count += 1
            if locale.upper() == 'EN':
                en_optimized += 1

    # Output path
    if args.output:
        output_path = args.output
    elif args.in_place:
        output_path = csv_path
    else:
        base, ext = os.path.splitext(csv_path)
        output_path = f"{base}_translated{ext}"

    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, delimiter=',', lineterminator='\n')
        writer.writerows(rows)

    # Summary
    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"Total rows        : {len(rows) - 1}")
    print(f"Translated        : {processed} ({multiline_count} multi-line)")
    if translator.already_count:
        print(f"Already translated: {translator.already_count}")
    if en_optimized:
        print(f"EN optimized      : {en_optimized}")
    print(f"Numbers skipped   : {number_skipped}")
    print(f"Missing           : {missing_count}")
    print(f"Output            : {output_path}")

    untranslated = translator.report()
    if untranslated:
        print(f"\n{'='*50}")
        print(f"UNTRANSLATED ({len(untranslated)} unique)")
        print(f"{'='*50}")
        for src, loc, is_ml in untranslated:
            tag = "ML" if is_ml else "SL"
            print(f"  [{loc}] [{tag}] {src}")
        print(f"\n  Add to references/translations.json under")
        print(f"  'single_line' or 'multi_line' as appropriate.")

        # JSON output
        if args.missing_json:
            sl_entries = []
            ml_entries = []
            for src, loc, is_ml in untranslated:
                if is_ml:
                    ml_entries.append({"source": src, "locale": loc})
                else:
                    sl_entries.append({"source": src, "locale": loc})
            report = {}
            if sl_entries:
                report["single_line"] = sl_entries
            if ml_entries:
                report["multi_line"] = ml_entries
            with open(args.missing_json, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n  Missing report written to: {args.missing_json}")

    print()


if __name__ == '__main__':
    main()
