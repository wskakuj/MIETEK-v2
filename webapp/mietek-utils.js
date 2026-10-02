(function (root, factory) {
  if (typeof module !== "undefined" && module.exports) module.exports = factory();
  else root.MietekUtils = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>\"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; });
  }

  function normalizePath(path) {
    var p = String(path || "").replace(/\\/g, "/").replace(/^\.?\/+/, "");
    p = p.replace(/\/+/g, "/").replace(/\/$/, "");
    return p;
  }

  function fileDir(file) {
    var rel = normalizePath(file.webkitRelativePath || file.relativePath || file.path || file.name || "");
    if (!rel || rel === file.name) return "(wczytane)";
    var parts = rel.split("/");
    parts.pop();
    return parts.join("/") || "(wczytane)";
  }

  function dbfTypeFromName(name, knownTypes) {
    var nm = String(name || "").toUpperCase().replace(/\.DBF$/, "");
    var typ = nm.indexOf("WSIE") === 0 ? "WSIE" : nm.charAt(0);
    if (knownTypes.indexOf(typ) < 0) typ = nm.charAt(0);
    return knownTypes.indexOf(typ) >= 0 ? typ : "";
  }

  function groupImportFiles(files, knownTypes) {
    knownTypes = knownTypes || ["W", "D", "O", "R", "WSIE"];
    var list = Array.prototype.slice.call(files || []);
    var dirs = {};
    var lstFiles = [];
    var dbfCount = 0;

    list.forEach(function (f) {
      var name = String(f.name || "");
      if (/\.LST$/i.test(name)) { lstFiles.push(f); return; }
      if (!/\.DBF$/i.test(name)) return;
      dbfCount++;
      var dir = fileDir(f);
      if (!dirs[dir]) dirs[dir] = { folder: dir, types: {}, files: [] };
      var typ = dbfTypeFromName(name, knownTypes);
      if (!typ) return;
      if (!dirs[dir].types[typ]) dirs[dir].types[typ] = [];
      dirs[dir].types[typ].push(f);
      dirs[dir].files.push(f);
    });

    var sets = Object.keys(dirs).map(function (dir, idx) {
      var d = dirs[dir];
      var pliki = {};
      var duplicates = [];
      knownTypes.forEach(function (typ) {
        if (d.types[typ] && d.types[typ].length) {
          pliki[typ] = d.types[typ][0];
          if (d.types[typ].length > 1) duplicates.push(typ);
        }
      });
      var names = Object.keys(pliki).sort().map(function (t) { return String(pliki[t].name || "").toUpperCase(); });
      return {
        id: "set" + idx,
        folder: d.folder,
        name: normalizePath(d.folder).split("/").pop() || d.folder || "(wczytane)",
        pliki: pliki,
        duplicates: duplicates,
        signature: names.join("|")
      };
    }).filter(function (s) { return Object.keys(s.pliki).length > 0; });

    var bySignature = {};
    sets.forEach(function (s) {
      if (!s.signature) return;
      (bySignature[s.signature] = bySignature[s.signature] || []).push(s.folder);
    });
    var sameNameGroups = Object.keys(bySignature).filter(function (k) { return bySignature[k].length > 1; }).map(function (k) {
      return { signature: k, folders: bySignature[k] };
    });

    return { sets: sets, lstFiles: lstFiles, dbfCount: dbfCount, sameNameGroups: sameNameGroups };
  }

  function defaultPrintSettings(reportId) {
    var landscape = /^(optax|rejestr|tabklw|wskaz)$/.test(String(reportId || ""));
    return {
      format: "A4",
      orientation: landscape ? "landscape" : "portrait",
      margins: { top: 8, right: 6, bottom: 8, left: 6 }
    };
  }

  function sanitizePrintSettings(raw, reportId) {
    var d = defaultPrintSettings(reportId);
    var src = raw || {};
    var m = (src.margins || {});
    function mm(v, fb) {
      var n = typeof v === "number" ? v : parseFloat(String(v || "").replace(",", "."));
      if (!isFinite(n)) n = fb;
      if (n < 0) n = 0;
      if (n > 50) n = 50;
      return Math.round(n * 10) / 10;
    }
    var fmt = String(src.format || d.format).toUpperCase();
    if (["A5", "A4", "A3", "LETTER"].indexOf(fmt) < 0) fmt = "A4";
    var orient = src.orientation === "portrait" || src.orientation === "landscape" ? src.orientation : d.orientation;
    return {
      format: fmt,
      orientation: orient,
      margins: {
        top: mm(m.top, d.margins.top),
        right: mm(m.right, d.margins.right),
        bottom: mm(m.bottom, d.margins.bottom),
        left: mm(m.left, d.margins.left)
      }
    };
  }

  function splitPages(text) {
    var lines = String(text || "").split("\n");
    var pages = [];
    var cur = [];
    lines.forEach(function (l) {
      if (l.indexOf("AGENCJA") === 0 && cur.length) { pages.push(cur); cur = []; }
      cur.push(l);
    });
    if (cur.length || !pages.length) pages.push(cur);
    return pages;
  }

  function reportHtml(args) {
    var text = String(args.text || "");
    var settings = sanitizePrintSettings(args.settings, args.reportId);
    var pages = splitPages(text);
    var maxLen = 0;
    text.split("\n").forEach(function (l) { if (l.length > maxLen) maxLen = l.length; });
    var pageBlocks = pages.map(function (pg, i) {
      return '<section class="mietek-page' + (i < pages.length - 1 ? ' brk' : '') + '"><pre class="mietek-report">' + esc(pg.join("\n")) + '</pre></section>';
    }).join("");
    var html = '<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">' +
      '<title>' + esc(args.title || "Wydruk MIETEK") + '</title>' +
      '<style>@page{size:' + settings.format + ' ' + settings.orientation + ';margin:' + settings.margins.top + 'mm ' + settings.margins.right + 'mm ' + settings.margins.bottom + 'mm ' + settings.margins.left + 'mm}' +
      'html,body{margin:0;padding:0;background:#f2f4f7;color:#111;font:12px/1.25 "Consolas","DejaVu Sans Mono",monospace}' +
      '.mietek-wrap{max-width:1600px;margin:0 auto;padding:8px 10px}.mietek-meta{font:600 13px/1.35 "Segoe UI",Arial,sans-serif;color:#1f2937;margin:0 0 8px}' +
      '.mietek-note{font:12px/1.35 "Segoe UI",Arial,sans-serif;color:#475569;margin:0 0 12px}.mietek-page{background:#fff;border:1px solid #d0d7de;border-radius:8px;padding:6mm;box-shadow:0 1px 4px rgba(15,23,42,.1);margin:0 0 10px;overflow:auto}' +
      '.mietek-report{margin:0;white-space:pre;min-width:max-content}.mietek-page.brk{break-after:page;page-break-after:always}' +
      'table{border-collapse:collapse;width:100%}thead{display:table-header-group}tr,img{break-inside:avoid;page-break-inside:avoid}@media print{body{background:#fff}.mietek-wrap{padding:0}.mietek-page{border:0;box-shadow:none;padding:0;margin:0;border-radius:0;overflow:visible}}' +
      '</style></head><body><main class="mietek-wrap"><p class="mietek-meta"><b>' + esc(args.fileName || "wydruk.txt") + '</b>' +
      ' · stron: ' + pages.length + ' · max kolumn: ' + maxLen + (args.objectName ? (' · obiekt: ' + esc(args.objectName)) : '') + '</p>' +
      '<p class="mietek-note">Podgląd i druk korzystają z tego samego dokumentu HTML. Wynik końcowy może się różnić zależnie od sterownika PDF/drukarki i silnika przeglądarki.</p>' +
      pageBlocks + '</main></body></html>';
    return { html: html, pages: pages.length, maxLen: maxLen, settings: settings };
  }

  return {
    normalizePath: normalizePath,
    fileDir: fileDir,
    dbfTypeFromName: dbfTypeFromName,
    groupImportFiles: groupImportFiles,
    defaultPrintSettings: defaultPrintSettings,
    sanitizePrintSettings: sanitizePrintSettings,
    splitPages: splitPages,
    reportHtml: reportHtml
  };
});
