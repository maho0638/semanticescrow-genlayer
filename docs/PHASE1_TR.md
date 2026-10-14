# SemanticEscrow — 1. aşama teslim ve durum

**Tarih:** 15 Ekim 2026. **Yalnızca mimari ve tasarım aşaması.**

## Tamamlanan tasarım
- Bağımsız, yeniden kullanılabilir, native GEN teminatlı, 1–5 aşamalı iş/ödeme sözleşmesinin amacı ve sınırları.
- Alıcı, satıcı ve herkese açık süre sonu çağrılarının yetki tablosu; sonradan değişmez şartlar.
- Teslim kanıtı, birbirinden bağımsız validator incelemesi, 48 saatlik tek itiraz, 7 günlük değerlendirme sınırları.
- Ödeme/iade muhasebesi; tek seferlik ödeme niyeti, çift ödemeye karşı terminal durumlar, sonraki aşamalara geçiş.
- 27 maddelik güvenlik ve sınır testi matrisi; kaynaklar ve açık kalan üretim güvenliği koşulları.

## Kritik gerçek
`PAYOUT_QUEUED` para geçti demek değildir. Gerçek EVM transferinin başarısız olabilmesi, DNS/SSRF/source authenticity, validator semantik tutarlılığı **henüz çözülmüş/çalışan kodla test edilmiş değildir**. Bu nedenle gerçek para kabulü ve herkese açık kullanımı uygun ilan edilmez.

## Bilerek yapılmayanlar
- 2. aşama GenVM sözleşme kodu, deploy, Studio testi, cüzdan/GEN kullanımı, Portal başvurusu, PR merge yapılmadı.
- Çalışma ayrı tasarım dalında tutuldu; `main` yalnızca boş depo başlatmak için README içeriyor.

Sonraki adım (şimdi BAŞLATILMAYACAK): Bu nihai arayüz ve kurallara göre ayrı sözleşme kodlaması, SDK/linter uyumu ve gerçek testlerin üretilmesi.
