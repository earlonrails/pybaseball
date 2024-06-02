import io
from datetime import date
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup

from . import cache
from .utils import most_recent_season, sanitize_date_range
from .datasources.bref import BRefSession

session = BRefSession()


def get_soup(team: str, start_dt: date, doubleheader: int = 0) -> BeautifulSoup:
    # get most recent standings if date not specified
    # if((start_dt is None) or (end_dt is None)):
    #    print('Error: a date range needs to be specified')
    #    return None
    # https://www.baseball-reference.com/boxes/DET/DET201007190.shtml
    url = "http://www.baseball-reference.com/boxes/{}/{}{}{}.shtml".format(team, team, start_dt.strftime('%Y%m%d'), doubleheader)
    s = session.get(url).content
    # a workaround to avoid beautiful soup applying the wrong encoding
    s = s.decode('utf-8')
    return BeautifulSoup(s, features="lxml")

def extract_line_score(data):
    return {
        'team': data[1],
        'line_score': ''.join(data[2:-4]),
        'runs': data[-4],
        'hits': data[-3],
        'errors': data[-2],
    }


def get_table(soup: BeautifulSoup) -> pd.DataFrame:
    table = soup.find_all('table')[0]
    data = []
    headings = [th.get_text() for th in table.find("tr").find_all("th")][1:]
    headings.append("mlbID")
    data.append(headings)
    table_body = table.find('tbody')
    rows = table_body.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        row_anchor = row.find("a")
        mlbid = row_anchor["href"].split("mlb_ID=")[-1] if row_anchor else pd.NA  # ID str or nan
        cols = [ele.text.strip() for ele in cols]
        cols.append(mlbid)
        data.append([ele for ele in cols])
    data = [extract_line_score(d) for d in data]
    df = pd.DataFrame(data)
    df = df.reindex(df.index.drop(0))
    return df


def boxes(team: str, date: str) -> pd.DataFrame:
    """
    Get all batting stats for a set time range. This can be the past week, the
    month of August, anything. Just supply the start and end date in YYYY-MM-DD
    format.
    """
    # make sure date inputs are valid
    game_date, end_dt_date = sanitize_date_range(date, date)
    if game_date.year < 2008:
        raise ValueError("Year must be 2008 or later")
    if end_dt_date.year < 2008:
        raise ValueError("Year must be 2008 or later")
    # retrieve html from baseball reference
    soup = get_soup(team, game_date)
    table = get_table(soup)
    table = table.dropna(how='all')  # drop if all columns are NA
    # scraped data is initially in string format.
    # convert the necessary columns to numeric.
    for column in ['Age', '#days', 'G', 'PA', 'AB', 'R', 'H', '2B', '3B',
                    'HR', 'RBI', 'BB', 'IBB', 'SO', 'HBP', 'SH', 'SF', 'GDP',
                    'SB', 'CS', 'BA', 'OBP', 'SLG', 'OPS', 'mlbID']:
        #table[column] = table[column].astype('float')
        table[column] = pd.to_numeric(table[column])
        #table['column'] = table['column'].convert_objects(convert_numeric=True)
    table = table.drop('', axis=1)
    return table
