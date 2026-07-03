# Tokenwise Projesi - QA ve Eksiklik Raporu

Proje klasöründeki tüm dosyaları (`hooks`, `skills`, `.claude-plugin`, `README.md` vb.) detaylı bir şekilde inceledim. Kod mimarisi ve mantık genel olarak çok başarılı olsa da, aşağıdaki **eksik noktaları ve potansiyel hataları** (bug) tespit ettim:

### 1. `plan-critique` Yeteneği Unutulmuş (Dokümantasyon Eksikliği)
Proje klasörleri arasında `skills/plan-critique` yeteneği mevcut ve içi dolu (`SKILL.md` yazılmış). Ancak bu yetenek dışarıdan tamamen görünmez durumda:
* **`README.md`**: "What's inside" tablosunda ve klasör ağacında (Layout) `plan-critique` yer almıyor.
* **`plugin.json`**: Description kısmında "root-cause debug, TDD, and atomic-commit" yeteneklerinden bahsediliyor ama "plan critique" yok.
* **Çözüm**: Bu yetenek `README.md` ve `plugin.json` dosyalarına eklenmeli.

### 2. `tokenwise-activate.js` Çıktı Kesilme Riski (Race Condition)
`hooks/tokenwise-activate.js` dosyasının en sonunda şu yapı kullanılıyor:
```javascript
emit(ctx);
process.exit(0);
```
`emit` fonksiyonu `process.stdout.write()` kullanır. Node.js'de `stdout.write`, özellikle pipe/yönlendirme yapıldığında Windows'ta ve bazı CI/CD ortamlarında **asenkron** davranabilir. Çıktı tampondan (buffer) işletim sistemine yazılmadan hemen `process.exit(0)` çağrıldığı için JSON çıktısı yarıda kesilebilir ve hook çöker.
* **Çözüm**: Senkron kod akışının sonunda Node.js zaten kapanacağı için `process.exit(0)` satırını silebilirsiniz veya stdout buffer'ının boşaldığından emin olmak için işlemi bir callback'e/event'e bağlayabilirsiniz.

### 3. Ajanı Çıkmaza Sokacak `git add -p` Önerisi
`skills/git-commit/SKILL.md` dosyasında ajana şu kural verilmiş:
> `git add -p` to stage individual hunks...

Ajanların (LLM asistanlarının) çalıştığı terminaller genellikle interaktif değildir (interactive session). Bir ajan `git add -p` komutunu çalıştırırsa terminal kullanıcıdan Yes/No (y/n) onayı bekleyecek ve ortam süresiz askıda kalacaktır (timeout yiyene kadar).
* **Çözüm**: "Use `git add -p`" ifadesi ajan kurallarından kesinlikle kaldırılmalı ve sadece "Tam dosya yollarını (explicit paths) kullanarak `git add` yap" kuralı tutulmalıdır.

### 4. `tokenwise-mode-tracker.js` İçindeki Regex Kısıtlaması
Kullanıcıdan gelen girdiyi (prompt) kontrol eden tracker dosyasında mod değiştirmek için şu regex kullanılmış:
```javascript
const m = prompt.match(/^[/@$]tokenwise(?:\s+(\w+))?/);
```
Buradaki `^` (satır başı) karakteri, kullanıcının "Lütfen /tokenwise lite moduna geç" gibi cümle içinde komut vermesini engeller. Komutun sadece mesajın en başında olması durumunda çalışır. Oysa aynı dosyadaki kapatma komutu (`/\b(stop tokenwise|normal mode)\b/`) mesajın herhangi bir yerinde çalışabilmektedir.
* **Çözüm**: Kullanıcı deneyimini (UX) iyileştirmek için `^` işareti kaldırılıp `/(?:^|\s)[/@$]tokenwise(?:\s+(\w+))?/` şeklinde daha esnek bir yapıya geçilebilir.

### 5. `RULES.md` Entegrasyonu (Kullanıcı Deneyimi)
`README.md` dosyasında kullanıcılara "Drop a `RULES.md` at your project root (see `RULES.template.md`)" deniyor. Ancak bunu otomatikleştiren bir komut yok. Kullanıcıların şablonu taşıması için `README.md`'nin **Install** veya **Use** adımına doğrudan çalıştırabilecekleri bir kopyalama komutu eklenebilir:
```bash
cp .claude/plugins/tokenwise/RULES.template.md ./RULES.md
```

### 6. Node.js Bağımlılığının Açıkça Vurgulanması
Windows komut setlerinde `if (Get-Command node ...)` gibi önlemler alınmış olsa da, eğer kullanıcının sisteminde `node` yoksa eklenti tamamen sessizce başarısız olacak (SilentlyContinue) ve Tokenwise modu asla devreye girmeyecektir. 
* **Çözüm**: `README.md` dosyasındaki "The hooks need node on PATH" uyarısı daha belirgin (örneğin kalın veya dikkat çekici bir blokla) hale getirilebilir.

### Özet:
Proje konsept olarak sağlam. Temelde sadece unutulan `plan-critique` yeteneğini README'ye eklemek, `process.exit(0)` kısmını güvenli hale getirmek ve `git add -p` gibi ajanı kilitleyecek komut tavsiyelerini temizlemek projenin tamamen sorunsuz (production-ready) hale gelmesi için yeterli olacaktır.
