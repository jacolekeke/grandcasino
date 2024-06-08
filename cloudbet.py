import time

import requests
import json

import datetime
from app import BetOdd, OpenBet, app, db

api_key = "eyJhbGciOiJSUzI1NiIsImtpZCI6IkhKcDkyNnF3ZXBjNnF3LU9rMk4zV05pXzBrRFd6cEdwTzAxNlRJUjdRWDAiLCJ0eXAiOiJKV1QifQ.eyJhY2Nlc3NfdGllciI6InRyYWRpbmciLCJleHAiOjIwMjgwNDU1ODksImlhdCI6MTcxMjY4NTU4OSwianRpIjoiYjIxZGRjZGYtZjZmNy00NTg1LWFlZDItOTVhNTkwMmU2YmUxIiwic3ViIjoiMzEyMTg1NDgtY2U3MS00NWJiLTlmNTctNmE4YmI3NTI5NjY2IiwidGVuYW50IjoiY2xvdWRiZXQiLCJ1dWlkIjoiMzEyMTg1NDgtY2U3MS00NWJiLTlmNTctNmE4YmI3NTI5NjY2In0.1e8o2kkX_UEccVndkKZDUS0IER6pFJPaSpIR3dzb486PyfpbFq82UggU6goIj9g7hns8sB1HNV__9U6XXLStE_x2qWDd2ZoFwMTeZeuGyMBFqdUK3Z-GGAg-_uYr3wqRB9QbhHHrS_BXEyTpRoxuGLncY8Yq87XuyfH0KbTAjexJOqd6RoseKGLnkex2mAaCc53CrLJh2ysq8wvLtRAYDxCQQN7eCbhRm58TDjTFZKU49u3kokNy4JuwLgjubcqC7F1ibYXwLMGPYH6kSN2zkApje_kmw3SSpJ3HqXptfdy1bIsV-GvlSXStpFnz7btp2Jj2Dhv4E4Hqclt8bRQRng"


def get_odds_cloudbet(is_live=False, sport_name="soccer"):
    with open("cloudbets_readable_json", "r") as language_data:
        language_dictionary = json.loads(language_data.read())

    if not is_live:
        event_url = f"https://sports-api.cloudbet.com/pub/v2/odds/events?sport={sport_name}&live=false&limit=1000&from={int(time.time())}&to={int(time.time() + 3600 * 24)}"
    else:
        event_url = f"https://sports-api.cloudbet.com/pub/v2/odds/events?sport={sport_name}&live=true&limit=1000"

    event_id = 123456
    headers = {
        "accept": "application/json",
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    bets = []

    try:
        response = requests.get(event_url.format(event_id), headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        event_data = response.json()
        data = (json.dumps(event_data, indent=4))

    except requests.exceptions.RequestException as e:
        print("Error:", e)
        return 0

    for competition in event_data.get("competitions"):
        for event in competition.get("events"):
            match = {
                "MatchID": event.get("id"),
                "DateTime": datetime.datetime.strptime(event.get("cutoffTime"), "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(hours=3),
                "League": competition.get("name"),
                "LeagueFlag": "n/a",
                "Team1": event.get("home").get("name"),
                "Team2": event.get("away").get("name"),
            }
            odds = []
            for market in event.get("markets").keys():
                submarkets = event.get("markets").get(market).get("submarkets")
                selections = []
                for submarket in list(submarkets.keys()):
                    for selection in submarkets.get(submarket).get("selections"):
                        selections.append(selection)
                category = "Tüm Bahisler"
                if len(language_dictionary.get(market).get("Variables")) > 0:
                    category = language_dictionary.get(market).get("Variables")[0]
                odds.append(
                    {
                        "gameName": language_dictionary.get(market).get("Name").replace("{{team}}", ""),
                        "category": category,
                        "gameDetails": "",
                        "odds": [{
                            "gameID": f'{event.get("id")}-{market}-{str(selection.get("outcome").replace("_", "/").replace("=", ": ").capitalize() + str(" | " if len(selection.get("params").replace("=", ": ")) > 3 else "") + selection.get("params").replace("=", ": ").replace("&", " ")).replace("%2b", "+")}',
                            "value": str(selection.get("outcome").replace("_", "/").replace("=", ": ").capitalize() + str(" | " if len(selection.get("params").replace("=", ": ")) > 3 else "") + selection.get("params").replace("=", ": ").replace("&", " ")).replace("%2b", "+"),
                            "odd": float(selection.get("price")),
                            "market_url": f"{market}/{selection.get('outcome')}?{selection.get('params')}"
                        } for selection in selections]
                    }
                )

            match["Bets"] = odds
            bets.append(match)

    return bets


def place_bet(bet_odd: BetOdd, reference_id):
    from app import app
    with app.app_context():
        trading_url = f"http://172.232.34.102/place/bet"
        headers = {
            "accept": "application/json",
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        open_bet = OpenBet.query.get(bet_odd.bet_option.open_bet_fk)
        market_url = bet_odd.market_url
        if len(market_url.split("?")[-1]) < 3:
            market_url = market_url.replace("?", "")
        data = {
            "acceptPriceChange": "BETTER",
            "currency": "PLAY_EUR",
            "eventId": str(open_bet.api_match_id),
            "marketUrl": str(market_url),
            "price": "1.02",
            "referenceId": str(reference_id),
            "stake": "1.1"
        }
        response = requests.post(trading_url, headers=headers, data=data)
        return response.json().get("status") == "ACCEPTED" or response.json().get("status") == "PENDING_ACCEPTANCE"


def cloudbet_instant_odd_update(bet_odd: BetOdd):
    with app.app_context():
        odd_url = f"https://sports-api.cloudbet.com/pub/v2/odds/lines"
        headers = {
            "accept": "application/json",
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        open_bet = OpenBet.query.get(bet_odd.bet_option.open_bet_fk)
        data = {
            "eventId": open_bet.api_match_id,
            "marketUrl": bet_odd.market_url,
        }
        response = requests.post(odd_url, headers=headers, data=json.dumps(data))
        for i in range(3):
            try:
                bet_odd.bettable = response.json().get("status") == "SELECTION_ENABLED"
                bet_odd.odd = float(response.json().get("price", 1))
                db.session.commit()
                break
            except:
                time.sleep(0.05)
                pass


def get_status_of_bet(bet_reference_id):
    odd_url = f"http://172.232.34.102/check/bet/{bet_reference_id}"
    headers = {
        "accept": "application/json",
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    response = requests.get(odd_url, headers=headers)
    return response.json().get("status")
