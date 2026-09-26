#!/usr/bin/env python3
"""Fetch guest job pages for shortlisted ids (data/enrich_ids.txt), extract pay range + description snippet.
Cached in raw/<id>.html; output data/enriched.json (id -> info). ~1 req / 1.3s."""
import json, re, sys, time, html as H, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT/'raw'; OUT = ROOT/'data'/'enriched.json'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
MONEY = re.compile(r'\$\s?(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[kK])\s*(?:USD)?\s*(?:-|–|—|to|and)\s*\$?\s?(\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[kK])')

def num(s):
    s = s.replace(',', '').replace(' ', '')
    return float(s[:-1]) * 1000 if s[-1] in 'kK' else float(s)

def pay(text):
    lo, hi = None, None
    for a, b in MONEY.findall(text):
        a, b = num(a), num(b)
        if a < 60000 or b > 3000000 or b < a: continue
        lo = a if lo is None else min(lo, a); hi = b if hi is None else max(hi, b)
    return lo, hi

def fetch(jid):
    p = RAW/f'{jid}.html'
    if p.exists() and p.stat().st_size > 5000: return p.read_text()
    req = urllib.request.Request(f'https://www.linkedin.com/jobs/view/{jid}/', headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: body = r.read().decode('utf-8', 'replace')
    except Exception as e:
        print('fail', jid, e, flush=True); return None
    p.write_text(body); time.sleep(float(__import__("os").environ.get("ENRICH_SLEEP","1.3"))); return body

def extract(body):
    m = re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', body, re.S)
    desc = re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', m.group(1) if m else ''))).strip()
    comp = re.search(r'compensation__salary[^>]*>(.*?)</div>', body, re.S)
    comp_t = H.unescape(re.sub(r'<[^>]+>', ' ', comp.group(1))) if comp else ''
    lo, hi = pay(comp_t)
    src = 'linkedin_pay_box' if hi else ''
    if not hi:
        lo, hi = pay(desc); src = 'description' if hi else ''
    closed = 'No longer accepting applications' in body
    lvl = re.search(r'Seniority level\s*</h3>\s*<span[^>]*>\s*(.*?)\s*</span>', body, re.S)
    return {'salary_low': lo, 'salary_high': hi, 'salary_src': src, 'closed': closed,
            'seniority': lvl.group(1).strip() if lvl else '', 'desc': desc[:1500],
            'remote': bool(re.search(r'\bremote\b', desc, re.I))}

def main():
    ids = [x for x in (ROOT/'data'/'enrich_ids.txt').read_text().split() if x]
    out = json.loads(OUT.read_text()) if OUT.exists() else {}
    for i, jid in enumerate(ids):
        if jid in out and out[jid].get('ok'): continue
        body = fetch(jid)
        if body is None or len(body) < 5000: out[jid] = {'ok': False}; continue
        out[jid] = dict(extract(body), ok=True)
        if i % 20 == 0:
            print(i, len(ids), jid, out[jid]['salary_high'], flush=True); OUT.write_text(json.dumps(out))
    OUT.write_text(json.dumps(out)); print('DONE', len(out))
if __name__ == '__main__': main()
