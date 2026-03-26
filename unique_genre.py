import ast
import re
from collections import Counter, defaultdict

MAIN_GENRES = [
    "Pop", "Rock", "Hip-Hop", "Electronic", "Jazz",
    "Classical", "Country", "R&B", "Reggae",
    "Latin", "Metal", "Folk", "Blues"
]

# Keyword signals (compact but high coverage)
GENRE_KEYWORDS = {
    "Hip-Hop": ["hip hop", "rap", "trap", "drill", "boom bap", "grime"],
    "Rock": ["rock", "punk", "grunge", "indie rock", "alt rock"],
    "Metal": ["metal", "metalcore", "death metal", "black metal"],
    "Electronic": ["edm", "house", "techno", "trance", "dubstep", "electro", "dnb", "drum and bass"],
    "Pop": ["pop", "electropop", "synthpop", "dance pop", "idol"],
    "Jazz": ["jazz", "bebop", "swing", "fusion"],
    "Classical": ["classical", "baroque", "romanticism", "orchestra", "opera"],
    "Country": ["country", "bluegrass", "americana", "honky tonk"],
    "R&B": ["r&b", "soul", "neo soul", "motown"],
    "Reggae": ["reggae", "dancehall", "dub"],
    "Latin": ["latin", "reggaeton", "salsa", "bachata", "cumbia"],
    "Folk": ["folk", "singer-songwriter", "traditional"],
    "Blues": ["blues", "delta blues", "chicago blues"]
}

def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9& ]+', ' ', text)
    return text

def map_genre(genre):
    g = normalize(genre)
    scores = defaultdict(int)

    for main, keywords in GENRE_KEYWORDS.items():
        for kw in keywords:
            if g.endswith(kw):
                return main

    return "Other"


def parse_raw_genres(genres_str: str) -> list:
    try:
        genres = ast.literal_eval(str(genres_str))
        if isinstance(genres, list):
            return [g.strip() for g in genres if str(g).strip()]
    except Exception:
        pass
    return []


def compute_simplified_genres(genres_str: str) -> list:
    seen = set()
    result = []
    for g in parse_raw_genres(genres_str):
        mapped = map_genre(g)
        if mapped not in seen:
            seen.add(mapped)
            result.append(mapped)
    return result


def compute_main_genre(genres_str: str) -> str:
    counts = Counter(map_genre(g) for g in parse_raw_genres(genres_str))
    non_other = {g: c for g, c in counts.items() if g != "Other"}
    if non_other:
        return max(non_other, key=non_other.get)
    return "Other"


if __name__ == "__main__":
    import pandas as pd

    df = pd.read_csv("data/nodes.csv")

    # Write unique raw genres
    unique_genres = set()
    for genres_str in df["genres"]:
        for genre in genres_str.split(","):
            unique_genres.add(genre.strip().strip("]").strip("[").strip("'").strip('"'))
    with open("unique_genres.txt", "w") as f:
        for genre in sorted(unique_genres):
            f.write(genre + "\n")

    # Enrich nodes.csv with simplified_genres and main_genre
    df["simplified_genres"] = df["genres"].apply(compute_simplified_genres)
    df["main_genre"] = df["genres"].apply(compute_main_genre)
    df.to_csv("data/nodes.csv", index=False)
    print(f"Updated data/nodes.csv with simplified_genres and main_genre for {len(df)} nodes.")
