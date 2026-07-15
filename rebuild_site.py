#!/usr/bin/env python3
"""
Rebuilds the transplant reference site from the source Word docs.

Current scope (protocols temporarily omitted while being refined):
  - atss_guidelines_aptos.docx  -> guide.html   (service + resident guide)
  - reading list (data below)   -> reading.html (encouraged reading)

Also generates: index.html, manifest.webmanifest, sw.js, icon-192/512.png
Automatically bumps the service-worker cache version so devices refetch.

To re-add protocols later: restore the protocols block in main(), add
'protocols.html' back to the SW ASSETS list, and add its menu card in the landing.

Usage:  python3 rebuild_site.py
Deps:   pip install mammoth pillow
"""
import re, os, html, glob

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(HERE)          # parent folder holds the .docx files
OUT = HERE                                # write pages next to this script

SRC_GUIDE = os.path.join(SRC_DIR, "atss_guidelines_aptos.docx")

GUIDE_TITLE   = ("Guide to the Transplant Surgery Service", "Resident Guide", "Updated July 2026")
READING_TITLE = ("Transplant Surgery Rotation — Encouraged Reading List", "Reading List",
                 "Updated July 2026")

# Reading list: (section, [(title, citation, url, unverified?), ...])
READING = [
 ("History of Organ Transplantation", [
   ("Historical Overview of Transplantation", "Cold Spring Harb Perspect Med. 2013",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3684003/pdf/cshperspectmed-TRN-a014977.pdf", False)]),
 ("Liver Transplantation", [
   ("A Model to Predict Survival in Patients with End-Stage Liver Disease (MELD)", "Hepatology. 2001",
    "https://aasldpubs.onlinelibrary.wiley.com/doi/abs/10.1053/jhep.2001.22172", False),
   ("The Survival Benefit of Liver Transplantation", "Am J Transplant. 2005",
    "https://onlinelibrary.wiley.com/doi/full/10.1111/j.1600-6143.2004.00703.x?sid=nlm%3Apubmed", False),
   ("The Survival Benefit of Deceased Donor Liver Transplantation as a Function of Candidate Disease Severity and Donor Quality", "Am J Transplant. 2008",
    "https://onlinelibrary.wiley.com/doi/full/10.1111/j.1600-6143.2007.02086.x", False),
   ("Characteristics Associated with Liver Graft Failure: The Concept of a Donor Risk Index (DRI)", "Am J Transplant. 2006",
    "https://onlinelibrary.wiley.com/doi/full/10.1111/j.1600-6143.2006.01242.x?sid=nlm%3Apubmed", False),
   ("Liver Transplantation for the Treatment of Small Hepatocellular Carcinomas in Patients with Cirrhosis (Milan Criteria)", "N Engl J Med. 1996",
    "https://www.nejm.org/doi/10.1056/NEJM199603143341104", False)]),
 ("Infection in Organ Transplantation", [
   ("Infection in Organ Transplantation", "Am J Transplant. 2017",
    "https://onlinelibrary.wiley.com/doi/epdf/10.1111/ajt.14208", False)]),
 ("Anatomy in Organ Transplantation", [
   ("Anatomical Variation and Its Management in Transplantation", "Am J Transplant. 2015",
    "https://onlinelibrary.wiley.com/doi/epdf/10.1111/ajt.13310", False)]),
 ("HCV in Organ Transplantation", [
   ("Direct-Acting Antiviral Prophylaxis for HCV-Seronegative Recipients of HCV-Seropositive Donor Kidneys", "Transpl Int. 2019",
    "https://www.ncbi.nlm.nih.gov/pubmed/30920681", True),
   ("Center-Level Trends in Utilization of HCV-Exposed Donors for HCV-Uninfected Kidney and Liver Transplant Recipients in the United States", "Am J Transplant. 2019",
    "https://www.ncbi.nlm.nih.gov/pubmed/30861279", False),
   ("Changes in Utilization and Discard of HCV Antibody-Positive Deceased Donor Kidneys in the Era of Direct-Acting Antiviral Therapy", "Am J Transplant. 2018",
    "https://www.ncbi.nlm.nih.gov/pubmed/29912046", False)]),
 ("Immunosuppression", [
   ("Liver Transplantation with Use of Cyclosporin A and Prednisone", "N Engl J Med. 1981",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2772056/pdf/nihms147225.pdf", False)]),
 ("Hot Topics in Organ Transplantation", [
   ("Realizing HOPE: The Ethics of Organ Transplantation from HIV-Infected Donors", "Ann Intern Med. 2016",
    "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4949150/pdf/nihms-786616.pdf", False),
   ("Early Liver Transplantation for Severe Alcoholic Hepatitis", "N Engl J Med. 2011",
    "https://www.nejm.org/doi/full/10.1056/Nejmoa1105703", False),
   ("Article in the Journal of the American College of Surgeons", "J Am Coll Surg. 2018",
    "https://www.journalacs.org/article/S1072-7515(18)30025-5/fulltext", True),
   ("The Drug Overdose Epidemic and Deceased-Donor Transplantation in the United States: A National Registry Study", "Ann Intern Med. 2018",
    "https://www.ncbi.nlm.nih.gov/pubmed/29710288", False)]),
 ("Risks of Living Kidney Donation", [
   ("Risks of Living Kidney Donation: Current State of Knowledge on Outcomes Important to Donors", "Clin J Am Soc Nephrol. 2019",
    "https://www.ncbi.nlm.nih.gov/pubmed/30858158", False)]),
 ("Changes in Kidney Allocation for the Highly Sensitized", [
   ("The National Landscape of Deceased Donor Kidney Transplantation for the Highly Sensitized: Transplant Rates, Waitlist Mortality, and Post-Transplant Survival Under KAS", "Am J Transplant. 2019",
    "https://www.ncbi.nlm.nih.gov/pubmed/30372592", False)]),
 ("Predicting Survival After DDKT by Donor–Recipient Combination", [
   ("Who Can Tolerate a Marginal Kidney? Predicting Survival After Deceased-Donor Kidney Transplantation by Donor–Recipient Combination", "Am J Transplant. 2019",
    "https://www.ncbi.nlm.nih.gov/pubmed/29935051", False)]),
]

# ---------------------------------------------------------------- helpers
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
        title = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        if not title:               # skip blank heading-styled lines
            return ""
        base = slugify(inner); sid = base; i = 2
        while sid in used:
            sid = f"{base}-{i}"; i += 1
        used.add(sid)
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
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Aptos",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;line-height:1.6;-webkit-text-size-adjust:100%}
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
.search{position:sticky;top:52px;z-index:30;display:flex;gap:6px;align-items:center;background:var(--bg);padding:10px 0 8px}
.search input{flex:1;font-size:16px;padding:9px 12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);-webkit-appearance:none;min-width:0}
.search button{width:38px;height:38px;flex:none;border:1px solid var(--line);background:var(--card);border-radius:10px;font-size:20px;line-height:1;color:var(--accent);cursor:pointer}
.search button:active{background:var(--line)}
.search #qinfo{color:var(--muted);font-size:12.5px;min-width:46px;text-align:right;font-variant-numeric:tabular-nums}
mark.hit{background:#fde68a;color:inherit;border-radius:3px;padding:0 1px}
mark.hit.cur{background:#f59e0b;color:#1a2530}
.readlist h2{font-size:16px;margin:22px 0 8px;color:var(--accent-dark);border-top:2px solid var(--line);padding-top:14px}
.readlist h2:first-of-type{border-top:none;padding-top:0}
.readlist .ref{margin:0 0 14px}
.readlist .ref a{font-weight:600;line-height:1.45}
.readlist .cite{display:block;color:var(--muted);font-size:12.5px;margin-top:2px}
.readlist .flag{color:var(--local);font-weight:700}
.readlist .note{margin-top:22px;padding-top:12px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;font-style:italic}
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
(function(){var box=document.getElementById('q');if(!box)return;
var root=document.querySelector('.doc');if(!root)return;var info=document.getElementById('qinfo');var hits=[],idx=-1,t;
function clear(){var ms=root.querySelectorAll('mark.hit');for(var i=0;i<ms.length;i++){var m=ms[i];m.parentNode.replaceChild(document.createTextNode(m.textContent),m);}root.normalize();}
function show(){for(var i=0;i<hits.length;i++)hits[i].classList.remove('cur');var h=hits[idx];if(!h)return;h.classList.add('cur');h.scrollIntoView({block:'center',behavior:'smooth'});info.textContent=(idx+1)+'/'+hits.length;}
function run(){clear();hits=[];idx=-1;var term=box.value.trim();if(term.length<2){info.textContent='';return;}
var rx=new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi');
var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),nodes=[];while(w.nextNode())nodes.push(w.currentNode);
for(var i=0;i<nodes.length;i++){var n=nodes[i],s=n.nodeValue;rx.lastIndex=0;if(!rx.test(s))continue;rx.lastIndex=0;
var frag=document.createDocumentFragment(),last=0,m;while((m=rx.exec(s))){if(m.index>last)frag.appendChild(document.createTextNode(s.slice(last,m.index)));var mk=document.createElement('mark');mk.className='hit';mk.textContent=m[0];frag.appendChild(mk);hits.push(mk);last=m.index+m[0].length;if(m.index===rx.lastIndex)rx.lastIndex++;}
if(last<s.length)frag.appendChild(document.createTextNode(s.slice(last)));n.parentNode.replaceChild(frag,n);}
if(hits.length){idx=0;show();}else info.textContent='0/0';}
function step(d){if(!hits.length)return;idx=(idx+d+hits.length)%hits.length;show();}
box.addEventListener('input',function(){clearTimeout(t);t=setTimeout(run,120);});
box.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();step(e.shiftKey?-1:1);}});
document.getElementById('qnext').addEventListener('click',function(){step(1);});
document.getElementById('qprev').addEventListener('click',function(){step(-1);});
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
<div class="search"><input id="q" type="search" placeholder="Search this page&hellip;" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false">
<button id="qprev" type="button" aria-label="Previous match">&lsaquo;</button><button id="qnext" type="button" aria-label="Next match">&rsaquo;</button>
<span id="qinfo" aria-live="polite"></span></div>
<details class="toc" open><summary>Contents</summary><ul>{build_toc_html(toc)}</ul></details>
<div class="card doc">{content}</div>
<p class="footer">Reference use only — confirm against institutional protocol and attending orders.</p>
</div>"""
    return page(title, short, body)

def reading_page(titles):
    title, short, updated = titles
    rows, any_flag = [], False
    for section, items in READING:
        rows.append(f'<h2>{html.escape(section)}</h2>')
        for t, cite, url, flag in items:
            star = ' <span class="flag" title="citation not verified">*</span>' if flag else ''
            any_flag = any_flag or flag
            rows.append(
                f'<p class="ref"><a href="{html.escape(url)}" target="_blank" rel="noopener">'
                f'{html.escape(t)}</a>{star}<span class="cite">{html.escape(cite)}</span></p>')
    note = ('<p class="note">* Full citation could not be verified against PubMed; '
            'the original link is preserved as provided.</p>') if any_flag else ''
    body = f"""<div class="wrap">
<p class="updated">{html.escape(updated)}</p>
<div class="card readlist">
<p style="margin-top:0;color:var(--muted)">Links to articles pertinent to transplantation — a sample of landmark studies and papers outlining the most up-to-date practices in the field.</p>
{''.join(rows)}
{note}
</div>
<p class="footer">Reference use only. External links open on the publisher's site.</p>
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
    guide_c, guide_toc = process_content(docx_to_html(SRC_GUIDE))

    open(os.path.join(OUT, "guide.html"), "w").write(doc_page(GUIDE_TITLE, guide_c, guide_toc))
    open(os.path.join(OUT, "reading.html"), "w").write(reading_page(READING_TITLE))

    landing = """<div class="wrap">
<div class="hero"><img class="logo" src="icon-192.png" alt="">
<h1>Transplant Surgery</h1><p>Resident reference &middot; inpatient service</p></div>
<nav class="menu">
<a href="guide.html"><div class="m-title">Resident Guide <span class="arrow">›</span></div>
<div class="m-desc">Service structure, resident responsibilities, consults, consents, kidney &amp; liver admission checklists, drains &amp; procurements.</div></a>
<a href="reading.html"><div class="m-title">Encouraged Reading List <span class="arrow">›</span></div>
<div class="m-desc">Landmark studies and current-practice papers across liver, kidney, HCV, immunosuppression, and donation.</div></a>
</nav>
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
const ASSETS=['index.html','guide.html','reading.html','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS.map(a=>new Request(a,{cache:'reload'})))).catch(()=>{}));});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).then(res=>{const c=res.clone();caches.open(CACHE).then(x=>x.put(e.request,c)).catch(()=>{});return res;}).catch(()=>caches.match(e.request).then(r=>r||caches.match('index.html'))));});
""" % ver)

    if not os.path.exists(os.path.join(OUT, "icon-192.png")):
        make_icons()

    print("Rebuilt site in", OUT)
    print("  guide source:", os.path.basename(SRC_GUIDE))
    print("  guide TOC:", len(guide_toc), "| reading sections:", len(READING))
    print("  service-worker cache:", ver, "(bump devices will refetch)")

if __name__ == "__main__":
    main()
