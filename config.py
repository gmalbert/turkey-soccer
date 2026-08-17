"""League-owned configuration for a thin Pitch Oracle consumer."""

import os
from dataclasses import replace

from pitch_oracle_core import get_league_config


# Odds-API.io's real Süper Lig slug ("Turkiye - Super Lig"); "turkey-super-lig"
# 404s. Sport slug is lowercase "football".
ODDS_API_IO_LEAGUE_SLUG = "turkiye-super-lig"

# Read from the environment (comma-separated), e.g. ODDS_API_IO_BOOKMAKERS=DraftKings,Bet365.
_DEFAULT_BOOKMAKERS = ("Bet365", "Unibet")
ODDS_API_IO_BOOKMAKERS = tuple(
    name.strip()
    for name in os.getenv("ODDS_API_IO_BOOKMAKERS", "").split(",")
    if name.strip()
) or _DEFAULT_BOOKMAKERS

ODDS_VALUE_MIN_EDGE = 0.05
ODDS_VALUE_MIN_EXPECTED_RETURN = 0.03


# GPS coordinates (lat, lon) for each team's home stadium. Covers every team in
# the historical data plus the current upcoming-fixture slate so the weather
# backfill and upcoming enrichment both resolve coordinates.
STADIUM_COORDINATES = {
    # Current 2026-27 Süper Lig teams
    "Alanyaspor": (36.5417, 32.0183),      # Alanya Oba Stadium
    "Amed SFK": (37.9144, 40.2306),        # Diyarbakır Stadyumu
    "Besiktas": (41.0392, 29.0111),        # Beşiktaş Park
    "Buyuksehyr": (41.0043, 28.9646),      # Başakşehir Fatih Terim Stadium
    "Erzurum BB": (39.9211, 41.2928),      # Kazım Karabekir Stadium
    "Eyupspor": (41.0453, 28.9283),        # Eyüp Stadium
    "Fenerbahce": (40.9878, 29.0366),      # Şükrü Saracoğlu Stadium
    "Galatasaray": (41.1033, 29.0242),     # RAMS Park (Türk Telekom)
    "Gaziantep": (37.0887, 37.3800),       # Kalyon Stadium
    "Genclerbirligi": (39.9439, 32.8450),  # Eryaman Stadium
    "Goztep": (38.3922, 27.0764),          # Gürsel Aksel Stadium
    "Kasimpasa": (41.1175, 28.9867),       # Recep Tayyip Erdoğan Stadium
    "Kocaelispor": (40.7669, 29.9403),     # Kocaeli Stadium
    "Konyaspor": (37.9553, 32.5053),       # Konya Büyükşehir Stadium
    "Rizespor": (41.0244, 40.5228),        # Çaykur Didi Stadium
    "Samsunspor": (41.2933, 36.3425),      # Samsun 19 Mayıs Stadium
    "Trabzonspor": (40.9992, 39.6428),     # Papara Park (Şenol Güneş)
    "Corum": (40.5444, 34.9533),           # Çorum Şehir Stadium
    # Historical / recent Süper Lig teams (weather backfill coverage)
    "Ad. Demirspor": (37.0712, 35.3528),   # Yeni Adana Stadium
    "Ankaragucu": (39.9439, 32.8450),      # Eryaman Stadium
    "Antalyaspor": (36.8883, 30.6694),     # Antalya Stadium
    "Bodrumspor": (37.0397, 27.4306),      # Bodrum İlçe Stadium
    "Giresunspor": (40.9128, 38.3897),     # Çotanak Stadium
    "Hatayspor": (36.1794, 36.1611),       # Yeni Hatay Stadium
    "Istanbulspor": (41.0142, 28.9756),    # Necmi Kadıoğlu Stadium
    "Karagumruk": (41.0244, 28.9250),      # Atatürk Olympic Stadium
    "Kayserispor": (38.7317, 35.4875),     # Kayseri Kadir Has Stadium
    "Pendikspor": (40.8772, 29.2397),      # Pendik Stadium
    "Sivasspor": (39.7486, 37.0178),       # Sivas 4 Eylül Stadium
    "Umraniyespor": (41.0106, 29.0878),    # Ümraniye Municipality City Stadium
}


# The v1.3.26 registry predates ESPN's verified Süper Lig identifier. Keep the
# core release immutable while owning the confirmed league-specific value here.
LEAGUE_CONFIG = replace(
    get_league_config("turkey"),
    espn_slug="tur.1",
    team_aliases={
        "Caykur Rizespor": "Rizespor",
        "Gaziantep FK": "Gaziantep",
        "Goztepe": "Goztep",
        "Göztepe": "Goztep",
        "Istanbul Basaksehir": "Buyuksehyr",
        "Istanbul Basaksehir FK": "Buyuksehyr",
        "Başakşehir": "Buyuksehyr",
        "Çaykur Rizespor": "Rizespor",
        "Çorum FK": "Corum",
        "Corum FK": "Corum",
        "Çorum": "Corum",
        "Amedspor": "Amed SFK",
        "Amed SK": "Amed SFK",
        "Erzurumspor FK": "Erzurum BB",
        "BB Erzurumspor": "Erzurum BB",
        "Eyüpspor": "Eyupspor",
        # Odds-API.io appends the city ("Istanbul") or legacy suffix ("SK") to
        # club names; map them to the canonical model names so odds rows match.
        "Galatasaray Istanbul": "Galatasaray",
        "Kasimpasa Istanbul": "Kasimpasa",
        "Fenerbahce Istanbul": "Fenerbahce",
        "Besiktas Istanbul": "Besiktas",
        "Goztepe Izmir": "Goztep",
        "Genclerbirligi SK": "Genclerbirligi",
        "Amed Sportif Faaliyetler": "Amed SFK",
    },
    stadium_coordinates=STADIUM_COORDINATES,
)
