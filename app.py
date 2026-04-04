import os
import json
from flask import Flask, request, Response, render_template, stream_with_context, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
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


@app.route("/")
def index():
    return render_template("index.html")


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

    # Limit conversation history to last 20 messages to control costs
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


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
