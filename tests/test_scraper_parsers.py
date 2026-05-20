
from __future__ import annotations

import textwrap

from bs4 import BeautifulSoup

from scraper.scraper import (
    _parse_career_stats,
    _parse_fight_history,
    _parse_list_page,
)


LISTING_HTML = textwrap.dedent("""
<html><body>
<table class="b-statistics__table">
  <thead>
    <tr><th colspan="10">Header</th></tr>
    <tr><th>First</th><th>Last</th><th>Nickname</th>
        <th>Ht.</th><th>Wt.</th><th>Reach</th><th>Stance</th>
        <th>W</th><th>L</th><th>D</th></tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="http://ufcstats.com/fighter-details/abc123">Jon</a></td>
      <td><a>Jones</a></td>
      <td><a>Bones</a></td>
      <td>6' 4"</td>
      <td>205 lbs.</td>
      <td>84.5"</td>
      <td>Orthodox</td>
      <td>27</td>
      <td>1</td>
      <td>0</td>
    </tr>
    <tr>
      <td><a href="http://ufcstats.com/fighter-details/def456">Khabib</a></td>
      <td><a>Nurmagomedov</a></td>
      <td><a>The Eagle</a></td>
      <td>5' 10"</td>
      <td>155 lbs.</td>
      <td>70.0"</td>
      <td>Orthodox</td>
      <td>29</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr><td colspan="10">malformed short row</td></tr>
  </tbody>
</table>
</body></html>
""").strip()


CAREER_STATS_HTML = textwrap.dedent("""
<html><body>
<ul>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">SLpM:</i> 4.30
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">Str. Acc.:</i> 57%
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">SApM:</i> 2.22
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">Str. Def:</i> 64%
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">TD Avg.:</i> 1.91
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">TD Acc.:</i> 44%
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">TD Def.:</i> 95%
  </li>
  <li class="b-list__box-list-item_type_block">
    <i class="b-list__box-item-title">Sub. Avg.:</i> 0.5
  </li>
</ul>
</body></html>
""").strip()


def _fight_row(result, our_name, opponent, kd, str_, td, sub, event, date, method, detail, rnd, time):
    """Render one b-fight-details__table-row matching ufcstats.com markup."""
    return f"""
<tr class="b-fight-details__table-row">
  <td class="b-fight-details__table-col">
    <i class="b-flag__text">{result}</i>
  </td>
  <td class="b-fight-details__table-col">
    <p>{our_name}</p>
    <p>{opponent}</p>
  </td>
  <td class="b-fight-details__table-col"><p>{kd}</p></td>
  <td class="b-fight-details__table-col"><p>{str_}</p></td>
  <td class="b-fight-details__table-col"><p>{td}</p></td>
  <td class="b-fight-details__table-col"><p>{sub}</p></td>
  <td class="b-fight-details__table-col">
    <p>{event}</p>
    <p>{date}</p>
  </td>
  <td class="b-fight-details__table-col">
    <p>{method}</p>
    <p>{detail}</p>
  </td>
  <td class="b-fight-details__table-col"><p>{rnd}</p></td>
  <td class="b-fight-details__table-col"><p>{time}</p></td>
</tr>
"""


FIGHT_HISTORY_HTML = (
    '<html><body><table class="b-fight-details__table"><tbody>'
    + _fight_row("win", "Jon Jones", "Stipe Miocic", "0", "10", "0", "0",
                 "UFC 309", "Nov. 16, 2024", "KO/TKO", "Spinning back kick", "3", "4:29")
    + _fight_row("win", "Jon Jones", "Ciryl Gane", "0", "12", "1", "1",
                 "UFC 285", "Mar. 04, 2023", "SUB", "Guillotine Choke", "1", "2:04")
    + _fight_row("loss", "Jon Jones", "Matt Hamill", "0", "0", "0", "0",
                 "TUF 10 Finale", "Dec. 05, 2009", "DQ", "Illegal Elbows", "1", "4:14")
    + "</tbody></table></body></html>"
)



class TestParseListPage:
    def test_extracts_all_valid_rows(self):
        rows = _parse_list_page(LISTING_HTML)
        assert len(rows) == 2

    def test_first_row_fields(self):
        rows = _parse_list_page(LISTING_HTML)
        jon = rows[0]
        assert jon["first_name"] == "Jon"
        assert jon["last_name"] == "Jones"
        assert jon["nickname"] == "Bones"
        assert jon["height"] == "6' 4\""
        assert jon["weight"] == "205 lbs."
        assert jon["reach"] == "84.5\""
        assert jon["stance"] == "Orthodox"
        assert jon["wins"] == "27"
        assert jon["losses"] == "1"
        assert jon["draws"] == "0"
        assert jon["url"] == "http://ufcstats.com/fighter-details/abc123"

    def test_skips_malformed_rows(self):
        # Third row has only one cell — must not appear in the output.
        rows = _parse_list_page(LISTING_HTML)
        assert all(r["last_name"] in {"Jones", "Nurmagomedov"} for r in rows)

    def test_empty_html_returns_empty(self):
        assert _parse_list_page("<html></html>") == []


class TestParseCareerStats:
    def test_all_eight_stats_extracted(self):
        soup = BeautifulSoup(CAREER_STATS_HTML, "html.parser")
        stats = _parse_career_stats(soup)
        assert stats["slpm"] == "4.30"
        assert stats["str_acc"] == "57%"
        assert stats["sapm"] == "2.22"
        assert stats["str_def"] == "64%"
        assert stats["td_avg"] == "1.91"
        assert stats["td_acc"] == "44%"
        assert stats["td_def"] == "95%"
        assert stats["sub_avg"] == "0.5"

    def test_missing_blocks_return_empty_strings(self):
        soup = BeautifulSoup("<html><body></body></html>", "html.parser")
        stats = _parse_career_stats(soup)
        # All eight keys present, all empty
        assert set(stats.keys()) == {
            "slpm", "str_acc", "sapm", "str_def",
            "td_avg", "td_acc", "td_def", "sub_avg",
        }
        assert all(v == "" for v in stats.values())


class TestParseFightHistory:
    def test_extracts_all_rows(self):
        soup = BeautifulSoup(FIGHT_HISTORY_HTML, "html.parser")
        fights = _parse_fight_history(soup, "http://example.com/fighter/abc")
        assert len(fights) == 3

    def test_first_fight_fields(self):
        soup = BeautifulSoup(FIGHT_HISTORY_HTML, "html.parser")
        fight = _parse_fight_history(soup, "http://example.com/fighter/abc")[0]
        assert fight["fighter_url"] == "http://example.com/fighter/abc"
        assert fight["result"] == "win"
        assert fight["opponent"] == "Stipe Miocic"
        assert fight["event"] == "UFC 309"
        assert fight["event_date"] == "Nov. 16, 2024"
        assert fight["method"] == "KO/TKO"
        assert fight["method_detail"] == "Spinning back kick"
        assert fight["round"] == "3"
        assert fight["time"] == "4:29"

    def test_loss_fight_captured(self):
        soup = BeautifulSoup(FIGHT_HISTORY_HTML, "html.parser")
        fights = _parse_fight_history(soup, "http://example.com/fighter/abc")
        loss = next(f for f in fights if f["result"] == "loss")
        assert loss["opponent"] == "Matt Hamill"
        assert loss["method"] == "DQ"

    def test_no_table_returns_empty(self):
        soup = BeautifulSoup("<html><body><p>No fights</p></body></html>", "html.parser")
        assert _parse_fight_history(soup, "http://x") == []
