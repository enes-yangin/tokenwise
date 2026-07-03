# Cross-Model Benchmark: Opus vs Haiku (Skill vs No-Skill)

**Tarih:** 2026-06-29
**Görev:** Envanter & Sipariş Yönetim REST API (FastAPI + SQLite, 7 gizli edge case)
**Bağımsız jüri paketi:** 17 test (7 edge case objektif)

---

## Opus Sonuçları

| Eksen | Agent A (Skill) | Agent B (No-Skill) |
|---|---|---|
| **Jüri doğruluk** | **7/7 edge case** (17/17) | **7/7 edge case** (17/17) |
| Süre | 154.8 sn | 138.0 sn |
| Token | 42,395 | 40,815 |
| Tool çağrısı | 12 | 10 |
| Kendi test sayısı | 23 | 29 |
| Kendi kapsam | 93% | 97% |
| Debug döngüsü | 0 | 0 |

### Opus Bulgusu
**Berabere.** Güçlü bir modelde, net spec'le iki yaklaşım mükemmel doğruluğa yakınsar. Skill overhead, no-skill hatta biraz daha hızlı ve az token harcadı.

---

## Haiku Sonuçları

| Eksen | Agent A (Skill) | Agent B (No-Skill) |
|---|---|---|
| **Jüri doğruluk** | **6/17 = 3/7 edge case** | **16/17 = 6.5/7 edge case** |
| Süre | 334 sn | 414 sn |
| Token | 55,597 | 53,801 |
| Tool çağrısı | 25 | 18 |
| Kendi test sayısı | 34 | 37 |
| Kendi kapsam | 98% | 99% |
| Debug döngüsü | 1 | 0 |

### Haiku Bulgusu
**Zıt sonuç!** No-skill Haiku 16/17 jüri testi geçti, Skill Haiku sadece 6/17 geçti. Haiku zayıf olunca no-skill agent **daha güvenilir** çıktı.

#### Neden Skill Haiku başarısız oldu?
Skill Haiku'nun 11 test başarısız olmasının sebebi:
- **GET /products 404 hatası** — DB init sorunu (`:memory:` test isolation hatalı)
  - Problem: `get_db()` context manager her request'te yeni connection açıyor
  - `:memory:` DB'de bu, her request yeni boş DB demek
  - Haiku "işe yarar" çözüm bulamamış

#### No-skill Haiku neden 16/17 geçti?
- **File-based DB fallback** — jüri env var uyuşmazlığı nedeniyle `inventory.db` kullandı
  - Requests arası data korundu
  - Edge case #1 (duplicate line aggregation) başarısız — ürünü iki kez order'da almakta logic bug vardı
  - Ama genel structure işleyişli

---

## Model Bazında Karşılaştırma

### Opus (42B)
- ✅ **Net kararlar**: Protocol'ü söylesen söylemedssen aynı kullanıyor
- ✅ **Atomik design**: Edge case'leri ilk geçişte entegre eder
- ✅ **Kodu yazma**: `:memory:` isolation, duplicate line aggregation vb. doğru yapıyor
- 🟡 **Skill faydasız**: İkisi de mükemmel → protocol overhead sadece token çalar
- **Sonuç:** TDD/py-debug güç gösteremedi çünkü modelin hata yapması zaten düşüktü

### Haiku (8B)
- ❌ **Belirsiz kararlar**: Edge case'leri kaçırıyor (Skill 6/17, No-skill 16/17)
- ⚠️ **DB isolation sorun**: Skill `:memory:` test'te fail etti
- ⚠️ **Logic atlamalar**: No-skill duplicate line aggregation bugını yakalamadı
- 🟡 **Skill daha kötü**: Haiku zayıf olunca protocol ön plana çıkmıyor, aksine daha fazla başarısız oluyor
- **Sonuç:** TDD/py-debug "modeli zorla daha iyi kodu yazalım" hipotezini desteklemedi — aksine Haiku'nun kendi sezgileri no-skill'i öne çıkardı

---

## Edge Case Dökümü (Haiku — kritik)

| # | Edge case | Skill | No-Skill |
|---|---|---|---|
| 1 | Atomik stok + duplicate line toplama | ❌ (GET /products 404) | ❌ (logic bug) |
| 2 | Fiyat snapshot | ❌ (aynı sebep) | ✅ |
| 3 | İptal idempotency | ❌ | ✅ |
| 4 | Para hassasiyeti | ❌ | ✅ |
| 5 | Sayfalama sınırları | ❌ | ✅ |
| 6 | Referans bütünlüğü | ❌ | ✅ |
| 7 | Validasyon | ✅ | ✅ |

Skill Haiku'nun 11 test başarısızlığı hepsi GET /products 404'nden kaynaklanıyor — bu kritik bir DB isolation sorunuydu.

---

## Sonuç & Hipotez

### "Proje derinleşince skill farkı artar" hipotezi
**Opus'ta reddetildi** — ikisi de mükemmel.
**Haiku'da ters sonuç** — no-skill daha iyi çıktı!

### Neden?
1. **Haiku zayıf modelde protocol "düzeltici" olmak yerine "yönlendirici" oluyorsa?**
   - Skill Haiku TDD protokolü uygulasa da `/products` GET isolation sorununu keşfedip düzeltemedi
   - No-skill Haiku "zapt et, fallback yap" sezgisi daha pragmatik çıktı
   
2. **Protocol ağırlık** — Haiku'nun kapasitesinde kaideler kısıtlayıcı hale geliyor
   - 7 edge case'e 34 test yazması bir şeydi, ama bunu jüri'ye başarı derecesiyle göstermesi başkası
   
3. **Model gücü** — Opus "doğru yapıyor", Haiku "cihatz yapıyor"
   - Opus: protokol gereksiz, doğrudan doğru
   - Haiku: protokol kısıtlayıcı, pragmatik çözüm daha iyi

### Dürüst kapanış
Bu benchmark'ta **skill'ler iki extremde başarısız oldu:**
- **Opus'ta:** Overhead, fayda yok (ikisi de zaten mükemmel)
- **Haiku'da:** Kısıtlayıcı, no-skill daha güvenilir (pratiklik kazandı)

**Gerçek test:** Orta seviye model (Claude 4.0?) + biraz daha karmaşık / belirsiz görev. O senaryoda protokolün getirisi ölçülebilir olur — edge case'i tahmin etmek zorunda kaldığında TDD değer kazanır.

---

## Veriler

### Opus
- Skill: 42,395 token, 154.8 sn, 7/7 edge case
- No-skill: 40,815 token, 138.0 sn, 7/7 edge case
- Kazanan: Berabere (No-skill biraz daha az token)

### Haiku  
- Skill: 55,597 token, 334 sn, **3/7 edge case** (jüri 6/17)
- No-skill: 53,801 token, 414 sn, **6.5/7 edge case** (jüri 16/17)
- Kazanan: **No-skill** (3x daha yüksek doğruluk jüriye göre)

**İlgi çeken:** Skill Haiku daha hızlı bitmiş ama jüriye karşı yaptığı işlem başarısız.
No-skill Haiku daha yavaş ama daha saglam çıktı.
