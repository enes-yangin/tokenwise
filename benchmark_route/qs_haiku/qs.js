function parseQuery(str) {
  if (!str || str === '?') return {};

  // Baştaki ? varsa kaldır
  if (str.startsWith('?')) {
    str = str.slice(1);
  }

  if (!str) return {};

  const result = {};
  const pairs = str.split('&');

  pairs.forEach(pair => {
    if (!pair) return;

    const eqIndex = pair.indexOf('=');
    let key, value;

    if (eqIndex === -1) {
      key = pair;
      value = '';
    } else {
      key = pair.slice(0, eqIndex);
      value = pair.slice(eqIndex + 1);
    }

    // URL decode: %20 ve + boşluğa çözülür
    key = decodeURIComponent(key.replace(/\+/g, ' '));
    value = decodeURIComponent(value.replace(/\+/g, ' '));

    // Tekrarlı anahtar → dizi
    if (key in result) {
      if (!Array.isArray(result[key])) {
        result[key] = [result[key]];
      }
      result[key].push(value);
    } else {
      result[key] = value;
    }
  });

  return result;
}

function stringifyQuery(obj) {
  if (!obj || Object.keys(obj).length === 0) return '';

  const pairs = [];

  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const value = obj[key];
      const encodedKey = encodeURIComponent(key);

      if (Array.isArray(value)) {
        value.forEach(v => {
          pairs.push(encodedKey + '=' + encodeURIComponent(v));
        });
      } else {
        pairs.push(encodedKey + '=' + encodeURIComponent(value));
      }
    }
  }

  return pairs.join('&');
}

module.exports = { parseQuery, stringifyQuery };
