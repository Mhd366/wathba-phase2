from io import BytesIO
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from .schemas import AnalysisResult

def build_pdf(result: AnalysisResult) -> bytes:
    stream=BytesIO(); page=Canvas(stream,pagesize=A4); width,height=A4
    page.setFillColor(HexColor("#146EF5")); page.rect(0,height-84,width,84,fill=1,stroke=0)
    page.setFillColorRGB(1,1,1); page.setFont("Helvetica-Bold",22); page.drawString(42,height-52,"WATHBA PERFORMANCE REPORT")
    page.setFillColor(HexColor("#12233F")); page.setFont("Helvetica-Bold",16); page.drawString(42,height-124,result.athlete_name)
    page.setFont("Helvetica",10); page.drawString(42,height-143,f"{result.event.value} · {result.phase} · {result.analysis_id}")
    y=height-185; page.setFont("Helvetica-Bold",12); page.drawString(42,y,"Analysis summary"); y-=22
    page.setFont("Helvetica",10); page.drawString(42,y,f"Status: {result.status.value}"); y-=16
    page.drawString(42,y,f"Reference status: {result.reference_status.value}"); y-=16
    page.drawString(42,y,f"Capture quality: {result.quality.score*100:.0f}%"); y-=30
    page.setFont("Helvetica-Bold",12); page.drawString(42,y,"Measured metrics"); y-=20
    page.setFont("Helvetica",9)
    for metric in result.metrics:
        value="Unavailable" if metric.value is None else f"{metric.value:g} {metric.unit}"
        page.drawString(52,y,f"{metric.label}: {value} · confidence {metric.confidence*100:.0f}%"); y-=15
    y-=10; page.setFont("Helvetica-Bold",12); page.drawString(42,y,"Quality notes"); y-=20; page.setFont("Helvetica",9)
    if not result.quality.warnings: page.drawString(52,y,"No capture warnings.")
    for warning in result.quality.warnings:
        page.drawString(52,y,f"{warning.code}: {warning.message}"); y-=15
    page.setFillColor(HexColor("#64748B")); page.setFont("Helvetica",8); page.drawString(42,35,"Decision-support report. Not a race-result guarantee.")
    page.save(); return stream.getvalue()

