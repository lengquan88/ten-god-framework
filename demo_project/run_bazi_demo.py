"""
run_bazi_demo.py — 八字排盘一键演示
= = = = = = = = = = = = = = = = = = =
用法:
  python run_bazi_demo.py                           # 1990-06-15 10:30 默认示例
  python run_bazi_demo.py --year 1988 --month 8 --day 8 --hour 12 --minute 0 --male
  python run_bazi_demo.py --export bazi_output.json  # 导出JSON供前端读取
  python run_bazi_demo.py --html bazi.html          # 生成独立HTML页面

产出:
  1. 控制台综合分析报告
  2. 可选的 JSON 数据文件（供前端可视化）
  3. 可选的 HTML 单文件报告页面
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tengod.bazi_analyzer import BaziAnalyzer
from tengod.bazi_calculator import BaziChart  # noqa: F401
from tengod.dayun_liunian import derive_shigan  # noqa: F401


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>八字排盘分析报告 — {title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #e8e8e8; min-height: 100vh; padding: 20px;
  }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ text-align: center; font-size: 28px; margin-bottom: 8px;
        background: linear-gradient(90deg, #f5d76e, #e8b14f);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
  .subtitle {{ text-align: center; color: #8e9aaf; margin-bottom: 24px; font-size: 14px; }}
  .section {{ background: rgba(255,255,255,0.04); border: 1px solid rgba(255,215,110,0.15);
              border-radius: 12px; padding: 20px; margin-bottom: 16px;
              backdrop-filter: blur(10px); }}
  .section-title {{ font-size: 16px; color: #f5d76e; margin-bottom: 14px;
                    border-bottom: 1px solid rgba(255,215,110,0.2); padding-bottom: 8px; }}
  .pillars {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .pillar {{ background: linear-gradient(180deg, rgba(245,215,110,0.08), transparent);
             border: 1px solid rgba(245,215,110,0.2); border-radius: 10px;
             padding: 16px; text-align: center; transition: transform 0.3s; }}
  .pillar:hover {{ transform: translateY(-3px); }}
  .pillar-label {{ font-size: 12px; color: #8e9aaf; margin-bottom: 8px; }}
  .pillar-main {{ font-size: 38px; font-weight: bold; margin: 10px 0;
                  letter-spacing: 6px; color: #fff5d6; }}
  .pillar-shigan {{ font-size: 13px; color: #f5d76e; padding-top: 6px;
                     border-top: 1px dashed rgba(245,215,110,0.2); }}
  .wuxing-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }}
  .wuxing-item {{ padding: 14px 8px; border-radius: 8px; text-align: center;
                  border: 1px solid rgba(255,255,255,0.1); }}
  .wuxing-name {{ font-size: 18px; font-weight: bold; margin-bottom: 4px; }}
  .wuxing-count {{ font-size: 12px; color: #8e9aaf; }}
  .wood {{ background: rgba(46,139,87,0.15); border-color: rgba(46,139,87,0.3); color: #52b788; }}
  .fire {{ background: rgba(220,20,60,0.12); border-color: rgba(220,20,60,0.3); color: #ff6b6b; }}
  .earth {{ background: rgba(205,133,63,0.12); border-color: rgba(205,133,63,0.3); color: #e0a060; }}
  .metal {{ background: rgba(192,192,192,0.12); border-color: rgba(192,192,192,0.3); color: #d4d4d4; }}
  .water {{ background: rgba(70,130,180,0.15); border-color: rgba(70,130,180,0.3); color: #7bb6de; }}
  .missing {{ opacity: 0.4; }}
  .dayun-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }}
  .dayun-item {{ background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
                 border-radius: 8px; padding: 10px; font-size: 13px; }}
  .dayun-year {{ color: #8e9aaf; font-size: 11px; }}
  .dayun-pillar {{ font-size: 18px; font-weight: bold; color: #fff5d6; margin: 4px 0; letter-spacing: 3px; }}
  .conclusion {{ line-height: 1.8; color: #d4d4d4; }}
  .meta {{ display: flex; justify-content: space-between; font-size: 13px; color: #8e9aaf; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="container">
  <h1>八字排盘分析报告</h1>
  <div class="subtitle">{title}</div>
  <div class="meta"><span>真太阳时: {solar}</span><span>经度: {lon}°</span></div>

  <div class="section">
    <div class="section-title">▎四柱</div>
    <div class="pillars">
      {pillars_html}
    </div>
  </div>

  <div class="section">
    <div class="section-title">▎五行分布</div>
    <div class="wuxing-grid">
      {wuxing_html}
    </div>
  </div>

  <div class="section">
    <div class="section-title">▎十神分布</div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px;">
      {shigan_html}
    </div>
  </div>

  <div class="section">
    <div class="section-title">▎大运（每步10年）</div>
    <div class="dayun-list">
      {dayun_html}
    </div>
  </div>

  <div class="section">
    <div class="section-title">▎近期流年</div>
    <div class="dayun-list">
      {liunian_html}
    </div>
  </div>

  <div class="section">
    <div class="section-title">▎分析结论</div>
    <div class="conclusion">{conclusion}</div>
  </div>
</div>
</body>
</html>"""


def build_html(title: str, solar: str, lon: float, analysis: dict) -> str:
    a = analysis
    pillars = a['pillars']
    shigan_map = a['shigan_map']
    pillar_names = [('年柱', 'year', 'year_gan'), ('月柱', 'month', 'month_gan'),
                    ('日柱', 'day', 'day'), ('时柱', 'hour', 'hour_gan')]

    def pillar_html(label: str, key: str, shigan_key: str) -> str:
        shigan = shigan_map.get(shigan_key, '日主')
        if key == 'day':
            shigan = f'日主 {pillars[key][0]}'
        return (f'<div class="pillar"><div class="pillar-label">{label}</div>'
                f'<div class="pillar-main">{pillars[key]}</div>'
                f'<div class="pillar-shigan">{shigan}</div></div>')

    pillars_html = ''.join(pillar_html(label, key, sk) for label, key, sk in pillar_names)

    # 五行
    wuxing_html = ''
    for wx, color in [('木', 'wood'), ('火', 'fire'), ('土', 'earth'), ('金', 'metal'), ('水', 'water')]:
        count = a['wuxing'].get(wx, 0)
        missing_cls = 'missing' if count == 0 else ''
        score_line = a['wuxing_score'].get(wx, '-')
        wuxing_html += (f'<div class="wuxing-item {color} {missing_cls}">'
                        f'<div class="wuxing-name">{wx}</div>'
                        f'<div class="wuxing-count">{score_line}</div></div>')

    # 十神
    shigan_html = ''
    for sg, cnt in sorted(a['shigan_count'].items(), key=lambda x: -x[1]):
        shigan_html += f'<div class="wuxing-item metal"><div class="wuxing-name">{sg}</div><div class="wuxing-count">{cnt}</div></div>'

    # 大运
    dayun_html = ''
    for du in a['dayuns']:
        gan_shigan = derive_shigan(a['day_master'], du['pillar'][0])
        dayun_html += (f'<div class="dayun-item"><div class="dayun-year">{du["age"]}-{du["age"]+9}岁 '
                       f'({du["start_year"]}-{du["start_year"]+9})</div>'
                       f'<div class="dayun-pillar">{du["pillar"]}</div>'
                       f'<div class="pillar-shigan">{gan_shigan}</div></div>')

    # 流年
    liunian_html = ''
    for ln in a['liunians'][:14]:
        liunian_html += (f'<div class="dayun-item"><div class="dayun-year">{ln["year"]}年</div>'
                        f'<div class="dayun-pillar">{ln["pillar"]}</div>'
                        f'<div class="pillar-shigan">{ln["gan_shigan"]}</div></div>')

    return HTML_TEMPLATE.format(
        title=title,
        solar=solar,
        lon=lon,
        pillars_html=pillars_html,
        wuxing_html=wuxing_html,
        shigan_html=shigan_html,
        dayun_html=dayun_html,
        liunian_html=liunian_html,
        conclusion=a['conclusion'],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description='八字排盘演示')
    parser.add_argument('--year', type=int, default=1990)
    parser.add_argument('--month', type=int, default=6)
    parser.add_argument('--day', type=int, default=15)
    parser.add_argument('--hour', type=int, default=10)
    parser.add_argument('--minute', type=int, default=30)
    parser.add_argument('--male', action='store_true', default=True, help='男命')
    parser.add_argument('--female', dest='male', action='store_false', help='女命')
    parser.add_argument('--longitude', type=float, default=116.4)
    parser.add_argument('--latitude', type=float, default=39.9)
    parser.add_argument('--export', type=str, default='', help='导出JSON文件名')
    parser.add_argument('--html', type=str, default='', help='导出HTML文件名')
    args = parser.parse_args()

    analyzer = BaziAnalyzer(args.year, args.month, args.day, args.hour, args.minute,
                             args.male, args.longitude, args.latitude)
    print(analyzer.text_report())

    if args.export:
        with open(args.export, 'w', encoding='utf-8') as f:
            json.dump(analyzer.json_report(), f, ensure_ascii=False, indent=2)
        print(f'\n[✓] JSON 已导出至 {args.export}')

    if args.html:
        title = f'{args.year}-{args.month:02d}-{args.day:02d} {"男命" if args.male else "女命"}'
        solar = f'{analyzer.chart.true_hour:02d}:{analyzer.chart.true_minute:02d}'
        html = build_html(title, solar, args.longitude, analyzer.json_report())
        with open(args.html, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'[✓] HTML 已导出至 {args.html}')


if __name__ == '__main__':
    main()
