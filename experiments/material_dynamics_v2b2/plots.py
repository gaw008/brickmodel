"""Light, static, discrete-data SVG; generation and coordinate checking use CSV."""
import csv
import xml.etree.ElementTree as ET

NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
COLORS=['#2563a0','#d27432','#4a8065','#8a5e9d']
LABEL='无量纲假设研究，非工厂配方或烧成时长预测'


def element(parent,tag,**attrs): return ET.SubElement(parent,'{'+NS+'}'+tag,{k.replace('_','-'):str(v) for k,v in attrs.items()})

def text(root,x,y,value,size=14):
    el=element(root,'text',x=x,y=y,fill='#28394b',font_size=size,font_family='sans-serif'); el.text=value; return el

def canvas(title,binding):
    root=ET.Element('{'+NS+'}svg',{'viewBox':'0 0 1040 640','width':'1040','height':'640','role':'img','data-binding':binding})
    element(root,'rect',x=0,y=0,width=1040,height=640,fill='#fafbfc')
    text(root,55,44,title,24); text(root,55,74,LABEL,14)
    text(root,55,102,'映射 unknown_real_material；仅离散样点，guard=0.005 非全域误差界',13)
    element(root,'line',x1=80,y1=500,x2=900,y2=500,stroke='#a6b0ba')
    element(root,'line',x1=80,y1=130,x2=80,y2=500,stroke='#a6b0ba')
    for value in (0,.25,.5,.75,1):
        y=500-350*value
        element(root,'line',x1=80,y1=y,x2=900,y2=y,stroke='#e3e8ed')
        text(root,32,y+4,str(value),12)
    text(root,55,610,'数值标签不等于 Safety / 生产批准；未发生事件为 null，不绘成零时间柱。',13)
    return root


def csv_rows(path):
    with path.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))


def generate(out,binding_status):
    rows=csv_rows(out/'timeseries.csv'); ids=list(dict.fromkeys(r['scenario_id'] for r in rows))
    selected=[i for i in ('W03','W04','L02','C03') if i in ids] or ids[:4]
    root=canvas('给温反应—输运：局部残碳与芯部氧',binding_status)
    for index,sid in enumerate(selected):
        data=[r for r in rows if r['scenario_id']==sid]
        for field,style in (('f_max','none'),('u_core','5 4')):
            points=' '.join(f'{80+40*float(r["tau"]):.9f},{500-350*float(r[field]):.9f}' for r in data)
            element(root,'polyline',points=points,fill='none',stroke=COLORS[index],stroke_width=1.7,stroke_dasharray=style,data_scenario=sid,data_field=field)
        text(root,85+index*200,545,sid+' 实线 f_max / 虚线 u_core',12)
    text(root,720,580,'共同时间 τ（无量纲）',14)
    ET.ElementTree(root).write(out/'thermal_profiles.svg',encoding='utf-8',xml_declaration=True)
    rows=csv_rows(out/'screening.csv'); root=canvas('离散条件筛选：联合假设包下的局部剩余量',binding_status)
    for r in rows:
        sid=r['scenario_id']; gamma=float(r['Gamma']); f=float(r['f_max'])
        x=80+90*gamma+(8 if r['program_id']=='P_LATE' else -8)
        y=500-350*f; color='#2563a0' if r['bundle_id']=='U0' else '#d27432'
        dot=element(root,'circle',cx=f'{x:.9f}',cy=f'{y:.9f}',r=4,fill=color,data_scenario=sid,data_field='f_max',data_numerical_validation=r['numerical_validation'],data_screening_status=r['screening_status'])
        element(dot,'title').text=sid+' | '+r['screening_status']+' | '+r['numerical_validation']
        text(root,x+6,y-6,sid,10)
    text(root,90,545,'横轴：假设可氧化负荷 Γ；左右轻微偏移仅区分给温程序',13)
    text(root,90,570,'蓝色 U0；橙色 U1/诊断；纵轴 f_max；无连续可行窗填充',13)
    ET.ElementTree(root).write(out/'conditional_screening.svg',encoding='utf-8',xml_declaration=True)


def verify(out):
    checks=0
    ts=csv_rows(out/'timeseries.csv'); sc={r['scenario_id']:r for r in csv_rows(out/'screening.csv')}
    for name in ('thermal_profiles.svg','conditional_screening.svg'):
        root=ET.parse(out/name).getroot()
        for el in root.iter():
            if el.tag.split('}')[-1] not in ('svg','rect','text','line','polyline','circle','title'): raise ValueError('unsafe_svg_tag')
            if any(k.lower().startswith('on') or 'href' in k.lower() for k in el.attrib): raise ValueError('unsafe_svg_attribute')
            if el.tag.endswith('polyline'):
                rs=[r for r in ts if r['scenario_id']==el.get('data-scenario')]; field=el.get('data-field')
                points=[tuple(map(float,p.split(','))) for p in el.get('points').split()]
                if len(points)!=len(rs): raise ValueError('svg_count')
                for (x,y),r in zip(points,rs):
                    if abs(x-(80+40*float(r['tau'])))>1e-6 or abs(y-(500-350*float(r[field])))>1e-6: raise ValueError('svg_coordinate')
                    checks+=1
            if el.tag.endswith('circle'):
                r=sc[el.get('data-scenario')]; x=80+90*float(r['Gamma'])+(8 if r['program_id']=='P_LATE' else -8); y=500-350*float(r['f_max'])
                if abs(float(el.get('cx'))-x)>1e-6 or abs(float(el.get('cy'))-y)>1e-6: raise ValueError('svg_coordinate')
                if el.get('data-numerical-validation')!=r['numerical_validation'] or el.get('data-screening-status')!=r['screening_status']: raise ValueError('svg_status')
                checks+=1
    return {'passed':True,'coordinate_checks':checks,'pixel_or_CJK_rendering_verified':False}
