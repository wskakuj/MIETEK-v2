import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const U = require(path.join(repoRoot, 'webapp', 'mietek-utils.js'));

function fakeFile(name, rel) {
  return { name, webkitRelativePath: rel };
}

test('import z podfolderów wykrywa zestawy DBF i .DBF', () => {
  const out = U.groupImportFiles([
    fakeFile('W001.dbf', 'NADL/A/W001.dbf'),
    fakeFile('D001.DBF', 'NADL/A/D001.DBF'),
    fakeFile('O001.dbf', 'NADL/A/O001.dbf'),
    fakeFile('R001.dbf', 'NADL/A/R001.dbf'),
    fakeFile('WSIE001.DBF', 'NADL/A/WSIE001.DBF')
  ], ['W', 'D', 'O', 'R', 'WSIE']);

  assert.equal(out.sets.length, 1);
  assert.deepEqual(Object.keys(out.sets[0].pliki).sort(), ['D', 'O', 'R', 'W', 'WSIE']);
});

test('kolizje nazw zestawów są wykrywane i nie mieszają folderów', () => {
  const out = U.groupImportFiles([
    fakeFile('W001.DBF', 'A/obr1/W001.DBF'),
    fakeFile('D001.DBF', 'A/obr1/D001.DBF'),
    fakeFile('W001.DBF', 'B/obr2/W001.DBF'),
    fakeFile('D001.DBF', 'B/obr2/D001.DBF')
  ], ['W', 'D', 'O', 'R', 'WSIE']);

  assert.equal(out.sets.length, 2);
  assert.equal(out.sameNameGroups.length, 1);
  assert.deepEqual(out.sameNameGroups[0].folders.sort(), ['A/obr1', 'B/obr2']);
});

test('pusty start: index nie ładuje DEMO automatycznie', () => {
  const html = fs.readFileSync(path.join(repoRoot, 'webapp', 'index.html'), 'utf8');
  assert.match(html, /var DEMO = null;/);
  assert.doesNotMatch(html, /if \(DEMO\) wczytajDemo\(\);/);
});

test('HTML wydruku używa marginesów po walidacji', () => {
  const cfg = U.sanitizePrintSettings({
    format: 'A4',
    orientation: 'landscape',
    margins: { top: -1, right: 8.2, bottom: 99, left: '4,5' }
  }, 'optax');

  assert.deepEqual(cfg.margins, { top: 0, right: 8.2, bottom: 50, left: 4.5 });

  const html = U.reportHtml({ reportId: 'optax', fileName: 'OPTAX.TXT', text: 'AGENCJA\nlinia', settings: cfg }).html;
  assert.match(html, /@page\{size:A4 landscape;margin:0mm 8\.2mm 50mm 4\.5mm\}/);
});
