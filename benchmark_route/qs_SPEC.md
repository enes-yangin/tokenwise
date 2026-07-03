# Görev: Query-string parse/stringify (saf JavaScript)

`qs.js` dosyasında iki fonksiyon yaz ve CommonJS ile export et:
`module.exports = { parseQuery, stringifyQuery }`. Harici bağımlılık YOK.

## `parseQuery(str)` → object

- Baştaki `?` varsa yok say: `"?a=1"` ve `"a=1"` aynı.
- `a=1&b=2` → `{ a: "1", b: "2" }` (değerler her zaman string).
- **Tekrarlı anahtar** → dizi: `a=1&a=2` → `{ a: ["1", "2"] }`. Üç+ tekrar da dizi.
- `a=` → `{ a: "" }` (boş değer).
- `a` (eşittir yok) → `{ a: "" }`.
- **URL decode**: hem `%20` hem `+` boşluğa çözülür (anahtar ve değerde).
  Örn: `a%20b=c+d` → `{ "a b": "c d" }`.
- Boş string `""` veya sadece `"?"` → `{}`.

## `stringifyQuery(obj)` → string

- `parseQuery`'nin tersi (round-trip): `{ a: "1", b: "2" }` → `"a=1&b=2"`.
- Dizi değer → tekrarlı anahtar: `{ a: ["1","2"] }` → `"a=1&a=2"`.
- **URL encode**: özel karakterler encode edilir (boşluk `%20`, `&`, `=` vb.).
  Örn: `{ "a b": "c&d" }` → `"a%20b=c%26d"`.
- Boş obje `{}` → `""`. Baştaki `?` EKLENMEZ.
- Anahtar sırası: obje ekleme sırası korunur.

## Doğrulama
`node -e "require('./qs.js')"` hata vermemeli. Teslim edilen tek dosya `qs.js`.
Sadece kendi dizininde çalış.
