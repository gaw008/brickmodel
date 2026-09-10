"""Independent passive JSON/Fraction check: no model imports or provider calls."""
import hashlib,itertools,json,re,time
from fractions import Fraction as F
from pathlib import Path
BASE=Path('/Users/wanggaoying/Desktop/brickmodel-github')
OUT=Path('/private/tmp/brick-source-net-roots-v1/physics')
NEW=Path('/private/tmp/brick-source-net-roots-v1/root/native-roots-result.json')
OLD=BASE/'docs/sandbox/research/source-net-panel-v1/native-replay-result.json'
NATIVE=BASE/'docs/sandbox/research/exact-source-column-v1/native-result.json'
SOURCE=BASE/'src/sludge_sandbox/source_net_roots.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(x):
    if isinstance(x,list):return [decode(y) for y in x]
    if isinstance(x,dict):
        if set(x)=={'numerator','denominator'}:return F(x['numerator'],x['denominator'])
        if set(x)=={'type','fields'}:return decode(x['fields'])
        return {k:decode(v) for k,v in x.items()}
    return x
count=0
def check(ok,label):
    global count
    count+=1
    if not ok:raise AssertionError(label)
t0=time.monotonic()
check(sha(NEW)=='b1f45c66d896528e1ffe22fdeaed71cee85a6612794d51bf5c2091cd29238b87','new SHA')
check(sha(OLD)=='b1652b5b9c0e6887592bee70a0927637df78ea4213eb1411c4ffc87bd274a643','panel SHA')
check(sha(NATIVE)=='033dccd09ed268eeb2ce9570a37d52f66d4eb5da18b68f2f44a89bd01054c4f2','native SHA')
check(sha(SOURCE)=='022912c0a26c4fba15fe1071880b5cc9b2e41c3cf3e0a50f190e87fb063ee6f2','source SHA')
a=json.loads(NEW.read_text());b=json.loads(OLD.read_text());native=json.loads(NATIVE.read_text())
check(a['status']==b['status']=='completed','terminal statuses')
check(a['input_sha256']==b['input_sha256']==sha(NATIVE),'input binding')
check(a['audit_sha256']==b['audit_sha256'],'audit binding')
check(len(a['trials'])==len(b['trials'])==7,'seven trials')
minima=[];statuses=[];vertices=0
for k,(raw,priorraw) in enumerate(zip(a['trials'],b['trials'])):
    t,p=decode(raw),decode(priorraw);o=t['order'];h=F(t['original_trial']['h']);start=F(t['original_trial']['start'])
    for key in ('capture_indices','original_trial','sample_bindings'):
        check(raw[key]==priorraw[key],f'{k} exact raw {key}')
    c0,cm=t['capture_indices'];cap=decode(native['captures'][c0]);mid=decode(native['captures'][cm])
    check(t['operator_identity']==cap['evaluation']['operator_identity']==mid['evaluation']['operator_identity'],f'{k} operator')
    check(t['start']==cap['time'] and t['start']['seconds']==start,f'{k} start')
    check(t['upper']['seconds']==start+h==F(t['original_trial']['end']),f'{k} upper')
    check(mid['time']['seconds']==start+h/2,f'{k} midpoint')
    check(t['sample_bindings'][2]==t['upper'],f'{k} upper binding')
    check(raw['order']['fields']['polynomials']==priorraw['inventory_polynomials'],f'{k} exact raw coefficients')
    check(o['duration']==h,f'{k} duration')
    check([(q['family'],q['cell'],q['index']) for q in o['polynomials']]==[('liquid' if j==0 else 'gas',i,j) for i in range(3) for j in range(4)],f'{k} all labels')
    check(len(o['exclusions'])==12,f'{k} exclusions count')
    check(o['status']=='no_roots' and o['complete'] is True and o['roots']==[] and o['earliest_labels']==[] and o['zero_initial_labels']==[] and o['refinement_level']==0,f'{k} no fabricated root')
    check(o['qualification']=='numerical_first_zero_order_not_physical_event_admission',f'{k} qualification')
    check(t['material_qualified'] is False and t['physical_trajectory_or_event_admitted'] is False,f'{k} no admission')
    for j,(q,e) in enumerate(zip(o['polynomials'],o['exclusions'])):
        n,r,s=q['initial'],q['linear'],q['quadratic'];v=lambda x:n+r*x+s*x*x
        candidates=[(v(F(0)),F(0)),(v(h),h)]
        if s>0 and 0 < -r/(2*s) < h:
            x=-r/(2*s);candidates.append((v(x),x));vertices+=1
        value,at=min(candidates,key=lambda z:z[0]);minima.append(value)
        check(n>0,f'{k}/{j} no omitted initial zero')
        check(e['polynomial']==q and e['duration']==h,f'{k}/{j} exclusion binding')
        check(e['minimum']==value and e['minimum_time']==at and value>0,f'{k}/{j} positive exact minimum')
        check(p['minima'][j]==[q['family'],q['cell'],q['index'],value,at],f'{k}/{j} prior minimum')
    statuses.append(t['original_trial']['status'])
# Verify annotation-only delta by finding exactly six removed return annotations.
src=SOURCE.read_text();matches=list(re.finditer(r' -> [^:\n]+(?=:)',src));found=[]
for chosen in itertools.combinations(range(len(matches)),6):
    changed=src
    for i in reversed(chosen):
        m=matches[i];changed=changed[:m.start()]+changed[m.end():]
    if hashlib.sha256(changed.encode()).hexdigest()=='c0389459f403d9d298e02808ec8432ad377c824283af68c02f071930af05b215':found.append(chosen)
check(len(found)==1,'exactly six annotations reproduce c038 source bytes')
result={'status':'passed','checks':count,'trials':7,'inventories':len(minima),'interior_convex_vertices':vertices,'minimum_inventory':str(min(minima)),'prior_statuses':statuses,'annotation_delta_six_match_indices':found,'hashes':{str(p):sha(p) for p in (NEW,OLD,NATIVE,SOURCE)},'elapsed_s':time.monotonic()-t0,'scope':'Saved polynomial numerical no-root evidence only; no physical trajectory/event or material validation; no EOS calls or suite rerun.'}
(OUT/'NATIVE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
