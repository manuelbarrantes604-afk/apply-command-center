#!/usr/bin/env python3
"""v5 wide sweep: LinkedIn guest jobs API, last 30 days, Director/Executive levels.
Output: data/sweep_raw.json  (dict jobId -> card). Resumable via data/sweep_log.jsonl."""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'data'/'sweep_raw.json'; LOG = ROOT/'data'/'sweep_log.jsonl'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
KW = ['Senior Director Operations','VP Operations','Head of Operations','Head of Marketplace',
 'Director Strategy and Operations','Head of Strategy & Operations','VP Last Mile','Head of Logistics',
 'Director Fulfillment','VP Fulfillment','Head of AI Transformation','Director AI Strategy','Future of Work',
 'Workforce Strategy Director','Head of Trust and Safety Operations','VP Customer Operations','Chief of Staff COO',
 'Director Marketplace Operations','Head of Delivery Operations','VP Supply Chain','Director Public Policy AI',
 'Head of Workforce Policy']
LOCS = ['United States','Remote','Washington, District of Columbia, United States','Bentonville, Arkansas, United States']
HUBS = ['San Francisco Bay Area','New York City Metropolitan Area','Seattle, Washington, United States']
HUB_KW = ['Senior Director Operations','Head of Strategy & Operations','Head of Marketplace','VP Operations','Head of AI Transformation']
COS = ['Google','Amazon','Meta','Microsoft','Apple','OpenAI','Anthropic','Uber','DoorDash','Instacart','Lyft','Airbnb',
 'Stripe','Salesforce','Oracle','TikTok','ByteDance','Capital One','JPMorgan','Walmart','Target','Costco','FedEx','UPS',
 'Shopify','Netflix','NVIDIA','Databricks','Snowflake','Scale AI','Palantir','McKinsey','Boston Consulting Group','Bain','Deloitte','Accenture']

def fetch(kw, loc, start, extra):
    p = {'keywords': kw, 'location': loc, 'f_TPR': 'r2592000', 'sortBy': 'R', 'start': str(start)}
    p.update(extra)
    url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?' + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return 0, str(e)

def clean(s): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).replace('&amp;', '&').strip()

def parse(html):
    out = []
    for part in re.split(r'<li>', html)[1:]:
        m = re.search(r'urn:li:jobPosting:(\d+)', part)
        if not m: continue
        t = re.search(r'base-search-card__title[^>]*>(.*?)</h3>', part, re.S)
        c = re.search(r'base-search-card__subtitle[^>]*>(.*?)</h4>', part, re.S)
        l = re.search(r'job-search-card__location[^>]*>(.*?)</span>', part, re.S)
        d = re.search(r'datetime="([^"]+)"', part)
        s = re.search(r'job-search-card__salary-info[^>]*>(.*?)</span>', part, re.S)
        lg = re.search(r'data-delayed-url="(https://media\.licdn\.com/[^"]+)"', part)
        out.append({'jobId': m.group(1), 'title': clean(t.group(1) if t else ''), 'company': clean(c.group(1) if c else ''),
                    'location': clean(l.group(1) if l else ''), 'listedAt': d.group(1) if d else '',
                    'card_salary': clean(s.group(1)) if s else '', 'logo': lg.group(1).replace('&amp;', '&') if lg else ''})
    return out

def plan():
    q = []
    for kw in KW:
        for loc in LOCS: q.append((kw, loc, {'f_E': '5,6'}, 3))
    for kw in HUB_KW:
        for loc in HUBS: q.append((kw, loc, {'f_E': '5,6'}, 2))
    for co in COS: q.append((co, 'United States', {'f_E': '5,6'}, 5))
    for kw in ['Senior Director Operations','Head of Operations','VP Operations','Director Strategy and Operations','Head of Marketplace']:
        q.append((kw, 'United States', {'f_SB2': '9'}, 3))
    return q

def main():
    jobs = json.loads(OUT.read_text()) if OUT.exists() else {}
    done = set()
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            r = json.loads(line); done.add((r['kw'], r['loc'], json.dumps(r['extra'], sort_keys=True), r['start']))
    logf = open(LOG, 'a'); fails = 0
    for kw, loc, extra, pages in plan():
        for pg in range(pages):
            key = (kw, loc, json.dumps(extra, sort_keys=True), pg*10)
            if key in done: continue
            st, body = fetch(kw, loc, pg*10, extra)
            if st != 200:
                fails += 1; print('non-200', st, kw, loc, flush=True); time.sleep(20)
                if fails > 8: print('too many failures, stopping'); OUT.write_text(json.dumps(jobs)); return
                break
            cards = parse(body)
            logf.write(json.dumps({'kw': kw, 'loc': loc, 'extra': extra, 'start': pg*10, 'n': len(cards)}) + '\n'); logf.flush()
            for c in cards:
                j = jobs.setdefault(c['jobId'], c); j.setdefault('queries', [])
                if kw not in j['queries']: j['queries'].append(kw)
                if c['card_salary'] and not j.get('card_salary'): j['card_salary'] = c['card_salary']
            print(f'{kw} | {loc} | {extra} | s{pg*10} -> {len(cards)} (total {len(jobs)})', flush=True)
            time.sleep(1.1)
            if len(cards) < 10: break
        OUT.write_text(json.dumps(jobs))
    OUT.write_text(json.dumps(jobs)); print('DONE', len(jobs))
if __name__ == '__main__': main()
