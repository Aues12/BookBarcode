"""Yayına hazır, nominal boyutta ISBN-13 / EAN-13 SVG üreticisi.

Ölçüler GS1'in EAN-13 için verdiği nominal (X = 0,33 mm) ölçülerdir:
95 modüllük sembol, solda 11X/sağda 7X sessiz alan, 22,85 mm çubuk
yüksekliği ve 5X aşağı uzayan başlangıç/orta/bitiş koruma çubukları.
"""

from __future__ import annotations

import argparse
import re
from html import escape
from pathlib import Path
from xml.etree import ElementTree


X_MM = 0.33
SYMBOL_MODULES = 95
LEFT_QUIET_MODULES = 11
RIGHT_QUIET_MODULES = 7
BAR_HEIGHT_MM = 22.85
GUARD_EXTENSION_MODULES = 5

TITLE_BASELINE_MM = 3.5
BAR_TOP_MM = 5.0
HRI_BASELINE_MM = BAR_TOP_MM + BAR_HEIGHT_MM + 2.85
BOTTOM_MARGIN_MM = 0.8

TOTAL_WIDTH_MM = (LEFT_QUIET_MODULES + SYMBOL_MODULES + RIGHT_QUIET_MODULES) * X_MM
TOTAL_HEIGHT_MM = HRI_BASELINE_MM + BOTTOM_MARGIN_MM
SYMBOL_START_MM = LEFT_QUIET_MODULES * X_MM

LEFT_PATTERNS = (
    "LLLLLL",
    "LLGLGG",
    "LLGGLG",
    "LLGGGL",
    "LGLLGG",
    "LGGLLG",
    "LGGGLL",
    "LGLGLG",
    "LGLGGL",
    "LGGLGL",
)
L_CODES = (
    "0001101", "0011001", "0010011", "0111101", "0100011",
    "0110001", "0101111", "0111011", "0110111", "0001011",
)
R_CODES = tuple("".join("1" if bit == "0" else "0" for bit in code) for code in L_CODES)
G_CODES = tuple(code[::-1] for code in R_CODES)
GUARD_MODULES = frozenset((0, 2, 46, 48, 92, 94))


def normalise_isbn(value: str) -> str:
    """Boşlukları, tireleri ve isteğe bağlı ISBN önekini kaldırır."""
    value = re.sub(r"^\s*ISBN(?:-13)?\s*:?\s*", "", value, flags=re.IGNORECASE)
    return re.sub(r"[-\s]", "", value)


def calculate_check_digit(first_twelve_digits: str) -> str:
    """İlk 12 rakamdan EAN-13 kontrol rakamını hesaplar."""
    if len(first_twelve_digits) != 12 or not first_twelve_digits.isdigit():
        raise ValueError("Kontrol rakamı için tam 12 rakam gerekir.")
    weighted_sum = sum(
        int(digit) * (1 if index % 2 == 0 else 3)
        for index, digit in enumerate(first_twelve_digits)
    )
    return str((-weighted_sum) % 10)


def validate_isbn13(value: str) -> str:
    """ISBN-13 biçimini, önekini ve kontrol rakamını doğrular."""
    isbn = normalise_isbn(value)
    if len(isbn) != 13 or not isbn.isdigit():
        raise ValueError("ISBN-13, tireler hariç tam 13 rakamdan oluşmalıdır.")
    if not isbn.startswith(("978", "979")):
        raise ValueError("ISBN-13, 978 veya 979 ön ekiyle başlamalıdır.")
    expected = calculate_check_digit(isbn[:12])
    if isbn[-1] != expected:
        raise ValueError(
            f"Geçersiz ISBN-13 kontrol rakamı: {isbn[-1]} yerine {expected} olmalı."
        )
    return isbn


def validate_display_text(display_text: str, isbn: str) -> str:
    """Üst başlığın kodlanan ISBN ile aynı rakamları taşıdığını doğrular."""
    if not re.match(r"^ISBN(?:-13)?\s", display_text, flags=re.IGNORECASE):
        raise ValueError("Üst başlık 'ISBN ' veya 'ISBN-13 ' ile başlamalıdır.")
    if normalise_isbn(display_text) != isbn:
        raise ValueError("Üst başlıktaki rakamlar barkoda kodlanan ISBN ile aynı değil.")
    return display_text.strip()


def encode_ean13(isbn: str) -> str:
    """13 rakamı, EAN-13'ün 95 modüllük 0/1 desenine dönüştürür."""
    parity = LEFT_PATTERNS[int(isbn[0])]
    left = "".join(
        (L_CODES if encoding == "L" else G_CODES)[int(digit)]
        for digit, encoding in zip(isbn[1:7], parity)
    )
    right = "".join(R_CODES[int(digit)] for digit in isbn[7:])
    pattern = f"101{left}01010{right}101"
    if len(pattern) != SYMBOL_MODULES:
        raise AssertionError("EAN-13 deseni 95 modül olmalı.")
    return pattern


def _mm(value: float) -> str:
    """Milimetre değerini SVG için gereksiz sıfırlardan arındırır."""
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _black_runs(pattern: str) -> list[tuple[int, int]]:
    """Ardışık siyah modülleri başlangıç ve genişlik çiftlerine dönüştürür."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, bit in enumerate(pattern + "0"):
        if bit == "1" and start is None:
            start = index
        elif bit == "0" and start is not None:
            runs.append((start, index - start))
            start = None
    return runs


def build_svg(isbn: str, display_text: str) -> str:
    """Doğrulanmış ISBN için yayın dizgisine uygun SVG metni oluşturur."""
    isbn = validate_isbn13(isbn)
    display_text = validate_display_text(display_text, isbn)
    pattern = encode_ean13(isbn)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{_mm(TOTAL_WIDTH_MM)}mm" height="{_mm(TOTAL_HEIGHT_MM)}mm" '
            f'viewBox="0 0 {_mm(TOTAL_WIDTH_MM)} {_mm(TOTAL_HEIGHT_MM)}" '
            'role="img" aria-labelledby="title desc">'
        ),
        f'  <title id="title">{escape(display_text)} barkodu</title>',
        (
            f'  <desc id="desc">EAN-13 biçiminde kodlanmış ISBN '
            f'{escape(isbn)}; nominal X boyutu 0,33 mm.</desc>'
        ),
        f'  <rect width="{_mm(TOTAL_WIDTH_MM)}" height="{_mm(TOTAL_HEIGHT_MM)}" fill="#fff"/>',
        (
            f'  <text id="isbn-title" x="{_mm(TOTAL_WIDTH_MM / 2)}" '
            f'y="{_mm(TITLE_BASELINE_MM)}" text-anchor="middle" '
            'font-family="Arial, Helvetica, sans-serif" font-size="3.175">'
            f'{escape(display_text)}</text>'
        ),
        '  <g id="bars" fill="#000" shape-rendering="crispEdges">',
    ]

    for run_start, run_width in _black_runs(pattern):
        x = SYMBOL_START_MM + run_start * X_MM
        run_modules = range(run_start, run_start + run_width)
        is_guard = all(module in GUARD_MODULES for module in run_modules)
        height = BAR_HEIGHT_MM + (GUARD_EXTENSION_MODULES * X_MM if is_guard else 0)
        kind = "guard" if is_guard else "data"
        lines.append(
            f'    <rect class="{kind}" data-module="{run_start}" '
            f'x="{_mm(x)}" y="{_mm(BAR_TOP_MM)}" width="{_mm(run_width * X_MM)}" '
            f'height="{_mm(height)}"/>'
        )

    lines.extend(
        [
            "  </g>",
            (
                '  <g id="human-readable" fill="#000" '
                'font-family="OCR-B, OCRB, Arial, Helvetica, sans-serif" '
                'font-size="2.75" text-anchor="middle">'
            ),
            f'    <text x="{_mm(SYMBOL_START_MM - 4 * X_MM)}" y="{_mm(HRI_BASELINE_MM)}">{isbn[0]}</text>',
        ]
    )

    # Her rakamı kendi 7 modüllük karakter alanına ortalamak, fonttan bağımsız
    # olarak GS1 EAN-13 insan-okunur dizgisinin hizasını korur.
    for index, digit in enumerate(isbn[1:7]):
        x = SYMBOL_START_MM + (6.5 + 7 * index) * X_MM
        lines.append(f'    <text x="{_mm(x)}" y="{_mm(HRI_BASELINE_MM)}">{digit}</text>')
    for index, digit in enumerate(isbn[7:]):
        x = SYMBOL_START_MM + (53.5 + 7 * index) * X_MM
        lines.append(f'    <text x="{_mm(x)}" y="{_mm(HRI_BASELINE_MM)}">{digit}</text>')

    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def write_svg(isbn: str, display_text: str, output: Path) -> Path:
    """SVG'yi UTF-8 olarak diske yazar ve gerçek dosya yolunu döndürür."""
    output = output.with_suffix(".svg")
    output.write_text(build_svg(isbn, display_text), encoding="utf-8")
    return output


def verify_svg(path: Path, expected_isbn: str) -> list[str]:
    """Üretilen dosyanın XML, ölçü, metin ve EAN desenini tekrar denetler."""
    expected_isbn = validate_isbn13(expected_isbn)
    root = ElementTree.parse(path).getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    errors: list[str] = []

    if root.get("width") != f"{_mm(TOTAL_WIDTH_MM)}mm":
        errors.append("Toplam genişlik nominal 113X değil.")
    if root.get("viewBox") != f"0 0 {_mm(TOTAL_WIDTH_MM)} {_mm(TOTAL_HEIGHT_MM)}":
        errors.append("SVG viewBox fiziksel ölçülerle uyuşmuyor.")

    bars = root.findall(".//svg:g[@id='bars']/svg:rect", ns)
    reconstructed = ["0"] * SYMBOL_MODULES
    for bar in bars:
        start = int(bar.attrib["data-module"])
        modules = round(float(bar.attrib["width"]) / X_MM)
        for module in range(start, start + modules):
            if not 0 <= module < SYMBOL_MODULES or reconstructed[module] == "1":
                errors.append("Çubuk modülleri taşıyor veya üst üste biniyor.")
                continue
            reconstructed[module] = "1"
        expected_height = BAR_HEIGHT_MM + (
            GUARD_EXTENSION_MODULES * X_MM if bar.get("class") == "guard" else 0
        )
        if abs(float(bar.attrib["height"]) - expected_height) > 0.001:
            errors.append("Bir çubuğun yüksekliği standarda uymuyor.")

    if "".join(reconstructed) != encode_ean13(expected_isbn):
        errors.append("SVG çubuk deseni beklenen ISBN'i kodlamıyor.")

    hri = root.findall(".//svg:g[@id='human-readable']/svg:text", ns)
    if "".join(text.text or "" for text in hri) != expected_isbn:
        errors.append("Alt insan-okunur rakamlar ISBN ile uyuşmuyor.")
    if len(root.findall(".//svg:rect[@class='guard']", ns)) != 6:
        errors.append("Altı koruma çubuğunun tamamı bulunamadı.")

    return errors


def main() -> None:
    """Komut satırı seçeneklerini okuyup SVG'yi üretir ve doğrular."""
    parser = argparse.ArgumentParser(
        description="Yayına hazır ISBN-13 / EAN-13 SVG üretir."
    )
    parser.add_argument("--isbn", default="9786253798338", help="Geçerli ISBN-13")
    parser.add_argument(
        "--display",
        default="ISBN 978-625-379-833-8",
        help="Barkodun üstünde gösterilecek, atanmış tirelemeyi koruyan ISBN",
    )
    parser.add_argument("--output", type=Path, default=Path("isbn_barkod_tam_format.svg"))
    args = parser.parse_args()

    isbn = validate_isbn13(args.isbn)
    output = write_svg(isbn, args.display, args.output)
    errors = verify_svg(output, isbn)
    if errors:
        raise RuntimeError("SVG doğrulaması başarısız:\n- " + "\n- ".join(errors))
    print(f"SVG oluşturuldu ve doğrulandı: {output}")


if __name__ == "__main__":
    main()
