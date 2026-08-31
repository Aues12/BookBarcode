# BookBarcode Türkçe kullanım kılavuzu

BookBarcode, geçerli bir ISBN-13 numarasından EAN-13 barkodu üretir. Aynı
çekirdek üç farklı kullanım biçimini destekler:

* normal Python paketi;
* insanlar için `bookbarcode` komut satırı;
* agent-tools için JSON stdin/stdout adaptörü.

Üretilen dosya biçimleri:

* **PDF:** Baskıya gönderilmesi önerilen çıktıdır. Barkod ve yazılar gerçek
  process black, yani `C:0 M:0 Y:0 K:100` ile çizilir.
* **SVG:** Vektörel düzenleme ve önizleme içindir. CMYK niyeti işaretlenir;
  SVG uygulamalarının renk yönetimi farklı olabildiği için son baskıda PDF
  tercih edilmelidir.

KDY ölçü ve renk özetinin dayanağı için
[KDY referans notlarına](KDY-REFERANS-NOTLARI.md) bakın. İngilizce sürüm için
[English user guide](USAGE.md) belgesine bakın.

## Gereksinimler

* Python 3.9 veya daha yeni bir sürüm
* Çalışma zamanında harici Python paketi gerekmez

Python sürümünü kontrol edin:

```bash
python3 --version
```

## Kurulum

BookBarcode repo köküne geçin:

```bash
cd /path/to/BookBarcode
```

Geliştirme kurulumu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

Windows PowerShell üzerinde sanal ortamı etkinleştirme komutu:

```powershell
.venv\Scripts\Activate.ps1
```

Kurulumdan sonra:

```bash
bookbarcode --help
```

Kurulum yapmadan, BookBarcode repo kökünden de çalıştırılabilir:

```bash
python3 -m bookbarcode.cli --help
```

## En basit CLI kullanımı

ISBN komuta pozisyonel argüman olarak verilir:

```bash
bookbarcode 9786253798338
```

Varsayılan olarak çalışma klasöründe şu dosyalar oluşturulur:

```text
book-barcode.svg
book-barcode.pdf
```

Program ISBN kontrol rakamını ve üretilen dosyaları doğrular. Mevcut bir hedef
dosya, açıkça `--overwrite` verilmedikçe değiştirilmez.

## ISBN başlığının tirelenmesi

`--display` verilmezse başlık okunabilir bir `3-3-3-3-1` gruplamasıyla
gösterilir:

```text
ISBN 978-625-379-833-8
```

Bu gruplama resmî ISBN registrant aralıklarını çıkarmaz. Kuruma atanmış doğru
tireleme farklıysa açıkça verin:

```bash
bookbarcode 9786059681131 \
  --display "ISBN 978-605-9681-13-1"
```

Başlıktaki rakamlar kodlanan ISBN ile aynı olmak zorundadır. Yalnız tirelerin
konumu değişebilir.

## KDY ölçü önayarları

| Önayar | Barkod genişliği | Barkod yüksekliği |
|---|---:|---:|
| `normal` | 35 mm | 19 mm |
| `minimum` | 26 mm | 14 mm |

Normal ölçü varsayılandır:

```bash
bookbarcode 9786253798338 --preset normal
```

Minimum ölçü:

```bash
bookbarcode 9786253798338 --preset minimum
```

Minimum ölçünün altına inmek baskı ve okutma güvenilirliği açısından
önerilmez.

## Özel ölçüler ve çubuk yüksekliği

Toplam ölçüler milimetre cinsinden değiştirilebilir:

```bash
bookbarcode 9786253798338 \
  --width-mm 38 \
  --height-mm 20
```

Veri çubuklarının yüksekliği ayrıca belirlenebilir:

```bash
bookbarcode 9786253798338 \
  --height-mm 20 \
  --bar-height-mm 12.5
```

Koruma çubukları veri çubuklarından `5X` daha uzun üretilir. Çubuklar insan
tarafından okunabilir rakamların alanına taşıyorsa layout reddedilir.

## Beyaz sessiz alanlar

İki yan marjini birlikte ayarlamak için:

```bash
bookbarcode 9786253798338 --side-margin-mm 3
```

Sol ve sağ marjin ayrı verilebilir:

```bash
bookbarcode 9786253798338 \
  --left-margin-mm 3.5 \
  --right-margin-mm 2.5
```

`--left-margin-mm` ve `--right-margin-mm`, kendi taraflarında
`--side-margin-mm` değerini geçersiz kılar. Özel marjin verilmezse EAN-13 için
sol `11X` ve sağ `7X` sessiz alan otomatik hesaplanır.

## Çıktı biçimi, yolu ve üzerine yazma

Varsayılan `--format both` hem SVG hem PDF üretir. Yalnız PDF:

```bash
bookbarcode 9786253798338 --format pdf
```

Yalnız SVG:

```bash
bookbarcode 9786253798338 --format svg
```

Çıktı kökü `--output` veya `-o` ile belirlenir:

```bash
bookbarcode 9786253798338 \
  --output output/kitap-adi/barkod
```

Hedef klasör önceden var olmalıdır. `--format both` seçeneğinde örnek şu iki
dosyayı üretir:

```text
output/kitap-adi/barkod.svg
output/kitap-adi/barkod.pdf
```

Mevcut dosyaları doğrulanmış yeni çıktıyla değiştirmek için:

```bash
bookbarcode 9786253798338 --output output/barkod --overwrite
```

Yeni içerik önce geçici bir komşu dosyaya yazılır ve doğrulanır; hedef ancak
başarılı doğrulamadan sonra atomik olarak değiştirilir.

## CLI seçenekleri

| Seçenek | Açıklama |
|---|---|
| `isbn` | Barkoda kodlanacak ISBN-13 |
| `--display` | Üstte gösterilecek özel ISBN başlığı |
| `-o`, `--output` | Çıktı yolu kökü |
| `--format` | `svg`, `pdf` veya `both` |
| `--preset` | `normal` veya `minimum` |
| `--width-mm` | Marjinler dahil toplam genişlik |
| `--height-mm` | Toplam yükseklik |
| `--bar-height-mm` | Veri çubuklarının yüksekliği |
| `--side-margin-mm` | İki yan için ortak marjin |
| `--left-margin-mm` | Sol marjin |
| `--right-margin-mm` | Sağ marjin |
| `--overwrite` | Mevcut doğrulanmış hedefi değiştirmeye izin verir |
| `-h`, `--help` | Yardım metnini gösterir |

## Python API

Dosya yazmadan içerik üretmek için:

```python
from bookbarcode import Barcode

barcode = Barcode("9786253798338")
svg_text = barcode.to_svg()
pdf_bytes = barcode.to_pdf()
```

Özel layout ve doğrulanmış dosya yazımı:

```python
from bookbarcode import Barcode, BarcodeLayout

layout = BarcodeLayout.from_preset(
    "normal",
    side_margin_mm=3,
    bar_height_mm=12.5,
)
barcode = Barcode(
    "9786253798338",
    display_text="ISBN 978-625-379-833-8",
    layout=layout,
)
barcode.write_svg("book-barcode.svg")
barcode.write_pdf("book-barcode.pdf")
```

## Agent-tools JSON arayüzü

BookBarcode repo kökünden SVG ve PDF üretmek için:

```bash
printf '%s' '{
  "operation": "write_barcode",
  "params": {
    "isbn": "9786253798338",
    "output_base": "/tmp/book-barcode",
    "layout": {"preset": "normal"}
  }
}' | python3 isbn_barcode.py
```

Desteklenen operasyonlar:

* `generate_svg`
* `write_svg`
* `write_pdf`
* `write_barcode`
* `verify_svg`
* `verify_pdf`

İstek ve yanıt sözleşmesinin ayrıntıları için üst seviye [SKILL.yaml](../SKILL.yaml)
kullanılmalıdır.

## Uçtan uca örnekler

Normal ölçüde baskılık PDF:

```bash
bookbarcode 9786253798338 \
  --format pdf \
  --output output/normal-barkod
```

Minimum ölçüde SVG ve PDF:

```bash
bookbarcode 9786253798338 \
  --preset minimum \
  --format both \
  --output output/minimum-barkod
```

Özel ölçü, ayrı marjin ve atanmış tireleme:

```bash
bookbarcode 9786059681131 \
  --display "ISBN 978-605-9681-13-1" \
  --width-mm 39 \
  --height-mm 20 \
  --bar-height-mm 12 \
  --left-margin-mm 3.5 \
  --right-margin-mm 2.5 \
  --format pdf \
  --output output/ozel-barkod
```

## Baskı ve CMYK notları

* Matbaaya PDF dosyasını gönderin.
* Siyah öğeler yalnız `K:100` process black kullanır.
* `C:100 M:100 Y:100 K:100` rich black kullanılmaz.
* Barkodu orantısız ölçeklemeyin.
* Vektörel PDF'yi rasterleştirmeyin veya ekran görüntüsüne dönüştürmeyin.
* Beyaz sessiz alanları başka grafiklerle kapatmayın.
* Üretim öncesinde gerçek barkod okuyucu ve matbaa preflight kontrolü yapın.

## Sık görülen hatalar

### Geçersiz kontrol rakamı

ISBN'nin son rakamı ilk 12 rakamdan hesaplanır. Araç hatalı ISBN'yi sessizce
düzeltmez; numarayı yayıncı veya ISBN kaydıyla karşılaştırın.

### Başlık ve ISBN uyuşmuyor

`display_text` içindeki rakamlar kodlanan ISBN ile aynı olmalıdır.

### Marjinler genişliği kaplıyor

Sol ve sağ marjinlerin toplamı barkodun toplam genişliğinden küçük olmalıdır.

### Çubuk yüksekliği sığmıyor

Toplam yüksekliği artırın veya veri çubuğu yüksekliğini azaltın.

### Çıktı klasörü bulunamadı

BookBarcode hedef klasörü kendiliğinden oluşturmaz. Önce klasörü oluşturun ve
komutu tekrar çalıştırın.

## Testler

BookBarcode repo kökünden:

```bash
python3 -m unittest discover -s tests -v
```

Testler ISBN/EAN vektörlerini, fiziksel layout'u, SVG/PDF render işlemlerini,
CMYK komutlarını, bozulmuş çıktı tespitini, CLI'yi ve agent JSON sözleşmesini
denetler.
