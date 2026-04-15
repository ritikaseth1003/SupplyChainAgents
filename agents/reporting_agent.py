import os
import datetime
from fpdf import FPDF
from utils.openai_client import ask_gpt

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def safe_txt(text: str) -> str:
    return str(text).encode('latin-1', 'replace').decode('latin-1')

class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, safe_txt('Supply Chain Daily Report'), 0, 1, 'C')
        self.ln(5)

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 8, safe_txt(title), 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 6, safe_txt(text))
        self.ln(4)


async def generate_pdf_report(state: dict) -> str:
    """Generates the PDF report and returns the filename/path."""
    
    day = state.get("sim_day", 0)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metrics = state.get("metrics", {})
    inventory = state.get("inventory", {})
    safety = state.get("safety_stock", {})
    pos = state.get("purchase_orders", [])
    disruption = state.get("active_disruption")

    # Fetch AI Insights
    prompt = (
        f"Generate a brief execution summary and any actionable recommendations based on this state:\n"
        f"Metrics: {metrics}\n"
        f"Disruptions: {disruption}\n"
        "Return just the text of the insights."
    )
    
    try:
        insights = await ask_gpt(
            system_prompt="You are a senior supply chain analyst.",
            user_prompt=prompt
        )
    except Exception as e:
        insights = f"AI Insights temporarily unavailable due to connection error. ({str(e)})"

    # Start PDF
    pdf = PDFReport()
    pdf.add_page()
    
    # 1. Header Info
    pdf.set_font("helvetica", "", 11)
    pdf.cell(0, 6, safe_txt(f"Simulation Day: {day}"), ln=1)
    pdf.cell(0, 6, safe_txt(f"Generated At: {now}"), ln=1)
    pdf.ln(5)

    # 2. Key Metrics
    pdf.chapter_title("Key Metrics")
    total_demand = max(metrics.get("total_demand", 1), 1)
    stockouts = metrics.get("stockout_count", 0)
    stockout_rate = round(stockouts / total_demand * 100, 2)
    turonver_base = max( (sum(inventory.values()) / max(len(inventory), 1)) * max(metrics.get("days_simulated", 1), 1), 1 )
    turnover = round(total_demand / turonver_base, 2)

    metrics_text = (
        f"Stockout Rate: {stockout_rate}%\n"
        f"Inventory Turnover: {turnover}x\n"
        f"Total Cost: ${metrics.get('total_cost', 0):,.0f}\n"
        f"Recovery Time: {metrics.get('disruption_recovery_time', 0):.1f}s"
    )
    pdf.chapter_body(metrics_text)

    # 3. Inventory Status
    pdf.chapter_title("Inventory Status")
    # Table headers
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(50, 8, "Product", 1)
    pdf.cell(35, 8, "Stock Level", 1)
    pdf.cell(35, 8, "Safety Stock", 1)
    pdf.cell(40, 8, "Status", 1, ln=1)
    
    pdf.set_font("helvetica", "", 10)
    for prod, stock in inventory.items():
        ss = safety.get(prod, 150)
        status = "OK" if stock >= ss else "LOW" if stock > 0 else "STOCKOUT"
        pdf.cell(50, 8, safe_txt(str(prod)), 1)
        pdf.cell(35, 8, safe_txt(str(stock)), 1)
        pdf.cell(35, 8, safe_txt(str(ss)), 1)
        pdf.cell(40, 8, safe_txt(status), 1, ln=1)
    pdf.ln(5)

    # 4. Active Disruptions
    if disruption:
        pdf.chapter_title("Active Disruptions")
        pdf.chapter_body(f"Type: {disruption.get('type', 'Unknown')}\nDescription: {disruption.get('description', '')}")

    # 5. AI Insights
    pdf.chapter_title("AI Insights & Recommendations")
    pdf.chapter_body(insights)

    # 6. Recent Purchase Orders
    pdf.chapter_title("Recent Purchase Orders")
    if pos:
        for po in list(reversed(pos))[:5]:
            pdf.chapter_body(f"[{po.get('status', 'open').upper()}] {po.get('id')} - {po.get('quantity')}x {po.get('product')} via {po.get('supplier')}")
    else:
        pdf.chapter_body("No active purchase orders.")

    # Save
    filename = f"report_day_{day}_{datetime.datetime.now().strftime('%H%M%S')}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    pdf.output(filepath)
    
    return filename
