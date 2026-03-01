"""Foxhole War API client for faction control data.

Queries the public War API to determine which faction controls each hex region.
API docs: https://github.com/clapfoot/warapi
"""

from __future__ import annotations

import json
import logging
import urllib.request
from collections import Counter

log = logging.getLogger(__name__)

API_BASE = "https://war-service-live.foxholeservices.com/api"

# Mapping from API hex names to our display region names
_API_TO_REGION: dict[str, str] = {
    "OarbreakerHex": "Oarbreaker Isles",
    "FishermansRowHex": "Fisherman's Row",
    "StemaLandingHex": "Stema Landing",
    "NevishLineHex": "Nevish Line",
    "CallumsCapeHex": "Callum's Cape",
    "SpeakingWoodsHex": "Speaking Woods",
    "BasinSionnachHex": "Basin Sionnach",
    "HowlCountyHex": "Howl County",
    "ViperPitHex": "Viper Pit",
    "MarbanHollow": "Marban Hollow",
    "GodcroftsHex": "Godcrofts",
    "TempestIslandHex": "Tempest Island",
    "LinnMercyHex": "The Linn of Mercy",
    "LochMorHex": "Loch Mór",
    "HeartlandsHex": "The Heartlands",
    "StonecradleHex": "Stonecradle",
    "FarranacCoastHex": "Farranac Coast",
    "WestgateHex": "Westgate",
    "ReachingTrailHex": "Reaching Trail",
    "UmbralWildwoodHex": "Umbral Wildwood",
    "MorgensCrossingHex": "Morgen's Crossing",
    "TheFingersHex": "The Fingers",
    "TerminusHex": "Terminus",
    "AcrithiaHex": "Acrithia",
    "AshFieldsHex": "Ash Fields",
    "AllodsBightHex": "Allod's Bight",
    "WeatheredExpanseHex": "Weathered Expanse",
    "ClahstraHex": "The Clahstra",
    "ShackledChasmHex": "Shackled Chasm",
    "EndlessShoreHex": "Endless Shore",
    "DeadLandsHex": "Deadlands",
    "OriginHex": "Origin",
    "KalokaiHex": "Kalokai",
    "RedRiverHex": "Red River",
    "GreatMarchHex": "Great March",
    "SableportHex": "Sableport",
}


def _get_json(path: str) -> object:
    """Fetch JSON from the War API."""
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def fetch_faction_control() -> dict[str, str]:
    """Fetch faction control for all regions.

    Returns:
        Dict mapping region display name to 'colonial', 'warden', or 'neutral'.
    """
    try:
        hex_names = _get_json("/worldconquest/maps")
    except Exception:
        log.warning("Failed to fetch map list from War API", exc_info=True)
        return {}

    control: dict[str, str] = {}

    for hex_name in hex_names:
        region_name = _API_TO_REGION.get(hex_name)
        if region_name is None:
            continue

        try:
            data = _get_json(f"/worldconquest/maps/{hex_name}/dynamic/public")
        except Exception:
            log.debug("Failed to fetch dynamic data for %s", hex_name)
            continue

        items = data.get("mapItems", [])
        if not items:
            control[region_name] = "neutral"
            continue

        # Count team ownership of map items
        teams: Counter[str] = Counter()
        for item in items:
            tid = item.get("teamId", "NONE")
            if tid != "NONE":
                teams[tid] += 1

        if not teams:
            control[region_name] = "neutral"
        else:
            dominant = teams.most_common(1)[0][0]
            if dominant == "COLONIALS":
                control[region_name] = "colonial"
            elif dominant == "WARDENS":
                control[region_name] = "warden"
            else:
                control[region_name] = "neutral"

    return control
