// Bağımsız jüri — qs.js. Agent'lar görmez.
// Kullanım: JUDGE_TARGET=<dir> node judge_qs.js
const path = require('path');
const assert = require('assert');
const { parseQuery, stringifyQuery } = require(path.join(process.env.JUDGE_TARGET, 'qs.js'));

const results = [];
function check(name, fn) {
  try { fn(); results.push([name, true, '']); }
  catch (e) { results.push([name, false, e.message]); }
}
const eq = (a, b) => assert.deepStrictEqual(a, b);

// parse
check('parse_basic', () => eq(parseQuery('a=1&b=2'), { a: '1', b: '2' }));
check('parse_leading_qmark', () => eq(parseQuery('?a=1'), { a: '1' }));
check('parse_repeated_key_array', () => eq(parseQuery('a=1&a=2'), { a: ['1', '2'] }));
check('parse_three_repeats', () => eq(parseQuery('a=1&a=2&a=3'), { a: ['1', '2', '3'] }));
check('parse_empty_value', () => eq(parseQuery('a='), { a: '' }));
check('parse_no_equals', () => eq(parseQuery('a'), { a: '' }));
check('parse_percent_decode', () => eq(parseQuery('a%20b=c%20d'), { 'a b': 'c d' }));
check('parse_plus_decode', () => eq(parseQuery('a+b=c+d'), { 'a b': 'c d' }));
check('parse_empty', () => eq(parseQuery(''), {}));
check('parse_only_qmark', () => eq(parseQuery('?'), {}));

// stringify
check('stringify_basic', () => eq(stringifyQuery({ a: '1', b: '2' }), 'a=1&b=2'));
check('stringify_array', () => eq(stringifyQuery({ a: ['1', '2'] }), 'a=1&a=2'));
check('stringify_encode', () => eq(stringifyQuery({ 'a b': 'c&d' }), 'a%20b=c%26d'));
check('stringify_empty', () => eq(stringifyQuery({}), ''));

// round-trip
check('roundtrip', () => {
  const o = { name: 'a b', tags: ['x', 'y'], q: 'c&d=e' };
  eq(parseQuery(stringifyQuery(o)), o);
});

const passed = results.filter(r => r[1]).length;
for (const [name, ok, err] of results)
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}${ok ? '' : '  -> ' + err}`);
console.log(`SCORE: ${passed}/${results.length}`);
