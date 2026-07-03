# Benchmark 3: /heavy skill'i — gerçek 8-dosyalık feature (Opus)

**Tarih:** 2026-06-29
**Görev:** Katmanlı FastAPI kodtabanına "orders" kaynağı ekle (8 dosya: 5 yeni katman + db.py/main.py kayıtları + product_service referans değişikliği)
**Model:** Her iki agent claude-opus-4-8
**Bağımsız jüri:** `judge_orders.py`, 12 test (7 edge case)

## Sonuç Tablosu

| Eksen | Heavy (skill) | No-Skill | Kazanan |
|---|---|---|---|
| **Jüri doğruluk** | **12/12** (7/7 edge) | **12/12** (7/7 edge) | 🤝 Berabere |
| Kendi test | 16 geçti | 14 geçti | ~eşit |
| Token (toplam) | **93,168** ⚠️ | **43,309** | **No-Skill** |
| Token (sadece resume) | 56,779 | 43,309 | No-Skill |
| Süre | ~206 sn | 111 sn | No-Skill |
| Tool çağrısı | 32 | 24 | No-Skill |
| Orders kod satırı | 229 | 213 | ~eşit |

## Headline: %50 azalma İDDİASI BU KOŞULDA ÇÜRÜTÜLDÜ

`/heavy` token'ı **azaltmadı, ~2.15x ARTIRDI** (93k vs 43k). En cömert okumayla
bile (ilk iptal koşuyu yok sayıp sadece resume'u sayarsak: 56.8k) hâlâ **+%31 daha
pahalı**. Doğruluk eşit. Yani bu görevde skill net zarar.

## Neden? İki sebep

### 1. Confound: background agent + nested subagent kırılganlığı
Heavy agent ilk turda bir Explore subagent başlatıp **onu beklerken turunu erken
bitirdi** (36.4k token, 5 tool, 28s — boşa gitti). Resume etmem gerekti; resume
context'i yeniden türetti. İlk koşunun 36k'sı büyük ölçüde harcama. Bu bir **harness
artefaktı** — arka planda çalışan agent'ın iç içe subagent beklemesi pürüzlü.

### 2. Asıl sebep: kodtabanı KÜÇÜK — lever 1'in ısıracağı bir şey yoktu
`/heavy`'nin token-tasarruf kaldıracı (subagent fan-out) sadece **gerçekten büyük
repo'larda** öder; orada okuma maliyeti baskındır. Bu benchmark'ta `app/` paketinin
tamamı ~16 minik dosya — hepsini doğrudan okumak ~3-4k token. Explore subagent'ın
overhead'i + round-trip'i, kazandırdığı okumadan fazla. **Break-even eşiği "1-2
dosyadan fazla" değil, çok daha yüksek.**

Skill'in description'ı "%30-50 azalma" iddiasını açıkça "exploration-heavy /
büyük repo" ile sınırlamıştı. Bu benchmark o çıtayı karşılamıyor — yani üst iddianın
adil testi değil, ama "orta ölçekli çok-dosyalı feature'da /heavy yardım eder mi?"
sorusunun adil testi, ve cevap: **hayır, zarar etti.**

## Verification-first lever'i ne oldu?
Çalıştı — heavy agent acceptance test'i önce yazdı, failing baseline gördü, **0 debug
döngüsü**. AMA no-skill Opus da ilk denemede her şeyi doğru yaptı (14/14 + 12/12 jüri).
Yani Opus'ta bu lever de fark yaratmadı — Benchmark 1 ile birebir tutarlı.

## Üç benchmark birlikte — tutarlı tablo

| Benchmark | Model | Skill faydası |
|---|---|---|
| 1: ExpenseTracker (sığ) | Opus | Yok — berabere, skill biraz pahalı |
| 2: REST API (derin) | Opus | Yok — 7/7 berabere, skill biraz pahalı |
| 2b: REST API (derin) | Haiku | **Ters** — no-skill 16/17 vs skill 6/17 |
| 3: /heavy feature (8 dosya) | Opus | **Ters** — eşit doğruluk, skill 2.15x token |

**Değişmeyen bulgu:** Opus + net spec'te skill'ler (ister prose-protokol ister
yapısal) doğruluğu artırmıyor — model zaten yeterince iyi. /heavy ayrıca küçük/orta
kodtabanında overhead yüzünden token'ı artırıyor.

## Dürüst sonuç & öneri

`/heavy` şu an yazıldığı haliyle **dar bir niş aracı**: sadece gerçekten büyük
repo'da (keşfin pahalı olduğu, on binlerce satır) değer üretebilir. Orta ölçekte
ters teper. İki seçenek:

1. **Trigger'ı daralt** — description'ı "yalnızca büyük/tanımadığın repo'da, geniş
   keşif gerektiğinde" diye sıkılaştır; orta işlerde tetiklenmesin.
2. **Subagent zorunluluğunu yumuşat** — "fan-out yalnızca repo büyükse; küçükse
   doğrudan surgical read" kuralı ekle ki overhead'i kendisi elesin.

Ayrıca background-agent + nested-subagent kırılganlığı gerçek: `/heavy` interaktif
ana oturumda (background değil) daha güvenilir çalışır.

## Ham veri
- Heavy: 36,389 (iptal) + 56,779 (resume) = 93,168 token; 32 tool; ~206s; 12/12 jüri
  - + sayılmayan Explore subagent token'ları (nested, üst toplama yansımıyor olabilir)
- No-skill: 43,309 token; 24 tool; 111s; 12/12 jüri
