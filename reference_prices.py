"""
Reference price database for premium coffee machines.
Maps brand/model keywords to approximate UK retail prices (£).
Used to calculate arbitrage potential when matched against auction listings.
"""

# Format: { "search_key": {"brand": str, "model": str, "retail_gbp": int, "category": str} }
# Categories: "prosumer" (£400-2000), "commercial_single" (£2000-6000), "commercial_multi" (£5000+)

REFERENCE_MACHINES = {
    # === LA MARZOCCO (Top tier) ===
    "la marzocco linea mini": {"brand": "La Marzocco", "model": "Linea Mini", "retail_gbp": 3800, "category": "commercial_single"},
    "la marzocco linea mini r": {"brand": "La Marzocco", "model": "Linea Mini R", "retail_gbp": 4200, "category": "commercial_single"},
    "la marzocco gs3": {"brand": "La Marzocco", "model": "GS3", "retail_gbp": 6500, "category": "commercial_single"},
    "la marzocco gs3 av": {"brand": "La Marzocco", "model": "GS3 AV", "retail_gbp": 6500, "category": "commercial_single"},
    "la marzocco gs3 mp": {"brand": "La Marzocco", "model": "GS3 MP", "retail_gbp": 7000, "category": "commercial_single"},
    "la marzocco linea micra": {"brand": "La Marzocco", "model": "Linea Micra", "retail_gbp": 2800, "category": "commercial_single"},
    "la marzocco linea classic": {"brand": "La Marzocco", "model": "Linea Classic", "retail_gbp": 8000, "category": "commercial_multi"},
    "la marzocco linea pb": {"brand": "La Marzocco", "model": "Linea PB", "retail_gbp": 12000, "category": "commercial_multi"},
    "la marzocco strada": {"brand": "La Marzocco", "model": "Strada", "retail_gbp": 15000, "category": "commercial_multi"},
    "la marzocco kb90": {"brand": "La Marzocco", "model": "KB90", "retail_gbp": 16000, "category": "commercial_multi"},

    # === SAGE / BREVILLE (Prosumer) ===
    "sage barista express": {"brand": "Sage", "model": "Barista Express", "retail_gbp": 550, "category": "prosumer"},
    "sage barista pro": {"brand": "Sage", "model": "Barista Pro", "retail_gbp": 700, "category": "prosumer"},
    "sage barista touch": {"brand": "Sage", "model": "Barista Touch", "retail_gbp": 900, "category": "prosumer"},
    "sage barista touch impress": {"brand": "Sage", "model": "Barista Touch Impress", "retail_gbp": 1100, "category": "prosumer"},
    "sage dual boiler": {"brand": "Sage", "model": "Dual Boiler", "retail_gbp": 1300, "category": "prosumer"},
    "sage oracle": {"brand": "Sage", "model": "Oracle", "retail_gbp": 1700, "category": "prosumer"},
    "sage oracle touch": {"brand": "Sage", "model": "Oracle Touch", "retail_gbp": 2000, "category": "prosumer"},
    "sage oracle jet": {"brand": "Sage", "model": "Oracle Jet", "retail_gbp": 2200, "category": "prosumer"},
    "sage bambino": {"brand": "Sage", "model": "Bambino", "retail_gbp": 300, "category": "prosumer"},
    "sage bambino plus": {"brand": "Sage", "model": "Bambino Plus", "retail_gbp": 400, "category": "prosumer"},

    # === DE'LONGHI (Prosumer) ===
    "delonghi specialista": {"brand": "De'Longhi", "model": "Specialista", "retail_gbp": 500, "category": "prosumer"},
    "delonghi specialista arte": {"brand": "De'Longhi", "model": "Specialista Arte", "retail_gbp": 450, "category": "prosumer"},
    "delonghi specialista maestro": {"brand": "De'Longhi", "model": "Specialista Maestro", "retail_gbp": 700, "category": "prosumer"},
    "delonghi specialista opera": {"brand": "De'Longhi", "model": "Specialista Opera", "retail_gbp": 900, "category": "prosumer"},
    "delonghi la specialista prestigio": {"brand": "De'Longhi", "model": "La Specialista Prestigio", "retail_gbp": 800, "category": "prosumer"},
    "delonghi magnifica evo": {"brand": "De'Longhi", "model": "Magnifica Evo", "retail_gbp": 450, "category": "prosumer"},
    "delonghi eletta explore": {"brand": "De'Longhi", "model": "Eletta Explore", "retail_gbp": 900, "category": "prosumer"},
    "delonghi primadonna soul": {"brand": "De'Longhi", "model": "PrimaDonna Soul", "retail_gbp": 1200, "category": "prosumer"},
    "delonghi rivelia": {"brand": "De'Longhi", "model": "Rivelia", "retail_gbp": 800, "category": "prosumer"},

    # === ROCKET ESPRESSO ===
    "rocket appartamento": {"brand": "Rocket", "model": "Appartamento", "retail_gbp": 1400, "category": "prosumer"},
    "rocket mozzafiato": {"brand": "Rocket", "model": "Mozzafiato", "retail_gbp": 1800, "category": "prosumer"},
    "rocket giotto": {"brand": "Rocket", "model": "Giotto", "retail_gbp": 2200, "category": "commercial_single"},
    "rocket r58": {"brand": "Rocket", "model": "R58", "retail_gbp": 2400, "category": "commercial_single"},
    "rocket r nine one": {"brand": "Rocket", "model": "R Nine One", "retail_gbp": 3500, "category": "commercial_single"},

    # === ECM ===
    "ecm synchronika": {"brand": "ECM", "model": "Synchronika", "retail_gbp": 2600, "category": "commercial_single"},
    "ecm mechanika": {"brand": "ECM", "model": "Mechanika", "retail_gbp": 1800, "category": "prosumer"},
    "ecm technika": {"brand": "ECM", "model": "Technika", "retail_gbp": 2800, "category": "commercial_single"},
    "ecm classika": {"brand": "ECM", "model": "Classika", "retail_gbp": 1200, "category": "prosumer"},

    # === LELIT ===
    "lelit bianca": {"brand": "Lelit", "model": "Bianca", "retail_gbp": 2000, "category": "prosumer"},
    "lelit mara x": {"brand": "Lelit", "model": "Mara X", "retail_gbp": 1200, "category": "prosumer"},
    "lelit elizabeth": {"brand": "Lelit", "model": "Elizabeth", "retail_gbp": 1100, "category": "prosumer"},

    # === VICTORIA ARDUINO ===
    "victoria arduino eagle one": {"brand": "Victoria Arduino", "model": "Eagle One", "retail_gbp": 5000, "category": "commercial_single"},
    "victoria arduino eagle one prima": {"brand": "Victoria Arduino", "model": "Eagle One Prima", "retail_gbp": 3200, "category": "commercial_single"},
    "victoria arduino mythos": {"brand": "Victoria Arduino", "model": "Mythos (Grinder)", "retail_gbp": 3000, "category": "commercial_single"},

    # === NUOVA SIMONELLI ===
    "nuova simonelli oscar": {"brand": "Nuova Simonelli", "model": "Oscar II", "retail_gbp": 900, "category": "prosumer"},
    "nuova simonelli musica": {"brand": "Nuova Simonelli", "model": "Musica", "retail_gbp": 1200, "category": "prosumer"},
    "nuova simonelli aurelia": {"brand": "Nuova Simonelli", "model": "Aurelia", "retail_gbp": 8000, "category": "commercial_multi"},
    "nuova simonelli appia": {"brand": "Nuova Simonelli", "model": "Appia", "retail_gbp": 5000, "category": "commercial_multi"},

    # === SANREMO ===
    "sanremo cafe racer": {"brand": "Sanremo", "model": "Café Racer", "retail_gbp": 10000, "category": "commercial_multi"},
    "sanremo zoe": {"brand": "Sanremo", "model": "Zoe", "retail_gbp": 4000, "category": "commercial_multi"},
    "sanremo you": {"brand": "Sanremo", "model": "YOU", "retail_gbp": 2500, "category": "commercial_single"},

    # === PREMIUM GRINDERS (also arbitrageable) ===
    "mazzer mini": {"brand": "Mazzer", "model": "Mini", "retail_gbp": 600, "category": "prosumer"},
    "mazzer super jolly": {"brand": "Mazzer", "model": "Super Jolly", "retail_gbp": 800, "category": "prosumer"},
    "mazzer major": {"brand": "Mazzer", "model": "Major", "retail_gbp": 1200, "category": "commercial_single"},
    "mazzer robur": {"brand": "Mazzer", "model": "Robur", "retail_gbp": 2000, "category": "commercial_single"},
    "eureka mignon": {"brand": "Eureka", "model": "Mignon", "retail_gbp": 400, "category": "prosumer"},
    "eureka atom": {"brand": "Eureka", "model": "Atom", "retail_gbp": 700, "category": "prosumer"},
    "mahlkonig ek43": {"brand": "Mahlkönig", "model": "EK43", "retail_gbp": 2500, "category": "commercial_single"},
    "mahlkonig e65s": {"brand": "Mahlkönig", "model": "E65S", "retail_gbp": 1800, "category": "commercial_single"},
    "niche zero": {"brand": "Niche", "model": "Zero", "retail_gbp": 500, "category": "prosumer"},
    "niche duo": {"brand": "Niche", "model": "Duo", "retail_gbp": 600, "category": "prosumer"},
    "ceado e37": {"brand": "Ceado", "model": "E37", "retail_gbp": 1500, "category": "commercial_single"},

    # === OTHER PREMIUM BRANDS ===
    "dalla corte mina": {"brand": "Dalla Corte", "model": "Mina", "retail_gbp": 3500, "category": "commercial_single"},
    "slayer single group": {"brand": "Slayer", "model": "Single Group", "retail_gbp": 8000, "category": "commercial_single"},
    "decent de1": {"brand": "Decent", "model": "DE1", "retail_gbp": 3500, "category": "commercial_single"},
    "profitec pro 700": {"brand": "Profitec", "model": "Pro 700", "retail_gbp": 2200, "category": "commercial_single"},
    "profitec pro 600": {"brand": "Profitec", "model": "Pro 600", "retail_gbp": 1600, "category": "prosumer"},
    "ascaso steel duo": {"brand": "Ascaso", "model": "Steel Duo PID", "retail_gbp": 1400, "category": "prosumer"},

    # === JURA (Bean-to-cup premium) ===
    "jura z10": {"brand": "Jura", "model": "Z10", "retail_gbp": 2500, "category": "prosumer"},
    "jura z8": {"brand": "Jura", "model": "Z8", "retail_gbp": 2200, "category": "prosumer"},
    "jura s8": {"brand": "Jura", "model": "S8", "retail_gbp": 1300, "category": "prosumer"},
    "jura e8": {"brand": "Jura", "model": "E8", "retail_gbp": 1200, "category": "prosumer"},
    "jura giga": {"brand": "Jura", "model": "GIGA", "retail_gbp": 4500, "category": "commercial_single"},
}

# Simplified keyword matching: brand aliases to catch variations
BRAND_ALIASES = {
    "delonghi": ["de'longhi", "de longhi", "delonghi"],
    "la marzocco": ["lamarzocco", "la marzocco", "lm", "marzocco"],
    "sage": ["sage", "breville"],
    "victoria arduino": ["victoria arduino", "va"],
    "nuova simonelli": ["nuova simonelli", "simonelli"],
    "mahlkonig": ["mahlkonig", "mahlkönig", "mahlkoenig"],
}


def match_listing_to_reference(listing_title: str) -> dict | None:
    """
    Try to match a listing title to a known machine in the reference database.
    Returns the reference entry if matched, None otherwise.
    """
    title_lower = listing_title.lower()

    # Direct substring matching against reference keys (most reliable)
    best_match = None
    best_match_len = 0

    for key, ref in REFERENCE_MACHINES.items():
        if key in title_lower and len(key) > best_match_len:
            best_match = ref
            best_match_len = len(key)

    if best_match:
        return best_match

    # Fallback: check for brand + model fragments
    for key, ref in REFERENCE_MACHINES.items():
        brand_lower = ref["brand"].lower()
        model_lower = ref["model"].lower()
        # Check if both brand and model appear somewhere in the title
        brand_found = brand_lower in title_lower
        # Also check aliases
        if not brand_found:
            for alias_key, aliases in BRAND_ALIASES.items():
                if alias_key == brand_lower or brand_lower in aliases:
                    brand_found = any(a in title_lower for a in aliases)
                    break
        if brand_found and model_lower in title_lower:
            if len(key) > best_match_len:
                best_match = ref
                best_match_len = len(key)

    return best_match


def calculate_arbitrage(current_price_gbp: float, ref: dict) -> dict:
    """Calculate arbitrage metrics for a matched listing."""
    retail = ref["retail_gbp"]
    discount_pct = ((retail - current_price_gbp) / retail) * 100
    potential_profit = retail - current_price_gbp
    # Conservative resale estimate: 60-70% of retail for refurbished
    conservative_resale = retail * 0.65
    conservative_profit = conservative_resale - current_price_gbp
    return {
        "retail_price": retail,
        "current_price": current_price_gbp,
        "discount_pct": round(discount_pct, 1),
        "gross_potential": round(potential_profit, 2),
        "conservative_resale": round(conservative_resale, 2),
        "conservative_profit": round(conservative_profit, 2),
        "rating": "🔥 STRONG BUY" if discount_pct >= 60 else "✅ GOOD DEAL" if discount_pct >= 40 else "⚠️ FAIR" if discount_pct >= 20 else "❌ OVERPRICED"
    }
