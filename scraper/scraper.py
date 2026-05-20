from __future__ import annotations

import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_LIST_URL = "http://ufcstats.com/statistics/fighters"
BASE_EVENTS_URL = "http://ufcstats.com/statistics/events/completed?page=all"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PATH = DATA_DIR / "fighters.csv"
FIGHTS_CSV_PATH = DATA_DIR / "fights.csv"
EVENTS_CSV_PATH = DATA_DIR / "events.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

LIST_COLUMNS = [
    "first_name",
    "last_name",
    "nickname",
    "height",
    "weight",
    "reach",
    "stance",
    "wins",
    "losses",
    "draws",
]

DETAIL_COLUMNS = [
    "slpm",
    "str_acc",
    "sapm",
    "str_def",
    "td_avg",
    "td_acc",
    "td_def",
    "sub_avg",
]


def _get(url: str, session: requests.Session, retries: int = 3) -> str:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_exc = exc
            time.sleep(1 + attempt)
    raise RuntimeError(f"Failed to GET {url}: {last_exc}")


def _clean(value: str) -> str:
    value = (value or "").strip()
    return "" if value in {"--", "---"} else value


def _parse_list_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="b-statistics__table")
    if table is None:
        return []

    rows: list[dict] = []
    for tr in table.find_all("tr")[2:]:
        cells = tr.find_all("td")
        if len(cells) < 10:
            continue

        link_tag = cells[0].find("a")
        if link_tag is None:
            continue

        fighter_url = link_tag.get("href", "").strip()
        values = [_clean(td.get_text()) for td in cells[:10]]
        rows.append(dict(zip(LIST_COLUMNS, values, strict=False)) | {"url": fighter_url})
    return rows


def _scrape_listing(session: requests.Session) -> list[dict]:
    fighters: list[dict] = []
    for letter in string.ascii_lowercase:
        url = f"{BASE_LIST_URL}?char={letter}&page=all"
        html = _get(url, session)
        page_rows = _parse_list_page(html)
        fighters.extend(page_rows)
    return fighters


def _parse_career_stats(soup: BeautifulSoup) -> dict:
    text_blocks = soup.find_all("li", class_="b-list__box-list-item_type_block")

    wanted = {
        "SLpM:": "slpm",
        "Str. Acc.:": "str_acc",
        "SApM:": "sapm",
        "Str. Def:": "str_def",
        "TD Avg.:": "td_avg",
        "TD Acc.:": "td_acc",
        "TD Def.:": "td_def",
        "Sub. Avg.:": "sub_avg",
    }

    result = {key: "" for key in DETAIL_COLUMNS}
    for block in text_blocks:
        title_tag = block.find("i", class_="b-list__box-item-title")
        if title_tag is None:
            continue
        label = title_tag.get_text(strip=True)
        if label in wanted:
            full_text = block.get_text(" ", strip=True)
            value = full_text.replace(label, "").strip()
            result[wanted[label]] = _clean(value)
    return result


def _parse_fight_history(soup: BeautifulSoup, fighter_url: str) -> list[dict]:
    table = soup.find("table", class_="b-fight-details__table")
    if table is None:
        return []

    rows: list[dict] = []
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr", class_="b-fight-details__table-row"):
        cells = tr.find_all("td", class_="b-fight-details__table-col")
        if len(cells) < 10:
            continue

        flag = cells[0].find("i", class_="b-flag__text")
        result = _clean(flag.get_text()) if flag else ""

        name_paragraphs = cells[1].find_all("p")
        if len(name_paragraphs) >= 2:
            names = [_clean(p.get_text()) for p in name_paragraphs]
        else:
            names = [_clean(cells[1].get_text())]

        event_paragraphs = cells[6].find_all("p") if len(cells) > 6 else []
        event_name = _clean(event_paragraphs[0].get_text()) if event_paragraphs else ""
        event_date = _clean(event_paragraphs[1].get_text()) if len(event_paragraphs) > 1 else ""

        method_paragraphs = cells[7].find_all("p") if len(cells) > 7 else []
        method = _clean(method_paragraphs[0].get_text()) if method_paragraphs else ""
        method_detail = _clean(method_paragraphs[1].get_text()) if len(method_paragraphs) > 1 else ""

        round_ = _clean(cells[8].get_text()) if len(cells) > 8 else ""
        fight_time = _clean(cells[9].get_text()) if len(cells) > 9 else ""

        rows.append({
            "fighter_url": fighter_url,
            "result": result,
            "opponent": names[1] if len(names) >= 2 else "",
            "event": event_name,
            "event_date": event_date,
            "method": method,
            "method_detail": method_detail,
            "round": round_,
            "time": fight_time,
        })
    return rows


def _scrape_detail(url: str, session: requests.Session) -> tuple[dict, list[dict]]:
    try:
        html = _get(url, session)
        soup = BeautifulSoup(html, "html.parser")
        return _parse_career_stats(soup), _parse_fight_history(soup, url)
    except Exception:
        return {col: "" for col in DETAIL_COLUMNS}, []


def _enrich_with_details(
    fighters: list[dict],
    session: requests.Session,
    max_workers: int = 12,
    progress=None,
) -> tuple[list[dict], list[dict]]:
    total = len(fighters)
    completed = 0
    all_fights: list[dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_scrape_detail, fighter["url"], session): idx
            for idx, fighter in enumerate(fighters)
            if fighter.get("url")
        }
        for future in as_completed(futures):
            idx = futures[future]
            stats, fights = future.result()
            fighters[idx].update(stats)
            all_fights.extend(fights)
            completed += 1
            if progress is not None:
                progress(completed, total)
    return fighters, all_fights


def _to_dataframe(fighters: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(list(fighters))
    if df.empty:
        return df

    df["name"] = (df["first_name"].fillna("") + " " + df["last_name"].fillna("")).str.strip()

    df["height_in"] = df["height"].apply(_height_to_inches)
    df["weight_lbs"] = df["weight"].apply(_weight_to_lbs)
    df["reach_in"] = df["reach"].apply(_reach_to_inches)

    for col in ["wins", "losses", "draws"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    for col in ["slpm", "sapm", "td_avg", "sub_avg"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["str_acc", "str_def", "td_acc", "td_def"]:
        df[col] = (
            df[col].astype(str).str.replace("%", "", regex=False).replace("", None)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["weight_class"] = df["weight_lbs"].apply(_classify_weight)
    df["total_fights"] = df["wins"] + df["losses"] + df["draws"]

    no_fights = df["total_fights"] == 0
    rate_cols = ["str_acc", "str_def", "td_acc", "td_def", "slpm", "sapm", "td_avg", "sub_avg"]
    df.loc[no_fights, rate_cols] = pd.NA

    return df


def _height_to_inches(raw: str) -> float | None:
    if not raw or "'" not in raw:
        return None
    try:
        feet_part, inch_part = raw.split("'")
        feet = int(feet_part.strip())
        inches = int(inch_part.replace('"', "").strip() or 0)
        return feet * 12 + inches
    except ValueError:
        return None


def _weight_to_lbs(raw: str) -> float | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
    return float(digits) if digits else None


def _reach_to_inches(raw: str) -> float | None:
    if not raw:
        return None
    digits = raw.replace('"', "").strip()
    try:
        return float(digits)
    except ValueError:
        return None


WEIGHT_CLASSES = [
    ("Strawweight", 115),
    ("Flyweight", 125),
    ("Bantamweight", 135),
    ("Featherweight", 145),
    ("Lightweight", 155),
    ("Welterweight", 170),
    ("Middleweight", 185),
    ("Light Heavyweight", 205),
    ("Heavyweight", 265),
]


def _classify_weight(weight: float | None) -> str:
    if weight is None or pd.isna(weight):
        return "Unknown"
    for name, ceiling in WEIGHT_CLASSES:
        if weight <= ceiling:
            return name
    return "Super Heavyweight"


def _parse_events_index(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="b-statistics__table-events")
    if table is None:
        return []
    rows: list[dict] = []
    for tr in table.find_all("tr"):
        link = tr.find("a", class_="b-link b-link_style_black")
        if link is None:
            continue
        name = _clean(link.get_text())
        url = link.get("href", "").strip()
        date_span = tr.find("span", class_="b-statistics__date")
        event_date = _clean(date_span.get_text()) if date_span else ""
        rows.append({"event_url": url, "event_name": name, "event_date": event_date})
    return rows


def _parse_event_detail(html: str, event_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="b-fight-details__table")
    if table is None:
        return []

    rows: list[dict] = []
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr", class_="b-fight-details__table-row"):
        cells = tr.find_all("td", class_="b-fight-details__table-col")
        if len(cells) < 7:
            continue

        fighter_paragraphs = cells[1].find_all("p")
        fighters = [_clean(p.get_text()) for p in fighter_paragraphs[:2]]
        if len(fighters) < 2:
            continue

        is_title = _detect_title_fight(tr)
        fight_link = tr.get("data-link") or ""

        rows.append({
            "event_url": event_url,
            "fight_url": _clean(fight_link),
            "fighter_a": fighters[0],
            "fighter_b": fighters[1],
            "is_title_fight": bool(is_title),
        })
    return rows


def _detect_title_fight(row_tag) -> bool:
    for img in row_tag.find_all("img"):
        src = (img.get("src") or "").lower()
        alt = (img.get("alt") or "").lower()
        if "belt" in src or "belt" in alt:
            return True
    for tag in row_tag.find_all(class_=True):
        classes = " ".join(tag.get("class", [])).lower()
        if "belt" in classes:
            return True
    return False


def _scrape_event(url: str, session: requests.Session) -> list[dict]:
    try:
        html = _get(url, session)
        return _parse_event_detail(html, url)
    except Exception:
        return []


def scrape_events(progress=None) -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        index_html = _get(BASE_EVENTS_URL, session)
        events = _parse_events_index(index_html)

        all_fights: list[dict] = []
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {
                pool.submit(_scrape_event, e["event_url"], session): e
                for e in events
                if e.get("event_url")
            }
            total = len(futures)
            done = 0
            for future in as_completed(futures):
                event = futures[future]
                for row in future.result():
                    row["event_name"] = event["event_name"]
                    row["event_date"] = event["event_date"]
                    all_fights.append(row)
                done += 1
                if progress is not None:
                    progress(done, total)

    df = pd.DataFrame(all_fights)
    if not df.empty:
        df["event_date_parsed"] = pd.to_datetime(
            df["event_date"], errors="coerce", format="%B %d, %Y"
        )
    df.to_csv(EVENTS_CSV_PATH, index=False)
    return df


def load_cached_events() -> pd.DataFrame | None:
    if not EVENTS_CSV_PATH.exists():
        return None
    try:
        return pd.read_csv(EVENTS_CSV_PATH)
    except Exception:
        return None


def scrape_fighters(progress=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        if progress is not None:
            progress(0, 1)
        fighters = _scrape_listing(session)
        fighters, all_fights = _enrich_with_details(fighters, session, progress=progress)

    df = _to_dataframe(fighters)
    df.to_csv(CSV_PATH, index=False)

    fights_df = pd.DataFrame(all_fights)
    if not fights_df.empty:
        fights_df["event_date_parsed"] = pd.to_datetime(
            fights_df["event_date"], errors="coerce", format="%b. %d, %Y"
        )
        fights_df = fights_df.drop_duplicates(
            subset=["fighter_url", "event", "opponent"], keep="first"
        )
    fights_df.to_csv(FIGHTS_CSV_PATH, index=False)

    try:
        scrape_events(progress=progress)
    except Exception:
        pass

    return df, fights_df


def load_cached() -> pd.DataFrame | None:
    if not CSV_PATH.exists():
        return None
    try:
        return pd.read_csv(CSV_PATH)
    except Exception:
        return None


def load_cached_fights() -> pd.DataFrame | None:
    if not FIGHTS_CSV_PATH.exists():
        return None
    try:
        df = pd.read_csv(FIGHTS_CSV_PATH)
        if "event_date" in df.columns:
            df["event_date_parsed"] = pd.to_datetime(
                df["event_date"], errors="coerce", format="%b. %d, %Y"
            )
        dedup_cols = [c for c in ("fighter_url", "event", "opponent") if c in df.columns]
        if dedup_cols:
            df = df.drop_duplicates(subset=dedup_cols, keep="first")
        return df
    except Exception:
        return None


def load_or_scrape(progress=None) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    cached = load_cached()
    if cached is not None and not cached.empty:
        return cached, load_cached_fights()
    return scrape_fighters(progress=progress)


if __name__ == "__main__":
    def _cli_progress(done: int, total: int) -> None:
        print(f"[scraper] {done}/{total}", end="\r")

    frame, fights = scrape_fighters(progress=_cli_progress)
    print(f"\nSaved {len(frame)} fighters to {CSV_PATH}")
    print(f"Saved {len(fights)} fight rows to {FIGHTS_CSV_PATH}")
