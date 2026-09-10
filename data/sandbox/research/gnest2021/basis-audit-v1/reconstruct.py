from decimal import Decimal as D
from pathlib import Path
import json,hashlib,argparse
parser=argparse.ArgumentParser(description='Reconstruct finite printed GNEST basis arithmetic; no source download or model calls.')
parser.add_argument('--output-directory',type=Path,required=True)
parser.add_argument('--source-pdf',type=Path,help='Optional privately supplied source for SHA verification, never copied')
args=parser.parse_args()
P=args.output_directory
P.mkdir(parents=True,exist_ok=True)
source_sha='3b49eae9d37fb2fab1c9097b2c5b2606e9ecbfe60e52f639f6e9ae637b78d536'
if args.source_pdf is not None:
    if hashlib.sha256(args.source_pdf.read_bytes()).hexdigest()!=source_sha:
        raise ValueError('source PDF differs from visually audited accepted manuscript')
feed=list(map(D,['.2947','.0391','.1262','.0343','.0338']))
solid570=list(map(D,['.2069','.0134','.0420','.0213','.0344']))
solid960=list(map(D,['.1296','.0028','.0115','.0042','.0221']))
liq=list(map(D,['.5000','.0987','.3001','.0670','.0343']))
y570=list(map(D,['.6919','.2917','.0041','.0100','.0016','.0007']))
y960=list(map(D,['.5687','.2917','.0588','.0183','.0026','.0106']))
gas=[list(map(D,['.4288','0','.5712','0','0'])),list(map(D,['.2729','0','.7271','0','0'])),list(map(D,['.7487','.2513','0','0','0'])),list(map(D,['0','1','0','0','0']))]
r={'basis':'printed decimals, not independent instrument data','feed_CHONS_sum':str(sum(feed)),'implied_unassigned_ash_fraction':str(1-sum(feed)),'liquid_CHONS_sum':str(sum(liq)),'solid570_CHONS_sum':str(sum(solid570)),'solid960_CHONS_sum':str(sum(solid960)),'rows':[]}
for T,y,solid in [(570,y570,solid570),(960,y960,solid960)]:
 for i,el in enumerate('CHONS'):
  flows=[y[0]*solid[i],y[1]*liq[i]]+[y[j+2]*g[i] for j,g in enumerate(gas)]
  inferred=(feed[i]-flows[0]-sum(flows[2:]))/y[1]
  r['rows'].append({'T_C':T,'element':el,'independent_multiplication_of_printed_y_and_composition':list(map(str,flows)),'sum':str(sum(flows)),'sum_minus_printed_feed':str(sum(flows)-feed[i]),'composition_liquid_required_for_exact_printed_feed_balance':str(inferred),'printed_liquid_composition':str(liq[i])})
# Explicit illustrative interpretation, not a corrected paper energy balance.
ys,yl,yg=y570[0],y570[1],sum(y570[2:]);solidE=ys*D('7.77');gasE=yg*D('12.16');organicE=yl*(1-D('.182'))*D('33.42');net=solidE+gasE+organicE-D('11.3')
r['illustrative_LHV_25C_balance_MJ_kg_feed']={'water_assumption':'18.2 percent of total liquid; explicit interpretation','solid':str(solidE),'gas':str(gasE),'organic_liquid':str(organicE),'sum_minus_printed_feed_LHV11_3':str(net),'printed_inferred_requirement':'2.18','not_reproduction_or_correction':True}
r['source_sha256']=source_sha
(P/'BASIS_ARITHMETIC.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
