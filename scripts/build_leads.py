#!/usr/bin/env python3
"""Build data/leads.json for companies on the v5 board from real, previously gathered people + web-found leads.
Never invents names. Excludes Walmart/Sam's colleagues. Companies with no named people get one search-link seat."""
import json, re, sys, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; NET = ROOT.parent/'dashboard'/'network'
sys.path.insert(0, str(ROOT/'scripts')); from score import co_key
NOTE = ("Hi {first}, I'm Manuel, a Walmart operations leader (Last Mile / Spark marketplace) and White House Fellow working on AI "
        "in the workplace at the Dept. of Labor. I'm exploring {role_type} roles at {company} and would value connecting.")
board = json.loads((ROOT/'data'/'jobs.json').read_text())['jobs']
board = [j for j in board if j['prob'] >= 25]
by_co = {}
for j in board: by_co.setdefault(j['company'], []).append(j)
order = sorted(by_co, key=lambda c: -max(j['prob'] for j in by_co[c]))

people = []
def add(company, name, title, kind, url, src):
    if not url or '/in/' not in url: return
    c = co_key(company)
    if re.search(r'recruit|talent acq', title, re.I) and not kind.startswith('Recruiter'): kind = kind.replace('Employee', 'Recruiter')
    if re.search(r'walmart|sam.?s club', c + ' ' + title, re.I): return      # no Walmart colleagues
    people.append({'company': c, 'name': re.sub(r',?\s+(MBA|PHR|SHRM-CP|MSS)\b.*$', '', name).strip(), 'title': title, 'kind': kind,
                   'linkedin_url': url.split('?')[0], 'source': src})
for p in json.loads((NET/'recruiters_alt_v4.json').read_text())['people']:
    add(p['company'], f"{p['first_name']} {p['last_name']}", p['title'], 'Recruiter' if p['role_type'] == 'recruiter' else 'Employee', p['linkedin_url'], 'recruiters_alt_v4')
for p in json.loads((NET/'linkedin_connect_v4.json').read_text())['people']:
    add(p['company'], f"{p['first_name']} {p['last_name']}", re.sub(r'\s+at\s+door ?dash$', '', p['title'], flags=re.I), 'Employee', p['linkedin_url'], 'linkedin_connect_v4')
for p in json.loads((ROOT.parent/'dashboard'/'network.json').read_text())['people']:
    if p.get('is_seat') or p.get('example'): continue
    c, t = p.get('company', ''), p.get('title', '')
    if re.search(r'former|emeritus|founder|professor|consultant|advisor|chairman|trainer', t, re.I): continue   # not a current employee
    if '(' in c: continue                                                   # "current-company filter; headline shows X" = mismatch
    m = re.search(r'(?:\s@\s?|\bat\s)([A-Z][\w&.\' ]+)', t)
    if m and co_key(m.group(1).strip()) != co_key(c): continue              # headline says they work elsewhere
    kind = 'Recruiter' if re.search(r'recruit|talent acq', t, re.I) else 'Employee'
    if p.get('type') == '1st-degree': kind += ' · 1st'
    add(c, f"{p['first_name']} {p['last_name']}", t, kind, p.get('linkedin_url'), 'network.json')
for p in json.loads((ROOT/'data'/'leads_web.json').read_text()):
    add(p['company'], p['name'], p['title'], p['kind'], p['linkedin_url'], p['source'])

seen, leads = set(), []
def jobs_label(c):
    js = sorted(by_co[c], key=lambda j: -j['prob'])
    s = f"{js[0]['title']} ({js[0]['prob']}%)"
    return s + (f" +{len(js)-1} more" if len(js) > 1 else '')
for c in order:
    group = [p for p in people if p['company'] == c]
    group.sort(key=lambda p: (0 if p['kind'].startswith('Recruiter') else 1))
    top = max(by_co[c], key=lambda j: j['prob'])
    n = 0
    for p in group:
        key = p['linkedin_url'].rstrip('/').lower()
        if key in seen or n >= 8: continue
        seen.add(key); n += 1
        leads.append(dict(p, best_prob=top['prob'], jobs_label=jobs_label(c), job_ids=[j['id'] for j in by_co[c]],
                          note=NOTE.format(first=p['name'].split()[0], role_type=top['role_type'], company=c)))
    if n == 0:
        q = urllib.parse.quote(f'{c} recruiter')
        leads.append({'company': c, 'seat': True, 'best_prob': top['prob'], 'jobs_label': jobs_label(c), 'job_ids': [j['id'] for j in by_co[c]],
                      'linkedin_url': f'https://www.linkedin.com/search/results/people/?keywords={q}', 'kind': 'Seat', 'name': f'Find a recruiter at {c}'})
named = [l for l in leads if not l.get('seat')]
meta = {'named_recruiters': sum(l['kind'].startswith('Recruiter') for l in named), 'named_employees': sum(l['kind'].startswith('Employee') for l in named),
        'seats': sum(1 for l in leads if l.get('seat')), 'companies_named': sorted({l['company'] for l in named}), 'companies_on_board': len(order)}
(ROOT/'data'/'leads.json').write_text(json.dumps({'meta': meta, 'leads': leads}, indent=1))
print(json.dumps(meta, indent=1))
