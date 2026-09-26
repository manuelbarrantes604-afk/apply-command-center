#!/usr/bin/env python3
"""v5 scoring. Usage:
  python3 scripts/score.py shortlist   -> data/enrich_ids.txt (candidates needing a job-page salary check)
  python3 scripts/score.py final       -> data/jobs.json (board: $280k+ only, probability bands)
Inputs: data/sweep_raw.json (new sweep), ../dashboard/jobs.json (Sep 23 sweep), data/enriched.json."""
import json, re, sys, html as H
from datetime import date, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 9, 26); CUTOFF_DAYS = 30; FLOOR = 280000

# ---------- company normalisation / tiers ----------
CO = [('TikTok', r'tiktok|bytedance'), ('Walmart', r'walmart|sam.?s club'), ('DoorDash', r'doordash'), ('Uber', r'\buber\b'),
 ('Lyft', r'\blyft\b'), ('Instacart', r'instacart'), ('Meta', r'^meta\b|facebook'), ('Google', r'^google|deepmind|^youtube'),
 ('Amazon', r'^amazon|\baws\b|amazon web services|^whole foods'), ('OpenAI', r'openai'), ('Anthropic', r'anthropic'), ('Microsoft', r'microsoft|^linkedin$'),
 ('Apple', r'^apple$'), ('NVIDIA', r'nvidia'), ('Salesforce', r'salesforce'), ('Databricks', r'databricks'), ('Snowflake', r'snowflake'),
 ('Target', r'^target$'), ('Costco', r'costco'), ('Capital One', r'capital one'), ('JPMorgan Chase', r'jpmorgan|jp morgan|chase'),
 ('Airbnb', r'airbnb'), ('Stripe', r'^stripe'), ('Shopify', r'shopify'), ('Netflix', r'netflix'), ('Oracle', r'^oracle'),
 ('Scale AI', r'scale ai|scale\.ai'), ('Palantir', r'palantir'), ('FedEx', r'fedex'), ('UPS', r'^ups$|united parcel'),
 ('McKinsey', r'mckinsey'), ('BCG', r'boston consulting|^bcg'), ('Bain', r'^bain'), ('Deloitte', r'deloitte'), ('Accenture', r'accenture'),
 ('Block', r'^block$|^square$|cash app'), ('Coinbase', r'coinbase'), ('Reddit', r'reddit'), ('Pinterest', r'pinterest'), ('Snap', r'^snap'),
 ('Adobe', r'^adobe'), ('ServiceNow', r'servicenow'), ('Workday', r'^workday'), ('Intuit', r'intuit'), ('Cloudflare', r'cloudflare'),
 ('xAI', r'^xai$'), ('Waymo', r'waymo'), ('Zoox', r'zoox'), ('Tesla', r'^tesla'), ('Visa', r'^visa$'), ('Mastercard', r'mastercard'),
 ('American Express', r'american express'), ('Goldman Sachs', r'goldman'), ('PayPal', r'paypal'), ('Gopuff', r'gopuff'), ('Grubhub', r'grubhub'),
 ('Anduril', r'anduril'), ('Palo Alto Networks', r'palo alto networks'), ('Affirm', r'^affirm'), ('Cisco', r'^cisco'), ('Citi', r'^citi$|^citigroup|^citibank'), ('Morgan Stanley', r'morgan stanley'), ('Wells Fargo', r'wells fargo'), ('Bank of America', r'bank of america'), ('The Home Depot', r'home depot'), ("Lowe's", r'^lowe'), ('Kroger', r'^kroger'), ('PepsiCo', r'pepsico'), ('Procter & Gamble', r'procter'), ('Alvarez & Marsal', r'alvarez'), ('EY-Parthenon', r'ey-parthenon|^ey$|ernst'), ('PwC', r'^pwc'), ('KPMG', r'^kpmg'), ('DHL', r'^dhl'), ('Nike', r'^nike'), ('Starbucks', r'starbucks'), ('Chewy', r'^chewy'), ('Wayfair', r'wayfair'), ('eBay', r'^ebay'), ('Etsy', r'^etsy'), ('Expedia', r'expedia'), ('Booking', r'booking'), ('Spotify', r'spotify'), ('Roblox', r'roblox'), ('Rivian', r'rivian'), ('Figma', r'^figma'), ('Ramp', r'^ramp$'), ('Plaid', r'^plaid'), ('Robinhood', r'robinhood'), ('Chime', r'^chime')]
TIER_A = {'Google','Meta','Amazon','Microsoft','Apple','OpenAI','Anthropic','NVIDIA','Netflix','Uber','DoorDash','Instacart','Lyft','Airbnb',
 'Stripe','Salesforce','Databricks','Snowflake','Scale AI','Palantir','TikTok','Shopify','Block','Coinbase','Reddit','Pinterest','Snap',
 'Adobe','ServiceNow','Workday','Intuit','xAI','Waymo','Oracle','Cloudflare','Palo Alto Networks','Affirm','Cisco','eBay','Etsy','Expedia','Booking','Spotify','Roblox','Robinhood','Ramp','Plaid','Figma','Anduril','Tesla','Zoox'}
TIER_B = {'Capital One','JPMorgan Chase','Walmart','Target','Costco','FedEx','UPS','McKinsey','BCG','Bain','Deloitte','Accenture','Visa',
 'Mastercard','American Express','Goldman Sachs','PayPal','Gopuff','Grubhub','Chime','Citi','Morgan Stanley','Wells Fargo','Bank of America','The Home Depot',"Lowe's",'Kroger','PepsiCo','Procter & Gamble','Alvarez & Marsal','EY-Parthenon','PwC','KPMG','DHL','Nike','Starbucks','Chewy','Wayfair','Rivian'}
GIG_RETAIL = {'DoorDash','Uber','Instacart','Lyft','Walmart','Amazon','Target','Costco','Shopify','TikTok','Gopuff','Grubhub','Airbnb','FedEx','UPS','DHL','Kroger','The Home Depot',"Lowe's",'Chewy','Wayfair','Veho'}
SPAM = re.compile(r'jobgether|ladders|swooped|lensa|hirenza|staffing|recruit|talent|executive search|headhunt|jobot|cybercoders|insight global|'
 r'actalent|virtual vocations|dice|ziprecruiter|crossing hurdles|clickjobs|jobs? ?board|confidential|stealth|korn ferry|heidrick|russell reynolds|'
 r'\bsearch\b|saragossa|executive alliance|biospace|solomon page|r2 global|addison group|skywater|harnham|beacon hill|kelly services|manpower|aerotek|teksystems|spencer stuart|egon zehnder|hays|randstad|adecco|kforce|robert half|motion recruitment|careers? ?(hub|group)|placement|consultancy group', re.I)

def co_key(c):
    c = H.unescape(c or '').strip()
    for k, p in CO:
        if re.search(p, c, re.I): return k
    return c

# ---------- title rules ----------
HARD_OUT = re.compile(r'(software|engineer|scientist|research|developer|architect|account executive|sales\b|business development|recruit|talent acq|'
 r'marketing|brand|creative|design|counsel|legal|attorney|finance|fp&a|accounting|controller|tax|treasury|audit|investor|medical|clinical|'
 r'nurs|pharm|physician|hospital|patient|health system|construction|manufactur|plant|facility|facilities|real estate|data center|semiconductor|'
 r'hardware|silicon|security|cyber|it operations|information technology|infrastructure|network|devops|product manag|product management|'
 r'program manag|payroll|benefits|compensation|merchandis|category|store manager|district manager|restaurant|hotel|school|university|'
 r'college|church|fundrais|nonprofit|revenue cycle|underwrit|actuar|lending|mortgage|wealth|portfolio|investment|energy|utility|oil|mining|'
 r'\bhr\b|human resources|business partner|employee relations|labor relations|total rewards|account|client director|critical environment|vaccine|therapeutic|technology operations|tech ops|emerging threats|\bproduct\b(?! strategy)|principal|hvac|electrical|mechanical|quality assurance|regulatory affairs|editorial|content|communications|partnerships? (sales|manager))', re.I)
LEVEL = [(r'\b(chief operating officer|coo)\b', 'C-level'), (r'\b(svp|evp|senior vice president|executive vice president)\b', 'SVP'),
 (r'\b(vice president|vp)\b', 'VP'), (r'\bchief of staff\b', 'CoS'), (r'\b(group director|managing director)\b', 'Group Dir'),
 (r'\b(senior director|sr\.? director|sr director)\b', 'Sr Dir'), (r'\bhead\b', 'Head'), (r'\bgeneral manager\b', 'GM'),
 (r'\bdirector\b', 'Director')]
STRONG = re.compile(r'marketplace|last.?mile|gig|courier|dasher|shopper|driver|(?<!service )(?<!care )(?<!technology )(?<!project )delivery(?! cent)|fulfil|logistics|regional op|field op|'
 r'strategy (?:&|and) op|strategy & ops|s&o|biz ?ops|business operations|workforce|future of work|ai transformation|ai adoption|'
 r'ai strategy|ai enablement|trust (?:&|and) safety|integrity op|customer (?:experience|support|care|operations|success op)|cx\b|'
 r'community op|live op|network op|operations excellence|operational excellence|central op|global op|supply chain op|transportation', re.I)
ADJ = re.compile(r'operations|\bops\b|supply chain|strategy|transformation|public policy|policy|government|public sector|chief of staff|'
 r'general manager|planning|commerce|retail|grocery|expansion|launch|excellence|enablement|people|labor|economic', re.I)
WHF = re.compile(r'workforce|future of work|labor|economic|ai (?:adoption|transformation|strategy|enablement|impact)|responsible ai|federal', re.I)
SPECIALIST = re.compile(r'sanctions|collateral|reference data|derivatives|claims|lounge|child safety|containment|regulatory|compliance|privacy|intellectual property|digital rights|government relations|government affairs|export|lobby|tax|clinical', re.I)
TECH_OPS = re.compile(r'compute|gpu|model|inference|ml ops|mlops|platform ops|revenue op|sales op|gtm|go.to.market|deal desk|finance op|legal op|'
 r'marketing op|security op|it |engineering op|clinical op|research op|lab op', re.I)

def level(t):
    for p, n in LEVEL:
        if re.search(p, t, re.I): return n
    return None

def geo(loc, remote_flag=False):
    l = (loc or '').lower()
    if 'remote' in l or remote_flag: return 'Remote', 7
    if re.search(r'washington, dc|district of columbia|washington dc|arlington, va|mclean|alexandria, va|reston|bethesda', l): return 'DC', 6
    if re.search(r'bentonville|rogers, ar|springdale|fayetteville, ar|arkansas', l): return 'NWA', 6
    if l.strip() in ('united states', 'us'): return 'US', 4
    if re.search(r'new york|san francisco|seattle|bellevue|mountain view|sunnyvale|palo alto|menlo park|san jose|bay area|chicago|austin|boston|'
                 r'atlanta|los angeles|dallas|denver|redmond|santa clara|oakland|kirkland|miami', l): return 'Hub', 0
    return 'Other', -6

US_ST = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split())
def us_loc(l):
    l = (l or '').strip()
    if re.search(r'united states|^remote$|metropolitan area|bay area|\bmetroplex\b|greater .* area', l, re.I) and not re.search(r'canada|kingdom|india|japan|mexico|germany|australia|singapore|brazil|ireland|france|korea|seoul|incheon|china|taiwan|hong kong|philippines|poland|spain|italy|netherlands|sweden|israel|dubai|emirates|saudi|argentina|colombia|chile|vietnam|thailand|indonesia|malaysia|zealand|south africa', l, re.I): return True
    m = re.search(r',\s*([A-Z]{2})$', l)
    return bool(m and m.group(1) in US_ST)

def age_days(d):
    try: return (TODAY - datetime.strptime(d[:10], '%Y-%m-%d').date()).days
    except Exception: return 99

# ---------- salary estimate (total comp, $k) ----------
EST = {'A': {'Director': (300, 450), 'Head': (350, 550), 'Sr Dir': (400, 600), 'Group Dir': (400, 650), 'CoS': (300, 480), 'GM': (400, 650),
             'Principal': (300, 450), 'VP': (500, 900), 'SVP': (700, 1200), 'C-level': (700, 1500)},
       'B': {'Director': (190, 270), 'Head': (220, 320), 'Sr Dir': (260, 380), 'Group Dir': (260, 380), 'CoS': (220, 320), 'GM': (260, 380),
             'Principal': (220, 320), 'VP': (350, 600), 'SVP': (500, 900), 'C-level': (500, 1000)}}
BASIS = {'A': 'typical {lvl} total comp at {co} (Levels.fyi-style band)', 'B': 'typical {lvl} total comp at {co} (base + bonus + equity band)'}

BANKS = {'JPMorgan Chase','Goldman Sachs','Citi','Morgan Stanley','Bank of America','Wells Fargo','Capital One','American Express'}
def estimate(co, lvl):
    tier = 'A' if co in TIER_A else 'B' if co in TIER_B else None
    if not tier: return None
    if co in BANKS and lvl in ('VP', 'SVP'): return None      # bank VP titles are mid-level; need posted pay
    if tier == 'B' and lvl == 'GM': return None                # retail/logistics GMs are often site-level
    if co in ('DHL', 'FedEx', 'UPS', 'The Home Depot', "Lowe's", 'Kroger', 'Costco', 'Target', 'Starbucks', 'Nike', 'Chewy', 'Wayfair') and lvl in ('VP', 'SVP', 'Head'):
        return None                                            # site/regional VP titles vary too much; need posted pay
    lo, hi = EST[tier][lvl]
    return lo * 1000, hi * 1000, BASIS[tier].format(lvl=lvl, co=co)

def parse_card_salary(s):
    m = re.findall(r'\$([\d,.]+)([kK]?)(?:/yr)?', s or '')
    vals = [float(a.replace(',', '')) * (1000 if k else 1) for a, k in m]
    vals = [v for v in vals if v > 50000]
    return (min(vals), max(vals)) if len(vals) >= 1 else (None, None)

# ---------- probability ----------
def prob(j):
    t, co, lvl = j['title'], j['company_key'], j['level']
    tl = t.lower(); desc = j.get('desc', '')
    s = {'Director': 50, 'Principal': 45, 'Head': 46, 'Sr Dir': 46, 'Group Dir': 44, 'CoS': 46, 'GM': 38, 'VP': 34, 'SVP': 18, 'C-level': 12}[lvl]
    why = []
    strong, adj = STRONG.search(t), ADJ.search(t)
    if strong: s += 20; why.append(strong.group(0).strip().lower())
    elif adj: s += 6
    else: s -= 12
    if TECH_OPS.search(t): s -= 14
    if co in GIG_RETAIL: s += 10; why.append('gig/retail operator')
    elif co in TIER_A: s -= 2
    if co not in TIER_A and co not in TIER_B and co not in GIG_RETAIL: s -= 5   # household names preferred
    if co in ('OpenAI', 'Anthropic', 'xAI', 'NVIDIA', 'Databricks', 'Snowflake', 'Palantir', 'Scale AI', 'Apple', 'Netflix'): s -= 6
    if co in ('McKinsey', 'BCG', 'Bain'): s -= 12
    if WHF.search(t): s += 8; why.append('WHF / AI-workforce edge')
    elif re.search(r'policy|government|public sector', t, re.I): s += 3
    if SPECIALIST.search(t): s -= 18
    if re.search(r'deepmind', t + ' ' + j['company'], re.I): s -= 6
    if co == 'Walmart': s += 10; why.append('internal Walmart')
    if lvl in ('VP', 'SVP', 'C-level') and co in TIER_A: s -= 8
    g, gs = j['geo'], geo(j['location'], j.get('remote_flag'))[1]
    s += gs
    if age_days(j['listedAt']) > 21: s -= 4
    s = max(5, min(92, round(s)))
    return s, why

def why_line(j, tags):
    craft = {'marketplace': 'Runs Walmart Spark gig marketplace', 'last mile': 'Runs Walmart Last Mile', 'last-mile': 'Runs Walmart Last Mile',
             'delivery': 'Runs Walmart Last Mile delivery', 'driver': 'Leads Spark driver network', 'shopper': 'Leads Spark shopper network',
             'fulfil': 'Last-mile + 180-store fulfillment ops', 'logistics': 'Last-mile logistics at Walmart scale',
             'workforce': 'WHF on AI + workforce at DOL', 'future of work': 'WHF on future of work at DOL', 'ai transformation': 'WHF AI-in-workplace + Walmart ops',
             'ai strategy': 'WHF AI-in-workplace + Walmart ops', 'ai adoption': 'WHF AI-in-workplace + Walmart ops', 'ai enablement': 'WHF AI-in-workplace + Walmart ops',
             'trust & safety': 'Gig marketplace integrity at Spark', 'trust and safety': 'Gig marketplace integrity at Spark',
             'regional op': 'Ran 180 stores / 13 states', 'field op': 'Ran 180 stores / 13 states', 'transportation': 'Last-mile transportation ops'}
    t = j['title'].lower(); lead = None
    if re.search(r'(service|care|technology|project) delivery|delivery cent', t): lead = 'Scaled service operations across 180 stores + Spark support'
    for k, v in ({} if lead else craft).items():
        if k in t: lead = v; break
    if not lead:
        if re.search(r'strategy (&|and) op|s&o|biz ?ops|business op|chief of staff', t): lead = 'Director-level S&O across Walmart Spark + regional ops'
        elif re.search(r'customer|cx|support|care', t): lead = 'Owns shopper/driver + customer experience at Spark'
        elif re.search(r'policy|government|public', t): lead = 'White House Fellow, DOL AI-in-workplace policy'
        elif re.search(r'supply chain', t): lead = '180-store supply + last-mile operator'
        else: lead = 'Large-scale ops leader (180 stores, Spark marketplace)'
    extra = {'Remote': 'remote', 'DC': 'DC-based', 'NWA': 'NWA home base', 'US': 'US-wide'}.get(j['geo'])
    step = {'VP': 'VP step-up', 'SVP': 'big step-up', 'Sr Dir': 'Sr Dir step-up', 'Group Dir': 'step-up', 'Head': 'Head step-up'}.get(j['level'])
    bits = [lead] + [b for b in (step, extra) if b]
    return '; '.join(bits) + '.'

ROLE_TYPE = [(r'marketplace', 'marketplace operations'), (r'last.?mile|delivery|courier|driver', 'last-mile / delivery'),
 (r'fulfil|logistics|supply chain|transportation', 'fulfillment & logistics'), (r'trust|safety|integrity', 'trust & safety operations'),
 (r'customer|cx|support|care', 'customer operations'), (r'chief of staff', 'chief of staff'), (r'policy|government|public', 'AI & workforce policy'),
 (r'workforce|future of work|ai ', 'AI transformation / workforce'), (r'strategy', 'strategy & operations')]
def role_type(t):
    for p, n in ROLE_TYPE:
        if re.search(p, t + ' ', re.I): return n
    return 'operations leadership'

# ---------- pipeline ----------
def load_candidates():
    new = json.loads((ROOT/'data'/'sweep_raw.json').read_text())
    old = json.loads((ROOT.parent/'dashboard'/'jobs.json').read_text())['jobs']
    allj = {}
    for j in old:
        allj[j['jobId']] = {'jobId': j['jobId'], 'title': j['title'], 'company': j['company'], 'location': j['location'],
                            'listedAt': j['listedAt'], 'card_salary': '', 'logo': '', 'src': 'sep23',
                            'old_posted': (j.get('salary_low'), j.get('salary_high')) if j.get('salary_source') == 'posted' else None}
    for jid, c in new.items():
        prev = allj.get(jid, {}); allj[jid] = dict(prev, **c, src='sep26' if not prev else 'both')
    out = []
    for j in allj.values():
        j['title'] = H.unescape(j['title']); j['company'] = H.unescape(j['company'])
        j['company_key'] = co_key(j['company'])
        if age_days(j['listedAt']) > CUTOFF_DAYS: continue
        if SPAM.search(j['company']): continue
        if HARD_OUT.search(j['title']): continue
        lv = level(j['title'])
        if not lv: continue
        if not (STRONG.search(j['title']) or ADJ.search(j['title'])): continue
        if re.search(r'\b(intern|associate director|assistant director|manager)\b', j['title'], re.I) and lv == 'Director' and 'associate director' in j['title'].lower(): continue
        if re.search(r'associate director|assistant director|deputy director', j['title'], re.I): continue
        if j['company_key'] == 'Walmart' and lv == 'Director': continue   # Walmart: Sr Dir+ only
        if not us_loc(j['location']): continue
        j['level'] = lv
        out.append(j)
    # dedupe reposts: same company + title -> keep best geo / newest
    best = {}
    for j in out:
        k = (j['company_key'], re.sub(r'\W+', ' ', j['title'].lower()).strip())
        g = geo(j['location'])[1]
        if k not in best or (g, j['listedAt']) > (geo(best[k]['location'])[1], best[k]['listedAt']): best[k] = j
    return list(best.values())

def main(mode):
    cands = load_candidates()
    print('candidates after filters:', len(cands))
    if mode == 'shortlist':
        ids = []
        for j in cands:
            known = j.get('old_posted') or parse_card_salary(j.get('card_salary'))[1]
            est = estimate(j['company_key'], j['level'])
            # everything needs a page check (salary + still open), prioritise tier cos
            j['geo'] = geo(j['location'])[0]
            ids.append((0 if est else 1, -prob(j)[0], j['jobId']))
        ids.sort()
        (ROOT/'data'/'enrich_ids.txt').write_text('\n'.join(x[-1] for x in ids)); print('enrich ids:', len(ids)); return
    enr = json.loads((ROOT/'data'/'enriched.json').read_text()) if (ROOT/'data'/'enriched.json').exists() else {}
    board, dropped = [], {'closed': 0, 'below_floor': 0, 'no_salary_signal': 0}
    for j in cands:
        e = enr.get(j['jobId'], {})
        if e.get('closed'): dropped['closed'] += 1; continue
        j['desc'] = e.get('desc', ''); j['remote_flag'] = False
        lo = hi = None; src = None
        if e.get('salary_high'): lo, hi, src = e['salary_low'], e['salary_high'], 'posted'
        elif parse_card_salary(j.get('card_salary'))[1]: lo, hi = parse_card_salary(j['card_salary']); src = 'posted'
        elif j.get('old_posted') and j['old_posted'][1]: lo, hi = j['old_posted']; src = 'posted'
        basis = ''
        if src == 'posted':
            if hi < FLOOR: dropped['below_floor'] += 1; continue
        else:
            est = estimate(j['company_key'], j['level'])
            if not est: dropped['no_salary_signal'] += 1; continue
            lo, hi, basis = est; src = 'est'
            if hi < FLOOR: dropped['below_floor'] += 1; continue
        j['geo'] = geo(j['location'])[0]
        p, tags = prob(j)
        board.append({'id': j['jobId'], 'title': j['title'], 'company': j['company_key'], 'company_raw': j['company'], 'location': j['location'],
                      'geo': j['geo'], 'level': j['level'], 'listed': j['listedAt'][:10], 'logo': j.get('logo', ''),
                      'salary_low': int(lo) if lo else None, 'salary_high': int(hi), 'salary_type': src, 'salary_basis': basis,
                      'prob': p, 'why': why_line(j, tags), 'role_type': role_type(j['title']),
                      'link': f"https://www.linkedin.com/jobs/view/{j['jobId']}/"})
    board = [b for b in board if b['prob'] >= 25 or True]
    tier = lambda c: 0 if c in TIER_A or c in TIER_B else 1
    board.sort(key=lambda b: (-b['prob'], tier(b['company']), -b['salary_high']))
    band = lambda p: '75-100' if p >= 75 else '50-75' if p >= 50 else '25-50' if p >= 25 else '<25'
    for b in board: b['band'] = band(b['prob'])
    from collections import Counter
    meta = {'generated': datetime.now().strftime('%Y-%m-%d %H:%M'), 'total': len(board), 'bands': Counter(b['band'] for b in board),
            'posted': sum(b['salary_type'] == 'posted' for b in board), 'est': sum(b['salary_type'] == 'est' for b in board), 'dropped': dropped}
    (ROOT/'data'/'jobs.json').write_text(json.dumps({'meta': meta, 'jobs': board}, indent=1))
    print(json.dumps(meta, indent=1))
    for b in board[:40]: print(b['prob'], '|', b['title'], '|', b['company'], '|', b['location'], '|', b['salary_type'], b['salary_high'])

if __name__ == '__main__': main(sys.argv[1] if len(sys.argv) > 1 else 'final')
