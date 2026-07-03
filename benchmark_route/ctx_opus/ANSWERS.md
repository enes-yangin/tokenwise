# Cevaplar

1) `off` değeri (string olarak) yazılır — flag dosyası silinmez. `clearMode()`, `setMode('off')` çağırarak dosyaya `"off"` yazar. Dosya: `hooks/tokenwise-mode-tracker.js` (satır 25-27). Sebep: silinen flag "henüz flag yok" gibi okunup env/`full` varsayılanına düşerek modu sessizce yeniden açardı.

2) Karakter sınırı **6000** (`RULES_MAX_CHARS = 6000`). Aşılırsa metin kesilir ve bir uyarı notu eklenir. Dosya: `hooks/tokenwise-activate.js` (satır 39, 46-48).

3) **Flag dosyası kazanır.** `readMode()` önce flag dosyasını okur; geçerli bir değer (`lite`/`full`/`off`) bulursa hemen döner ve `TOKENWISE_MODE` env değişkenine hiç bakmaz. Env yalnızca flag hiç yazılmamışken (fallback) devreye girer. Dosya: `hooks/tokenwise-activate.js` (satır 27-35).

4) `hooks/tokenwise-flag.js` modülündeki `flagPath()` mekanizması yapar. Anahtar, `process.cwd()` (proje kökü) değerinin SHA-1 hash'inin ilk 10 karakteri alınarak üretilir; dosya adı `.tokenwise-active-<key>` olur ve `claudeDir()` içine yazılır. Böylece her proje kendi flag dosyasına sahip olur. Dosya: `hooks/tokenwise-flag.js` (satır 19-22).

5) **SessionStart** ve **UserPromptSubmit**. Dosya: `hooks/tokenwise-hooks.json` (satır 3 ve 17).

6) `full` moddaki "Tool discipline" paragrafı: "Tool discipline: batch independent tool calls in one turn (parallel). Prefer the dedicated tool over a shell equivalent. Keep context stable to stay within the prompt cache window." `lite` modda bu paragraf eklenmez. Dosya: `hooks/tokenwise-ruleset.js` (satır 17-21).
