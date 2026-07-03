# Derin Benchmark Sonuçları: Skill vs No-Skill

**Görev:** Envanter & Sipariş Yönetim REST API'si (FastAPI + SQLite, 7 gizli edge case)
**Model:** Her iki agent claude-opus-4-8
**Ölçüm tarihi:** 2026-06-29

## Koşullar
- **Agent A (Skill):** tokenwise + tdd + py-debug protokolleri prompt'ta tarif edildi.
- **Agent B (No-Skill):** protokolsüz, "yaz sonra test ekle".
- Bağımlılıklar önceden ortak venv'e kuruldu (kurulum süresi sayılmadı).
- Aynı pinlenmiş API kontratı (`SPEC.md`) ikisine de verildi.
- **Bağımsız jüri paketi** (`judge/test_contract.py`, 17 test) agent'lar görmeden ikisine de uygulandı.

## Sonuç Tablosu

| Eksen | Agent A (Skill) | Agent B (No-Skill) | Kazanan |
|---|---|---|---|
| **Jüri doğruluk skoru** | **7/7 edge case** (17/17 test) | **7/7 edge case** (17/17 test) | Berabere |
| Süre (duration_ms) | 154.8 sn | **138.0 sn** | No-Skill |
| Token (subagent) | 42,395 | **40,815** | No-Skill |
| Tool çağrısı | 12 | **10** | No-Skill |
| Kendi test sayısı | 23 | **29** | No-Skill |
| Kendi test kapsamı | 93% | **97%** | No-Skill |
| Uygulama satırı | 365 | 350 | ~eşit |
| Debug döngüsü | 0 | 0 | Berabere |

## Jüri Edge Case Dökümü (her ikisi de geçti)

| # | Edge case | Skill | No-Skill |
|---|---|---|---|
| 1 | Atomik stok düşümü (kısmi düşüm yok + duplicate satır toplama) | ✅ | ✅ |
| 2 | Fiyat snapshot'ı (geçmiş sipariş donar) | ✅ | ✅ |
| 3 | İptal idempotency (çift iptal stoğu iki kat yüklemez) | ✅ | ✅ |
| 4 | Para hassasiyeti (int cents, float yok) | ✅ | ✅ |
| 5 | Sayfalama sınırları (offset taşması boş liste) | ✅ | ✅ |
| 6 | Referans bütünlüğü (siparişteki ürün silinemez) | ✅ | ✅ |
| 7 | Validasyon (negatif fiyat/stok/quantity → 422) | ✅ | ✅ |

## Yorum

**Hipotez doğrulanmadı.** "Proje derinleşince skill agent gizli edge case'lerde
ayrışır" beklentisinin aksine, **güçlü bir modelde (Opus) ve net bir spec'le iki
yaklaşım da mükemmel doğruluğa yakınsadı.** No-skill agent hatta biraz daha hızlı,
daha az token harcadı ve daha yüksek kapsamlı (97% vs 93%) test yazdı.

### Neden?
1. **Opus zaten "içselleştirilmiş TDD" yapıyor.** Protokolü açıkça söylemek, modelin
   zaten yaptığı şeyi tekrar etti — marjinal fayda sıfır, hatta küçük overhead.
2. **Spec netti ve edge case'ler açıkça listelenmişti.** py-debug'ın parladığı yer
   belirsizlik ve hata ayıklamadır; burada ikisi de ilk denemede 0 hata aldı.
3. **Tek seferlik üretim.** Skill'in asıl getirisi (refactor döngüsü, bakım, hata
   avı) zamana yayılır; tek atışlık benchmark'ta görünmez.

### Skill'in gerçekten kazanacağı koşullar
- **Daha zayıf model** (Haiku/Sonnet) — protokol, modelin atlayacağı adımları zorlar.
- **Belirsiz/eksik spec** — edge case'leri kendin keşfetmen gerektiğinde tdd üretken.
- **Gerçek bug avı** — bir test patladığında py-debug tahmin-döngüsünü engeller.
- **Uzun bakım** — tokenwise asıl tasarrufu çok oturumlu çalışmada yapar.

### Dürüst kapanış
Bu görev/model kombinasyonunda **skill'ler ölçülebilir kalite kazancı sağlamadı**
ve hafifçe daha pahalıydı. Skill setinin değeri burada "yanlış yapmama sigortası"
— Opus'ta zaten düşük olan hata riskini daha da düşürür, ama ücretsiz değil.
Asıl test, daha zayıf bir modelde veya belirsiz bir görevde tekrar koşmak olur.
