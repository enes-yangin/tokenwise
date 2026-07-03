'use strict';

function decode(s) {
  // '+' means space in query strings; do this before percent-decoding.
  return decodeURIComponent(s.replace(/\+/g, ' '));
}

function encode(s) {
  // encodeURIComponent leaves some chars unescaped; space stays %20 (not '+').
  return encodeURIComponent(s);
}

function parseQuery(str) {
  const result = {};
  if (typeof str !== 'string') return result;

  let s = str;
  if (s.charAt(0) === '?') s = s.slice(1);
  if (s === '') return result;

  for (const pair of s.split('&')) {
    if (pair === '') continue;
    const eq = pair.indexOf('=');
    let rawKey, rawVal;
    if (eq === -1) {
      rawKey = pair;
      rawVal = '';
    } else {
      rawKey = pair.slice(0, eq);
      rawVal = pair.slice(eq + 1);
    }
    const key = decode(rawKey);
    const val = decode(rawVal);

    if (Object.prototype.hasOwnProperty.call(result, key)) {
      if (Array.isArray(result[key])) {
        result[key].push(val);
      } else {
        result[key] = [result[key], val];
      }
    } else {
      result[key] = val;
    }
  }

  return result;
}

function stringifyQuery(obj) {
  if (obj === null || typeof obj !== 'object') return '';

  const parts = [];
  for (const key of Object.keys(obj)) {
    const value = obj[key];
    const encKey = encode(key);
    if (Array.isArray(value)) {
      for (const v of value) {
        parts.push(encKey + '=' + encode(String(v)));
      }
    } else {
      parts.push(encKey + '=' + encode(String(value)));
    }
  }

  return parts.join('&');
}

module.exports = { parseQuery, stringifyQuery };
