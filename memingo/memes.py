"""Curated, text-only classic meme vocabulary for the Memingo language.

The registry stores descriptive metadata, not copyrighted image or video assets.
"""
import re


_CLASSICS = (
    ("dancing-baby", "Dancing Baby", 1996, "vintage", "Early web 3D animation that became a viral hit.", ("baby", "animation", "web")),
    ("hamster-dance", "Hampster Dance", 1998, "vintage", "A looping hamster webpage from the early web.", ("hamster", "music", "web")),
    ("all-your-base", "All Your Base Are Belong To Us", 2001, "vintage", "A memorable game translation spread through forums and Flash edits.", ("gaming", "translation", "flash")),
    ("numa-numa", "Numa Numa", 2004, "viral", "A webcam performance that helped define viral-video culture.", ("webcam", "dance", "video")),
    ("rickroll", "Rickroll", 2007, "viral", "A bait-and-switch built around an unexpected music-video link.", ("link", "bait", "music")),
    ("trollface", "Trollface", 2008, "rage", "The iconic face of internet trolling and rage comics.", ("troll", "rage comic")),
    ("rage-guy", "Rage Guy", 2008, "rage", "A foundational character from the rage-comic era.", ("rage comic", "fffffffuuuuuu")),
    ("keyboard-cat", "Keyboard Cat", 2009, "viral", "A keyboard-playing cat used as a comedic video sign-off.", ("cat", "music", "video")),
    ("forever-alone", "Forever Alone", 2010, "rage", "A rage-comic character expressing loneliness through humor.", ("rage comic", "reaction")),
    ("double-rainbow", "Double Rainbow", 2010, "viral", "An enthusiastic reaction to seeing a double rainbow.", ("rainbow", "reaction", "video")),
    ("success-kid", "Success Kid", 2007, "reaction", "A small triumphant moment turned into a victory template.", ("success", "reaction")),
    ("nyan-cat", "Nyan Cat", 2011, "viral", "A pixel-art flying cat with a rainbow trail.", ("cat", "pixel", "rainbow")),
    ("bad-luck-brian", "Bad Luck Brian", 2012, "reaction", "A portrait used for stories of spectacular bad luck.", ("luck", "reaction")),
    ("overly-attached-girlfriend", "Overly Attached Girlfriend", 2012, "reaction", "A parody format about exaggerated attachment.", ("reaction", "parody")),
    ("doge", "Doge", 2013, "viral", "A Shiba Inu image paired with playful internal monologue.", ("shiba", "wow", "such", "much")),
    ("this-is-fine", "This Is Fine", 2013, "reaction", "A calm response to a situation that is clearly chaotic.", ("dog", "chaos", "reaction")),
    ("we-are-number-one", "We Are Number One", 2014, "dank", "A musical LazyTown moment that inspired community remixes.", ("music", "remix")),
    ("mlg-montage", "MLG Montage Parodies", 2014, "dank", "Fast-cut gaming edits with intentionally excessive effects.", ("gaming", "montage")),
    ("harambe", "Harambe", 2016, "viral", "A widely discussed internet phenomenon and its many references.", ("internet history",)),
    ("dat-boi", "Dat Boi", 2016, "dank", "A frog on a unicycle associated with absurdist humor.", ("frog", "unicycle")),
    ("arthur-fist", "Arthur Fist", 2016, "reaction", "A clenched fist used to express contained frustration.", ("reaction", "cartoon")),
    ("distracted-boyfriend", "Distracted Boyfriend", 2017, "reaction", "A stock-photo format for comparing competing priorities.", ("stock photo", "comparison")),
    ("mocking-spongebob", "Mocking SpongeBob", 2017, "reaction", "A sarcastic response format using alternating letter case.", ("spongebob", "sarcasm")),
    ("ugandan-knuckles", "Ugandan Knuckles", 2017, "dank", "A 3D character popularized in social VR spaces.", ("vr", "3d")),
    ("expanding-brain", "Expanding Brain", 2017, "dank", "A visual ladder of increasingly exaggerated ideas.", ("brain", "tiers")),
    ("stonks", "Stonks", 2017, "dank", "A surreal stock-chart image used for absurd financial jokes.", ("stocks", "finance")),
    ("surprised-pikachu", "Surprised Pikachu", 2018, "reaction", "A surprised expression for an entirely predictable outcome.", ("pokemon", "surprise")),
    ("big-chungus", "Big Chungus", 2018, "dank", "An exaggerated Bugs Bunny image turned into absurdist humor.", ("cartoon", "absurd")),
    ("woman-yelling-at-cat", "Woman Yelling at a Cat", 2019, "reaction", "Two contrasting images used for arguments and misunderstandings.", ("cat", "argument")),
    ("coffin-dance", "Coffin Dance", 2020, "viral", "A Ghanaian pallbearer performance used as a humorous punchline.", ("dance", "video")),
)
_REGISTRY = {
    meme_id: {
        "id": meme_id,
        "name": name,
        "year": year,
        "category": category,
        "era": "90s" if year < 2000 else "2000s" if year < 2010 else "2010s" if year < 2020 else "2020s",
        "description": description,
        "keywords": list(keywords),
    }
    for meme_id, name, year, category, description, keywords in _CLASSICS
}


def _normalize(value):
    if not isinstance(value, str):
        raise TypeError("meme name or query must be text")
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def meme_info(name):
    """Return a copy of a classic meme record, accepting its id or display name."""
    key = _normalize(name)
    record = _REGISTRY.get(key)
    if record is None:
        record = next(
            (item for item in _REGISTRY.values() if _normalize(item["name"]) == key),
            None,
        )
    if record is None:
        raise ValueError(f"unknown classic meme {name!r}; use meme_catalog() or meme_search()")
    return {**record, "keywords": list(record["keywords"])}


def meme_catalog(category=None):
    """Return all classics, optionally filtered by category."""
    if category is not None:
        if not isinstance(category, str):
            raise TypeError("category must be text")
        category = category.casefold()
    return [
        {**item, "keywords": list(item["keywords"])}
        for item in _REGISTRY.values()
        if category is None or item["category"] == category
    ]


def meme_search(query):
    """Search classic meme names, ids, descriptions and keywords."""
    if not isinstance(query, str):
        raise TypeError("query must be text")
    needle = query.casefold().strip()
    if not needle:
        return meme_catalog()
    return [
        {**item, "keywords": list(item["keywords"])}
        for item in _REGISTRY.values()
        if needle in " ".join(
            [item["id"], item["name"], item["category"], item["description"], *item["keywords"]]
        ).casefold()
    ]


def meme_caption(name, caption):
    """Build a portable, text-only meme object for downstream renderers."""
    if not isinstance(caption, str):
        raise TypeError("caption must be text")
    record = meme_info(name)
    return {
        "format": "memingo.meme/v1",
        "kind": "caption",
        "meme": record["id"],
        "name": record["name"],
        "year": record["year"],
        "category": record["category"],
        "caption": caption,
        "alt": f'{record["name"]}: {caption}',
    }


def meme_react(name, situation):
    """Build a structured reaction reference without generating an image."""
    if not isinstance(situation, str):
        raise TypeError("situation must be text")
    record = meme_info(name)
    return {
        "format": "memingo.meme/v1",
        "kind": "reaction",
        "meme": record["id"],
        "name": record["name"],
        "year": record["year"],
        "category": record["category"],
        "situation": situation,
        "alt": f'{record["name"]} reaction to: {situation}',
    }
