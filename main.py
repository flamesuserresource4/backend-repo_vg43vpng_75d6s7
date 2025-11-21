import os
import random
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ActivateRequest(BaseModel):
    session_id: str


class ReadRequest(BaseModel):
    session_id: str


# Simple tarot deck (mystical archetypes). In a full build, replace/extend with complete deck.
TAROT_DECK = [
    {
        "name": "The Moon",
        "symbol": "🌙",
        "meaning": "intuition, dreams, hidden waters",
        "whisper": "Trust the tide beneath the mind."
    },
    {
        "name": "The Star",
        "symbol": "✨",
        "meaning": "healing, hope, luminous guidance",
        "whisper": "A silver thread is guiding you home."
    },
    {
        "name": "The Tower",
        "symbol": "🗼",
        "meaning": "revelation, rupture, divine reset",
        "whisper": "What falls was never yours to carry."
    },
    {
        "name": "The Empress",
        "symbol": "🌿",
        "meaning": "creation, sweetness, fertile ground",
        "whisper": "What you tend will bloom."
    },
    {
        "name": "The Magician",
        "symbol": "🜂",
        "meaning": "will, craft, manifestation",
        "whisper": "As within, so without — choose and conjure."
    },
    {
        "name": "Death",
        "symbol": "🦋",
        "meaning": "transmutation, ending, sacred molt",
        "whisper": "Shed the husk; the wings are ready."
    },
    {
        "name": "The Lovers",
        "symbol": "💫",
        "meaning": "union, choice, mirrored flame",
        "whisper": "What you vow to becomes you."
    },
    {
        "name": "The Hermit",
        "symbol": "🕯️",
        "meaning": "solitude, lantern, inner path",
        "whisper": "Go inward; there is a door only you can open."
    },
]


def get_session_count(session_id: str) -> int:
    doc = db["session"].find_one({"session_id": session_id})
    return int(doc.get("count", 0)) if doc else 0


def increment_session_count(session_id: str) -> int:
    now = datetime.now(timezone.utc)
    result = db["session"].find_one_and_update(
        {"session_id": session_id},
        {"$inc": {"count": 1}, "$setOnInsert": {"created_at": now}, "$set": {"updated_at": now}},
        upsert=True,
        return_document=True,
    )
    # find_one_and_update may return None on some drivers with upsert; ensure fetch
    if result is None:
        doc = db["session"].find_one({"session_id": session_id})
        return int(doc.get("count", 1)) if doc else 1
    return int(result.get("count", 1))


@app.get("/")
def read_root():
    return {"message": "Madame of the Moon • Oracle online"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.post("/api/activate")
def activate(req: ActivateRequest):
    # Ensure session exists without incrementing count
    existing = db["session"].find_one({"session_id": req.session_id})
    if not existing:
        now = datetime.now(timezone.utc)
        db["session"].insert_one({
            "session_id": req.session_id,
            "count": 0,
            "created_at": now,
            "updated_at": now,
        })
    return {
        "phrase": "The oracle is awakened. The first card already vibrates between the veils.",
        "status": "ready",
    }


def build_reading(cards: List[Dict[str, str]]) -> Dict[str, Any]:
    lines = []
    addressed = random.choice(["child of the Moon", "soul in crossing"])  # address form

    for idx, c in enumerate(cards, start=1):
        lines.append(
            f"{c['symbol']} Card {idx}: {c['name']} — {c['meaning']}. {c['whisper']}"
        )

    hint = (
        "It pulses behind the veil… holding a stronger destiny.\n"
        "A portal is opening… but it reveals itself only to those who dare to cross.\n"
        "The last card does not appear in public. I can reveal it ONLY inside the Portal…"
    )

    hook = random.choice([
        "Return tomorrow; I will feel new vibrations.",
        "Something new is coming… I will be here between the veils.",
    ])

    whisper = (
        f"{addressed}, hear me: "
        "I see threads tightening and loosening around you — a design seeking your permission.\n"
    )

    text = (
        "\n".join([
            whisper,
            *lines,
            "\n" + hint,
            "\n" + hook,
        ])
    )

    # Hidden sales flow CTA copy
    cta = {
        "cta": "Enter the Portal on WhatsApp to unveil the Hidden Card and receive a private ritual.",
        "cta_sub": "I can perform the lunar sweetening ritual to open your paths, but I need your permission…",
    }

    return {"cards": cards, "message": text, **cta}


FINAL_WARNING = (
    "If you do not act now, the veil will close. What was about to be revealed may be lost for entire cycles.\n"
    "Only with your energetic contribution can the portal remain open."
)

FINAL_BLOCK = (
    "The Oracle has been sealed after 3 visions. To continue your journey, you must activate the full ritual through the energy exchange."
)

FINAL_PORTAL = (
    "Child of the Moon… forcing the veils or acting with malice awakens the Shadow Return — a cycle of confusion, losses, and energetic disorder."
)


@app.post("/api/read")
def read_cards(req: ReadRequest):
    # Enforce total consultations via database-stored counter per session
    total = get_session_count(req.session_id)
    if total >= 3:
        return [
            {"name": "alert", "description": FINAL_WARNING}
        ]

    # Increment then generate reading
    current = increment_session_count(req.session_id)

    # Safety: if somehow exceeds
    if current > 3:
        return [
            {"name": "alert", "description": FINAL_BLOCK}
        ]

    picks = random.sample(TAROT_DECK, 3)
    payload = build_reading(picks)
    return payload


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
