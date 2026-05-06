#!/usr/bin/env python3
import json
import time
import urllib.request
from datetime import datetime, timezone

API = "https://statsapi.mlb.com/api/v1"
SEASON = 2026

CAREER_GPHR = {
    "Cal Raleigh": 6.2, "Kyle Schwarber": 5.6, "Shohei Ohtani": 4.3,
    "Aaron Judge": 3.2, "Eugenio Suarez": 7.0, "Junior Caminero": 5.5,
    "Juan Soto": 6.8, "Pete Alonso": 5.8, "Jo Adell": 9.5,
    "Taylor Ward": 10.2, "Riley Greene": 8.8, "Nick Kurtz": 7.0,
    "Rafael Devers": 6.3, "Byron Buxton": 6.5, "Trent Grisham": 11.5,
    "Matt Olson": 5.7, "Gunnar Henderson": 5.1, "Yordan Alvarez": 5.0,
    "Freddie Freeman": 7.5, "Manny Machado": 7.4, "Munetaka Murakami": 5.8,
    "Austin Riley": 6.0, "Vladimir Guerrero": 6.0, "Julio Rodriguez": 7.6,
    "Bobby Witt Jr.": 8.0, "Jose Ramirez": 7.8, "Adolis Garcia": 7.2,
    "William Contreras": 7.0, "Christian Walker": 8.2, "Salvador Perez": 7.9,
    "Kyle Tucker": 6.5, "Mookie Betts": 7.5,
}

HR_2025 = {
    "Cal Raleigh": 60, "Kyle Schwarber": 56, "Shohei Ohtani": 55,
    "Aaron Judge": 53, "Eugenio Suarez": 49, "Junior Caminero": 45,
    "Juan Soto": 43, "Pete Alonso": 38, "Jo Adell": 37,
    "Taylor Ward": 36, "Riley Greene": 36, "Nick Kurtz": 36,
    "Rafael Devers": 35, "Byron Buxton": 35, "Trent Grisham": 34,
}

def fetch(url, retries=3):
    headers = {"User-Agent": "DroughtWatch/1.0"}
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)

def get_hr_leaders():
    url = f"{API}/stats/leaders?leaderCategories=homeRuns&season={SEASON}&limit=50&sportId=1&statGroup=hitting&gameType=R"
    data = fetch(url)
    leaders = data.get("leagueLeaders", [{}])[0].get("leaders", [])
    return [{"id": l["person"]["id"], "name": l["person"]["fullName"], "team": l.get("team", {}).get("abbreviation", "—"), "hr": int(l.get("value", 0))} for l in leaders]

def get_game_log(player_id):
    url = f"{API}/people/{player_id}/stats?stats=gameLog&group=hitting&season={SEASON}&gameType=R"
    data = fetch(url)
    return data.get("stats", [{}])[0].get("splits", [])

def calc_drought(splits):
    if not splits:
        return 0, None, 0
    sorted_splits = sorted(splits, key=lambda s: s.get("date", ""), reverse=True)
    drought = 0
    last_hr = None
    for game in sorted_splits:
        if game.get("stat", {}).get("homeRuns", 0) > 0:
            last_hr = game.get("date")
            break
        drought += 1
    return drought, last_hr, len(splits)

def get_career_gphr(player_id, name):
    if name in CAREER_GPHR:
        return CAREER_GPHR[name]
    try:
        url = f"{API}/people/{player_id}/stats?stats=career&group=hitting&gameType=R"
        data = fetch(url)
        stat = data.get("stats", [{}])[0].get("splits", [{}])[0].get("stat", {})
        gp = stat.get("gamesPlayed", 0)
        hr = stat.get("homeRuns", 0)
        if hr > 0:
            return round(gp / hr, 1)
    except:
        pass
    return None

def format_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %-d")
    except:
        return date_str

def main():
    print("Fetching HR leaders...")
    leaders = get_hr_leaders()
    results = []
    for i, p in enumerate(leaders):
        print(f"  [{i+1}/{len(leaders)}] {p['name']}")
        try:
            splits = get_game_log(p["id"])
            drought, last_hr_raw, gp = calc_drought(splits)
            career_gphr = get_career_gphr(p["id"], p["name"])
            results.append({
                "id": p["id"], "name": p["name"], "team": p["team"],
                "hr2026": p["hr"], "gp2026": gp, "drought": drought,
                "lastHR": format_date(last_hr_raw), "careerGPHR": career_gphr,
                "seasonGPHR": round(gp / p["hr"], 1) if p["hr"] > 0 and gp > 0 else None,
                "ratio": round(drought / career_gphr, 3) if career_gphr and drought is not None else None,
                "hr2025": HR_2025.get(p["name"]),
            })
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"id": p["id"], "name": p["name"], "team": p["team"], "hr2026": p["hr"], "gp2026": None, "drought": None, "lastHR": None, "careerGPHR": CAREER_GPHR.get(p["name"]), "seasonGPHR": None, "ratio": None, "hr2025": HR_2025.get(p["name"])})
        time.sleep(0.3)

    out = {"updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "updatedLabel": datetime.now(timezone.utc).strftime("%b %-d, %Y %H:%M UTC"), "season": SEASON, "players": results}
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/drought.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"Done — {len(results)} players written")

if __name__ == "__main__":
    main()
