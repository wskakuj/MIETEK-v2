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
      margins: { top: 8, right: 4, bottom: 8, left: 4 }
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
    var pages = splitPages(text), maxLen = 0;
    text.split("\n").forEach(function(l){maxLen=Math.max(maxLen,l.length);});
    var dims = {A4:[210,297], A3:[297,420], A5:[148,210], LETTER:[215.9,279.4]};
    var d = dims[settings.format] || dims.A4;
    var w = settings.orientation === "landscape" ? d[1] : d[0];
    var h = settings.orientation === "landscape" ? d[0] : d[1];
    var m = settings.margins;
    var available = Math.max(1, w-m.left-m.right);
    var fs = Math.min(13,available*96/25.4/(Math.max(1,maxLen)*0.61));
    var blocks = pages.map(function(pg,i){return '<section class="page'+(i<pages.length-1?' brk':'')+'"><pre class="raport">'+esc(pg.join("\n"))+'</pre></section>';}).join('');
    var html = '<!DOCTYPE html><html lang="pl"><head><meta charset="utf-8"><title>'+esc(args.title||'Wydruk MIETEK')+'</title><style>'+ 
      '@page{size:'+settings.format+' '+settings.orientation+';margin:'+m.top+'mm '+m.right+'mm '+m.bottom+'mm '+m.left+'mm}'+
      'html,body{margin:0;padding:0;color:#111;background:#e5e7eb}body{--report-font:'+fs+'px}'+
      '.page{box-sizing:border-box;width:'+w+'mm;min-height:'+h+'mm;margin:12px auto;background:white;padding:'+m.top+'mm '+m.right+'mm '+m.bottom+'mm '+m.left+'mm;box-shadow:0 2px 10px #0002}'+
      'pre.raport{margin:0 auto;width:max-content;white-space:pre;font-family:Consolas,"DejaVu Sans Mono",monospace;font-size:var(--report-font);line-height:1.08}'+
      '@media print{html,body{background:white}.page{width:auto;min-height:0;margin:0;padding:0;box-shadow:none}.brk{break-after:page;page-break-after:always}pre.raport{overflow:visible}}'+
      '</style></head><body>'+blocks+'<script>(function(){function fit(){var p=document.querySelector("pre.raport");if(!p)return;var span=document.createElement("span");span.style.cssText="position:absolute;visibility:hidden;font:100px monospace;white-space:pre";span.textContent="xxxxxxxxxx";document.body.appendChild(span);var cw=span.getBoundingClientRect().width/1000;span.remove();if(cw>0)document.body.style.setProperty("--report-font",Math.min(13,'+available+'*96/25.4/('+Math.max(1,maxLen)+'*cw))+"px");}fit();if(document.fonts)document.fonts.ready.then(fit);window.addEventListener("beforeprint",fit);})();</script></body></html>';
    return {html:html,pages:pages.length,maxLen:maxLen,settings:settings};
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
