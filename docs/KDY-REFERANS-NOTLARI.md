# KDY barkod ölçü ve renk referans notları

Bu belge, BookBarcode kaynak çalışma klasöründeki `KDY Barkod Klavuzu.PDF`
dosyasının tek sayfalık görsel içeriğinden çıkarılmış, metin tabanlı bir çalışma
notudur. PDF 1 Aralık 2020 tarihinde Adobe InDesign ile oluşturulmuş A4 bir
belgedir.

Bu not resmî KDY belgesinin yerine geçmez. Üretime girmeden önce güncel yayınevi
şartlarını ve matbaa gereksinimlerini ayrıca doğrulayın.

## Minimum ölçü

Minimum barkod ölçüsü:

```text
26 x 14 mm
```

| Kullanım | Barkod | Dış kutu |
|---|---:|---:|
| Açık zemin, çerçevesiz | 26 x 14 mm | Yok |
| Açık zemin, çerçeveli | 26 x 14 mm | 30 x 18 mm |
| Zeminli tasarım, beyaz kutu içinde | 26 x 14 mm | 30 x 18 mm |

Zeminli tasarımda barkod beyaz bir kutu içinde ve her kenardan 2 mm içeride
yerleştirilir.

## Normal ölçü

Normal barkod ölçüsü:

```text
35 x 19 mm
```

| Kullanım | Barkod | Dış kutu |
|---|---:|---:|
| Açık zemin, çerçevesiz | 35 x 19 mm | Yok |
| Açık zemin, çerçeveli | 35 x 19 mm | 39 x 23 mm |
| Zeminli tasarım, beyaz kutu içinde | 35 x 19 mm | 39 x 23 mm |

Dış kutu ölçüsü, barkodun dört yönünde 2 mm koruma alanı bırakır.

## Renk

Kılavuzda kabul edilen siyah:

```text
C:0 M:0 Y:0 K:100
```

Kabul edilmeyen rich black örneği:

```text
C:100 M:100 Y:100 K:100
```

BookBarcode PDF renderer'ı barkod ve metinler için doğrudan `0 0 0 1 k`
process-black komutunu kullanır.

## Paketleme ve yeniden dağıtım kararı

Kaynak PDF'nin yeniden dağıtım lisansı belirtilmediği için binary dosya Python
paketine veya agent-tools reposuna kopyalanmamıştır. Bu Markdown notu yalnızca
uygulamanın dayandığı ölçü ve renk kararlarını denetlenebilir biçimde kaydeder.
PDF'nin sahibi veya yayımlayıcısı tarafından yeniden dağıtım izni doğrulanırsa
orijinal belge ayrı bir `docs/references/` varlığı olarak eklenebilir; paket
manifestine dahil edilip edilmeyeceği ayrıca değerlendirilmelidir.
