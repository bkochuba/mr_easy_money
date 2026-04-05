import os
import io
import json
import math
import struct
import wave
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
def draw_star(c, cx, cy, r, color):
    """Draw a 5-pointed star at (cx, cy) with radius r."""
    c.setFillColor(color)
    p = c.beginPath()
    for i in range(5):
        angle = math.radians(90 + i * 144)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def draw_decorative_ring(c, cx, cy, radius, segments, color, line_width=1):
    """Draw a dashed decorative ring."""
    c.setStrokeColor(color)
    c.setLineWidth(line_width)
    for i in range(segments):
        a1 = math.radians(i * (360 / segments))
        a2 = math.radians(i * (360 / segments) + (360 / segments) * 0.6)
        c.arc(cx - radius, cy - radius, cx + radius, cy + radius,
              math.degrees(a1), math.degrees(a2 - a1))


def wrap_text(c, text, font, size, max_width):
    """Word-wrap text and return list of lines."""
    c.setFont(font, size)
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test = line + " " + word if line else word
        if c.stringWidth(test, font, size) < max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def generate_starmap_pdf(data, name, birth_date, birth_place):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.colors import HexColor, white, Color
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    mx = 50  # margin x

    # Colors
    bg = HexColor("#0f0f23")
    bg2 = HexColor("#141432")
    gold = HexColor("#f59e0b")
    gold_d = HexColor("#d97706")
    gold_dim = HexColor("#92630a")
    mint = HexColor("#10b981")
    orange = HexColor("#f97316")
    violet = HexColor("#8b5cf6")
    card = HexColor("#1a1a2e")
    card_b = HexColor("#252545")
    gray = HexColor("#9ca3af")
    light = HexColor("#e5e7eb")

    sign = data.get("sun_sign", "Aries")
    archetype = data.get("money_archetype", "The Cosmic Investor")

    # Try to embed the hero image
    hero_path = os.path.join(os.path.dirname(__file__), "static", "images", "hero.png")
    has_hero = os.path.exists(hero_path)

    # ====== PAGE 1: Cover ======
    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # Background image with overlay
    if has_hero:
        c.saveState()
        c.setFillColor(Color(0, 0, 0, alpha=0.5))
        c.drawImage(hero_path, 0, h / 2 - 100, w, h / 2 + 100, preserveAspectRatio=True, anchor="c", mask="auto")
        c.rect(0, 0, w, h, fill=1, stroke=0)  # dark overlay
        c.restoreState()

    # Decorative rings
    center_y = h / 2 + 20
    for r, alpha in [(180, 0.15), (140, 0.2), (100, 0.25), (60, 0.1)]:
        draw_decorative_ring(c, w / 2, center_y, r, 12, Color(0.96, 0.62, 0.04, alpha=alpha), 1.5)

    # Stars scattered around
    import random
    random.seed(hash(name))  # consistent per person
    for _ in range(30):
        sx = random.randint(30, int(w) - 30)
        sy = random.randint(30, int(h) - 30)
        sr = random.uniform(1.5, 3.5)
        draw_star(c, sx, sy, sr, Color(1, 1, 1, alpha=random.uniform(0.1, 0.4)))

    # Central zodiac sign text (large)
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 60)
    c.drawCentredString(w / 2, center_y - 15, sign.upper())
    c.setFont("Helvetica", 16)
    c.setFillColor(gold_d)
    c.drawCentredString(w / 2, center_y - 40, archetype)

    # Divider stars
    for i in range(5):
        draw_star(c, w / 2 - 40 + i * 20, center_y + 40, 4, gold)

    # Title block at top
    c.setFillColor(card)
    c.setStrokeColor(gold_dim)
    c.setLineWidth(1)
    c.roundRect(mx, h - 160, w - mx * 2, 110, 12, fill=1, stroke=1)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(w / 2, h - 95, "YOUR MONEY STAR MAP")

    c.setFillColor(gold)
    c.setFont("Helvetica", 13)
    c.drawCentredString(w / 2, h - 120, "by Mr. Easy Money  |  The Oracle of Capital Flows")

    # Gold accent bar
    c.setFillColor(gold)
    c.rect(w / 2 - 60, h - 135, 120, 2, fill=1, stroke=0)

    # Name block at bottom
    c.setFillColor(card)
    c.setStrokeColor(gold_dim)
    c.roundRect(mx, 80, w - mx * 2, 120, 12, fill=1, stroke=1)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(w / 2, 160, name.upper())

    c.setFillColor(gray)
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, 138, f"Born {birth_date}  |  {birth_place}")

    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, 112, f"{sign}  |  {archetype}")

    # Bottom disclaimer
    c.setFillColor(Color(0.4, 0.4, 0.5, alpha=0.7))
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 40, f"Generated {datetime.now().strftime('%B %d, %Y')}  |  mreaymoney.com  |  For entertainment & educational purposes only")

    c.showPage()

    # ====== PAGE 2: The Reading ======
    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    y = h - 50

    # Page header
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, y, "YOUR FINANCIAL COSMOS")
    y -= 8
    c.setFillColor(gold_d)
    c.rect(w / 2 - 80, y, 160, 1.5, fill=1, stroke=0)
    y -= 30

    # --- Ruling Planet & Element row ---
    col_w = (w - mx * 2 - 15) / 2
    for i, (label, val) in enumerate([
        ("RULING PLANET", data.get("ruling_planet", "")),
        ("MONEY ELEMENT", data.get("money_element", "")),
    ]):
        bx = mx + i * (col_w + 15)
        c.setFillColor(card)
        c.setStrokeColor(card_b)
        c.roundRect(bx, y - 55, col_w, 55, 8, fill=1, stroke=1)
        c.setFillColor(gold)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(bx + 12, y - 16, label)
        c.setFillColor(light)
        c.setFont("Helvetica", 10)
        # Truncate if too long
        display_val = val[:35] + "..." if len(val) > 35 else val
        c.drawString(bx + 12, y - 34, display_val)
    y -= 72

    # --- Wealth Prediction ---
    c.setFillColor(card)
    c.setStrokeColor(gold_dim)
    pred_lines = wrap_text(c, data.get("wealth_prediction", ""), "Helvetica", 10, w - mx * 2 - 30)
    pred_h = max(70, len(pred_lines) * 15 + 40)
    c.roundRect(mx, y - pred_h, w - mx * 2, pred_h, 8, fill=1, stroke=1)

    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(mx + 15, y - 20, "WEALTH PREDICTION")
    draw_star(c, mx + 145, y - 15, 5, gold)

    c.setFillColor(light)
    c.setFont("Helvetica", 10)
    ty = y - 40
    for line in pred_lines:
        c.drawString(mx + 15, ty, line)
        ty -= 15
    y -= pred_h + 15

    # --- Strengths & Challenges side by side ---
    col_w = (w - mx * 2 - 15) / 2
    strengths = data.get("strengths", [])
    challenges = data.get("challenges", [])
    box_h = max(len(strengths), len(challenges)) * 18 + 35

    for i, (label, items, color) in enumerate([
        ("FINANCIAL STRENGTHS", strengths, mint),
        ("WATCH OUT FOR", challenges, orange),
    ]):
        bx = mx + i * (col_w + 15)
        c.setFillColor(card)
        c.setStrokeColor(card_b)
        c.roundRect(bx, y - box_h, col_w, box_h, 8, fill=1, stroke=1)
        # Colored accent bar at top
        c.setFillColor(color)
        c.roundRect(bx, y - 3, col_w, 3, 1, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(bx + 12, y - 22, label)
        c.setFillColor(light)
        c.setFont("Helvetica", 10)
        iy = y - 40
        for item in items:
            item_display = item[:40] + "..." if len(item) > 40 else item
            c.setFillColor(color)
            c.circle(bx + 16, iy + 3, 2.5, fill=1, stroke=0)
            c.setFillColor(light)
            c.drawString(bx + 25, iy, item_display)
            iy -= 18
    y -= box_h + 15

    # --- Ideal Investments ---
    investments = data.get("ideal_investments", [])
    inv_h = len(investments) * 18 + 35
    c.setFillColor(card)
    c.setStrokeColor(card_b)
    c.roundRect(mx, y - inv_h, w - mx * 2, inv_h, 8, fill=1, stroke=1)
    c.setFillColor(violet)
    c.roundRect(mx, y - 3, w - mx * 2, 3, 1, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(mx + 15, y - 22, "IDEAL INVESTMENTS FOR YOUR SIGN")
    c.setFillColor(light)
    c.setFont("Helvetica", 10)
    iy = y - 40
    for inv in investments:
        c.setFillColor(violet)
        c.circle(mx + 19, iy + 3, 2.5, fill=1, stroke=0)
        c.setFillColor(light)
        c.drawString(mx + 28, iy, inv)
        iy -= 18
    y -= inv_h + 15

    # --- Lucky Numbers & Peak Years row ---
    col_w = (w - mx * 2 - 15) / 2
    lucky = ", ".join(str(n) for n in data.get("lucky_numbers", []))
    peak = data.get("peak_earning_years", "")
    for i, (label, val) in enumerate([
        ("LUCKY NUMBERS", lucky),
        ("PEAK EARNING YEARS", peak),
    ]):
        bx = mx + i * (col_w + 15)
        c.setFillColor(card)
        c.setStrokeColor(card_b)
        c.roundRect(bx, y - 50, col_w, 50, 8, fill=1, stroke=1)
        c.setFillColor(gray)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(bx + 12, y - 18, label)
        c.setFillColor(gold)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(bx + 12, y - 38, val)

    c.showPage()

    # ====== PAGE 3: Monthly Forecast + Mantra ======
    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    y = h - 50

    # Header
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, y, "6-MONTH MONEY FORECAST")
    # Stars flanking title
    for i in range(3):
        draw_star(c, w / 2 - 140 + i * 12, y + 5, 4, gold_d)
        draw_star(c, w / 2 + 120 + i * 12, y + 5, 4, gold_d)
    y -= 8
    c.setFillColor(gold_d)
    c.rect(w / 2 - 80, y, 160, 1.5, fill=1, stroke=0)
    y -= 30

    for mf in data.get("monthly_forecast", []):
        c.setFillColor(card)
        c.setStrokeColor(card_b)
        c.roundRect(mx, y - 55, w - mx * 2, 55, 8, fill=1, stroke=1)

        # Month name
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(mx + 15, y - 20, mf.get("month", ""))

        # Star rating (drawn stars, not Unicode)
        stars = mf.get("stars", 3)
        for i in range(5):
            sx = mx + 180 + i * 18
            if i < stars:
                draw_star(c, sx, y - 16, 6, gold)
            else:
                draw_star(c, sx, y - 16, 6, Color(0.3, 0.3, 0.4))

        # Insight
        c.setFillColor(gray)
        c.setFont("Helvetica", 9)
        insight = mf.get("insight", "")[:90]
        c.drawString(mx + 15, y - 42, insight)

        y -= 65

    y -= 5

    # --- Power Mantra box ---
    mantra = data.get("power_mantra", "")
    c.setFillColor(card)
    c.setStrokeColor(gold_dim)
    c.roundRect(mx, y - 70, w - mx * 2, 70, 10, fill=1, stroke=1)
    # Gold accent
    c.setFillColor(gold)
    c.roundRect(mx, y - 3, w - mx * 2, 3, 1, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w / 2, y - 22, "YOUR POWER MANTRA")
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 13)
    mantra_display = mantra if len(mantra) < 70 else mantra[:67] + "..."
    c.drawCentredString(w / 2, y - 48, f'"{mantra_display}"')
    y -= 85

    # --- Cosmic Advice box ---
    advice = data.get("cosmic_advice", "")
    advice_lines = wrap_text(c, advice, "Helvetica", 10, w - mx * 2 - 30)
    adv_h = len(advice_lines) * 15 + 35
    c.setFillColor(card)
    c.setStrokeColor(card_b)
    c.roundRect(mx, y - adv_h, w - mx * 2, adv_h, 8, fill=1, stroke=1)
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(mx + 15, y - 20, "COSMIC ADVICE")
    c.setFillColor(light)
    c.setFont("Helvetica", 10)
    ay = y - 38
    for line in advice_lines:
        c.drawString(mx + 15, ay, line)
        ay -= 15
    y -= adv_h + 20

    # --- CTA Footer ---
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, y, "Ready to activate your Money Star Map?")
    y -= 18
    c.setFillColor(white)
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, y, "Join The Money Glow-Up  |  Oct 17-19, 2026  |  Miami Beach")
    y -= 16
    c.setFillColor(gray)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, y, "mreaymoney.com  |  For entertainment & educational purposes only")

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
    if not GEMINI_API_KEY:
        return jsonify({"error": "Chat is currently unavailable. API key not configured."}), 503

    try:
        from google import genai
    except ImportError:
        return jsonify({"error": "Google GenAI SDK not installed."}), 503

    data = request.json or {}
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"error": "No messages provided."}), 400

    messages = messages[-20:]

    # Convert messages to Gemini format
    gemini_contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    def generate():
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=gemini_contents,
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "max_output_tokens": 1024,
                },
            )
            for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
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


def pcm_to_wav(pcm_data, sample_rate=24000, channels=1, sample_width=2):
    """Convert raw PCM audio to WAV format."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    buf.seek(0)
    return buf.read()


@app.route("/api/voice", methods=["POST"])
def voice_chat():
    """Accept audio, transcribe with Gemini, get response + TTS audio back."""
    if not GEMINI_API_KEY:
        return jsonify({"error": "Voice chat unavailable. API key not configured."}), 503

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return jsonify({"error": "Google GenAI SDK not installed."}), 503

    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided."}), 400

    audio_file = request.files["audio"]
    audio_bytes = audio_file.read()

    if len(audio_bytes) < 100:
        return jsonify({"error": "Audio too short."}), 400

    history_json = request.form.get("history", "[]")
    try:
        history = json.loads(history_json)
    except json.JSONDecodeError:
        history = []

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Step 1: Transcribe audio with Gemini
    print(f"[Voice] Step 1: Transcribing {len(audio_bytes)} bytes of audio...")
    try:
        transcribe_resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type="audio/webm"),
                "Transcribe this audio exactly. Return ONLY the transcription, nothing else.",
            ],
        )
        user_text = transcribe_resp.text.strip()
        print(f"[Voice] Step 1 done: '{user_text[:80]}'")
        if not user_text:
            return jsonify({"error": "Couldn't understand the audio. Try again."}), 400
    except Exception as e:
        print(f"[Voice] Step 1 FAILED: {e}")
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

    # Step 2: Get Mr. Easy Money text response
    history = history[-18:]
    gemini_contents = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        gemini_contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    gemini_contents.append({"role": "user", "parts": [{"text": user_text}]})

    print(f"[Voice] Step 2: Generating response...")
    try:
        chat_resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=gemini_contents,
            config={
                "system_instruction": SYSTEM_PROMPT + "\nCRITICAL: This is voice mode. Keep responses to 1-2 SHORT sentences max. Be extremely concise and punchy. No long explanations.\nIMPORTANT: You have a signature verbal tic — you casually drop 'bitch' at the end of sentences in an affectionate, hype-man way (like Jesse Pinkman or a best friend hyping you up). Examples: 'Let's make that money grow, bitch!', 'You're about to be debt-free, bitch!', 'Index funds, bitch — that's the move.' Use it naturally once per response, never mean-spirited, always celebratory.",
                "max_output_tokens": 150,
            },
        )
        assistant_text = chat_resp.text.strip()
        print(f"[Voice] Step 2 done: '{assistant_text[:80]}'")
    except Exception as e:
        print(f"[Voice] Step 2 FAILED: {e}")
        return jsonify({"error": f"Response generation failed: {str(e)}"}), 500

    print(f"[Voice] Done! Returning text (TTS via separate /api/tts call)")
    return jsonify({
        "user_text": user_text,
        "assistant_text": assistant_text,
    })


@app.route("/api/tts", methods=["POST"])
def tts():
    """Generate TTS audio for given text. Separate endpoint so voice chat isn't blocked."""
    if not GEMINI_API_KEY:
        return jsonify({"error": "TTS unavailable."}), 503

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return jsonify({"error": "SDK not installed."}), 503

    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided."}), 400

    # Keep TTS short — max 2 complete sentences, max 200 chars
    # This keeps generation under ~8 seconds
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    tts_text = ""
    count = 0
    for s in sentences:
        if count >= 2 or len(tts_text) + len(s) > 200:
            break
        tts_text += s + " "
        count += 1
    text = tts_text.strip() or text[:200]

    print(f"[TTS] Generating for {len(text)} chars...")
    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        tts_resp = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=f"Read the following text aloud naturally and expressively:\n\n{text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name="Puck"
                        )
                    )
                ),
            ),
        )
        for part in tts_resp.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                wav_data = pcm_to_wav(part.inline_data.data)
                print(f"[TTS] Done: {len(wav_data)} bytes WAV")
                return Response(wav_data, mimetype="audio/wav")

        return jsonify({"error": "No audio generated."}), 500
    except Exception as e:
        print(f"[TTS] FAILED: {e}")
        return jsonify({"error": str(e)}), 500


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

    # Use Gemini to generate the reading
    reading_data = None
    if GEMINI_API_KEY:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Generate a Money Star Map for:\nName: {name}\nBirth Date: {birth_date} ({sign})\nBirth Place: {birth_place}\n\nCurrent date: {datetime.now().strftime('%B %Y')}",
                config={
                    "system_instruction": STARMAP_PROMPT,
                    "max_output_tokens": 2048,
                },
            )
            raw = resp.text.strip()
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
