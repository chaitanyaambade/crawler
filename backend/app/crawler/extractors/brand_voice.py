from __future__ import annotations

import re

from bs4 import BeautifulSoup


def analyze_brand_voice(pages: dict[str, str]) -> dict:
    """Analyze brand voice from website copy.

    Examines homepage and about page text to determine:
    - tone: overall communication tone
    - formality: formal / informal / neutral
    - person: first_person / second_person / third_person
    - personality: list of trait keywords

    Returns dict matching BrandVoice model fields.
    """
    # Collect text from homepage and about pages
    texts: list[str] = []
    for url, html in pages.items():
        url_lower = url.lower()
        # Focus on homepage and about-style pages (richest brand copy)
        is_homepage = url.rstrip("/").count("/") <= 3
        is_about = any(p in url_lower for p in ("/about", "/our-story", "/who-we-are", "/mission"))
        if is_homepage or is_about:
            soup = BeautifulSoup(html, "lxml")
            # Remove nav, footer, script, style — keep main body copy
            for tag in soup.find_all(["nav", "footer", "script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(" ", strip=True)
            if text:
                texts.append(text)

    if not texts:
        return {"tone": "", "formality": "", "person": "", "personality": []}

    combined = " ".join(texts)

    formality = _detect_formality(combined)
    person = _detect_person(combined)
    personality = _detect_personality(combined)
    tone = _detect_tone(formality, personality)

    return {
        "tone": tone,
        "formality": formality,
        "person": person,
        "personality": personality[:5],
    }


# ---------------------------------------------------------------------------
# Detection helpers
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")

# Contractions signal informal writing
_CONTRACTION_RE = re.compile(
    r"\b(?:don't|won't|can't|isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't"
    r"|wouldn't|couldn't|shouldn't|it's|that's|there's|here's|what's|who's"
    r"|let's|we're|they're|you're|we've|they've|you've|i'm|we'll|you'll"
    r"|they'll|he's|she's)\b",
    re.IGNORECASE,
)

# Formal markers
_FORMAL_RE = re.compile(
    r"\b(?:furthermore|moreover|therefore|consequently|nevertheless|notwithstanding"
    r"|henceforth|pursuant|whereas|hereby|herein|thereof|therein"
    r"|aforementioned|commence|endeavour|endeavor|facilitate|utilize"
    r"|subsequently|accordingly)\b",
    re.IGNORECASE,
)


def _detect_formality(text: str) -> str:
    """Classify formality as formal / informal / neutral."""
    words = text.split()
    word_count = len(words)
    if word_count < 20:
        return ""

    # Sentence length: long sentences → formal
    sentences = _SENTENCE_RE.findall(text)
    avg_sentence_len = (
        sum(len(s.split()) for s in sentences) / len(sentences)
        if sentences
        else 0
    )

    contractions = len(_CONTRACTION_RE.findall(text))
    formal_words = len(_FORMAL_RE.findall(text))

    # Exclamation marks signal informal / enthusiastic
    exclamations = text.count("!")

    score = 0.0  # positive = formal, negative = informal
    score += min(formal_words * 1.5, 5.0)
    score -= min(contractions * 0.8, 5.0)
    score -= min(exclamations * 0.5, 3.0)
    if avg_sentence_len > 20:
        score += 1.5
    elif avg_sentence_len < 12:
        score -= 1.5

    if score > 2.0:
        return "formal"
    if score < -1.5:
        return "informal"
    return "neutral"


def _detect_person(text: str) -> str:
    """Detect dominant grammatical person: first / second / third."""
    text_lower = text.lower()

    first = len(re.findall(r"\b(?:we|our|us)\b", text_lower))
    second = len(re.findall(r"\b(?:you|your|yours)\b", text_lower))
    third = len(re.findall(r"\b(?:they|their|theirs|the company|the team)\b", text_lower))

    total = first + second + third
    if total < 5:
        return ""

    if first >= second and first >= third:
        return "first_person"
    if second >= first and second >= third:
        return "second_person"
    return "third_person"


def _detect_personality(text: str) -> list[str]:
    """Detect personality traits from word patterns."""
    text_lower = text.lower()
    traits: list[str] = []

    patterns: list[tuple[str, list[str]]] = [
        ("professional", ["professional", "expert", "industry", "enterprise", "corporate"]),
        ("innovative", ["innovate", "innovation", "cutting-edge", "breakthrough", "revolutionary", "disrupt"]),
        ("friendly", ["friendly", "welcoming", "community", "together", "family", "join us"]),
        ("authoritative", ["leading", "trusted", "authority", "definitive", "proven", "established"]),
        ("playful", ["fun", "exciting", "awesome", "amazing", "love", "enjoy", "delight"]),
        ("empathetic", ["understand", "care", "support", "help you", "your needs", "listen"]),
        ("bold", ["bold", "fearless", "dare", "challenge", "ambition", "audacious"]),
        ("minimalist", ["simple", "clean", "minimal", "streamline", "effortless", "intuitive"]),
        ("technical", ["algorithm", "platform", "infrastructure", "scalable", "robust", "architecture"]),
        ("luxurious", ["premium", "luxury", "exclusive", "curated", "bespoke", "artisan"]),
    ]

    for trait, keywords in patterns:
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits >= 2:
            traits.append(trait)

    return traits


def _detect_tone(formality: str, personality: list[str]) -> str:
    """Derive overall tone from formality + personality signals."""
    if not formality and not personality:
        return ""

    # Map personality combos to tone labels
    p_set = set(personality)

    if "playful" in p_set or "friendly" in p_set:
        return "conversational"
    if "authoritative" in p_set and formality == "formal":
        return "authoritative"
    if "technical" in p_set:
        return "technical"
    if "empathetic" in p_set:
        return "empathetic"
    if "luxurious" in p_set:
        return "aspirational"
    if "bold" in p_set:
        return "bold"
    if "innovative" in p_set:
        return "inspirational"
    if formality == "formal":
        return "professional"
    if formality == "informal":
        return "casual"
    return "neutral"
