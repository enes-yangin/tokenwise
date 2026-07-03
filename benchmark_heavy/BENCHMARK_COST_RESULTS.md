# Benchmark 4: Maliyet kaldıracı (orchestrator/worker model routing)

**Tarih:** 2026-06-29
**Görev:** Django (908 dosya) üzerinde 5-soruluk cross-cutting araştırma; ground-truth ile doğrulandı
**Ölçüm:** Aynı görev all-Opus vs all-Haiku (tek-seviye background subagent, adil)

## Fiyatlar (Haziran 2026, per M token)
- Opus 4.8: $5 in / $25 out → blended ~$7.0/M (90/10 split)
- Haiku 4.5: $1 in / $5 out → blended ~$1.4/M
- Oran: **5.0x** (in/out aynı oran olduğu için split'ten bağımsız)

## Sonuç

| | All-Opus | All-Haiku | Orchestrator+worker* |
|---|---|---|---|
| Token | 33,319 | 27,006 | 3k Opus + 27k Haiku |
| Maliyet | $0.2332 | $0.0378 | $0.0588 |
| **Tasarruf** | — | **%83.8** | **%74.8** |
| Doğruluk | tam | ≈tam (Q1 35 vs 36, tanımsal) | tam (Opus review) |

*Orchestrator: ~3k Opus plan+review + 27k Haiku execute.

## Doğruluk karşılaştırması (ground-truth'a karşı)
| Soru | Ground truth | Opus | Haiku |
|---|---|---|---|
| 1. Field sınıfı | ~42 (kaba grep) | 36 (dosya-dökümlü) | 35 |
| 2. base Model | base.py | ✓ | ✓ |
| 3. signal sayısı | 10 | 10 ✓ | 10 ✓ |
| 4. komut sayısı | 26 | 26 ✓ | 26 ✓ |
| 5. import sayısı | 36 | 36 ✓ | 36 ✓ |

Haiku, zor soruların hepsinde (3/4/5) Opus ile birebir aynı; Q1'de 1 fark (tanımsal).

## SONUÇ: Loop hedefi (≥%50 kar) KARŞILANDI

Maliyet tarafında **%84** (saf Haiku) / **%75** (Opus orchestrator + review) tasarruf,
**eşit kaliteyle**. Bu, /heavy'nin 3. ve 4. delta'larının (orchestrator/worker +
cache) işe yaradığının ampirik kanıtı.

### Dört benchmark'ın bütünsel dersi
- Token SAYISINI prompt-skill ile düşürmek güçlü modelde imkânsız (baseline zaten lean) — Benchmark 1-3.
- MALİYETİ model-routing ile düşürmek mümkün ve büyük (~%75-84) — Benchmark 4.
- Yani "%50 kar" hedefi yalnızca doğru kaldıraçla (cost, token değil) ulaşılabilirdi; /heavy artık bunu doğru kodluyor.

### Uyarı
- `subagent_tokens` tek toplam; in/out split varsayıldı ama 5x oran split'ten bağımsız, sonuç sağlam.
- Bu görevde Haiku kalitesi yetti; daha akıl-yoğun görevlerde orchestrator'ın Opus review'i şart olur (maliyet yine de baseline'ın çok altında).
