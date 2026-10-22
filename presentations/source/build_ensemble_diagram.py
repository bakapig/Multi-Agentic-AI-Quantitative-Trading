"""Build the current 16:9 ensemble architecture as SVG, HTML, PDF, PNG and JPEG.

Run with the bundled Python runtime (reportlab, Pillow) and Poppler on PATH.
"""
from html import escape
from pathlib import Path
import shutil
import subprocess

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "presentations/architecture_20261020"
PDF = ROOT / "output/pdf/Ensemble_Fund_Architecture_20261020.pdf"
W, H = 1920, 1080
INK, MUTED, PURPLE, GREEN = "#14243B", "#56677D", "#635BFF", "#087F6D"


class Diagram:
    def __init__(self, *, stem="ensemble_architecture", pdf_path=PDF,
                 title="Where AI fits in Meridian", description=None):
        self.stem = stem
        self.pdf_path = Path(pdf_path)
        self.title = title
        OUT.mkdir(parents=True, exist_ok=True)
        self.pdf_path.parent.mkdir(parents=True, exist_ok=True)
        self.pdf = canvas.Canvas(str(self.pdf_path), pagesize=(W / 2, H / 2))
        self.pdf.scale(.5, .5)
        self.pdf.setTitle(title + " - 20 October 2026")
        self.pdf.setAuthor("Meridian research team")
        description = description or ("Strategies, regime rules, allocation, fund risk, Phantom Book, orchestration, validation, storage and the web app are non-AI code. Analyst and Chair are AI-ready interfaces with code-generated reviews today. An optional external LLM can supply imported replies. Automatic LLM calls are not connected. Zero fills.")
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
                    '<title id="title">'+escape(title)+'</title>',
                    '<desc id="desc">'+escape(description)+'</desc>']
        self.fonts = {}
        for bold, filename in ((False, "segoeui.ttf"), (True, "segoeuib.ttf")):
            path = Path("C:/Windows/Fonts") / filename
            name = "UIBold" if bold else "UI"
            if path.exists():
                pdfmetrics.registerFont(TTFont(name, str(path)))
            else:
                name = "Helvetica-Bold" if bold else "Helvetica"
            self.fonts[bold] = name

    def rect(self, x, y, w, h, fill, stroke=None, radius=16):
        self.pdf.setFillColor(HexColor(fill))
        self.pdf.setStrokeColor(HexColor(stroke or fill))
        self.pdf.setLineWidth(1.4)
        self.pdf.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=bool(stroke))
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke or fill}" stroke-width="1.4"/>')

    def text(self, x, y, value, size=22, color=INK, bold=False, max_width=None):
        font = self.fonts[bold]
        if max_width is not None and pdfmetrics.stringWidth(value, font, size) > max_width:
            raise ValueError("Diagram text exceeds its box: " + value)
        self.pdf.setFillColor(HexColor(color))
        self.pdf.setFont(font, size)
        self.pdf.drawString(x, H-y, value)
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Segoe UI, Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')

    def line(self, points, color="#A0ADC0", arrow=False, dashed=False):
        self.pdf.setStrokeColor(HexColor(color))
        self.pdf.setLineWidth(2)
        self.pdf.setDash([6, 5] if dashed else [])
        for a, b in zip(points, points[1:]):
            self.pdf.line(a[0], H-a[1], b[0], H-b[1])
        dash=' stroke-dasharray="6 5"' if dashed else ''
        self.svg.append('<polyline points="'+" ".join(f"{x},{y}" for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="2"{dash}/>')
        self.pdf.setDash([])
        if arrow:
            (ax, ay), (bx, by) = points[-2:]
            if bx == ax:
                triangle = [(bx,by),(bx-6,by-9),(bx+6,by-9)]
            else:
                triangle = [(bx,by),(bx-9,by-6),(bx-9,by+6)]
            path=self.pdf.beginPath()
            path.moveTo(triangle[0][0],H-triangle[0][1])
            for x,y in triangle[1:]:
                path.lineTo(x,H-y)
            path.close()
            self.pdf.setFillColor(HexColor(color))
            self.pdf.drawPath(path,fill=1,stroke=0)
            self.svg.append('<polygon points="'+" ".join(f"{x},{y}" for x,y in triangle)+f'" fill="{color}"/>')

    def box(self,x,y,w,h,title,lines=(),accent=PURPLE):
        self.rect(x,y,w,h,"#FFFFFF","#DCE3EF",12)
        self.rect(x+16,y+20,4,h-40,accent,radius=2)
        self.text(x+34,y+37,title,25,bold=True,max_width=w-55)
        for i,line in enumerate(lines):
            self.text(x+34,y+67+27*i,line,20,MUTED,max_width=w-55)

    def save(self):
        self.pdf.showPage()
        self.pdf.save()
        self.svg.append('</svg>')
        svg="\n".join(self.svg)
        (OUT/(self.stem+".svg")).write_text(svg,encoding="utf-8")
        (OUT/(self.stem+".html")).write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(self.title)+'</title><style>body{margin:0;background:#eaf0f7}.slide{max-width:1920px;margin:0 auto}svg{display:block;width:100%;height:auto}@media print{@page{size:landscape;margin:0}body{background:white}}</style><main class="slide">'+svg+'</main></html>',encoding="utf-8")
        renderer=shutil.which("pdftoppm")
        if not renderer:
            raise RuntimeError("Put the bundled Poppler pdftoppm executable on PATH")
        prefix=OUT/self.stem
        subprocess.run([renderer,"-scale-to-x",str(W),"-scale-to-y",str(H),"-singlefile","-png",str(self.pdf_path),str(prefix)],check=True)
        with Image.open(prefix.with_suffix(".png")) as image:
            image.convert("RGB").save(prefix.with_suffix(".jpg"),quality=95,subsampling=0)
        print("Created architecture diagram:",OUT)
        print("PDF:",self.pdf_path)


def main():
    d=Diagram()
    d.rect(0,0,W,H,"#F4F7FC",radius=0)
    d.text(80,65,"MERIDIAN / DIGITAL INVESTMENT OFFICE",18,PURPLE,True)
    d.text(80,131,"Where AI fits in the architecture",54,INK,True)
    d.text(80,170,"Numerical code makes portfolio decisions. Automatic LLM calls are not connected.",24,MUTED)
    d.text(1590,65,"20 OCTOBER 2026",18,MUTED,True)
    d.rect(80,204,1760,62,"#FFF1D5",radius=12)
    d.text(106,244,"HUMAN OWNERSHIP",18,"#916000",True)
    d.text(350,244,"Universe, allocation policy and risk limits",23,INK)
    d.text(1175,244,"$3M ensemble  +  $2M central cash",23,PURPLE,True)

    d.rect(80,292,1110,638,"#EDF6F3","#CEDFD9",18)
    d.text(112,328,"LANE 1 / NON-AI QUANTITATIVE CODE",19,GREEN,True)
    d.text(930,328,"Rules + mathematics",18,GREEN)
    d.rect(112,348,1036,62,"#FFFFFF","#DCE3EF",12)
    d.text(136,386,"Data + validation | NON-AI",24,INK,True)
    d.text(500,386,"USD equity closes + SPY; completed sessions",21,MUTED)
    d.line([(630,410),(630,430)])
    d.line([(276,430),(983,430)])
    d.line([(276,430),(276,450)],arrow=True)
    d.line([(630,430),(630,450)],arrow=True,dashed=True)
    d.line([(983,430),(983,450)],arrow=True)
    d.box(112,450,329,99,"Trend | NON-AI",["MA 10 / 60 + market filter"],GREEN)
    d.box(465,450,329,99,"Momentum | IGNORED",["Excluded: losing money (-2.35%)"],MUTED)
    d.box(818,450,330,99,"Reversion | NON-AI",["Equity spread Z-scores"],GREEN)
    for x in (276,983):
        d.line([(x,549),(x,569)])
    d.line([(276,569),(983,569)])
    d.line([(630,569),(630,590)],arrow=True)
    d.box(112,590,1036,91,"Ensemble PM + regime rules | NON-AI",["Regime / equal weight / inverse volatility  |  Aggregate shared symbols"],GREEN)
    d.line([(630,681),(630,695),(362,695),(362,714)],arrow=True)
    d.box(112,714,500,105,"Fund risk | NON-AI",["Exposure caps + drawdown controls", "Phantom Book = exposure arithmetic"],GREEN)
    d.line([(612,767),(647,767)],arrow=True)
    d.box(647,714,501,105,"Intention records | NON-AI",["Exact approval + confirmed snapshot", "No broker orders; zero fills"],GREEN)
    d.text(112,857,"Signals, allocations and approvals are computed by numerical code.",21,GREEN)
    d.text(112,894,"FundCoordinator: fixed sequence in one Python process (NON-AI).",20,MUTED)

    d.rect(1226,292,614,638,"#F1EEFC","#DCD5F2",18)
    d.text(1258,328,"LANE 2 / AI-READY ADVISORY ROLES",19,PURPLE,True)
    d.rect(1258,348,550,105,PURPLE,radius=12)
    d.text(1292,385,"Optional external LLM | AI",25,"#FFFFFF",True,max_width=495)
    d.text(1292,415,"AI-generated replies can be imported",20,"#FFFFFF",max_width=495)
    d.text(1292,442,"Automatic calls: NOT CONNECTED",20,"#FFFFFF",True,max_width=495)
    d.line([(1533,453),(1533,493)],PURPLE,True,dashed=True)
    d.box(1258,493,550,99,"Ensemble analyst | AI-READY",["Today: read-only tools + code summary"],PURPLE)
    d.line([(1533,592),(1533,627)],PURPLE,True)
    d.box(1258,627,550,99,"Committee Chair | AI-READY",["Today: read-only tools + code summary"],PURPLE)
    d.line([(1533,726),(1533,751)],"#697A91",True)
    d.box(1258,751,550,99,"Shared claim checks | NON-AI",["Facts digest + metrics; used by both roles"],"#697A91")
    d.line([(1148,767),(1207,767),(1207,543),(1258,543)],"#8A7BC9",True,dashed=True)
    d.text(1154,690,"FACTS",14,MUTED,True)
    d.text(1258,876,"AI commentary has zero trading authority.",21,PURPLE)
    d.text(1258,905,"Dashed arrows: optional replies / read-only facts.",18,MUTED)

    d.rect(80,956,1760,70,"#E3E9F2",radius=14)
    d.text(108,1000,"SQLite + JSON storage + investor web app | NON-AI INFRASTRUCTURE",25,INK,True)
    d.text(1660,1000,"ZERO FILLS",22,GREEN,True)
    d.text(80,1054,"GREEN: NON-AI CODE   |   PURPLE: AI-READY ROLES / OPTIONAL AI   |   GRAY: NON-AI VALIDATION + INFRASTRUCTURE",17,MUTED)
    d.save()


if __name__ == "__main__":
    main()
