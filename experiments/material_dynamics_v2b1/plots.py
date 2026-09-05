"""Light Chinese SVGs drawn only from exported discrete records (no smoothing)."""
import csv
from html import escape
import json
from pathlib import Path

DISCLAIMER = "无量纲机制情景，非工厂配方/烧成时长预测"
LABELS = {"base":"基准", "reaction_slow":"慢反应", "reaction_fast":"快反应", "carbon_low":"低碳库存",
          "carbon_high":"高碳库存", "film_weak":"弱膜传递", "film_strong":"强膜传递", "sealed":"密闭",
          "finite_small":"小有限氧库", "finite_medium":"中有限氧库", "finite_large":"大有限氧库", "no_reaction":"无反应"}
COLORS = {"u_core":"#2166a5", "u_surface":"#58a5c4", "carbon_mean":"#b76b28", "carbon_max":"#8d405b"}


def text(x,y,value,size=15,fill="#293b4a",extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" {extra}>{escape(str(value))}</text>'


def header(title,height):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="1240" height="{height}" viewBox="0 0 1240 {height}" role="img">',
            f'<title>{escape(title)}</title><desc>{DISCLAIMER}；折线直接连接导出采样点。</desc>',
            '<rect width="1240" height="100%" fill="#fafbf9"/>',
            '<g font-family="Noto Sans CJK SC,Source Han Sans SC,Microsoft YaHei,sans-serif">',
            text(46,46,title,25), text(46,77,DISCLAIMER,15,"#53636e")]


def event_label(summary,percent):
    value = summary[f"t_burn{percent}"]
    if value is not None:
        return f"τ = {value:.3f}"
    return "未达：氧预算不足" if summary[f"t_burn{percent}_status"] == "oxygen_budget_limited" else "观察期内未达到"


def draw(out):
    out = Path(out)
    summaries = json.loads((out/"summary.json").read_text(encoding="utf-8"))["scenarios"]
    lookup = {s["scenario_id"]:s for s in summaries}
    with (out/"timeseries.csv").open(encoding="utf-8") as stream:
        series = list(csv.DictReader(stream))
    selected = [sid for sid in ("base","reaction_fast","finite_small","sealed") if sid in lookup]
    if not selected:
        selected = list(lookup)[:4]
    svg = header("供氧与残碳：反应近停，不等于库存完成",850)
    for i, metric in enumerate(COLORS):
        x = 50+i*285
        label = {"u_core":"芯区 O₂（首单元平均）", "u_surface":"表面 O₂（Robin重建）",
                 "carbon_mean":"平均剩余碳 f", "carbon_max":"最大局部剩余碳 f"}[metric]
        svg += [f'<line x1="{x}" x2="{x+23}" y1="108" y2="108" stroke="{COLORS[metric]}" stroke-width="3"/>',text(x+31,113,label,14)]
    for panel,sid in enumerate(selected):
        left, top = 78+(panel%2)*600, 175+(panel//2)*310
        width, height = 505, 230
        summary = lookup[sid]
        horizon = summary["config"]["tau_end"]
        svg.append(text(left,top-24,f'{LABELS.get(sid,sid)} · {sid}',18))
        for yvalue in (0,.25,.5,.75,1):
            y = top+height*(1-yvalue)
            svg += [f'<line x1="{left}" x2="{left+width}" y1="{y}" y2="{y}" stroke="#e1e7e7"/>',
                    text(left-12,y+5,f"{yvalue:g}",12,extra='text-anchor="end"')]
        for step in range(5):
            x = left+width*step/4
            svg.append(text(x,top+height+21,f"{horizon*step/4:g}",12,extra='text-anchor="middle"'))
        svg.append(text(left+width-8,top+height+42,"无量纲时间 τ",12,extra='text-anchor="end"'))
        rows = [r for r in series if r["scenario_id"] == sid]
        for metric,color in COLORS.items():
            points = " ".join(f'{left+width*float(r["tau"])/horizon:.4f},{top+height*(1-float(r[metric])):.4f}' for r in rows)
            dash = 'stroke-dasharray="6 4"' if metric in ("u_surface","carbon_max") else ""
            svg.append(f'<polyline data-scenario="{escape(sid)}" data-metric="{metric}" data-x0="{left}" data-y0="{top}" data-width="{width}" data-height="{height}" points="{points}" fill="none" stroke="{color}" stroke-width="2" {dash}/>')
    svg += [text(46,797,"f 为可氧化固体碳库存比例，不是 TG 残渣；芯区为单元平均，不是精确 ξ=0 点值。",14),
            text(46,825,"95% / 99% 仅为数值诊断阈值；缺氧停反应不能触发完成事件。",14,"#53636e"),'</g></svg>']
    (out/"oxygen_carbon_trajectories.svg").write_text("\n".join(svg)+"\n",encoding="utf-8")

    height = 270+len(summaries)*42
    svg = header(f"{len(summaries)}个离散情景：残碳与诊断事件",height)
    svg += [text(46,117,"情景 / 参数变化",15),text(350,117,"终点残碳：平均 / 最大局部",15),
            text(842,117,"95% 平均完成",15),text(1036,117,"99% 平均完成",15)]
    bar_x,bar_width = 350,420
    for frac in (0,.25,.5,.75,1):
        x = bar_x+bar_width*frac
        svg += [text(x,142,f"{frac:g}",12,extra='text-anchor="middle"'),
                f'<line x1="{x}" x2="{x}" y1="152" y2="{157+len(summaries)*42}" stroke="#e0e6e5"/>']
    for index,summary in enumerate(summaries):
        y = 176+index*42
        sid, cfg = summary["scenario_id"], summary["config"]
        svg += [text(46,y,f'{LABELS.get(sid,sid)} · {sid}',14),
                text(46,y+15,f'K={cfg["K"]:g}  Γ={cfg["Gamma"]:g}  Bi={cfg["Bi"]:g}  {cfg["boundary_mode"]}',10,"#61717a")]
        for offset,metric in ((-9,"carbon_mean"),(1,"carbon_max")):
            value = summary["final"][metric]
            svg.append(f'<rect data-scenario="{escape(sid)}" data-metric="{metric}" data-value="{value:.17g}" x="{bar_x}" y="{y+offset}" width="{bar_width*value:.5f}" height="7" fill="{COLORS[metric]}"/>')
        if cfg["boundary_mode"] in ("finite","sealed"):
            x = bar_x+bar_width*(1-summary["budget"]["max_conversion_upper_bound"])
            svg.append(f'<line x1="{x}" x2="{x}" y1="{y-13}" y2="{y+10}" stroke="#293b4a" stroke-width="2"/>')
        svg += [text(842,y,event_label(summary,95),13),text(1036,y,event_label(summary,99),13)]
    footer = height-60
    svg += [text(46,footer,"棕色：平均残碳；紫色：最大局部残碳；黑短线：封闭氧库存给出的平均残碳下界。",14),
            text(46,footer+24,"τ 为各情景的无量纲时间；有限库只在体内与封闭外库间交换，不代表向环境排放。",14),
            text(46,footer+48,"阈值非生产标准；图中没有插值构造连续可行域。完整局部完成时间见 summary.json。",13,"#53636e"),'</g></svg>']
    (out/"scenario_diagnostics.svg").write_text("\n".join(svg)+"\n",encoding="utf-8")
