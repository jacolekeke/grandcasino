import datetime
import time

import requests
import sys

from sqlalchemy import text
# api_key = "zHMFjNS3bRu7vNgUrtr6JPMwOD5Jcuer7O9yw9pwNZMX4XBFwe2tazdyQLsq"
api_key = "na"


def get_live_score(open_bet):
    r = requests.get("https://www.thesportsdb.com/api/v2/json/623577/livescore.php?s=Soccer")
    match_likelihood = 0
    if not r.json().get("events"):
        return {
            "intHomeScore": "-",
            "intAwayScore": "-",
            "strProgress": "N/A"
        }
    for i in r.json().get("events"):
        for c in open_bet.team_1.split(" "):
            if c in i.get("strHomeTeam"):
                match_likelihood += 1
        for c in open_bet.team_2.split(" "):
            if c in i.get("strAwayTeam"):
                match_likelihood += 1
        if match_likelihood >= 2:
            return i

    return {
        "intHomeScore": "-",
        "intAwayScore": "-",
        "strProgress": "N/A"
    }


def get_team_badge(team_name):
    try:
        r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={team_name}")
        return r.json().get("teams")[0].get("strTeamBadge")
    except:
        try:
            r = requests.get(f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={team_name.split(' ')[0]}")
            return r.json().get("teams")[0].get("strTeamBadge")
        except:
            return None


def get_bettable_matches(date):
    r = requests.get(f"https://www.nosyapi.com/apiv2/service/bettable-matches?apiKey={api_key}&date={date}")
    return r.json()


def get_odds(match_id):
    r = requests.get(
        f'https://www.nosyapi.com/apiv2/service/bettable-matches/details?matchID={match_id}&apiKey={api_key}')
    return r.json()


def get_bets(is_live=False, sport_name="soccer"):
    from cloudbet import get_odds_cloudbet
    return get_odds_cloudbet(is_live=is_live, sport_name=sport_name)


def instant_odds_update(specific_match=None):
    from app import app, db, OpenBet, BetOdd, BetOption, BetCoupon
    with app.app_context():
        from cloudbet import cloudbet_instant_odd_update
        if not specific_match:
            print("Updating odds")
            open_bets = OpenBet.query.filter(OpenBet.bet_ending_datetime < datetime.datetime.now()).all()
            for open_bet in open_bets:
                for option in open_bet.bet_options:
                    for odd in option.bet_odds:
                        cloudbet_instant_odd_update(odd)
            print("Updated odds")
        else:
            open_bet = OpenBet.query.get(specific_match)
            for option in open_bet.bet_options:
                for odd in option.bet_odds:
                    if odd.bettable:
                        cloudbet_instant_odd_update(odd)


# TO DO: Fix celery: https://medium.com/@Aman-tech/celery-with-flask-d1f1c555ceb7
def place_bets_with_coupon(current_coupon_id, current_user_id, coupon_value):
    from app import app, db, BetCoupon, User
    with app.app_context():
        with db.session.no_autoflush:
            current_coupon = BetCoupon.query.get(current_coupon_id)
            current_user = User.query.get(current_user_id)
            current_coupon.status = "Oluşturuldu"
            current_coupon.total_value = float(coupon_value)

            from cloudbet import place_bet
            for i in current_coupon.all_selects:
                if not place_bet(i.odd, i.reference_id):
                    raise ValueError

            if current_user.freebet:
                freebet_amount = current_user.freebet if current_user.freebet <= float(
                    coupon_value) else float(coupon_value)
                current_user.balance -= (float(coupon_value) - freebet_amount)
                current_coupon.freebet_amount = freebet_amount
                current_user.freebet -= freebet_amount
            else:
                current_user.balance -= float(coupon_value)
                current_coupon.freebet_amount = 0
            db.session.commit()


def register_open_bet():
    from app import app, db, OpenBet, BetOdd, BetOption, BetCoupon
    sports = ["soccer", "volleyball", "basketball", "tennis", "cricket", "american_football"]
    with app.app_context():
        for sport in sports:
            for bet in get_bets(is_live=False, sport_name=sport):
                start_time = time.time()
                if len(OpenBet.query.filter_by(api_match_id=bet.get("MatchID")).all()) > 0:
                    continue
                new_open_bet = OpenBet(
                    api_match_id=bet.get("MatchID"),
                    bet_ending_datetime=bet.get("DateTime"),
                    match_league=bet.get("League"),
                    league_icon_url=bet.get("LeagueFlag"),
                    team_1=bet.get("Team1"),
                    team_2=bet.get("Team2"),
                    has_odds=False,
                    live_betting_expired=False,
                    sport=sport
                )
                db.session.add(new_open_bet)
                db.session.commit()

                for bet_option in bet.get("Bets"):
                    new_bet_option = BetOption(
                        game_name=bet_option.get("gameName"),
                        game_details=bet_option.get("gameDetails"),
                        open_bet_fk=new_open_bet.id,
                        category=bet_option.get("category")
                    )
                    db.session.add(new_bet_option)
                    db.session.commit()

                    for bet_odd in bet_option.get("odds"):
                        query = """
                                    INSERT INTO bet_odd (game_id, odd, value, bet_option_fk, bettable, market_url)
                                    VALUES (:game_id, :odd, :value, :bet_option_fk, :bettable, :market_url)
                                    ON CONFLICT (game_id) DO UPDATE
                                    SET odd = EXCLUDED.odd, bettable = EXCLUDED.bettable, market_url = EXCLUDED.market_url, bet_option_fk = EXCLUDED.bet_option_fk
                                    """

                        params = {
                            "game_id": bet_odd.get("gameID"),
                            "odd": bet_odd.get("odd"),
                            "value": bet_odd.get("value").replace("Home", new_open_bet.team_1)
                            .replace("home", new_open_bet.team_1).replace("away", new_open_bet.team_2)
                            .replace("Away", new_open_bet.team_2).replace("Draw", "Berabere")
                            .replace("draw", "berabere"),
                            "bet_option_fk": new_bet_option.id,
                            "bettable": True,
                            "market_url": bet_odd.get("market_url")
                        }
                        new_open_bet.has_odds = True

                        db.session.execute(text(query), params)

                    db.session.commit()
                try:
                    new_open_bet.live_betting_expired = False
                    db.session.commit()
                except:
                    pass
                print(time.time() - start_time)
        db.session.commit()


def get_results(match_id):
    from app import app, db, OpenBet, BetOdd, BetOption, BetCoupon
    with app.app_context():
        r = requests.get(f'https://www.nosyapi.com/apiv2/service/bettable-result?matchID={match_id}&apiKey={api_key}')
        for i in r.json().get("data")[0].get("bettableResult", []):
            game_id = i.get("gameID")

            for c in BetOdd.query.filter_by(game_id=game_id).all():
                c.status = "Başarısız"

            value = i.get("value")
            BetOdd.query.filter_by(game_id=game_id).filter_by(value=value).first().status = "Başarılı"
            db.session.commit()


def live_betting():
    print("Live bet update options")
    start_time = time.time()
    from app import app, db, OpenBet, BetOdd, BetOption, BetCoupon
    import datetime

    sports = ["soccer", "volleyball", "basketball", "tennis", "cricket", "american_football"]

    with app.app_context():
        try:
            with db.session.no_autoflush:
                current_time = datetime.datetime.now()

                # Expire open bets and bet odds
                db.session.execute(
                    text("""
                    UPDATE open_bet
                    SET live_betting_expired = TRUE
                    WHERE bet_ending_datetime < :current_time AND live_betting_expired = FALSE
                    """),
                    {"current_time": current_time}
                )

                db.session.execute(
                    text("""
                    UPDATE bet_odd
                    SET bettable = FALSE, bet_option_fk = 0
                    WHERE bet_option_fk IN (
                        SELECT id FROM bet_option WHERE open_bet_fk IN (
                            SELECT id FROM open_bet WHERE live_betting_expired = TRUE
                        )
                    )
                    """)
                )

                db.session.execute(
                    text("""
                    DELETE FROM bet_option
                    WHERE open_bet_fk IN (
                        SELECT id FROM open_bet WHERE live_betting_expired = TRUE
                    )
                    """)
                )

                db.session.commit()

                for sport in sports:
                    for bet in get_bets(is_live=True, sport_name=sport):
                        start_time = time.time()
                        new_open_bet = OpenBet.query.filter_by(api_match_id=bet.get("MatchID")).first()
                        if not new_open_bet:
                            continue

                        for bet_option in bet.get("Bets"):
                            new_bet_option = BetOption(
                                game_name=bet_option.get("gameName"),
                                game_details=bet_option.get("gameDetails"),
                                open_bet_fk=new_open_bet.id,
                                category=bet_option.get("category")
                            )
                            db.session.add(new_bet_option)
                            db.session.commit()

                            for bet_odd in bet_option.get("odds"):
                                query = """
                                INSERT INTO bet_odd (game_id, odd, value, bet_option_fk, bettable, market_url)
                                VALUES (:game_id, :odd, :value, :bet_option_fk, :bettable, :market_url)
                                ON CONFLICT (game_id) DO UPDATE
                                SET odd = EXCLUDED.odd, bettable = EXCLUDED.bettable, market_url = EXCLUDED.market_url, bet_option_fk = EXCLUDED.bet_option_fk
                                """

                                params = {
                                    "game_id": bet_odd.get("gameID"),
                                    "odd": bet_odd.get("odd"),
                                    "value": bet_odd.get("value").replace("Home", new_open_bet.team_1)
                                    .replace("home", new_open_bet.team_1).replace("away", new_open_bet.team_2)
                                    .replace("Away", new_open_bet.team_2).replace("Draw", "Berabere")
                                    .replace("draw", "berabere"),
                                    "bet_option_fk": new_bet_option.id,
                                    "bettable": True,
                                    "market_url": bet_odd.get("market_url")
                                }

                                db.session.execute(text(query), params)

                            db.session.commit()
                        try:
                            new_open_bet.live_betting_expired = False
                            db.session.commit()
                        except:
                            pass
                db.session.commit()
        except Exception as e:
            print(f"Error occurred: {e}")

    print("Live bet updated options")
    print(time.time() - start_time)

# Integrate distribute_rewards for cloudbet and make it so people should click on the coupon to claim rewards.


def distribute_rewards():
    from app import app, db, OpenBet, BetOdd, BetOption, BetCoupon
    with app.app_context():
        for i in OpenBet.query.filter(
                OpenBet.bet_ending_datetime < datetime.datetime.now() + datetime.timedelta(hours=3)).all():
            try:
                i.update_results()
                db.session.delete(i)
                db.session.commit()
            except Exception as e:
                pass

        for i in BetCoupon.query.filter_by(status="Oluşturuldu"):
            try:
                i.give_reward()
                i.status = "Tamamlandı"
                db.session.commit()
            except Exception as e:
                pass


def open_bet_garbage_collector():
    from app import app, db, OpenBet, BetOption
    with app.app_context():
        for i in OpenBet.query.filter(
                OpenBet.bet_ending_datetime < datetime.datetime.now() + datetime.timedelta(hours=12)).all():
            for c in i.bet_options:
                for j in c.bet_odds:
                    db.session.delete(j)
                db.session.delete(c)
            db.session.delete(i)

