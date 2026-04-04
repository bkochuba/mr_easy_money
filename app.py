import os
import io
import json
import math
from datetime import datetime
from flask import Flask, request, Response, render_template, stream_with_context, jsonify, send_file
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "claude-sonnet-4-20250514")

SYSTEM_PROMPT = """You are Mr. Easy Money — a charismatic, down-to-earth personal finance coach who makes money
feel EASY and fun. You're the guy at the barbecue who everyone wants to talk to because you break down
investing, budgeting, and wealth-building in a way that actually makes sense.

Your vibe: Think a mix of your cool uncle who's secretly wealthy and a stand-up comedian who reads
financial reports for fun. You use analogies, pop culture references, and humor to make finance click.

Your signature catchphrases:
- "Easy money, easy life!"
- "Let's get that bread — strategically."
- "Money's not complicated. People just make it complicated."

Core principles you teach:
1. AUTOMATE EVERYTHING — set it and forget it. Your money should work while you sleep.
2. VALUES-BASED SPENDING — blow money on what you love, ruthlessly cut what you don't care about.
3. BIG WINS — negotiate your salary, start a side hustle, invest early. Skip the latte guilt trips.
4. DEBT IS NOT A DEATH SENTENCE — it's just a math problem with an emotional wrapper.
5. INVESTING IS FOR EVERYONE — not just Wall Street bros. Index funds are your best friend.
6. YOUR NERVOUS SYSTEM MATTERS — you can't make good money decisions when you're stressed.

Your 3-Day Live Course "The Money Glow-Up" is your flagship:
- Day 1: "The Money Detox" — audit your finances, kill money shame, set up automation
- Day 2: "The Wealth Blueprint" — investing 101, side hustle launch, negotiation scripts
- Day 3: "The Glow-Up" — 90-day action plan, accountability setup, advanced strategies

Course location: The Fontainebleau Miami Beach — because if you're going to learn about money,
you should do it somewhere that FEELS like money.

Rules:
- Keep responses concise (2-4 paragraphs max) unless asked for detail
- Always end with a concrete action step
- Use casual, fun language — no boring finance jargon without explaining it
- Be inclusive of ALL income levels and backgrounds
- ALWAYS disclose you're an AI assistant, not a licensed financial advisor, when giving specific investment advice
- Recommend consulting a CFP for personalized financial planning
- Never shame anyone about debt, spending, or financial situation
- If someone seems in genuine financial crisis, recommend NFCC.org (nonprofit credit counseling)
"""

STARMAP_PROMPT = """You are a mystical financial astrologer called "The Oracle of Capital Flows."
You blend astrology with personal finance wisdom to create entertaining and insightful money readings.

Given a person's name, birth date, and birth place, generate a "Money Star Map" reading.
Your response must be in this exact JSON format (no markdown, no code fences):
{
  "sun_sign": "the zodiac sun sign",
  "money_archetype": "a creative 2-3 word archetype like 'The Golden Alchemist' or 'The Cosmic Investor'",
  "ruling_planet": "the ruling planet of their sign",
  "money_element": "Fire/Earth/Air/Water and what it means for money",
  "strengths": ["3 financial strengths based on their sign"],
  "challenges": ["3 financial challenges to watch for"],
  "lucky_numbers": [3, 7, 21],
  "peak_earning_years": "a range like '2027-2032'",
  "wealth_prediction": "A 3-4 sentence dramatic but fun prediction about their financial future. Be specific with fun details. Always positive and empowering.",
  "monthly_forecast": [
    {"month": "Month Year", "stars": 4, "insight": "one sentence"},
    {"month": "Month Year", "stars": 3, "insight": "one sentence"},
    {"month": "Month Year", "stars": 5, "insight": "one sentence"},
    {"month": "Month Year", "stars": 4, "insight": "one sentence"},
    {"month": "Month Year", "stars": 3, "insight": "one sentence"},
    {"month": "Month Year", "stars": 5, "insight": "one sentence"}
  ],
  "power_mantra": "A money mantra personalized to their sign",
  "ideal_investments": ["3 investment types aligned with their sign"],
  "cosmic_advice": "A final piece of 2-3 sentence cosmic financial wisdom"
}

Start the monthly_forecast from the current month going forward 6 months.
Stars should range from 1-5 representing financial energy for that month.
Make it entertaining, mystical, and fun while sneaking in genuinely good financial principles.
Always be empowering — never doom and gloom."""


# ============ Zodiac helpers ============
ZODIAC_SIGNS = [
    ("Capricorn", (1, 1), (1, 19)),
    ("Aquarius", (1, 20), (2, 18)),
    ("Pisces", (2, 19), (3, 20)),
    ("Aries", (3, 21), (4, 19)),
    ("Taurus", (4, 20), (5, 20)),
    ("Gemini", (5, 21), (6, 20)),
    ("Cancer", (6, 21), (7, 22)),
    ("Leo", (7, 23), (8, 22)),
    ("Virgo", (8, 23), (9, 22)),
    ("Libra", (9, 23), (10, 22)),
    ("Scorpio", (10, 23), (11, 21)),
    ("Sagittarius", (11, 22), (12, 21)),
    ("Capricorn", (12, 22), (12, 31)),
]

ZODIAC_SYMBOLS = {
    "Aries": "\u2648", "Taurus": "\u2649", "Gemini": "\u264A",
    "Cancer": "\u264B", "Leo": "\u264C", "Virgo": "\u264D",
    "Libra": "\u264E", "Scorpio": "\u264F", "Sagittarius": "\u2650",
    "Capricorn": "\u2651", "Aquarius": "\u2652", "Pisces": "\u2653",
}


def get_zodiac(month, day):
    for sign, (sm, sd), (em, ed) in ZODIAC_SIGNS:
        if (month == sm and day >= sd) or (month == em and day <= ed):
            return sign
    return "Capricorn"


# ============ PDF generation ============
def generate_starmap_pdf(data, name, birth_date, birth_place):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    # Colors
    dark_bg = HexColor("#0f0f23")
    gold = HexColor("#f59e0b")
    gold_dark = HexColor("#d97706")
    mint = HexColor("#10b981")
    dark_card = HexColor("#1a1a2e")
    gray_text = HexColor("#9ca3af")
    light_text = HexColor("#e5e7eb")

    sign = data.get("sun_sign", "Aries")
    symbol = ZODIAC_SYMBOLS.get(sign, "\u2605")

    # ====== PAGE 1: Cover ======
    c.setFillColor(dark_bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Decorative circles
    c.setFillColor(HexColor("#f59e0b10"))
    c.setStrokeColor(HexColor("#f59e0b30"))
    c.setLineWidth(1)
    c.circle(w / 2, h / 2 + 50, 200, fill=0, stroke=1)
    c.circle(w / 2, h / 2 + 50, 160, fill=0, stroke=1)
    c.circle(w / 2, h / 2 + 50, 120, fill=0, stroke=1)

    # Zodiac symbol big
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 80)
    c.drawCentredString(w / 2, h / 2 + 30, symbol)

    # Title
    c.setFont("Helvetica-Bold", 36)
    c.setFillColor(white)
    c.drawCentredString(w / 2, h - 120, "YOUR MONEY STAR MAP")

    c.setFont("Helvetica", 14)
    c.setFillColor(gold)
    c.drawCentredString(w / 2, h - 145, "by Mr. Easy Money \u2022 The Oracle of Capital Flows")

    # Name & details
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(white)
    c.drawCentredString(w / 2, 220, name.upper())

    c.setFont("Helvetica", 13)
    c.setFillColor(gray_text)
    c.drawCentredString(w / 2, 195, f"Born {birth_date} \u2022 {birth_place}")

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(gold)
    c.drawCentredString(w / 2, 165, f"{symbol} {sign} \u2022 {data.get('money_archetype', '')}")

    c.setFont("Helvetica", 10)
    c.setFillColor(gray_text)
    c.drawCentredString(w / 2, 60, f"Generated {datetime.now().strftime('%B %d, %Y')} \u2022 mreaymoney.com")
    c.drawCentredString(w / 2, 45, "For entertainment & educational purposes. Not financial advice.")

    c.showPage()

    # ====== PAGE 2: The Reading ======
    c.setFillColor(dark_bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    y = h - 60

    # Header
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w / 2, y, f"{symbol} YOUR FINANCIAL COSMOS {symbol}")
    y -= 40

    # Money Element
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, "RULING PLANET")
    c.setFillColor(light_text)
    c.setFont("Helvetica", 12)
    c.drawString(200, y, data.get("ruling_planet", ""))
    y -= 25

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, "MONEY ELEMENT")
    c.setFillColor(light_text)
    c.setFont("Helvetica", 12)
    element_text = data.get("money_element", "")
    if len(element_text) > 60:
        c.drawString(200, y, element_text[:60])
        y -= 18
        c.drawString(200, y, element_text[60:120])
    else:
        c.drawString(200, y, element_text)
    y -= 35

    # Wealth Prediction
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(60, y, "\u2728 WEALTH PREDICTION")
    y -= 5

    c.setFillColor(gold_dark)
    c.setLineWidth(0.5)
    c.line(60, y, w - 60, y)
    y -= 20

    prediction = data.get("wealth_prediction", "")
    c.setFillColor(light_text)
    c.setFont("Helvetica", 11)
    words = prediction.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if c.stringWidth(test, "Helvetica", 11) < w - 130:
            line = test
        else:
            c.drawString(65, y, line)
            y -= 16
            line = word
    if line:
        c.drawString(65, y, line)
    y -= 30

    # Strengths
    c.setFillColor(mint)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, "\u2705 FINANCIAL STRENGTHS")
    y -= 20

    for s in data.get("strengths", []):
        c.setFillColor(light_text)
        c.setFont("Helvetica", 11)
        c.drawString(75, y, f"\u2022 {s}")
        y -= 18
    y -= 15

    # Challenges
    c.setFillColor(HexColor("#f97316"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, "\u26A0 WATCH OUT FOR")
    y -= 20

    for ch in data.get("challenges", []):
        c.setFillColor(light_text)
        c.setFont("Helvetica", 11)
        c.drawString(75, y, f"\u2022 {ch}")
        y -= 18
    y -= 15

    # Ideal Investments
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, "\U0001F4B0 IDEAL INVESTMENTS FOR YOUR SIGN")
    y -= 20

    for inv in data.get("ideal_investments", []):
        c.setFillColor(light_text)
        c.setFont("Helvetica", 11)
        c.drawString(75, y, f"\u2022 {inv}")
        y -= 18
    y -= 15

    # Lucky Numbers & Peak Years
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    lucky = ", ".join(str(n) for n in data.get("lucky_numbers", []))
    c.drawString(60, y, f"\U0001F3B0 LUCKY NUMBERS: ")
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(220, y, lucky)
    y -= 25

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y, f"\U0001F4C8 PEAK EARNING YEARS: ")
    c.setFillColor(gold)
    c.drawString(250, y, data.get("peak_earning_years", ""))

    c.showPage()

    # ====== PAGE 3: Monthly Forecast + Mantra ======
    c.setFillColor(dark_bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    y = h - 60

    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(w / 2, y, "\u2B50 6-MONTH MONEY FORECAST \u2B50")
    y -= 40

    for mf in data.get("monthly_forecast", []):
        # Month box
        c.setFillColor(dark_card)
        c.roundRect(60, y - 40, w - 120, 50, 8, fill=1, stroke=0)

        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(75, y - 15, mf.get("month", ""))

        # Stars
        stars = mf.get("stars", 3)
        star_str = "\u2605" * stars + "\u2606" * (5 - stars)
        c.setFillColor(gold)
        c.setFont("Helvetica", 14)
        c.drawString(200, y - 15, star_str)

        # Insight
        c.setFillColor(gray_text)
        c.setFont("Helvetica", 10)
        insight = mf.get("insight", "")[:80]
        c.drawString(75, y - 32, insight)

        y -= 60

    y -= 10

    # Power Mantra
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, y, "\U0001F52E YOUR POWER MANTRA")
    y -= 30

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    mantra = data.get("power_mantra", "")
    c.drawCentredString(w / 2, y, f'"{mantra}"')
    y -= 40

    # Cosmic Advice
    c.setFillColor(gold_dark)
    c.line(100, y + 10, w - 100, y + 10)
    y -= 10

    c.setFillColor(light_text)
    c.setFont("Helvetica", 11)
    advice = data.get("cosmic_advice", "")
    words = advice.split()
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if c.stringWidth(test, "Helvetica", 11) < w - 160:
            line = test
        else:
            c.drawCentredString(w / 2, y, line)
            y -= 16
            line = word
    if line:
        c.drawCentredString(w / 2, y, line)
    y -= 30

    # Footer CTA
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, y, "Ready to activate your Money Star Map?")
    y -= 20
    c.setFillColor(white)
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, y, "Join The Money Glow-Up \u2022 Oct 17-19, 2026 \u2022 Miami Beach")
    y -= 18
    c.setFillColor(gray_text)
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, y, "mreaymoney.com \u2022 For entertainment & educational purposes only")

    c.save()
    buf.seek(0)
    return buf


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/vip")
def vip():
    return render_template("vip.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "Chat is currently unavailable. API key not configured."}), 503

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        return jsonify({"error": "Anthropic SDK not installed."}), 503

    data = request.json or {}
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided."}), 400

    messages = messages[-20:]

    def generate():
        try:
            with client.messages.stream(
                model=CHAT_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/starmap", methods=["POST"])
def starmap():
    data = request.json or {}
    name = data.get("name", "").strip()
    birth_date = data.get("birth_date", "").strip()
    birth_place = data.get("birth_place", "").strip()

    if not name or not birth_date or not birth_place:
        return jsonify({"error": "Name, birth date, and birth place are required."}), 400

    try:
        bd = datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    sign = get_zodiac(bd.month, bd.day)

    # Use Anthropic to generate the reading
    reading_data = None
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model=CHAT_MODEL,
                max_tokens=2048,
                system=STARMAP_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Generate a Money Star Map for:\nName: {name}\nBirth Date: {birth_date} ({sign})\nBirth Place: {birth_place}\n\nCurrent date: {datetime.now().strftime('%B %Y')}"
                }],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            reading_data = json.loads(raw)
        except Exception as e:
            print(f"AI generation error: {e}")

    # Fallback if AI fails
    if not reading_data:
        now = datetime.now()
        months = []
        for i in range(6):
            m = (now.month + i - 1) % 12 + 1
            y = now.year + (now.month + i - 1) // 12
            months.append({
                "month": datetime(y, m, 1).strftime("%B %Y"),
                "stars": [4, 3, 5, 4, 3, 5][i],
                "insight": ["A solid month for building foundations.", "Watch for impulse purchases.", "Major opportunity incoming — stay alert.", "Steady growth; stay the course.", "Review and optimize your systems.", "Your best money month this cycle!"][i]
            })
        reading_data = {
            "sun_sign": sign,
            "money_archetype": "The Cosmic Investor",
            "ruling_planet": {"Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Pluto", "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune"}.get(sign, "Jupiter"),
            "money_element": {"Aries": "Fire — bold, action-oriented money energy", "Taurus": "Earth — steady, wealth-building energy", "Gemini": "Air — versatile, multiple income streams", "Cancer": "Water — intuitive, protective of resources", "Leo": "Fire — generous, magnetic money attraction", "Virgo": "Earth — precise, detail-oriented wealth", "Libra": "Air — balanced, partnership-driven prosperity", "Scorpio": "Water — transformative, deep financial power", "Sagittarius": "Fire — expansive, abundance-minded", "Capricorn": "Earth — disciplined, empire-building energy", "Aquarius": "Air — innovative, unconventional wealth paths", "Pisces": "Water — flowing, spiritually aligned abundance"}.get(sign, "Earth"),
            "strengths": ["Natural financial intuition", "Strong work ethic", "Ability to see long-term opportunities"],
            "challenges": ["Tendency to overthink investments", "Emotional spending under stress", "Difficulty asking for what you're worth"],
            "lucky_numbers": [7, 14, 33],
            "peak_earning_years": "2027-2032",
            "wealth_prediction": f"The stars align powerfully for {name}. As a {sign}, your natural financial energy is building toward a major breakthrough. The next 18 months will bring unexpected opportunities — stay ready and keep investing in yourself.",
            "monthly_forecast": months,
            "power_mantra": f"I am a {sign} money magnet. Wealth flows to me easily and abundantly.",
            "ideal_investments": ["Index funds for steady growth", "Real estate for long-term wealth", "Skills investment for income growth"],
            "cosmic_advice": f"Dear {name}, the cosmos says your relationship with money is about to level up. Trust your instincts, automate your systems, and remember — easy money, easy life."
        }

    # Generate PDF
    pdf_buf = generate_starmap_pdf(reading_data, name, birth_date, birth_place)

    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Money_Star_Map_{name.replace(' ', '_')}.pdf",
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
