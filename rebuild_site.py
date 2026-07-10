#!/usr/bin/env python3
"""
Rebuilds the transplant reference site from the source Word docs.

Sources (in the parent folder, one level up from this script):
  - Guide to the Transplant Service (Revised).docx   -> guide.html
  - Adult_Inpatient_Transplant_Postop_Protocols_v0.4.docx -> protocols.html
    (edit SRC_PROTOCOLS below if you bump to v0.5, etc.)

Also generates: index.html, manifest.webmanifest, sw.js, icon-192/512.png
Automatically bumps the service-worker cache version so devices refetch.

Usage:  python3 rebuild_site.py
Deps:   pip install mammoth pillow
"""
import re, os, html, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(HERE)          # parent folder holds the .docx files
OUT = HERE                                # write pages next to this script

SRC_GUIDE = os.path.join(SRC_DIR, "Guide to the Transplant Service (Revised).docx")
# Auto-pick the highest-version protocols docx if the exact name isn't found:
SRC_PROTOCOLS = os.path.join(SRC_DIR, "Adult_Inpatient_Transplant_Postop_Protocols_v0.4.docx")

GUIDE_TITLE   = ("Guide to the Transplant Surgery Service", "Resident Guide", "Updated June 2026")
PROT_TITLE    = ("Adult Inpatient Postop Management Protocols", "Inpatient Protocols",
                 "Working Draft — literature-checked May 2026")

# ---------------------------------------------------------------- helpers
def find_protocols_src():
    if os.path.exists(SRC_PROTOCOLS):
        return SRC_PROTOCOLS
    cands = sorted(glob.glob(os.path.join(SRC_DIR, "Adult_Inpatient_Transplant_Postop_Protocols_v*.docx")))
    if cands:
        return cands[-1]  # highest version
    raise SystemExit("Could not find a protocols .docx in " + SRC_DIR)

def docx_to_html(path):
    import mammoth
    with open(path, "rb") as f:
        return mammoth.convert_to_html(f).value

def slugify(text):
    t = html.unescape(re.sub(r"<[^>]+>", "", text)).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or "section"

def process_content(raw):
    toc, used = [], set()
    def repl(m):
        tag, inner = m.group(1), m.group(2)
        base = slugify(inner); sid = base; i = 2
        while sid in used:
            sid = f"{base}-{i}"; i += 1
        used.add(sid)
        title = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        toc.append((int(tag[1]), sid, title))
        return f'<{tag} id="{sid}">{inner}</{tag}>'
    return re.sub(r"<(h[12])>(.*?)</\1>", repl, raw, flags=re.S), toc

def build_toc_html(toc):
    return "\n".join(
        f'<li class="{"toc-h1" if lvl==1 else "toc-h2"}"><a href="#{sid}">{html.escape(t)}</a></li>'
        for lvl, sid, t in toc)

def next_sw_version():
    """Read current sw.js, bump tx-ref-vN -> vN+1 (default v1)."""
    p = os.path.join(OUT, "sw.js")
    n = 1
    if os.path.exists(p):
        m = re.search(r"tx-ref-v(\d+)", open(p).read())
        if m:
            n = int(m.group(1)) + 1
    return f"tx-ref-v{n}"

# ---------------------------------------------------------------- assets
CSS = r"""
:root{--bg:#f4f6f8;--card:#fff;--ink:#1a2530;--muted:#5b6b7a;--accent:#0d6e6e;
--accent-dark:#0a5252;--line:#e2e8ee;--local:#b45309;--local-bg:#fef3e2;
--center:#1d4ed8;--center-bg:#eaf0ff;--maxw:820px}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.6;-webkit-text-size-adjust:100%}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.topbar{position:sticky;top:0;z-index:50;background:var(--accent);color:#fff;padding:env(safe-area-inset-top) 0 0 0}
.topbar-inner{max-width:var(--maxw);margin:0 auto;display:flex;align-items:center;gap:12px;padding:12px 16px;min-height:52px}
.topbar a{color:#fff;font-weight:600}.topbar .home{font-size:20px;line-height:1}
.topbar h1{font-size:16px;margin:0;font-weight:600;flex:1}
.wrap{max-width:var(--maxw);margin:0 auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:16px;box-shadow:0 1px 3px rgba(20,40,60,.04)}
.doc h1{font-size:22px;margin:34px 0 10px;padding-top:8px;border-top:3px solid var(--accent);color:var(--accent-dark);scroll-margin-top:72px}
.doc h1:first-child{border-top:none;margin-top:4px}
.doc h2{font-size:18px;margin:24px 0 8px;color:var(--ink);scroll-margin-top:72px}
.doc h3{font-size:15px;margin:18px 0 6px;color:var(--muted)}
.doc p{margin:10px 0}.doc ul,.doc ol{margin:10px 0;padding-left:22px}.doc li{margin:5px 0}
.doc table{width:100%;border-collapse:collapse;font-size:13px;margin:14px 0;display:block;overflow-x:auto}
.doc th,.doc td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.doc thead th{background:#eef4f4}.doc em{color:var(--muted)}.doc strong{color:var(--ink)}
mark.local{background:var(--local-bg);color:var(--local);padding:1px 4px;border-radius:4px;font-weight:600;font-size:.85em}
mark.center{background:var(--center-bg);color:var(--center);padding:1px 4px;border-radius:4px;font-weight:600;font-size:.85em}
.toc{background:var(--card);border:1px solid var(--line);border-radius:14px;margin-bottom:16px;overflow:hidden}
.toc summary{cursor:pointer;padding:14px 18px;font-weight:600;list-style:none;display:flex;align-items:center;justify-content:space-between;user-select:none}
.toc summary::-webkit-details-marker{display:none}
.toc summary::after{content:"\25be";color:var(--muted);transition:transform .2s}
.toc[open] summary::after{transform:rotate(180deg)}
.toc ul{list-style:none;margin:0;padding:4px 0 12px;border-top:1px solid var(--line)}
.toc li a{display:block;padding:5px 18px;color:var(--ink);font-size:14px}
.toc .toc-h2 a{padding-left:34px;color:var(--muted);font-size:13px}
.updated{color:var(--muted);font-size:13px;margin:0 0 4px}
.hero{text-align:center;padding:26px 16px 8px}.hero .logo{width:66px;height:66px;margin:0 auto 12px;display:block}
.hero h1{font-size:24px;margin:6px 0 4px}.hero p{color:var(--muted);margin:0}
.menu{display:grid;gap:14px;margin-top:8px}
.menu a{display:block;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;box-shadow:0 1px 3px rgba(20,40,60,.05);color:var(--ink)}
.menu a:hover{border-color:var(--accent);box-shadow:0 3px 10px rgba(13,110,110,.10)}
.menu .m-title{font-size:17px;font-weight:600;color:var(--accent-dark);display:flex;align-items:center;gap:10px}
.menu .m-desc{color:var(--muted);font-size:14px;margin-top:5px}.menu .arrow{margin-left:auto;color:var(--accent)}
.legend{font-size:12.5px;color:var(--muted);margin-top:20px;line-height:1.8}
.footer{text-align:center;color:var(--muted);font-size:12px;padding:24px 16px 40px}
.backtop{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom));background:var(--accent);color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:20px;box-shadow:0 3px 10px rgba(0,0,0,.2);cursor:pointer;opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}
.backtop.show{opacity:.92;pointer-events:auto}
@media(min-width:720px){.doc h1{font-size:26px}.hero h1{font-size:28px}}
"""

PAGE_JS = r"""
(function(){var root=document.querySelector('.doc')||document.body;
var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),n=[];while(w.nextNode())n.push(w.currentNode);
n.forEach(function(x){if(/\[(LOCAL PROTOCOL[^\]]*|CENTER-SPECIFIC)\]/.test(x.nodeValue)){
var s=document.createElement('span');s.innerHTML=x.nodeValue
.replace(/\[(LOCAL PROTOCOL[^\]]*)\]/g,'<mark class="local">[$1]</mark>')
.replace(/\[(CENTER-SPECIFIC)\]/g,'<mark class="center">[$1]</mark>');
x.parentNode.replaceChild(s,x);}});
var b=document.querySelector('.backtop');if(b){window.addEventListener('scroll',function(){
b.classList.toggle('show',window.scrollY>500);});b.addEventListener('click',function(){window.scrollTo({top:0,behavior:'smooth'});});}
})();
"""
SW_REG = "if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('sw.js').catch(function(){});});}"

def page(title, short_title, body, is_home=False):
    home = "" if is_home else '<a class="home" href="index.html" aria-label="Home">☰</a>'
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d6e6e">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Transplant">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-192.png">
<title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<header class="topbar"><div class="topbar-inner">{home}<h1>{html.escape(short_title)}</h1></div></header>
{body}
<button class="backtop" aria-label="Back to top">↑</button>
<script>{PAGE_JS}{SW_REG}</script></body></html>"""

def doc_page(titles, content, toc):
    title, short, updated = titles
    body = f"""<div class="wrap">
<p class="updated">{html.escape(updated)}</p>
<details class="toc" open><summary>Contents</summary><ul>{build_toc_html(toc)}</ul></details>
<div class="card doc">{content}</div>
<p class="footer">Reference use only — confirm against institutional protocol and attending orders.</p>
</div>"""
    return page(title, short, body)

def make_icons():
    from PIL import Image, ImageDraw
    for sz in (192, 512):
        img = Image.new("RGB", (sz, sz), "#0d6e6e"); d = ImageDraw.Draw(img)
        m = int(sz*0.16); d.ellipse([m, m, sz-m, sz-m], fill="#0a5252")
        cw = int(sz*0.10); L = int(sz*0.30); c = sz//2
        d.rectangle([c-cw//2, c-L, c+cw//2, c+L], fill="#fff")
        d.rectangle([c-L, c-cw//2, c+L, c+cw//2], fill="#fff")
        img.save(os.path.join(OUT, f"icon-{sz}.png"))

# ---------------------------------------------------------------- build
def main():
    prot_src = find_protocols_src()
    guide_c, guide_toc = process_content(docx_to_html(SRC_GUIDE))
    prot_c,  prot_toc  = process_content(docx_to_html(prot_src))

    open(os.path.join(OUT, "guide.html"), "w").write(doc_page(GUIDE_TITLE, guide_c, guide_toc))
    open(os.path.join(OUT, "protocols.html"), "w").write(doc_page(PROT_TITLE, prot_c, prot_toc))

    landing = """<div class="wrap">
<div class="hero"><img class="logo" src="icon-192.png" alt="">
<h1>Transplant Surgery</h1><p>Resident reference &middot; inpatient service</p></div>
<nav class="menu">
<a href="guide.html"><div class="m-title">Resident Guide <span class="arrow">›</span></div>
<div class="m-desc">Service structure, resident responsibilities, consults, consents, kidney &amp; liver admission checklists, drains &amp; procurements.</div></a>
<a href="protocols.html"><div class="m-title">Inpatient Postop Protocols <span class="arrow">›</span></div>
<div class="m-desc">Evidence-based POD 0&ndash;discharge management for liver, kidney, and pancreas recipients.</div></a>
</nav>
<div class="legend"><mark class="local">[LOCAL PROTOCOL]</mark> attending preference at this center &nbsp;
<mark class="center">[CENTER-SPECIFIC]</mark> decision point governed by institutional protocol</div>
<p class="footer">Add to Home Screen for quick access. Reference use only — confirm against institutional protocol and attending orders.</p></div>"""
    open(os.path.join(OUT, "index.html"), "w").write(
        page("Transplant Surgery — Resident Reference", "Transplant Surgery", landing, is_home=True))

    open(os.path.join(OUT, "manifest.webmanifest"), "w").write("""{
  "name": "Transplant Surgery Reference",
  "short_name": "Transplant",
  "description": "Resident guide and inpatient postop protocols",
  "start_url": "index.html",
  "scope": "./",
  "display": "standalone",
  "background_color": "#f4f6f8",
  "theme_color": "#0d6e6e",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ]
}""")

    ver = next_sw_version()
    open(os.path.join(OUT, "sw.js"), "w").write(
"""const CACHE='%s';
const ASSETS=['index.html','guide.html','protocols.html','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS.map(a=>new Request(a,{cache:'reload'})))).catch(()=>{}));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(res=>{const c=res.clone();caches.open(CACHE).then(x=>x.put(e.request,c)).catch(()=>{});return res;}).catch(()=>caches.match(e.request).then(r=>r||caches.match('index.html'))));});
""" % ver)

    if not os.path.exists(os.path.join(OUT, "icon-192.png")):
        make_icons()

    print("Rebuilt site in", OUT)
    print("  protocols source:", os.path.basename(prot_src))
    print("  guide TOC:", len(guide_toc), "| protocols TOC:", len(prot_toc))
    print("  service-worker cache:", ver, "(bump devices will refetch)")

if __name__ == "__main__":
    main()
