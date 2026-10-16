# SemanticEscrow — kalan eksik 2: ödeme niyeti → child/EVM transfer → alıcı bakiyesi

**Tarih:** 2026-10-16. **Dal:** `audit/phase2-payment-intent-proof-20261016`.
**Durum:** Kanıt eşleştirme ve olumsuz test yazılımı tamamlanabilir;
**mevcut v0.2.16 dağıtımı için tekil dış GEN transferinin kesin
`intent_id_sha256` bağı ise henüz zincir üzerinde kanıtlanmadı.**
Bu dosya bütün maddeyi başarıyla bitirilmiş gibi sunmaz.

## Resmî protokol bulgusu ve önemli ayrım

Kaynak: GenLayer belgelerinin güncel *Messages* ve *Value Transfers*
bölümleri, ayrıca GenLayerJS `src/types/transactions.ts`.
- `MessageType.External = 0`, `MessageType.Internal = 1`.
- **Internal (IC → IC)** mesajları zincir üstü child GenLayer tx kimlikleri
  oluşturabilir; `getTriggeredTransactionIds` bu kimlikleri döndürür.
- **External (IC → EOA / EVM)** ödemeler child GenLayer tx makbuzu
  yerine **Ghost `handleOp()` üzerinden EVM çağrısı** şeklinde yürür.
  `getTriggeredTransactionIds` boş olsa bile EOA ödendi/ödenmedi
  sonucunu bundan çıkarmak geçersizdir.
- Harici mesaj `onAcceptance=False`, yani ancak ebeveyn FINALIZED
  olduktan sonra yürütülür. EVM işlem makbuzu ile GenLayer consensus
  makbuzu ayrı kimlikler ve ayrı kesinleşme katmanlarıdır.
- Eski SemanticEscrow sözleşmesi
  `get_transfer_intent(s)` yoluyla
  `SHA256(terms_digest, deal_id, milestone, kind, recipient, amount)`
  taahhüdünü döndürüyor; dış `_Recipient.emit_transfer(value=...)`
  için özgün intent SHA'sını **EVM calldata içerisine koymuyor**.
  İki ayrı anlaşma aynı alıcıya aynı wei miktarını gönderebilir.
  Benzer miktar/recipient görülmesi kriptografik *intent → EVM call*
  kanıtı değildir.

Kaynaklar:
- https://docs.genlayer.com/developers/intelligent-contracts/features/messages
- https://docs.genlayer.com/developers/intelligent-contracts/features/value-transfers
- https://docs.genlayer.com/developers/decentralized-applications/querying-a-transaction
- https://github.com/genlayerlabs/genlayer-js/blob/main/src/types/transactions.ts

## Tamamlanan izolasyonlu teknik işler

1. `tools/phase2_intent_child_correlator.py` önce Phase-8
   `reconcile_queued_intents` ile imzalı kaynakta üretilen frozen
   SHA/ledger/tutar/alıcı/milestone kayıtlarını doğruluyor.
2. GenLayer **ebeveyn** işlem kimliğini, gerçek `FINALIZED`
   durumunu, `FINISHED_WITH_RETURN` sonucunu ve hedef Ghost
   adresini ayırıyor. Sadece kabul edilmiş veya başarısız
   consensus işlemine ödeme sonucu atamıyor.
3. Gerçek mesaj türü `External = 0` ve on-finalization
   koşulu doğrulanmadan herhangi bir EOA native GEN transfer
   eşleştirmesine izin vermiyor. Yanlış tutar/alıcı,
   başkasına ait parent, hatalı calldata ve birden fazla
   eşdeğer transfer niyeti **ambiguous** olarak reddediliyor.
4. GenLayer **internal child** kimliği varsa ayrı collection
   olarak işliyor ve her çocuğun FINALIZED + successful olması
   gerekiyor; bunu harici EOA transferiymiş gibi yorumlamıyor.
5. `tools/phase8_release_gate.py` tarafından doğrulanan
   EVM mined receipt, Ghost→beneficiary iç CALL, en az 12
   EVM block confirmation ve B-1/B historical recipient
   bakiyeleri eşleştirilebiliyor. Bu, **yapıldığı
   gözlenen fakat belli bir intent'e bağlanamayan transfer**
   kategorisi; `PAID` veya `CREDITED` denmiyor.
6. `tools/phase2_public_parent_probe.py` yalnızca
   `eth_chainId`, `gen_getTransactionReceipt`,
   `gen_getTriggeredTransactionIds` gibi salt-okunur
   yöntemlerle parent ve child listesi inceliyor.
   Eski Bradbury node HTTP 403 veya method unsupported dönerse
   `UNAVAILABLE_NOT_EMPTY` / `UNVERIFIED` olarak kaydediliyor.
   GEN gönderimi, imza, cüzdan veya işlem tekrarı yok.
7. Yeni saldırgan/tuhaf veri regresyon testleri: sahte
   child kimliği, doğrulanmamış parent, INTERNAL mesajı
   EXTERNAL diye yorumlama, 0x tek haneli wei,
   çoğalan aynı miktar, gizli/onaysız veri, yanılmış
   EVM status, yanlış blok, yeterli onay yok, yanlış alıcı
   ve farklı Ledger digest testleri.

## Kesin tamamlanması için gerçekten eksik kanıt

- **Çalışan gerçek Bradbury 7. aşama işleminin sonucuna erişim:**
  başarılı parent cancellation settlement GenLayer ID;
  final durum/GenVM execution; yeni transferin ilgili EVM
  finalized `handleOp()` tx hash/trace; alıcının finalized
  bloktaki önceki-sonraki GEN bakiyesi.
- **Kriptografik özgün intent → EVM transfer bağlantısı:** mevcut
  doğrudan EOA native transferinin `data = 0x` payload'ında
  intent SHA yok; farklı anlaşmalarda aynı alıcı ve tutar
  ayırt edilemiyor. Bunun yeni deploy gerektirmeyen zincir
  tarafından doğrulanabilir benzersiz olay/ordinal bağlama
  kanıtı bulunmalı **veya** ileride yeni sürümde intent
  bazında zincire yazılan event/nonce ile Ghost external
  transferi eşleştiren denetlenmiş sözleşme/protokol yolu
  gerekecek. Yanlışlıkla duplicate ödeme olmamalı.
- Ayrı end-to-end gerçek ağ kanıtı elde edilince ve
  bu bağ doğrulanınca madde 2'nin tamamı FINISHED ilan edilebilir.

## Güvenlik sınırı

Dallar `main`, `test/phase7-bradbury-runtime-compat-20261015`,
`fix/phase7-create-deal-root-cause-20261016` ve
`audit/child-delivery-recovery-guard-20261016` değiştirilmedi.
Mevcut Windows GEN testine dokunulmadı; yeni GEN, PR, merge, Portal
yeniden gönderimi, gerçek deploy yapılmadı.

Yeni kaynak kodu **yalnız salt-okunur/çevrimdışı** bir doğrulama
korumasıdır; üretime çıkış izni, sahte `paid` etiketi veya
geri alma/çift ödeme izni vermez.

## Son test kanıtı — 2026-10-16

[GitHub Actions 469/469 PASS](https://github.com/maho0638/semanticescrow-genlayer/actions/runs/38954336793).

- 1 eski web API + 153 Direct Mode + 12 v0.6 receipt +
  83 SDK/güvenlik + **220 bağımsız transfer/denetim regresyonu**.
- Bu son grup daha önce 158 idi; **62 ek test** yeni
  payment-intent, GenLayer child/EVM Ghost ayrımı, unsupported public
  RPC ve replay/false-credit kontrolleridir.
- Gerçek v0.2.16 kaynak SHA pin, Python derleme, GenVM lint
  ve `pip check` de başarılı. Bu testler yeni imzalı
  Bradbury ödemeleri değildir.
- İlk yeni test çalışmaları ayrıca hatalı `0xa` RPC
  tutar biçimi şartını yakaladı ve ondan sonra düzeltilerek
  bütün paket tekrar çalıştırıldı. Başarısız deneme
  `38953870080` kayıtta kalıyor.

**Sonuç:** Delilleri toplama/ayıklama ve yanlış
`PAYMENT_DELIVERED` beyanını engelleyen teknik iş
tamamlandı; **her canlı intent için onchain teslimin kesin
kanıtlanması HENÜZ tamamlanmadı**. Kimlik zinciri bu
v0.2.16 dağıtımında kanıtlanmış değildir.
