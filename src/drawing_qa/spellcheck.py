"""Spell checking for drawing titles with MEP/construction terminology."""

from __future__ import annotations

import re

from spellchecker import SpellChecker

# Alphanumeric drawing codes (B1M, L00, M1, 00A) are not English words.
_CODE_LIKE = re.compile(r"^(?:[A-Za-z]{1,3}\d+[A-Za-z0-9]*|\d+[A-Za-z]{1,3})$")
# Token immediately after Level / Lvl is a storey code (LG, GF, B1M, 03-13).
_LEVEL_FOLLOWER = re.compile(
    r"(?i)\b(?:levels?|lvl)\s+([A-Za-z0-9]+(?:\s*-\s*[A-Za-z0-9]+)?)"
)


def get_mep_construction_terms() -> set[str]:
    """Return comprehensive set of MEP and construction terms to whitelist.

    These are technical terms, acronyms, and common words used in mechanical,
    electrical, plumbing, and construction drawings that should not be flagged
    as spelling errors.
    """
    return {
        # === MEP Systems ===
        "hvac",
        "mep",
        "meph",  # MEP + Health (includes public health)
        # === Plumbing / Drainage ===
        "svp",  # Soil Vent Pipe
        "rwp",  # Rain Water Pipe
        "cwp",  # Cold Water Pipe
        "hwp",  # Hot Water Pipe
        "dhw",  # Domestic Hot Water
        "cws",  # Cold Water Supply
        "hws",  # Hot Water Supply
        "lthw",  # Low Temperature Hot Water
        "mthw",  # Medium Temperature Hot Water
        "hhw",  # High Temperature Hot Water
        "chw",  # Chilled Water
        "cwr",  # Chilled Water Return
        "chwr",  # Chilled Water Return
        "cwst",  # Cold Water Storage Tank
        "hwst",  # Hot Water Storage Tank
        "pwc",  # Potable Water Cold
        "pwh",  # Potable Water Hot
        "wc",  # Water Closet / Toilet
        "whb",  # Wash Hand Basin
        "cwsc",  # Cold Water Storage Cistern
        "foul",
        "soakaway",
        "gully",
        "gulley",
        "manhole",
        "rodding",
        "inspection",
        "interceptor",
        # === HVAC Equipment ===
        "fcu",  # Fan Coil Unit
        "ahu",  # Air Handling Unit
        "vrf",  # Variable Refrigerant Flow
        "vrv",  # Variable Refrigerant Volume (Daikin trademark)
        "vav",  # Variable Air Volume
        "cav",  # Constant Air Volume
        "hiu",  # Heat Interface Unit
        "mvhr",  # Mechanical Ventilation Heat Recovery
        "aov",  # Automatic Opening Vent
        "bms",  # Building Management System
        "bcms",  # Building Control Management System
        "trvs",  # Thermostatic Radiator Valves
        "trv",
        "radiator",
        "radiators",
        "underfloor",
        "ufh",  # Underfloor Heating
        "riser",
        "risers",
        "ductwork",
        "duct",
        "ducts",
        "extract",
        "supply",
        "exhaust",
        "ventilation",
        "attenuator",
        "attenuators",
        "grille",
        "grilles",
        "diffuser",
        "diffusers",
        "louvre",
        "louvres",
        "damper",
        "dampers",
        "splitter",
        "plenum",
        "chiller",
        "boiler",
        "calorifier",
        "plantroom",
        "plant",
        "pressurisation",
        "pressurization",
        # === Electrical ===
        "lv",  # Low Voltage
        "hv",  # High Voltage
        "elv",  # Extra Low Voltage
        "db",  # Distribution Board
        "mdb",  # Main Distribution Board
        "sdb",  # Sub Distribution Board
        "mcb",  # Miniature Circuit Breaker
        "rcd",  # Residual Current Device
        "rcbo",  # RCD + MCB
        "mccb",  # Moulded Case Circuit Breaker
        "ups",  # Uninterruptible Power Supply
        "pdu",  # Power Distribution Unit
        "led",
        "luminaire",
        "luminaires",
        "lux",
        "cctv",
        "av",  # Audio Visual
        "matv",  # Master Antenna Television
        "smatv",  # Satellite Master Antenna Television
        "cableway",
        "tray",
        "trunking",
        "conduit",
        "containment",
        "busbar",
        "busbars",
        "earthing",
        "bonding",
        "switchgear",
        "transformer",
        "substation",
        "feeder",
        "socket",
        "sockets",
        "pir",  # Passive Infrared (sensor)
        "photoelectric",
        "occupancy",
        # === Fire Safety ===
        "sprinkler",
        "sprinklers",
        "suppression",
        "afd",  # Automatic Fire Detection
        "vesda",  # Very Early Smoke Detection Apparatus
        "fd",  # Fire Damper
        "fsd",  # Fire Smoke Damper
        "aov",  # Automatic Opening Vent (also HVAC)
        "smoke",
        "detector",
        "detectors",
        "sounders",
        "sounder",
        "callpoint",
        "callpoints",
        "extinguisher",
        "extinguishers",
        "hydrant",
        "hydrants",
        "riser",  # Dry/wet riser (also HVAC)
        "hose",
        "reel",
        "compartmentation",
        "intumescent",
        # === General Construction / Architectural ===
        "dwg",  # Drawing
        "drg",  # Drawing
        "rev",  # Revision
        "ga",  # General Arrangement
        "nts",  # Not To Scale
        "typ",  # Typical
        "rcp",  # Reflected Ceiling Plan
        "sht",  # Sheet
        "shts",  # Sheets
        "flr",  # Floor
        "lvl",  # Level
        "lg",  # Lower Ground
        "ug",  # Upper Ground
        "gf",  # Ground Floor
        "mez",  # Mezzanine
        "mezzanine",
        "rf",  # Roof
        "rfl",  # Roof Level
        "mezz",
        "storey",
        "storeys",
        "slab",
        "soffit",
        "bulkhead",
        "void",
        "riser",
        "shaft",
        "corridor",
        "corridors",
        "lobby",
        "lobbies",
        "stairwell",
        "staircase",
        "staircore",
        "stair",
        "stairs",
        "lift",
        "lifts",
        "apartment",
        "apartments",
        "apts",
        "apt",
        "resi",  # Residential
        "residential",
        "communal",
        "retail",
        "commercial",
        "carpark",
        "basement",
        "substation",
        "cupboard",
        "cupboards",
        "riser",
        "risers",
        "blockwork",
        "brickwork",
        "steelwork",
        "precast",
        "insitu",
        "screed",
        "dpm",  # Damp Proof Membrane
        "vapour",  # UK spelling
        "waterproofing",
        "tanking",
        # === ISO 19650 / Document Control ===
        "suitability",
        "wip",  # Work In Progress
        "info",  # For Information
        "coord",  # Coordination
        "originator",
        "volume",
        "deliverable",
        # === Room Types / Spaces ===
        "bedroom",
        "bedrooms",
        "bathroom",
        "bathrooms",
        "ensuite",
        "ensuites",
        "kitchen",
        "kitchens",
        "kitchenette",
        "living",
        "lounge",
        "dining",
        "utility",
        "wc",  # Also plumbing
        "toilet",
        "toilets",
        "washroom",
        "washrooms",
        "shower",
        "showers",
        "balcony",
        "balconies",
        "terrace",
        "terraces",
        "walkway",
        "walkways",
        "foyer",
        "reception",
        "entrance",
        "atrium",
        "bin",
        "bins",
        "refuse",
        "recycling",
        "cycle",
        "cycles",
        "parking",
        "meter",
        "meters",
        "comms",  # Communications
        "server",
        "storage",
        # === Directional / Orientation ===
        "north",
        "south",
        "east",
        "west",
        "ne",
        "nw",
        "se",
        "sw",
        "elevation",
        "elevations",
        "section",
        "sections",
        "axonometric",
        "isometric",
        "detail",
        "details",
        # === Common Drawing Descriptors ===
        "layout",
        "layouts",
        "plan",
        "plans",
        "floor",
        "floors",
        "proposed",
        "existing",
        "demolition",
        "new",
        "amended",
        "enlarged",
        "location",
        "key",
        "index",
        "schedule",
        "schedules",
        "schematic",
        "schematics",
        "diagram",
        "diagrams",
        "single",
        "line",
        "sld",  # Single Line Diagram
        "riser",  # Also a physical component
        "circuit",
        "circuits",
        "zone",
        "zones",
        "area",
        "areas",
        "block",
        "blocks",
        "core",
        "cores",
        "tower",
        "towers",
        "wing",
        "wings",
        "podium",
        "basement",
        "substructure",
        "superstructure",
        # === Units / Measurements (UK preference) ===
        "metre",
        "metres",
        "mm",
        "millimetre",
        "millimetres",
        "litre",
        "litres",
        "kw",  # Kilowatt
        "kwh",
        "mw",
        "pa",  # Pascals
        "cfm",  # Cubic Feet per Minute (still used in UK)
        "ach",  # Air Changes per Hour
        # === Phases / Stages ===
        "phase",
        "phases",
        "stage",
        "stages",
        "tender",
        "construction",
        "procurement",
        "feasibility",
        "concept",
        "developed",
        "technical",
        "handover",
        "completion",
        # === Common Abbreviations ===
        "incl",  # Including
        "excl",  # Excluding
        "max",
        "min",
        "approx",
        "qty",  # Quantity
        "no",  # Number
        "nos",  # Numbers
        "ref",  # Reference
        "tbc",  # To Be Confirmed
        "tbd",  # To Be Determined
        "n/a",
        "dia",  # Diameter
        # === Specific Equipment / Products ===
        "vav",
        "pir",
        "vsd",  # Variable Speed Drive
        "inverter",
        "inverters",
        "pump",
        "pumps",
        "fan",
        "fans",
        "valve",
        "valves",
        "isolator",
        "isolators",
        "sensor",
        "sensors",
        "controller",
        "controllers",
        "panel",
        "panels",
        "fitting",
        "fittings",
        "pipework",
        "pipe",
        "pipes",
        "manifold",
        "header",
        "tank",
        "tanks",
        "cylinder",
        "cylinders",
        "vessel",
        "vessels",
        "coil",
        "coils",
        "heat",
        "exchanger",
        "exchangers",
        "filter",
        "filters",
    }


def _level_code_tokens(text: str) -> set[str]:
    """Tokens that follow 'Level' / 'Lvl' and should not be spell-checked."""
    found: set[str] = set()
    for match in _LEVEL_FOLLOWER.finditer(text):
        token = match.group(1).lower()
        found.add(token)
        found.add("".join(c for c in token if c.isalpha()))
        for part in re.split(r"[\s\-]+", token):
            if part:
                found.add(part)
                found.add("".join(c for c in part if c.isalpha()))
    found.discard("")
    return found


def _should_skip_token(raw: str, level_codes: set[str]) -> bool:
    token = raw.strip(".,;:()[]{}'\"")
    if not token:
        return True
    lowered = token.lower()
    if lowered in level_codes:
        return True
    if any(ch.isdigit() for ch in token):
        return True
    if _CODE_LIKE.fullmatch(token):
        return True
    return False


def check_spelling(
    text: str | None,
    custom_terms: set[str] | None = None,
    language: str = "en_GB",
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Check spelling in text and return unknown words with suggestions.

    Args:
        text: Text to check for spelling errors
        custom_terms: Additional terms to whitelist (beyond MEP/construction defaults)
        language: Language code ('en_GB' for UK English, 'en_US' for US English)
                 Note: pyspellchecker uses 'en' for English; UK/US distinction is
                 handled through custom dictionary

    Returns:
        Tuple of (misspelled_words, suggestions)
        - misspelled_words: List of words not in dictionary
        - suggestions: List of (word, [suggestion1, suggestion2, ...]) tuples
    """
    if not text or not text.strip():
        return [], []

    # pyspellchecker uses 'en' for English, not 'en_GB' or 'en_US'
    # We'll use 'en' and add UK-specific spellings to custom dictionary
    lang_code = "en" if language.startswith("en") else language
    try:
        spell = SpellChecker(language=lang_code)
    except (ValueError, FileNotFoundError, OSError):
        return [], []

    # Add MEP/construction terms to dictionary
    default_terms = get_mep_construction_terms()
    
    # Add UK-specific spellings to support en_GB
    uk_spellings = {
        "metre", "metres", "centimetre", "centimetres", "millimetre", "millimetres",
        "litre", "litres", "colour", "colours", "honour", "honours",
        "vapour", "vapours", "behaviour", "centre", "centres",
        "fibre", "fibres", "calibre", "theatre", "manoeuvre",
    }
    default_terms = default_terms | uk_spellings
    
    spell.word_frequency.load_words(default_terms)

    # Add any additional custom terms
    if custom_terms:
        spell.word_frequency.load_words(custom_terms)

    # Extract words and check spelling
    # Split on spaces, hyphens, and common separators
    level_codes = _level_code_tokens(text)
    words = (
        text.lower()
        .replace("/", " ")
        .replace("&", " ")
        .replace("+", " ")
        .split()
    )

    # Filter out codes, mixed alphanumerics, and tokens after "Level"
    words_to_check = []
    for word in words:
        raw = word.replace("-", "")
        if _should_skip_token(word, level_codes) or _should_skip_token(raw, level_codes):
            continue
        pieces = word.replace("-", " ").split()
        for piece in pieces:
            if _should_skip_token(piece, level_codes):
                continue
            clean_word = "".join(c for c in piece if c.isalpha())
            if clean_word and len(clean_word) > 1:
                words_to_check.append(clean_word)

    # Find misspelled words
    misspelled = spell.unknown(words_to_check)

    if not misspelled:
        return [], []

    # Get suggestions for each misspelled word
    suggestions = []
    for word in sorted(misspelled):
        candidates = spell.candidates(word)
        if candidates:
            # Limit to top 3 suggestions
            top_suggestions = list(candidates)[:3]
            suggestions.append((word, top_suggestions))

    return sorted(misspelled), suggestions


def format_spelling_note(misspelled: list[str], suggestions: list[tuple[str, list[str]]]) -> str:
    """Format spelling errors and suggestions as a readable note.

    Args:
        misspelled: List of misspelled words
        suggestions: List of (word, [suggestions]) tuples

    Returns:
        Formatted string for display in report
    """
    if not misspelled:
        return ""

    parts = [f"Possible spelling errors: {', '.join(misspelled)}"]

    if suggestions:
        suggestion_texts = []
        for word, candidates in suggestions[:3]:  # Limit to 3 in note
            if candidates:
                suggestion_texts.append(f"'{word}' → {', '.join(candidates)}")
        if suggestion_texts:
            parts.append(f"Suggestions: {'; '.join(suggestion_texts)}")

    return " | ".join(parts)
