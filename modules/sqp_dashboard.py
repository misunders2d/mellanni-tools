import json
import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def render_sqp_dashboard(df_summary):
    st.markdown(
        """
    <style>
    #MainMenu { visibility: visible; }
    footer    { visibility: hidden; }
    .block-container { padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    [data-testid="stFileUploader"] { padding: 1rem 2rem 0; }
    [data-testid="stFileUploader"] label { display: none; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    def parse(f):
        pct_cols = [
            c
            for c in f.columns
            if any(k in c for k in ["Share", "Rate", "CTR", "Conversion"])
        ]
        for c in pct_cols:
            if pd.api.types.is_float_dtype(f[c]):
                f[c] = f[c] * 100
        return f

    df = parse(df_summary)
    # elif os.path.exists("2026-02-27T10-51_export.csv"):
    #     df = parse("2026-02-27T10-51_export.csv")
    # else:
    #     st.markdown(
    #         """
    #     <div style="display:flex;align-items:center;justify-content:center;height:70vh">
    #       <p style="font-family:monospace;color:#999;font-size:.8rem;letter-spacing:.2em">UPLOAD CSV TO BEGIN</p>
    #     </div>""",
    #         unsafe_allow_html=True,
    #     )
    #     st.stop()
    #
    r = df.iloc[0].to_dict()
    data_json = json.dumps(r)

    HTML = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

      * {{ margin:0; padding:0; box-sizing:border-box; }}

      body {{
        background: #f8f9fc;
        color: #111827;
        font-family: 'Inter', sans-serif;
        overflow-x: hidden;
      }}

      #dash {{
        padding: 28px 36px 56px;
        max-width: 1560px;
        margin: 0 auto;
      }}

      .hdr {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-bottom: 28px;
        padding-bottom: 20px;
        border-bottom: 1px solid #e5e7eb;
      }}
      .hdr-title {{
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.04em;
        color: #111827;
        line-height: 1;
      }}
      .hdr-title span {{ color: #4f46e5; }}
      .hdr-meta {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #6b7280;
        text-align: right;
        line-height: 1.8;
      }}

      .sec {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        letter-spacing: .12em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 12px;
        margin-top: 28px;
      }}

      .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(8,1fr);
        gap: 10px;
      }}
      .kpi {{
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px 16px 14px;
        transition: box-shadow .2s, transform .15s;
        position: relative;
        overflow: hidden;
      }}
      .kpi:hover {{ transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,.08); }}
      .kpi::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        background: var(--c);
      }}
      .kpi-lbl {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.58rem;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 8px;
      }}
      .kpi-val {{
        font-size: 1.6rem;
        font-weight: 700;
        color: #111827;
        letter-spacing: -.03em;
        line-height: 1;
      }}
      .kpi-sub {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.58rem;
        color: var(--c);
        margin-top: 5px;
        font-weight: 600;
      }}
      .kpi-bar {{ margin-top:10px; height:3px; background:#f3f4f6; border-radius:2px; overflow:hidden; }}
      .kpi-fill {{ height:100%; background:var(--c); border-radius:2px; width:0; transition:width 1.2s cubic-bezier(.22,1,.36,1); }}

      .row2 {{ display:grid; grid-template-columns:3fr 2fr; gap:16px; }}
      .row3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; }}

      .panel {{
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px 22px;
      }}
      .panel-ttl {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.62rem;
        letter-spacing: .1em;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 14px;
      }}

      #tip {{
        position: fixed;
        background: #1f2937;
        border-radius: 8px;
        padding: 8px 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem;
        color: #f9fafb;
        pointer-events: none;
        opacity: 0;
        transition: opacity .12s;
        z-index: 9999;
        line-height: 1.7;
        white-space: nowrap;
        box-shadow: 0 4px 16px rgba(0,0,0,.2);
      }}

      svg text {{ font-family:'Inter',sans-serif; }}
      .tick text {{ fill:#6b7280 !important; font-size:11px; font-family:'JetBrains Mono',monospace; }}
      .domain {{ stroke:#e5e7eb !important; }}
      .tick line {{ stroke:#f3f4f6 !important; }}
    </style>
    </head>
    <body>
    <div id="dash">

      <div class="hdr">
        <div class="hdr-title">Search <span>Performance</span></div>
        <div class="hdr-meta" id="hdr-meta"></div>
      </div>

      <div class="sec">Core Metrics</div>
      <div class="kpi-grid" id="kpi-grid"></div>

      <div class="sec">Purchase Funnel &amp; Market Share</div>
      <div class="row2">
        <div class="panel">
          <div class="panel-ttl">Total Market vs Your ASINs — All Stages</div>
          <svg id="svg-funnel"></svg>
        </div>
        <div class="panel">
          <div class="panel-ttl">ASIN Share of Market</div>
          <svg id="svg-radar"></svg>
        </div>
      </div>

      <div class="sec">Rates, Prices &amp; Fulfilment</div>
      <div class="row3">
        <div class="panel">
          <div class="panel-ttl">CTR &amp; Conversion — Market vs ASINs</div>
          <svg id="svg-rates"></svg>
        </div>
        <div class="panel">
          <div class="panel-ttl">Median Price by Stage</div>
          <svg id="svg-prices"></svg>
        </div>
        <div class="panel">
          <div class="panel-ttl">Shipping Speed Mix</div>
          <svg id="svg-ship"></svg>
        </div>
      </div>

      <div class="sec">Opportunity Gap</div>
      <div class="row3">
        <div class="panel">
          <div class="panel-ttl">Impression Capture</div>
          <svg id="svg-d1"></svg>
          <div id="missed-badge"></div>
        </div>
        <div class="panel">
          <div class="panel-ttl">Click Share</div>
          <svg id="svg-d2"></svg>
        </div>
        <div class="panel">
          <div class="panel-ttl">Revenue Captured vs Lost Sales</div>
          <svg id="svg-d3"></svg>
          <div id="rev-badges"></div>
        </div>
      </div>

    </div>
    <div id="tip"></div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <script>
    const RAW = {data_json};
    const d = {{
      startDate:  RAW.startDate || RAW['\\ufeffstartDate'],
      endDate:    RAW.endDate,
      period:     RAW.period,
      mkt:        RAW.marketplaces,
      sqv:        +RAW.searchQueryVolume,
      tImp:       +RAW.totalQueryImpressionCount,
      aImp:       +RAW.asinImpressionCount,
      aImpShare:  +RAW.asinImpressionShare,
      tClk:       +RAW.totalClickCount,
      aClk:       +RAW.asinClickCount,
      aClkShare:  +RAW.asinClickShare,
      tCTR:       +RAW.totalCTR,
      aCTR:       +RAW.asinCTR,
      tCrt:       +RAW.totalCartAddCount,
      aCrt:       +RAW.asinCartAddCount,
      aCrtShare:  +RAW.asinCartAddShare,
      tPur:       +RAW.totalPurchaseCount,
      aPur:       +RAW.asinPurchaseCount,
      aPurShare:  +RAW.asinPurchaseShare,
      tConv:      +RAW.totalConversion,
      aConv:      +RAW.asinConversion,
      tMedClkPx:  +RAW.totalMedianClickPrice_amount,
      aMedClkPx:  +RAW.asinMedianClickPrice_amount,
      tMedCrtPx:  +RAW.totalMedianCartAddPrice_amount,
      aMedCrtPx:  +RAW.asinMedianCartAddPrice_amount,
      tMedPurPx:  +RAW.totalMedianPurchasePrice_amount,
      aMedPurPx:  +RAW.asinMedianPurchasePrice_amount,
      sdClk: +RAW.totalSameDayShippingClickCount,
      odClk: +RAW.totalOneDayShippingClickCount,
      tdClk: +RAW.totalTwoDayShippingClickCount,
      sdCrt: +RAW.totalSameDayShippingCartAddCount,
      odCrt: +RAW.totalOneDayShippingCartAddCount,
      tdCrt: +RAW.totalTwoDayShippingCartAddCount,
      sdPur: +RAW.totalSameDayShippingPurchaseCount,
      odPur: +RAW.totalOneDayShippingPurchaseCount,
      tdPur: +RAW.totalTwoDayShippingPurchaseCount,
      missedImp:  +RAW.asinMissedImpressions,
      lostSales:  +RAW.asinLostSales,
      asinsShown: +RAW['ASINs shown'],
    }};
    const estRev = d.aPur * d.aMedPurPx;

    // Palette — saturated colors on white bg, each from a different hue family
    const C = {{
      blue:    '#2563eb',
      indigo:  '#4f46e5',
      cyan:    '#0891b2',
      green:   '#16a34a',
      teal:    '#0d9488',
      amber:   '#d97706',
      rose:    '#e11d48',
      purple:  '#7c3aed',
      mktBar:  '#2563eb',   // market  = blue
      asinBar: '#ea580c',   // ASINs   = orange
      price1:  '#0891b2',   // market prices = cyan
      price2:  '#d97706',   // ASIN prices   = amber
      shipSD:  '#16a34a',   // same day = green
      ship1D:  '#ea580c',   // 1-day    = orange
      ship2D:  '#2563eb',   // 2-day    = blue
      donut1:  '#4f46e5',
      donut2:  '#16a34a',
      donut3:  '#d97706',
      lost:    '#e11d48',
      bg:      '#f3f4f6',
      labelText: '#6b7280',
      axisLine:  '#e5e7eb',
    }};

    const fmtN = d3.format(',');
    const fmtK = v => v >= 1e6 ? (v/1e6).toFixed(1)+'M' : v >= 1e3 ? (v/1e3).toFixed(0)+'K' : String(Math.round(v));
    const fmtP = v => v.toFixed(2) + '%';
    const fmtD = v => '$' + v.toFixed(2);

    const tip = d3.select('#tip');
    const showTip = (html, ev) =>
      tip.html(html).style('opacity',1)
         .style('left',(ev.clientX+14)+'px')
         .style('top',(ev.clientY-10)+'px');
    const hideTip = () => tip.style('opacity',0);

    document.getElementById('hdr-meta').innerHTML =
      `${{d.startDate}} → ${{d.endDate}}<br>${{d.period}} · ${{d.mkt}}`;

    // ── KPI CARDS ─────────────────────────────────────────────────────────────────
    const KPIS = [
      {{ l:'Search Volume', v:fmtN(d.sqv),    s:'queries',                   c:C.blue,   p:65 }},
      {{ l:'Impressions',   v:fmtK(d.tImp),   s:'total market',              c:C.indigo, p:80 }},
      {{ l:'ASIN Impr.',    v:fmtK(d.aImp),   s:fmtP(d.aImpShare)+' share', c:C.cyan,   p:Math.min(d.aImpShare*8,100) }},
      {{ l:'Total Clicks',  v:fmtN(d.tClk),   s:'CTR '+fmtP(d.tCTR),        c:C.green,  p:Math.min(d.tCTR*8,100) }},
      {{ l:'ASIN Clicks',   v:fmtN(d.aClk),   s:fmtP(d.aClkShare)+' share', c:C.teal,   p:Math.min(d.aClkShare*8,100) }},
      {{ l:'Cart Adds',     v:fmtN(d.aCrt),   s:fmtP(d.aCrtShare)+' share', c:C.amber,  p:Math.min(d.aCrtShare*8,100) }},
      {{ l:'Purchases',     v:fmtN(d.aPur),   s:fmtP(d.aConv)+' conv.',     c:C.rose,   p:Math.min(d.aPurShare*8,100) }},
      {{ l:'Lost Sales',    v:'$'+fmtN(Math.round(d.lostSales)), s:'missed revenue', c:C.purple, p:Math.min(d.lostSales/(d.lostSales+estRev+.01)*100,100) }},
    ];

    const grid = document.getElementById('kpi-grid');
    KPIS.forEach(k => {{
      const el = document.createElement('div');
      el.className = 'kpi';
      el.style.setProperty('--c', k.c);
      el.innerHTML = `
        <div class="kpi-lbl">${{k.l}}</div>
        <div class="kpi-val">${{k.v}}</div>
        <div class="kpi-sub">${{k.s}}</div>
        <div class="kpi-bar"><div class="kpi-fill" data-p="${{k.p}}" style="background:${{k.c}}"></div></div>`;
      grid.appendChild(el);
    }});
    requestAnimationFrame(() => {{
      document.querySelectorAll('.kpi-fill').forEach(el =>
        setTimeout(() => el.style.width = el.dataset.p + '%', 80));
    }});

    // ── FUNNEL ────────────────────────────────────────────────────────────────────
    (function() {{
      const W = document.getElementById('svg-funnel').parentElement.clientWidth - 44;
      const H = 270;
      const m = {{t:8,r:16,b:28,l:100}};
      const iW = W-m.l-m.r, iH = H-m.t-m.b;
      const svg = d3.select('#svg-funnel').attr('width',W).attr('height',H);
      const g   = svg.append('g').attr('transform',`translate(${{m.l}},${{m.t}})`);

      const stages = ['Impressions','Clicks','Cart Adds','Purchases'];
      const tVals  = [d.tImp, d.tClk, d.tCrt, d.tPur];
      const aVals  = [d.aImp, d.aClk, d.aCrt, d.aPur];

      const xScale = d3.scaleLog().domain([1, d3.max(tVals)*1.2]).range([0,iW]).clamp(true);
      const yScale = d3.scaleBand().domain(stages).range([0,iH]).padding(.4);
      const bh     = yScale.bandwidth() * .46;

      [1e2,1e3,1e4,1e5].forEach(v => {{
        g.append('line')
          .attr('x1',xScale(v)).attr('x2',xScale(v)).attr('y1',0).attr('y2',iH)
          .attr('stroke','#f3f4f6').attr('stroke-dasharray','4,3');
      }});

      g.append('g').attr('transform',`translate(0,${{iH}})`)
        .call(d3.axisBottom(xScale).ticks(4,',.0s').tickSize(0).tickPadding(8))
        .select('.domain').remove();

      g.append('g').call(d3.axisLeft(yScale).tickSize(0).tickPadding(10))
        .select('.domain').remove();
      g.selectAll('.tick text').style('fill','#374151').style('font-size','11px');

      function drawSeries(vals, color, offset, name) {{
        g.selectAll(null).data(stages).enter().append('rect')
          .attr('x',0).attr('y',(_,i)=>yScale(stages[i])+offset)
          .attr('width',iW).attr('height',bh)
          .attr('fill','#f9fafb').attr('rx',3);

        const bars = g.selectAll(null).data(vals).enter().append('rect')
          .attr('x',0).attr('y',(_,i)=>yScale(stages[i])+offset)
          .attr('width',0).attr('height',bh)
          .attr('fill',color).attr('rx',3).attr('opacity',.9);

        bars.transition().duration(900).delay((_,i)=>i*70).ease(d3.easeCubicOut)
          .attr('width', v => xScale(Math.max(v,1)));

        g.selectAll(null).data(vals).enter().append('text')
          .attr('x', v => xScale(Math.max(v,1))+6)
          .attr('y', (_,i) => yScale(stages[i])+offset+bh/2+4)
          .text(v=>fmtK(v))
          .attr('fill',color).attr('font-size',10).attr('font-weight','600')
          .attr('font-family','JetBrains Mono,monospace').attr('opacity',0)
          .transition().delay(1000).duration(250).attr('opacity',1);

        bars.on('mousemove',(ev,v)=>showTip(`${{name}}: ${{stages[vals.indexOf(v)]}}<br>${{fmtN(v)}}`,ev))
            .on('mouseleave',hideTip);
      }}

      drawSeries(tVals, C.mktBar,  0,    'Total Market');
      drawSeries(aVals, C.asinBar, bh+3, 'Your ASINs');

      const leg = svg.append('g').attr('transform',`translate(${{m.l}},0)`);
      [['Total Market',C.mktBar],['Your ASINs',C.asinBar]].forEach(([n,c],i) => {{
        leg.append('rect').attr('x',i*130).attr('y',4).attr('width',10).attr('height',10).attr('fill',c).attr('rx',2);
        leg.append('text').attr('x',i*130+15).attr('y',13).text(n)
          .attr('fill','#374151').attr('font-size',11).attr('font-family','Inter,sans-serif');
      }});
    }})();

    // ── RADAR ─────────────────────────────────────────────────────────────────────
    (function() {{
      const cont = document.getElementById('svg-radar').parentElement;
      const size = cont.clientWidth - 44;
      const svg  = d3.select('#svg-radar').attr('width',size).attr('height',size);
      const g    = svg.append('g').attr('transform',`translate(${{size/2}},${{size/2+4}})`);

      const R = size * .33;
      const axes = [
        {{label:'Impressions', val:d.aImpShare}},
        {{label:'Clicks',      val:d.aClkShare}},
        {{label:'Cart Adds',   val:d.aCrtShare}},
        {{label:'Purchases',   val:d.aPurShare}},
      ];
      const N = axes.length;
      const maxV = Math.max(...axes.map(a=>a.val)) * 1.6 || 1;
      const ang = i => i*2*Math.PI/N - Math.PI/2;
      const rS  = d3.scaleLinear().domain([0,maxV]).range([0,R]);

      [.25,.5,.75,1].forEach(t => {{
        const pts = d3.range(N+1).map(i => {{
          const a=ang(i%N), r=R*t;
          return [Math.cos(a)*r, Math.sin(a)*r];
        }});
        g.append('polygon').attr('points',pts.map(p=>p.join(',')).join(' '))
         .attr('fill', t===1?'#f8f9fc':'none')
         .attr('stroke','#e5e7eb').attr('stroke-width',1);
      }});

      axes.forEach((_,i) => {{
        g.append('line').attr('x1',0).attr('y1',0)
         .attr('x2',Math.cos(ang(i))*R).attr('y2',Math.sin(ang(i))*R)
         .attr('stroke','#e5e7eb');
      }});

      const pts = axes.map((ax,i) => {{
        const a=ang(i), r=rS(ax.val);
        return [Math.cos(a)*r, Math.sin(a)*r];
      }});

      g.append('polygon').attr('points',pts.map(p=>p.join(',')).join(' '))
       .attr('fill','rgba(79,70,229,0.15)').attr('stroke',C.indigo).attr('stroke-width',2)
       .attr('stroke-linejoin','round').attr('opacity',0)
       .transition().duration(800).attr('opacity',1);

      axes.forEach((ax,i) => {{
        const [x,y]=pts[i];
        const lr=R*1.22, lx=Math.cos(ang(i))*lr, ly=Math.sin(ang(i))*lr;
        g.append('circle').attr('cx',x).attr('cy',y).attr('r',5)
         .attr('fill',C.indigo).attr('stroke','#fff').attr('stroke-width',2)
         .on('mousemove',ev=>showTip(`${{ax.label}}: ${{fmtP(ax.val)}} share`,ev))
         .on('mouseleave',hideTip);
        g.append('text').attr('x',lx).attr('y',ly+4).text(ax.label)
         .attr('text-anchor','middle').attr('fill','#374151')
         .attr('font-size',11).attr('font-family','Inter,sans-serif').attr('font-weight','500');
        g.append('text').attr('x',x*1.35).attr('y',y*1.35+4).text(fmtP(ax.val))
         .attr('text-anchor','middle').attr('fill',C.indigo)
         .attr('font-size',10).attr('font-family','JetBrains Mono,monospace').attr('font-weight','600');
      }});
    }})();

    // ── GROUPED BAR ───────────────────────────────────────────────────────────────
    function groupedBar(svgId, cats, series, yFmt) {{
      const W = document.getElementById(svgId).parentElement.clientWidth - 44;
      const H = 200;
      const m = {{t:8,r:8,b:36,l:44}};
      const iW=W-m.l-m.r, iH=H-m.t-m.b;
      const svg=d3.select('#'+svgId).attr('width',W).attr('height',H);
      const g=svg.append('g').attr('transform',`translate(${{m.l}},${{m.t}})`);

      const maxV = d3.max(series.flatMap(s=>s.vals)) * 1.28;
      const keys = series.map(s=>s.key);
      const x0=d3.scaleBand().domain(cats).range([0,iW]).padding(.3);
      const x1=d3.scaleBand().domain(keys).range([0,x0.bandwidth()]).padding(.1);
      const y=d3.scaleLinear().domain([0,maxV]).range([iH,0]);

      g.append('g').attr('transform',`translate(0,${{iH}})`)
       .call(d3.axisBottom(x0).tickSize(0).tickPadding(8)).select('.domain').remove();
      g.selectAll('.tick text').attr('fill','#374151').attr('font-size',11);

      g.append('g').call(d3.axisLeft(y).ticks(4).tickFormat(yFmt).tickSize(-iW).tickPadding(6))
       .call(ax=>ax.select('.domain').remove())
       .call(ax=>ax.selectAll('.tick line').attr('stroke','#f3f4f6').attr('stroke-dasharray','3,3'));
      g.selectAll('.tick text').attr('fill','#6b7280').attr('font-size',10);

      series.forEach(s => {{
        g.selectAll(null).data(cats).enter().append('rect')
          .attr('x',(_,i)=>x0(cats[i])+x1(s.key))
          .attr('y',iH).attr('width',x1.bandwidth()).attr('height',0)
          .attr('fill',s.color).attr('rx',3)
          .on('mousemove',(ev,c)=>showTip(`${{s.lbl}}: ${{c}}<br>${{yFmt(s.vals[cats.indexOf(c)])}}`,ev))
          .on('mouseleave',hideTip)
          .transition().duration(800).delay((_,i)=>i*60).ease(d3.easeCubicOut)
          .attr('y',(_,i)=>y(s.vals[i])).attr('height',(_,i)=>iH-y(s.vals[i]));

        g.selectAll(null).data(cats).enter().append('text')
          .attr('x',(_,i)=>x0(cats[i])+x1(s.key)+x1.bandwidth()/2)
          .attr('y',(_,i)=>y(s.vals[i])-5)
          .attr('text-anchor','middle').attr('fill',s.color)
          .attr('font-size',10).attr('font-weight','600').attr('font-family','JetBrains Mono,monospace')
          .text((_,i)=>yFmt(s.vals[i])).attr('opacity',0)
          .transition().delay(900).duration(250).attr('opacity',1);
      }});

      const leg=svg.append('g').attr('transform',`translate(${{m.l}},${{H-4}})`);
      series.forEach((s,i)=>{{
        leg.append('rect').attr('x',i*110).attr('y',-3).attr('width',10).attr('height',10).attr('fill',s.color).attr('rx',2);
        leg.append('text').attr('x',i*110+14).attr('y',7).text(s.lbl)
          .attr('fill','#374151').attr('font-size',11).attr('font-family','Inter,sans-serif');
      }});
    }}

    groupedBar('svg-rates',
      ['CTR','Conversion'],
      [
        {{key:'mkt',  vals:[d.tCTR,d.tConv],  color:C.mktBar,  lbl:'Market'}},
        {{key:'asin', vals:[d.aCTR,d.aConv],  color:C.asinBar, lbl:'ASINs'}},
      ],
      v=>v.toFixed(2)+'%'
    );

    groupedBar('svg-prices',
      ['Click','Cart Add','Purchase'],
      [
        {{key:'mkt',  vals:[d.tMedClkPx,d.tMedCrtPx,d.tMedPurPx], color:C.price1, lbl:'Market'}},
        {{key:'asin', vals:[d.aMedClkPx,d.aMedCrtPx,d.aMedPurPx], color:C.price2, lbl:'ASINs'}},
      ],
      v=>'$'+v.toFixed(2)
    );

    // ── SHIPPING ─────────────────────────────────────────────────────────────────
    (function() {{
      const W=document.getElementById('svg-ship').parentElement.clientWidth-44;
      const H=200;
      const m={{t:8,r:8,b:36,l:80}};
      const iW=W-m.l-m.r, iH=H-m.t-m.b;
      const svg=d3.select('#svg-ship').attr('width',W).attr('height',H);
      const g=svg.append('g').attr('transform',`translate(${{m.l}},${{m.t}})`);

      const rows=[
        {{label:'Clicks',    sd:d.sdClk, od:d.odClk, td:d.tdClk, tot:d.tClk}},
        {{label:'Cart Adds', sd:d.sdCrt, od:d.odCrt, td:d.tdCrt, tot:d.tCrt}},
        {{label:'Purchases', sd:d.sdPur, od:d.odPur, td:d.tdPur, tot:d.tPur}},
      ];
      const speeds=[
        {{key:'sd',color:C.shipSD,lbl:'Same Day'}},
        {{key:'od',color:C.ship1D,lbl:'1-Day'}},
        {{key:'td',color:C.ship2D,lbl:'2-Day'}},
      ];

      const y=d3.scaleBand().domain(rows.map(r=>r.label)).range([0,iH]).padding(.35);
      const x=d3.scaleLinear().domain([0,100]).range([0,iW]);

      g.append('g').call(d3.axisLeft(y).tickSize(0).tickPadding(10))
       .select('.domain').remove();
      g.selectAll('.tick text').attr('fill','#374151').attr('font-size',11);

      g.append('g').attr('transform',`translate(0,${{iH}})`)
       .call(d3.axisBottom(x).ticks(5).tickFormat(v=>v+'%').tickSize(0).tickPadding(8))
       .select('.domain').remove();

      rows.forEach(row=>{{
        let cx=0;
        speeds.forEach(sp=>{{
          const pct=row.tot>0?row[sp.key]/row.tot*100:0;
          g.append('rect')
            .attr('x',x(cx)).attr('y',y(row.label))
            .attr('height',y.bandwidth()).attr('width',0)
            .attr('fill',sp.color)
            .on('mousemove',ev=>showTip(`${{row.label}} — ${{sp.lbl}}<br>${{fmtN(row[sp.key])}} (${{pct.toFixed(1)}}%)`,ev))
            .on('mouseleave',hideTip)
            .transition().duration(700).delay(rows.indexOf(row)*80).ease(d3.easeCubicOut)
            .attr('width',x(pct));

          if (pct>7) {{
            g.append('text')
              .attr('x',x(cx+pct/2)).attr('y',y(row.label)+y.bandwidth()/2+4)
              .attr('text-anchor','middle').attr('fill','#fff')
              .attr('font-size',10).attr('font-weight','600')
              .attr('font-family','JetBrains Mono,monospace').attr('pointer-events','none')
              .text(pct.toFixed(0)+'%').attr('opacity',0)
              .transition().delay(800).duration(200).attr('opacity',1);
          }}
          cx+=pct;
        }});
      }});

      const leg=svg.append('g').attr('transform',`translate(${{m.l}},${{H-4}})`);
      speeds.forEach((s,i)=>{{
        leg.append('rect').attr('x',i*90).attr('y',-3).attr('width',10).attr('height',10).attr('fill',s.color).attr('rx',2);
        leg.append('text').attr('x',i*90+14).attr('y',7).text(s.lbl)
          .attr('fill','#374151').attr('font-size',11).attr('font-family','Inter,sans-serif');
      }});
    }})();

    // ── DONUT ─────────────────────────────────────────────────────────────────────
    function donut(svgId, segs, centerLines) {{
      const W=document.getElementById(svgId).parentElement.clientWidth-44;
      const H=200;
      const R=Math.min(W,H)*.36, ri=R*.62;
      const svg=d3.select('#'+svgId).attr('width',W).attr('height',H);
      const g=svg.append('g').attr('transform',`translate(${{W/2}},${{H/2}})`);

      const pie=d3.pie().value(s=>s.v).sort(null).padAngle(.04);
      const arc=d3.arc().innerRadius(ri).outerRadius(R).cornerRadius(4);
      const arcH=d3.arc().innerRadius(ri).outerRadius(R+6).cornerRadius(4);

      g.selectAll(null).data(pie(segs)).enter().append('path')
        .attr('d',arc).attr('fill',s=>s.data.c)
        .attr('stroke','#fff').attr('stroke-width',2).attr('opacity',.95)
        .on('mousemove',(ev,s)=>showTip(s.data.label+'<br>'+s.data.fmt,ev))
        .on('mouseenter',function(){{d3.select(this).attr('d',arcH);}})
        .on('mouseleave',function(){{d3.select(this).attr('d',arc);hideTip();}});

      centerLines.forEach((line,i)=>{{
        g.append('text').attr('y',(i-(centerLines.length-1)/2)*22)
         .attr('text-anchor','middle')
         .attr('fill',i===0?'#111827':'#6b7280')
         .attr('font-size',i===0?20:11)
         .attr('font-weight',i===0?'700':'500')
         .attr('font-family',i===0?'Inter':'JetBrains Mono,monospace')
         .attr('letter-spacing',i===0?'-.03em':'.08em')
         .text(line);
      }});
    }}

    donut('svg-d1',
      [
        {{v:d.aImp,        c:C.donut1, label:'Your ASINs', fmt:fmtN(d.aImp)+' impr.'}},
        {{v:d.tImp-d.aImp, c:C.bg,     label:'Others',     fmt:fmtN(d.tImp-d.aImp)+' impr.'}},
      ],
      [(d.aImp/d.tImp*100).toFixed(1)+'%','CAPTURED']
    );

    document.getElementById('missed-badge').innerHTML = `
      <div style="margin-top:12px;display:flex;align-items:center;gap:10px;padding:10px 12px;background:#faf5ff;border-radius:8px;border:1px solid #e9d5ff">
        <span style="font-family:JetBrains Mono,monospace;font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;color:#6b7280">Missed Impr.</span>
        <span style="font-family:Inter;font-size:1.1rem;font-weight:700;color:#7c3aed">${{fmtN(d.missedImp)}}</span>
      </div>`;

    donut('svg-d2',
      [
        {{v:d.aClk,        c:C.donut2, label:'Your ASINs', fmt:fmtN(d.aClk)+' clicks'}},
        {{v:d.tClk-d.aClk, c:C.bg,     label:'Others',     fmt:fmtN(d.tClk-d.aClk)+' clicks'}},
      ],
      [(d.aClk/d.tClk*100).toFixed(1)+'%','CLICK SHARE']
    );

    const totPot=estRev+d.lostSales;
    donut('svg-d3',
      [
        {{v:estRev,      c:C.donut3, label:'Est. Revenue', fmt:fmtD(estRev)}},
        {{v:d.lostSales, c:C.lost,   label:'Lost Sales',   fmt:fmtD(d.lostSales)}},
      ],
      [(totPot>0?estRev/totPot*100:0).toFixed(0)+'%','CAPTURED']
    );
    document.getElementById('rev-badges').innerHTML = `
      <div style="display:flex;gap:8px;margin-top:12px">
        <div style="flex:1;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:10px 12px">
          <span style="display:block;font-family:JetBrains Mono,monospace;font-size:.58rem;letter-spacing:.08em;text-transform:uppercase;color:#6b7280;margin-bottom:3px">Est. Revenue</span>
          <span style="font-size:1rem;font-weight:700;color:#d97706">${{fmtD(estRev)}}</span>
        </div>
        <div style="flex:1;background:#fff1f2;border:1px solid #fecdd3;border-radius:8px;padding:10px 12px">
          <span style="display:block;font-family:JetBrains Mono,monospace;font-size:.58rem;letter-spacing:.08em;text-transform:uppercase;color:#6b7280;margin-bottom:3px">Lost Sales</span>
          <span style="font-size:1rem;font-weight:700;color:#e11d48">${{fmtD(d.lostSales)}}</span>
        </div>
      </div>`;

    </script>
    </body>
    </html>"""

    components.html(HTML, height=1900, scrolling=True)


if __name__ == "__main__":
    st.set_page_config(layout="wide")
    df_summary = st.file_uploader("Upload Amazon SQP Data", type="csv")
    if df_summary:
        render_sqp_dashboard(pd.read_csv(df_summary))
