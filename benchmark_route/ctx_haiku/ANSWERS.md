# Tokenwise Kod Tabanı Analizi — Cevaplar

1. **Flag dosyasına yazılan değer:** `"off"` yazılır (silinmek yerine). 
   **Dosya:** `C:/Users/Enes/Desktop/skills/tokenwise/hooks/tokenwise-mode-tracker.js` (satır 26, `clearMode()` fonksiyonu) ve aynı mekanizma `tokenwise-activate.js`'de de kullanılır (satır 75).
   **Neden:** Satır 21-24 (tokenwise-mode-tracker.js) açıkça belirtiyor — silmek yerine "off" yazmak, dosya yokluğunun "default'a düş" anlamına gelmesini önler; böylece "/tokenwise off" kalıcı kalır.

2. **RULES.md karakter sınırı:** 6000 karakter, **dosya:** `C:/Users/Enes/Desktop/skills/tokenwise/hooks/tokenwise-activate.js`
   **Yer:** Satır 39 (`const RULES_MAX_CHARS = 6000;`) ve satır 46'da uygulanır (length kontrolü). İçindeki yorum: plugin'in amacı daha az token harcamak, bu yüzden "unbounded project file injected every single turn" istenmeyen durum.

3. **readMode() içinde çakışma durumu:** Flag dosyası kazanır.
   **Dosya:** `C:/Users/Enes/Desktop/skills/tokenwise/hooks/tokenwise-activate.js`, satır 27-35 (`readMode()` fonksiyonu).
   **Mantık:** Satır 22-26 açıklaması — "persisted flag (user's most recent explicit choice) beats the env var". Fonksiyonda try-catch ile flag önce okunur (satır 29), başarılı olursa döndürülür; sadece flag yoksa env var kontrol edilir (satır 32).

4. **Flag dosyası "proje bazlı" yapılışı:** 
   **Modül:** `C:/Users/Enes/Desktop/skills/tokenwise/hooks/tokenwise-flag.js`
   **Mekanizma:** SHA1 hash algoritması + cwd (current working directory) = 10 haneli hex key.
   **Kod:** Satır 20 — `crypto.createHash('sha1').update(process.cwd()).digest('hex').slice(0, 10)`
   **Path pattern:** `.tokenwise-active-{10-char-key}` (satır 21). Her proje kendi cwd'sine göre unique bir flag dosyası alır; bu sayede farklı projelerde açık oturumlarda mod seçimleri çakışmaz.

5. **Plugin kayıt olduğu hook olayları:** `SessionStart` ve `UserPromptSubmit`
   **Dosya:** `C:/Users/Enes/Desktop/skills/tokenwise/hooks/tokenwise-hooks.json`
   **Detay:** 
   - **SessionStart** (satır 3-15): `tokenwise-activate.js` çalıştırır, matcher: "startup|resume|clear|compact"
   - **UserPromptSubmit** (satır 17-28): `tokenwise-mode-tracker.js` çalıştırır, kullanıcı "/tokenwise ..." veya "stop tokenwise" yazarsa mod değiştirir

6. **full modda eklenen ama lite modda olmayan paragraf:**
   "Tool discipline: batch independent tool calls in one turn (parallel). Prefer the dedicated tool over a shell equivalent. Keep context stable to stay within the prompt cache window."
   
   **Dosya:** `C:/Users/Enes/Desktop/skills/tokenwise/hooks/tokenwise-ruleset.js`, satır 17-20 (if mode === 'full' bloğu).
   **Açıklama:** `lite` modu sadece temel 4 lever'ı ve "NEVER cut" kurallarını alır; `full` modu bunlara ek olarak tool discipline (paralel batch, dedicated tool tercihı, context stabilitesi) ekler.
