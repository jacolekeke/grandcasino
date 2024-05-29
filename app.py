import datetime
import os.path

import random
from uuid import uuid4

import flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_required, login_user, UserMixin, logout_user
from flask_bcrypt import Bcrypt
from sqlalchemy import desc
import requests

from sqlalchemy import or_

import shortuuid
import feedparser
import base64
from imap_tools import MailBox
from flask_mail import Mail, Message

app = flask.Flask(__name__)

games_and_descriptions = {
    "wheel": "In this Plutus original you place a  bet and turn the wheel. "
             "You either double your money or leave empty handed.",
    "up_or_down": "In this Plutus original you try to guess if the next number is going to be higher or "
                  "lower then the displayed number. For every correct guess get 50% compounded every time. In this "
                  "game we do not have a statistical edge a correct strategy and a strong will can even give you the "
                  "advantage.",
    "limbo": "Limbo seçtiğiniz çarpanın üzerinde mi yoksa altında mı çarpan geleceğini tahmin ettiğiniz bir KadroMilyon özel oyunudur.",
    "slots-egyptian": "Plutus Slots has the lowest house edge in "
                      "any slot game ever with only 0.015% (99.985% RTP). 1000x Jackpot",
    "slots-jungle": "A slot game build solely for adventure seekers. 13250x Jackpot and 500x if you match all 5 slots "
                    "but nothing else! Only 0.34% House Edge(99.66% RTP)",
    "slots-knight": "The least risky slot game! You win something in almost every condition!",
    "multiplier": "In this Plutus original you choose one of the five cards and receive the multiplier"
                  " written on their front. Four of them are going to make you lose money and one will triple it",
    "hit_or_pass": "In this Plutus original player decides to get a new multiplier or withdraw with the "
                   "existing ones. One you open a new card there is no going back when you withdraw all of your "
                   "multipliers are multiplied and your wins are calculated. ",
    "max_money": "Drawn daily and the player that bets the highest amount wins all the money",
    "double": "Double paranızı ikiye katlayabileceğiniz yüksek adrenelinli bir KadroMilyon orijinal oyunudur."
              " Double ile kazanma potansiyeliniz tam anlamıyla sınırsızdır. Paranızı sonsuza kadar ikiye katlamaya devam edebilirsiniz.",
    "divo": "In this Plutus original you divide your bet into different sections and only one of them wins. "
            "Create your own play style according to your risk tolerance.",
    "horse_races": "In Plutus version of the horse race betting all the bets are pooled into a prize pool "
                   "and "
                   "distributed equally between winners. Each bet is 5PLT,"
                   " make riskier bets to split the prize with fewer people.",
    "steal_hub": "In this Plutus original, you decide if you want to steal the "
                 "reward from the other person or 1.5x it and go for another round."
}

super_lig_teams = ['Hatayspor', 'Beşiktaş', 'Antalyaspor', 'Alanyaspor', 'Rizespor',
                   'Sivasspor', 'Fenerbahçe', 'Galatasaray', 'Gaziantep', 'İstanbulspor',
                   'Kasımpaşa', 'Ankaragücü', 'Kayserispor', 'Başakşehir', 'Pendikspor',
                   'Trabzonspor', 'Konyaspor', 'Karagümrük', 'Samsunspor', 'AdanaDemirspor']

premier_lig_teams = ['Arsenal', 'AstonVilla', 'Bournemouth', 'Brentford', 'Brighton',
                     'Burnley', 'Chelsea', 'CrystalPalace', 'Everton', 'Fulham', 'Liverpool',
                     'Luton', 'ManchesterCity', 'ManchesterUnited', 'NewcastleUnited',
                     'NotthinghamForest', 'NotthinghamForest', 'SheffieldUnited', 'TottenhamHotspur',
                     'WestHamUnited', 'WolverhamptonWanderers']

laliga_teams = ['AthleticBilbao', 'AtleticoMadrid', 'Osasuna', 'Cadiz',
                'DeportivoAlaves', 'Barcelona', 'Getafe', 'Girona', 'Granada',
                'RayoVallecano', 'CeltaVigo', 'Mallorca', 'RealBetis', 'RealMadrid',
                'RealSociedad', 'Sevilla', 'Almeria', 'LasPalmas', 'Valencia', 'Villareal']

bundesliga_teams = ['BayernMünih', 'BorussiaDortmund', 'Leipzig', 'UnionBerlin',
                    'Freiburg', 'BayerLeverkusen', 'EintrachtFrankfurt', 'Wolfsburg',
                    'Mainz', 'BorussiaMönchengladbach', 'Köln', 'Hoffenheim', 'WederBremen',
                    'Bochum', 'Augsburg', 'Stuttgart', 'Darmstadt', 'Heidenheim']

app.config["SECRET_KEY"] = "ksjf-sjc-wsf12-sac"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["DO_ROUTE_USERS"] = True
# True if website is not kadromilyon
app.config["CASINO_BASE_URL"] = "http://172.233.240.137/casino-callback/"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'operations@m2betting.com'
app.config['MAIL_PASSWORD'] = 'qvegsrxwmbwrxaxx'
app.config['MAIL_DEFAULT_SENDER'] = 'operations@m2betting.com'

mail = Mail(app)

db = SQLAlchemy(app)

login_manager = LoginManager(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)


def user_on_mobile() -> bool:
    user_agent = flask.request.headers.get("User-Agent")
    user_agent = user_agent.lower()
    phones = ["android", "iphone"]

    if any(x in user_agent for x in phones):
        return True
    return False


# TEST APP PASSWORD for kadromilyon@gmail.com: dbpixumfhzuvkvzu

def get_unread_emails(username, password):
    with MailBox('imap.gmail.com').login(username, password, 'INBOX') as mailbox:
        data = [(msg.subject, msg.text) for msg in mailbox.fetch()]


def get_unread_email(username, password):
    atom_feed_url = f"https://mail.google.com/mail/feed/atom"

    auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_str}"}
    response = feedparser.parse(requests.get(atom_feed_url, headers=headers).text)

    unread_emails = []

    for entry in response.entries:
        sender = entry.author
        subject = entry.title
        summary = entry.summary

        unread_emails.append({"sender": sender, "subject": subject, "summary": summary})

    return unread_emails


class PaymentSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_active_payment_source = db.Column(db.Boolean)
    payment_type = db.Column(db.String)
    payment_number = db.Column(db.String)
    account_holder_name = db.Column(db.String)


class Referrer(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_fk = db.Column(db.Integer)
    commission_rate = db.Column(db.Float)

    @property
    def user(self):
        return User.query.get(self.user_fk)


class SitePartner(db.Model):
    id = db.Column(db.String, primary_key=True)
    commission_rate = db.Column(db.Integer)
    partnership_earnings = db.Column(db.Float)
    partnership_balance = db.Column(db.Float)
    partnership_status = db.Column(db.String)


class UserAssignedPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_fk = db.Column(db.String)
    permission_fk = db.Column(db.String)


class UserPermissions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permissions_list = db.Column(db.String)
    permission_name = db.Column(db.String)


class ContactM2(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    message = db.Column(db.String)


class PartnerSession(db.Model):
    id = db.Column(db.String, primary_key=True)
    balance = db.Column(db.Float)
    api_key = db.Column(db.String)

    def trigger_balance_operation(self, balance_change, reason):
        casino_partner = CasinoPartner.query.filter_by(api_key=self.api_key).first()
        new_bet_transaction = BetTransaction(type=reason, api_key=self.api_key, amount=balance_change,
                                             transaction_date=datetime.date.today())
        db.session.add(new_bet_transaction)
        requests.post(casino_partner.callback_url, data={
            "balance_change": balance_change,
            "reason": reason,
            "session_id": self.id
        })
        db.session.commit()


class BonusAssigned(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bonus_fk = db.Column(db.Integer)
    user_fk = db.Column(db.Integer)
    bonus_assigned_date = db.Column(db.DateTime)
    status = db.Column(db.String)
    bonus_amount = db.Column(db.Float)

    @property
    def user(self):
        return User.query.get(self.user_fk)

    @property
    def bonus(self):
        return Bonus.query.get(self.bonus_fk)


class Bonus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bonus_product = db.Column(db.String)
    bonus_type = db.Column(db.String)
    bonus_name = db.Column(db.String)
    minimum_bonus_amount = db.Column(db.Float)
    maximum_bonus_amount = db.Column(db.Float)
    who_can_cancel = db.Column(db.String)
    on_cancel = db.Column(db.String)
    currency = db.Column(db.String)
    minimum_deposit = db.Column(db.Float)
    maximum_deposit = db.Column(db.Float)
    minimum_spin = db.Column(db.Integer)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    valid_thru = db.Column(db.Integer)
    bonus_description = db.Column(db.String)
    round_value = db.Column(db.Integer)


class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bonus_fk = db.Column(db.Integer)
    name = db.Column(db.String)
    code = db.Column(db.String)
    bonus_amount = db.Column(db.Float)
    number_of_users = db.Column(db.Integer)

    @property
    def bonus(self):
        return Bonus.query.get(self.bonus_fk)

    @property
    def n_players_using_promo_code(self):
        return len(list(filter(lambda item: item.user is not None, AssignedPromoCode.query.filter_by(promo_code_fk=self.id).all())))

    @property
    def players_using_promo_code(self):
        return [i.user for i in list(filter(lambda item: item.user is not None, AssignedPromoCode.query.filter_by(promo_code_fk=self.id).all()))]


class AssignedPromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_fk = db.Column(db.Integer)
    promo_code_fk = db.Column(db.Integer)

    @property
    def user(self):
        return User.query.get(self.user_fk)

    @property
    def promo_code(self):
        return PromoCode.query.get(self.promo_code_fk)


class BonusRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bonus_fk = db.Column(db.Integer)
    user_fk = db.Column(db.Integer)
    status = db.Column(db.String)

    @property
    def bonus(self):
        return Bonus.query.get(self.bonus_fk)

    @property
    def user(self):
        return User.query.get(self.user_fk)


class DoubleOrNothing(db.Model):
    id = db.Column(db.String, primary_key=True)
    current_offer = db.Column(db.Float)


class CasinoPartner(db.Model):
    id = db.Column(db.String, primary_key=True)
    api_key = db.Column(db.String)
    callback_url = db.Column(db.String)


class OpenUserBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_user_id = db.Column(db.String)
    creator_partner_api_key = db.Column(db.String)
    bet_description = db.Column(db.String)
    bet_amount = db.Column(db.Float)
    opp_amount = db.Column(db.Float)
    offer_expiration_datetime = db.Column(db.DateTime)

    def take_bet(self, user_2, user_2_api_key):
        if self.is_taken:
            return 0

        new_taken_bet = TakenBet(
            user_1_id=self.user_id, user_2_id=user_2, open_user_bet_fk=self.id,
            user_1_partner_api_key=self.creator_partner_api_key,
            user_2_partner_api_key=user_2_api_key
        )
        new_bet_transaction = BetTransaction(
            type="bet_taken",
            api_key=new_taken_bet.user_1_partner_api_key,
            amount=-1 * self.bet_amount + (-1 * self.bet_amount) / 100 * 0.14,
            transaction_date=datetime.date.today()
        )
        db.session.add(new_bet_transaction)

        new_bet_transaction_2 = BetTransaction(
            type="bet_taken",
            api_key=new_taken_bet.user_1_partner_api_key,
            amount=-1 * self.opp_amount + (-1 * self.bet_amount) / 100 * 0.14,
            transaction_date=datetime.date.today()
        )
        db.session.add(new_bet_transaction_2)

        db.session.add(new_taken_bet)
        db.session.commit()

        return new_taken_bet

    @property
    def is_taken(self):
        return len(TakenBet.query.filter_by(open_user_bet_fk=self.id).all()) > 0

    def submit_bet_claim(self, submitting_user):
        taken_bet = TakenBet.query.filter_by(open_user_bet_fk=self.id).first()
        taken_bet.status = "Claim Made"
        taken_bet.winner = submitting_user
        db.session.commit()

    def check_bet_claim_status(self, user_to_check_for):
        taken_bet = TakenBet.query.filter_by(open_user_bet_fk=self.id).first()
        if taken_bet is None:
            return "Pending Acceptance"
        if taken_bet.status == "Taken":
            return "Taken"
        if taken_bet.status == "Claim Made":
            if taken_bet.winner == user_to_check_for:
                return "Claim Made By You"
            else:
                return "Claim Made By Opposing"
        if taken_bet.status == "Disputed":
            return "Disputed"
        return "Unavailable"

    def dispute_bet_claim(self, disputing_user):
        taken_bet = TakenBet.query.filter_by(open_user_bet_fk=self.id).first()

        if taken_bet.status == "Claim Made" and not disputing_user == taken_bet.winner and \
                disputing_user in [taken_bet.user_1_id, taken_bet.user_2_id]:
            taken_bet.status = "Disputed"
            db.session.commit()

            partner_1 = CasinoPartner.query.filter_by(api_key=taken_bet.user_1_partner_api_key).first()
            partner_2 = CasinoPartner.query.filter_by(api_key=taken_bet.user_2_partner_api_key).first()

            requests.post(partner_1.callback_url, data={
                "reason": "Bet Disputed",
                "bet_id": taken_bet.open_user_bet_fk,
                "disputer": disputing_user
            })

            requests.post(partner_2.callback_url, data={
                "reason": "Bet Disputed",
                "bet_id": taken_bet.open_user_bet_fk,
                "disputer": disputing_user
            })

    def accept_bet_claim(self, accepting_user):
        taken_bet = TakenBet.query.filter_by(open_user_bet_fk=self.id).first()
        if taken_bet.status == "Claim Made" and not accepting_user == taken_bet.winner and \
                accepting_user in [taken_bet.user_1_id, taken_bet.user_2_id]:
            taken_bet.status = "Bet Completed"
            db.session.commit()

            partner_1 = CasinoPartner.query.filter_by(api_key=taken_bet.user_1_partner_api_key).first()
            partner_2 = CasinoPartner.query.filter_by(api_key=taken_bet.user_2_partner_api_key).first()

            requests.post(partner_1.callback_url, data={
                "reason": "Bet Completed",
                "bet_id": taken_bet.open_user_bet_fk,
                "winner": taken_bet.winner
            })

            requests.post(partner_2.callback_url, data={
                "reason": "Bet Completed",
                "bet_id": taken_bet.open_user_bet_fk,
                "winner": taken_bet.winner
            })

            return {
                "status": "Bet Completed",
                "winner": taken_bet.winner
            }
        return {
            "status": "Permission Denied, user cannot accept this bet."
        }


class TakenBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String, default="Taken")
    user_1_id = db.Column(db.String)
    user_1_partner_api_key = db.Column(db.String)
    user_2_id = db.Column(db.String)
    user_2_partner_api_key = db.Column(db.String)
    winner = db.Column(db.String, default="To Be Determined")
    open_user_bet_fk = db.Column(db.String)


class BetTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String)
    api_key = db.Column(db.String)
    amount = db.Column(db.Float)
    transaction_date = db.Column(db.Date)


class M2CallbackRouter(db.Model):
    id = db.Column(db.String, primary_key=True)
    user_uuid = db.Column(db.String)
    base_url = db.Column(db.String)


class User(db.Model, UserMixin):
    id = db.Column(db.String, primary_key=True)
    username = db.Column(db.String)
    user_uuid = db.Column(db.String)
    email = db.Column(db.String, unique=True)
    password = db.Column(db.String)
    is_admin = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Float, default=0)
    referred_by = db.Column(db.String)
    freebet = db.Column(db.Float)
    freebet_usable = db.Column(db.Float)
    telegram_chat_id = db.Column(db.String)
    last_login = db.Column(db.DateTime)
    registration_date = db.Column(db.DateTime)
    ip_address = db.Column(db.String)
    notes = db.Column(db.String)
    casino_bonus_balance = db.Column(db.Float)
    sports_bonus_balance = db.Column(db.Float)
    completed_first_deposit = db.Column(db.Boolean)
    site_partner_fk = db.Column(db.Integer)

    def send_password_reset_email(self, current_domain):
        msg = Message(
            'KadroMilyon şifre sıfırlama talebi ',
            recipients=[self.email],
            body=f'Şifrenizi sıfırlamak için bu linke tıklayın: {current_domain}?reset_code={self.user_uuid}'
        )
        mail.send(msg)

    @property
    def permission_name(self):
        assigned_permission = UserAssignedPermission.query.filter_by(user_fk=self.id).first()
        user_permission = UserPermissions.query.get(assigned_permission.permission_fk)
        return user_permission.permission_name

    def user_has_permission(self, permission_to_check):
        assigned_permission = UserAssignedPermission.query.filter_by(user_fk=self.id).first()
        user_permission = UserPermissions.query.get(assigned_permission.permission_fk)
        return permission_to_check in user_permission.permissions_list.split("&&")

    @property
    def site_partner(self):
        return SitePartner.query.get(self.site_partner_fk)

    @property
    def referrer(self):
        referrer_obj = Referrer.query.get(self.referred_by)
        if referrer_obj:
            return referrer_obj.user
        else:
            return None

    @property
    def reference_code(self):
        referrer_obj = Referrer.query.filter_by(user_fk=self.id).first()
        return referrer_obj.id

    def get_bonuses(self, product, bonus_type):
        assigned_bonuses = BonusAssigned.query.filter_by(user_fk=self.id).filter_by(status="Kullanılabilir").all()

        for assigned_bonus in assigned_bonuses:
            bonus = Bonus.query.get(assigned_bonus.bonus_fk)

            if bonus.bonus_type == bonus_type and bonus.bonus_product == product:
                if datetime.datetime.now() < assigned_bonus.bonus_assigned_date + \
                        datetime.timedelta(days=bonus.valid_thru):
                    return assigned_bonus
                else:
                    assigned_bonus.status = "Tarihi Geçti"
                    db.session.commit()

    def give_percent_bonus(self, bonus, amount):
        return amount / 100 * bonus.bonus_amount

    # To implement: freespin, loss, freebet, try

    @property
    def mybets(self):
        return BetCoupon.query.filter_by(user_fk=self.id).all()

    def update_bonus_balance(self, deposit_amount):
        bonuses = [
            self.get_bonuses("casino", "yatirim-bonusu"),
            self.get_bonuses("casino", "ilk-yatirim-bonusu"),
            self.get_bonuses("sport-betting", "ilk-yatirim-bonusu"),
            self.get_bonuses("sport-betting", "yatirim-bonusu")
        ]
        for bonus in bonuses:
            if not bonus:
                continue
            if bonus.bonus.minimum_deposit < deposit_amount < bonus.bonus.maximum_deposit:
                if bonus.bonus.bonus_product == "casino":
                    self.casino_bonus_balance += self.give_percent_bonus(bonus, deposit_amount)
                else:
                    self.sports_bonus_balance += self.give_percent_bonus(bonus, deposit_amount)
                bonus.status = "Kullanıldı"

        db.session.commit()

    # TO DO: call this method everytime user makes deposit

    def get_last(self, transaction_type):
        latest_transaction = TransactionLog.query.filter(
            TransactionLog.transaction_status == "Tamamlandı",
            TransactionLog.transaction_type == transaction_type,
            TransactionLog.user_fk == self.id
        ).order_by(desc(TransactionLog.transaction_date)).first()

        if transaction_type == "çekim":
            latest_transaction = WithdrawalRequest.query.filter(
                WithdrawalRequest.status == "Tamamlandı",
                WithdrawalRequest.user_fk == self.id
            ).order_by(desc(WithdrawalRequest.request_date)).first()
            if latest_transaction:
                return latest_transaction.request_date
            else:
                return "-"

        if latest_transaction:
            return latest_transaction.transaction_date
        else:
            return "-"

    def get_total_volume(self, transaction_type):
        latest_transactions = TransactionLog.query.filter(
            TransactionLog.transaction_status == "Tamamlandı",
            TransactionLog.transaction_type == transaction_type,
            TransactionLog.user_fk == self.id
        ).order_by(desc(TransactionLog.transaction_date)).all()

        if transaction_type == "çekim":
            latest_transactions = WithdrawalRequest.query.filter(
                WithdrawalRequest.status == "Tamamlandı",
                WithdrawalRequest.user_fk == self.id
            ).order_by(desc(WithdrawalRequest.request_date)).all()
            return sum([i.withdrawal_amount for i in latest_transactions])

        if latest_transactions:
            return sum([i.transaction_amount for i in latest_transactions])
        else:
            return "-"

    @property
    def total_bets(self):
        return sum([i.transaction_amount for i in TransactionLog.query.filter(
            TransactionLog.transaction_type.in_(["place_bet", "casino_win", "casino_bet"]),
            TransactionLog.user_fk == self.id
        ).all()])

    @property
    def user_information(self):
        user_information = UserInformation.query.filter_by(user_fk=self.id).first()

        if user_information is None:
            user_information = UserInformation(user_fk=self.id, tel_no="", address="", name="")
            db.session.add(user_information)
            db.session.commit()

        return user_information

    @property
    def active_drafts(self):
        drafts_for_user = Draft.query.filter_by(user_fk=self.id).all()
        active_drafts = []
        for i in drafts_for_user:
            if i.competition.end_date >= datetime.datetime.today().date():
                active_drafts.append(i)
        active_drafts.reverse()
        return active_drafts

    @property
    def previous_drafts(self):
        drafts_for_user = Draft.query.filter_by(user_fk=self.id).all()
        active_drafts = []
        for i in drafts_for_user:
            if i.competition.end_date < datetime.datetime.today().date():
                active_drafts.append(i)
        active_drafts.reverse()
        return active_drafts


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_name = db.Column(db.String)

    def add_image(self, image_url):
        img_data = requests.get(image_url).content
        with open("static/" + self.team_name + ".png", 'wb') as handler:
            handler.write(img_data)
        db.session.commit()


@login_manager.user_loader
def user_loader(user_id):
    user = User.query.get(user_id)
    return user


class UserInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    tel_no = db.Column(db.String)
    user_fk = db.Column(db.Integer)
    address = db.Column(db.String)
    date_of_birth = db.Column(db.String)
    tc_kimlik_no = db.Column(db.Integer)
    gender = db.Column(db.String)
    id_verified = db.Column(db.Boolean)


class OpenBet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_match_id = db.Column(db.String)
    bet_ending_datetime = db.Column(db.DateTime)
    league_icon_url = db.Column(db.String)
    match_league = db.Column(db.String)
    team_1 = db.Column(db.String)
    team_2 = db.Column(db.String)
    has_odds = db.Column(db.Boolean)
    live_betting_expired = db.Column(db.Boolean)
    sport = db.Column(db.String)

    def update_results(self):
        from betting_utils import get_results
        get_results(self.api_match_id)

    @property
    def team_1_logo(self):
        from betting_utils import get_team_badge
        return get_team_badge(self.team_1)

    @property
    def team_2_logo(self):
        from betting_utils import get_team_badge
        return get_team_badge(self.team_2)

    @property
    def who_wins_bet(self):
        return BetOption.query.filter_by(open_bet_fk=self.id).filter_by(game_name="Maç Sonucu").first()

    @property
    def sport_readable(self):
        sports_turkish = {
            "soccer": "Futbol",
            "volleyball": "Voleybol",
            "basketball": "Basketbol",
            "tennis": "Tennis",
            "cricket": "Kriket",
            "american_football": "Amerikan Futbolu"
        }
        return sports_turkish.get(self.sport)

    @property
    def bet_options(self):
        options = BetOption.query.filter_by(open_bet_fk=self.id).all()
        unique_games = []
        unique_game_names = []
        for i in options:
            if i.game_name not in unique_game_names:
                unique_games.append(i)
                unique_game_names.append(i.game_name)
        return unique_games

    @property
    def has_live_odds(self):
        return True


class BetCoupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_fk = db.Column(db.Integer)
    total_value = db.Column(db.Float, default=0)
    status = db.Column(db.String, default="Oluşturuluyor")
    freebet_amount = db.Column(db.Float)

    @property
    def all_selects(self):
        return BetSelectedOption.query.filter_by(bet_coupon_fk=self.id).all()

    @property
    def total_odd(self):
        total_odd = 1
        for i in BetSelectedOption.query.filter_by(bet_coupon_fk=self.id).all():
            if i.odd:
                total_odd *= i.odd_locked_in_rate

        return total_odd

    @property
    def odd_options(self):
        if self.status == "Oluşturuluyor":
            for i in self.all_selects:
                if not i.odd.bettable:
                    db.session.delete(i)
                    db.session.commit()
        return [i.odd for i in self.all_selects]

    def is_successful(self):
        all_success = True
        for i in BetSelectedOption.query.filter_by(bet_coupon_fk=self.total_value).all():
            if i.odd.status == "Sonuçlanmadı":
                self.status = "Sonuçlanmadı"
                db.session.commit()
                return 0

            if i.odd.status == "Başarısız":
                all_success = False

        return all_success

    def give_reward(self):
        all_success = True
        total_odd = 1
        for i in BetSelectedOption.query.filter_by(bet_coupon_fk=self.total_value).all():
            if i.odd.status == "Sonuçlanmadı":
                self.status = "Sonuçlanmadı"
                db.session.commit()
                return 0

            if i.odd.status == "Başarısız":
                all_success = False

            total_odd *= i.odd_locked_in_rate
        if all_success:
            self.status = "Başarısız"
            db.session.commit()
            return 0

        else:
            User.query.get(self.user_fk).balance = (self.total_value * total_odd) - self.freebet_amount
            db.session.commit()
            self.status = "Başarılı"
            db.session.commit()
            return 0


class BetSelectedOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bet_odd_fk = db.Column(db.Integer)
    bet_coupon_fk = db.Column(db.Integer)
    bet_option_fk = db.Column(db.Integer)
    odd_locked_in_rate = db.Column(db.Float)
    reference_id = db.Column(db.String)
    match_name = db.Column(db.String)
    game_name = db.Column(db.String)

    @property
    def odd(self):
        return BetOdd.query.get(self.bet_odd_fk)


class BetOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_name = db.Column(db.String)
    game_details = db.Column(db.String)
    open_bet_fk = db.Column(db.Integer)
    match_name_row = db.Column(db.String)

    @property
    def match_name(self):
        open_bet = OpenBet.query.get(self.open_bet_fk)
        if not open_bet:
            return self.match_name_row
        self.match_name_row = open_bet.team_1 + " - " + open_bet.team_2
        db.session.commit()
        return self.match_name_row

    @property
    def bet_odds(self):
        bet_odds = BetOdd.query.filter_by(bet_option_fk=self.id).filter_by(bettable=True).all()
        if self.game_name == "Maç Sonucu":
            processed_bet_odds = [0, 0, 0]
            for i in bet_odds:
                if i.value == self.open_bet_obj.team_1:
                    processed_bet_odds[0] = i
                elif i.value == self.open_bet_obj.team_2:
                    processed_bet_odds[2] = i
                else:
                    processed_bet_odds[1] = i

            return processed_bet_odds

        return bet_odds

    @property
    def open_bet_obj(self):
        return OpenBet.query.get(self.open_bet_fk)

    @property
    def has_odds(self):
        bet_odds = BetOdd.query.filter_by(bet_option_fk=self.id).filter_by(bettable=True).all()
        return len(bet_odds) > 0


class BetOdd(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.String, unique=True)
    odd = db.Column(db.Float)
    value = db.Column(db.String)
    bet_option_fk = db.Column(db.Integer)
    status = db.Column(db.String, default="Sonuçlanmadı")
    bettable = db.Column(db.Boolean)
    market_url = db.Column(db.String)

    @property
    def ended(self):
        return OpenBet.query.get(
            BetOption.query.get(self.bet_option_fk).open_bet_fk).bet_ending_datetime < datetime.datetime.now()

    @property
    def bet_option(self):
        return BetOption.query.get(self.bet_option_fk)

    @property
    def user_selected(self):
        current_coupon = BetCoupon.query.filter_by(user_fk=current_user.id).filter_by(status="Oluşturuluyor").first()
        if not current_coupon:
            return False
        selected_odds = [i.bet_odd_fk for i in BetSelectedOption.query.filter_by(bet_coupon_fk=current_coupon.id)]
        return self.id in selected_odds


class TransactionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_amount = db.Column(db.Float)
    transaction_type = db.Column(db.String)
    transaction_status = db.Column(db.String, default="initiated")
    transaction_date = db.Column(db.Date)
    payment_channel = db.Column(db.String)
    user_fk = db.Column(db.Integer)
    payment_unique_number = db.Column(db.String)

    @property
    def user(self):
        return User.query.get(self.user_fk)


class WithdrawalRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    withdrawal_amount = db.Column(db.Float)
    status = db.Column(db.String, default="Beklemede")
    user_fk = db.Column(db.Integer)
    withdraw_to = db.Column(db.String)
    withdraw_type = db.Column(db.String)
    request_date = db.Column(db.DateTime)
    bank_id = db.Column(db.String)

    @property
    def user(self):
        return User.query.get(self.user_fk)

    @property
    def full_info(self):
        return UserInformation.query.filter_by(user_fk=self.user_fk).first().name + "/" + self.withdraw_to


class BankInformation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    iban = db.Column(db.String)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    user_fk = db.Column(db.String)


class Draft(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_fk = db.Column(db.String)
    draft_name = db.Column(db.String)
    competition_fk = db.Column(db.Integer)

    def give_prize_to_user(self):
        self.user.balance += self.competition.calculate_prize_by_point(self.total_points)
        db.session.commit()

    @property
    def user(self):
        return User.query.get(self.user_fk)

    @property
    def competition(self):
        return Competition.query.get(self.competition_fk)

    @property
    def chosen_athletes(self):
        return [i for i in DraftedAthlete.query.filter_by(draft_fk=self.id).all()]

    @property
    def total_points(self):
        return sum([i.current_points for i in DraftedAthlete.query.filter_by(draft_fk=self.id).all()])

    @property
    def draft_value(self):
        return sum([i.athlete.athlete_cost for i in DraftedAthlete.query.filter_by(draft_fk=self.id).all()])

    @property
    def current_rank(self):
        return self.competition.calculate_rank_by_point(self.total_points)

    @property
    def current_prize(self):
        return self.competition.calculate_prize_by_point(self.total_points)


class Competition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    competition_name = db.Column(db.String)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    entry_fee = db.Column(db.Float)
    competition_type = db.Column(db.String)
    allow_multiple_entries = db.Column(db.Boolean)

    # prize properties
    highest_prize = db.Column(db.Float)
    max_number_of_participants = db.Column(db.Integer)
    prize_winners = db.Column(db.Integer)
    prize_decrease_multiplier = db.Column(db.Integer)
    minimum_prize = db.Column(db.Float)
    manual_prize_override = db.Column(db.String)

    @property
    def participant_max(self):
        return self.max_number_of_participants if \
            self.max_number_of_participants > self.total_participants else "Yarışma Dolu"

    @property
    def available_athletes(self):
        matches_between_dates = Match.query.filter(self.start_date <= Match.date).filter(
            self.end_date >= Match.date).filter_by(match_league=self.competition_type).all()
        all_available_athletes = []
        if not self.end_date == self.start_date:
            if self.competition_type == "Süper Lig":
                for c in super_lig_teams:
                    for i in Athlete.query.filter_by(team_fk=Team.query.filter_by(team_name=c).first().id).all():
                        all_available_athletes.append(i)

            if self.competition_type == "Premier Lig":
                for c in premier_lig_teams:
                    for i in Athlete.query.filter_by(team_fk=Team.query.filter_by(team_name=c).first().id).all():
                        all_available_athletes.append(i)

            if self.competition_type == "LaLiga":
                for c in laliga_teams:
                    for i in Athlete.query.filter_by(team_fk=Team.query.filter_by(team_name=c).first().id).all():
                        all_available_athletes.append(i)

            if self.competition_type == "Bundesliga":
                for c in bundesliga_teams:
                    for i in Athlete.query.filter_by(team_fk=Team.query.filter_by(team_name=c).first().id).all():
                        all_available_athletes.append(i)

        for i in matches_between_dates:
            for c in Athlete.query.filter_by(team_fk=i.team1_fk).all():
                all_available_athletes.append(c)
            for c in Athlete.query.filter_by(team_fk=i.team2_fk).all():
                all_available_athletes.append(c)
        return set(all_available_athletes)

    @property
    def prize_pool(self):
        total_price = self.highest_prize
        temp_price = self.highest_prize

        manual_override = self.manual_prize_override
        prize_ranges = {}

        if manual_override is not None:
            total_price = 0
            for i in manual_override.split("/"):
                prize_ranges[i.split(":")[0]] = float(i.split(":")[-1])
            for i in prize_ranges.keys():
                try:
                    number_of_people_in_range = int(i.split("-")[-1]) - int(i.split("-")[0]) + 1
                except IndexError:
                    number_of_people_in_range = 1
                prize_in_range = number_of_people_in_range * int(prize_ranges.get(i))
                total_price += prize_in_range
            return total_price

        for i in range(self.prize_winners):
            temp_price = temp_price / self.prize_decrease_multiplier if temp_price / self.prize_decrease_multiplier > self.minimum_prize else self.minimum_prize
            total_price += temp_price

        return total_price

    @property
    def total_participants(self):
        return Draft.query.filter_by(competition_fk=self.id).count()

    @property
    def all_prizes(self):
        all_prizes = {}
        temp_price = self.highest_prize
        manual_override = self.manual_prize_override
        prize_ranges = {}

        if manual_override is not None:
            for i in manual_override.split("/"):
                prize_ranges[i.split(":")[0]] = float(i.split(":")[-1])

            return prize_ranges

        for i in range(self.prize_winners):
            if temp_price in all_prizes.values():
                all_prizes.pop(i)
                all_prizes[str(i) + "-" + str(self.prize_winners)] = self.minimum_prize
                return all_prizes
            all_prizes[i + 1] = temp_price
            temp_price = temp_price / self.prize_decrease_multiplier if temp_price / self.prize_decrease_multiplier > self.minimum_prize else self.minimum_prize

        return all_prizes

    def calculate_players_by_point(self, point):
        num_of_players_at_point = 0
        for c in Draft.query.filter_by(competition_fk=self.id):
            if sum([i.current_points for i in DraftedAthlete.query.filter_by(draft_fk=c.id).all()]) == point:
                num_of_players_at_point += 1
        return num_of_players_at_point

    def calculate_prize_by_point(self, point):
        drafts = Draft.query.filter_by(competition_fk=self.id).all()
        draft_ranking = []

        for draft in drafts:
            total_points = 0
            drafted_athletes = DraftedAthlete.query.filter_by(draft_fk=draft.id).all()

            for drafted_athlete in drafted_athletes:
                athlete_points = Points.query.filter_by(athlete_fk=drafted_athlete.athlete_fk).filter(
                    Points.point_date >= self.start_date).filter(Points.point_date <= self.end_date).all()
                if athlete_points:
                    for i in athlete_points:
                        total_points += i.points

            draft_ranking.append({'draft_id': draft.id, 'total_points': total_points})

        draft_ranking.sort(key=lambda x: x['total_points'], reverse=True)

        ranking = next((i + 1 for i, d in enumerate(draft_ranking) if d['total_points'] == point), None)
        if self.manual_prize_override is not None:
            for i in self.manual_prize_override.split("/"):
                prize_range = i.split(":")[0]
                try:
                    if int(prize_range.split("-")[1]) >= ranking >= int(prize_range.split("-")[0]):
                        return float(i.split(":")[-1]) / self.calculate_players_by_point(point)
                except IndexError:
                    if ranking == int(prize_range):
                        return float(i.split(":")[-1]) / self.calculate_players_by_point(point)

        ranking -= 1
        customer_price = self.highest_prize

        if ranking > self.prize_winners:
            return 0

        for i in range(ranking):
            customer_price = customer_price / self.prize_decrease_multiplier if customer_price / self.prize_decrease_multiplier > self.minimum_prize else self.minimum_prize

        final_prize = customer_price / self.calculate_players_by_point(point)

        return final_prize

    @property
    def drafts(self):
        return Draft.query.filter_by(competition_fk=self.id).all()

    def calculate_rank_by_point(self, point):
        drafts = Draft.query.filter_by(competition_fk=self.id).all()
        draft_ranking = []

        for draft in drafts:
            total_points = 0
            drafted_athletes = DraftedAthlete.query.filter_by(draft_fk=draft.id).all()

            for drafted_athlete in drafted_athletes:
                athlete_points = Points.query.filter_by(athlete_fk=drafted_athlete.athlete_fk).filter(
                    Points.point_date >= self.start_date).filter(Points.point_date <= self.end_date).all()
                if athlete_points:
                    for i in athlete_points:
                        total_points += i.points

            draft_ranking.append({'draft_id': draft.id, 'total_points': total_points})

        draft_ranking.sort(key=lambda x: x['total_points'], reverse=True)

        ranking = next((i + 1 for i, d in enumerate(draft_ranking) if d['total_points'] == point), None)

        return ranking


class Athlete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_name = db.Column(db.String)
    athlete_cost = db.Column(db.Float)
    athlete_position = db.Column(db.String)
    team_fk = db.Column(db.Integer)
    image_url = db.Column(db.String)

    def add_image(self, image_url):
        img_data = requests.get(image_url).content
        with open("static/" + self.athlete_name + ".png", 'wb') as handler:
            handler.write(img_data)
        self.image_url = "set"
        db.session.commit()

    @property
    def image_is_set(self):
        if self.image_url == "set":
            return "Evet"
        else:
            return "Hayır"

    @property
    def team_name(self):
        return Team.query.get(self.team_fk).team_name


class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date)
    team1_fk = db.Column(db.Integer)
    team2_fk = db.Column(db.Integer)
    match_league = db.Column(db.String)


class Points(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    points = db.Column(db.Integer)
    athlete_fk = db.Column(db.Integer)
    point_date = db.Column(db.Date)
    # How it works: Enter points for each athlete for every day. Use start and end dates of competitions to calculate
    # points per competition


class DraftedAthlete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    athlete_fk = db.Column(db.String)
    draft_fk = db.Column(db.String)

    @property
    def athlete(self):
        return Athlete.query.get(self.athlete_fk)

    @property
    def calculate_reward(self):
        related_draft = Draft.query.get(self.draft_fk)
        return related_draft.competition.calculate_prize_by_point(self.current_points)

    @property
    def current_points(self):
        current_competition = Draft.query.get(self.draft_fk).competition
        all_points = Points.query.filter_by(athlete_fk=self.athlete_fk). \
            filter(current_competition.start_date <= Points.point_date). \
            filter(current_competition.end_date >= Points.point_date).all()
        return sum([i.points for i in all_points])


@app.route("/admin_console", methods=["POST", "GET"])
def admin_console():
    if not current_user.is_admin:
        return flask.redirect("/")
    if flask.request.method == "POST":
        if flask.request.values["command"] == "help":
            return '''
                distribute-rewards
                <br>
                // Ödülleri günlük dağıt
                <br>

                add-image <oyuncu_adı> <görsel_url>
                <br>
                // Oyuncuya görsel ekle
                <br>

                add-referrer <öneri_kodu> <kullanıcı_emaili> <komisyon_oranı>
                <br>
                // Affiliate ekle
                <br>

                add-team <takım_adı> <görsel_url>
                <br>
                // Takım ekle
                <br>

                add-athlete <oyuncu_adı> <oyuncu_maliyeti> <takım_adı>
                <br>
                // Oyuncu ekle
                <br>

                add-match <maçın_bugünden_kaç_gün_sonra_olacağı> <takım_1> <takım_2> <maçın_ligi>
                <br>
                // Maç ekle
                <br>

                change-request-status <status_id> <new_status>
                <br>
                // Ödeme Statüsü Değiştir
                <br>

                add-points <puan_miktarı> <oyuncu_adı> <puanın_kaç_gün_önce_kazanıldığı>
                <br>
                // Puan ekle
                <br>

                remove-athlete <oyuncu_adı>
                <br>
                // Oyuncuyu sil
                <br>

                list-players
                <br>
                // Oyuncuların listesi
                <br>

                list-teams
                <br>
                // Takımların listesi 
            '''.replace("<", "[").replace(">", "]").replace("[br]", "<br>")
        elif "add-team" in flask.request.values["command"]:
            new_team = Team(team_name=flask.request.values["command"].split(" ")[1].replace("-", " "))
            db.session.add(new_team)
            db.session.commit()
            new_team.add_image(flask.request.values["command"].split(" ")[2])
        elif "add-image" in flask.request.values["command"]:
            Athlete.query.filter_by(
                athlete_name=flask.request.values["command"].split(" ")[1].replace("-", " ")).first().add_image(
                flask.request.values["command"].split(" ")[2])
            db.session.commit()
        elif "list-players" == flask.request.values["command"]:
            return str(
                "<br>".join(i.athlete_name + " / Görsel Eklendi: " + i.image_is_set for i in Athlete.query.all()))
        elif "list-teams" == flask.request.values["command"]:
            return str("<br>".join(i.team_name for i in Team.query.all()))
        else:
            os.system("python3 util.py " + flask.request.values["command"])

    withdrawal_requests = WithdrawalRequest.query.filter(WithdrawalRequest.status != "Tamamlandı"). \
        filter(WithdrawalRequest.status != "Reddedildi").all()
    return flask.render_template("admin_console.html", withdrawal_requests=reversed(withdrawal_requests))


@app.route("/create/session", methods=["POST"])
def create_iframe_session():
    if flask.request.values["api_key"] not in [i.api_key for i in CasinoPartner.query.all()]:
        return "Unauthorized"
    new_session = PartnerSession(id=str(uuid4()), balance=float(flask.request.values["balance"]),
                                 api_key=flask.request.values["api_key"])
    db.session.add(new_session)
    db.session.commit()

    return flask.jsonify({
        "status": "Session Created",
        "session_id": new_session.id
    })


@app.route("/howtoplay")
def how_to_play():
    data = flask.request.args.get("data", "generalTermsAndConditions")
    info_file = os.listdir(f"img/text/{data}")[0]
    data_dict = {
        "generalTermsAndConditions": "Genel Kural ve Şartlar",
        "contact": "Firma Bilgileri ve İletişim",
        "generalBonusConditions": "Bonus Kuralları ve Şartları"
    }
    with open(f"img/text/{data}/{info_file}") as f:
        info = f.read()
    return flask.render_template("sss1.html", current_user=current_user, info=info, data=data, title=data_dict.get(data))


@app.route("/logout")
def logout():
    logout_user()
    return flask.redirect("/")


@app.route("/profile", methods=["POST", "GET"])
def profile():
    if not current_user.is_authenticated:
        return flask.redirect("/")

    available_manual_accounts = PaymentSource.query.filter_by(is_active_payment_source=True).all()
    available_withdraw_methods = {}

    from finance_utils import deposit_types, get_available_banks_kralpay

    for key, item in deposit_types.items():
        available_withdraw_methods[item] = key

    bank_list = get_available_banks_kralpay()

    if flask.request.method == "POST":
        values = flask.request.values
        if flask.request.values["form-type"] == "deposit-money":
            new_transaction = TransactionLog(transaction_amount=float(values["amount"]),
                                             transaction_type="yatirim", transaction_date=datetime.date.today(),
                                             user_fk=current_user.id, transaction_status="Ödeme Bekliyor",
                                             payment_unique_number=str(shortuuid.ShortUUID().random(length=8)))
            db.session.add(new_transaction)
            db.session.commit()

            from finance_utils import get_iframe_vevopay, get_iframe_url_kralpay
            if "vevopay_" in flask.request.values.get("deposit_type"):
                start_deposit_url = get_iframe_vevopay(new_transaction, flask.request.values.get("deposit_type"))
            if "kralpay_" in flask.request.values.get("deposit_type"):
                start_deposit_url = get_iframe_url_kralpay(new_transaction, flask.request.values.get("deposit_type"),
                                                           flask.request.base_url,
                                                           flask.request.values.get("bank_id", None))

            return flask.redirect(start_deposit_url, code=302)

        if flask.request.values["form-type"] == "user-info":
            user_info = UserInformation.query.filter_by(user_fk=current_user.id).first()

            user_info.name = values["name"]
            user_info.address = values["address"]
            user_info.tel_no = values["tel_no"]
            user_info.tc_kimlik_no = values["id_no"]
            user_info.gender = values["gender"]
            user_info.date_of_birth = str(values["dob"])

            current_user.freebet += current_user.freebet_usable
            current_user.freebet_usable = 0

            from tc_dogrulama import verify_id
            if verify_id(int(values["id_no"]), " ".join(values["name"].split(" ")[0:-1]), values["name"].split(" ")[-1],
                         int(str(values["dob"]).split("-")[0])):
                user_info.id_verified = True
                db.session.commit()

            return flask.redirect("/profile")
        if flask.request.values["form-type"] == "withdraw-money":
            new_wr = WithdrawalRequest(
                withdraw_type="auto_" + flask.request.values.get("withdraw_type"),
                withdrawal_amount=float(flask.request.values["amount"]),
                user_fk=current_user.id,
                withdraw_to=flask.request.values["iban"],
                request_date=datetime.datetime.now()
            )
            db.session.add(new_wr)
            db.session.commit()

    return flask.render_template("profile.html", bank_banks=bank_list,
                                 available_withdraw_methods=available_withdraw_methods, current_user=current_user,
                                 withdrawal_requests=reversed(
                                     WithdrawalRequest.query.filter_by(user_fk=current_user.id).all()),
                                 available_manual_accounts=available_manual_accounts)


# TO DO: Implement bonuses in profile.


@app.route("/contact_m2", methods=["POST", "GET"])
def contact_m2():
    if flask.request.method == "POST":
        contact_m2_form = ContactM2(email=flask.request.values["email"], message=flask.request.values["message"])
        db.session.add(contact_m2_form)
        db.session.commit()
        return flask.render_template("provider/message_received.html")
    return flask.render_template("provider/contact_m2.html")


@app.route("/")
def index():
    from casino_utils import get_providers, get_games
    providers = []
    games_popular = [[], []]
    sliders_main = []
    sliders_sub = []

    for i in os.listdir("img/slider/slider-main"):
        sliders_main.append(f"/img/slider/slider-main/{i}")

    for i in os.listdir("img/slider/slider-sub"):
        sliders_sub.append(f"/img/slider/slider-sub/{i}")

    for c in get_providers():
        providers.append({
            "img_vertical": c.get("logo"),
            "name": c.get("name"),
            "id": c.get("id")
        })
    live_casino_games = [[], []]
    col_index = 0
    for c in get_games(provider_id="22").get("games"):
        try:
            games_popular[col_index].append({
                "img": c.get("img_vertical"),
                "name": c.get("name"),
                "provider_name": "-",
                "category": c.get("category"),
                "id": c.get("id")
            })

            if len(games_popular[col_index]) >= 8:
                col_index += 1
            if col_index == 2:
                break
        except AttributeError or KeyError:
            pass
    col_index = 0

    for c in get_games(provider_id="1").get("games"):
        try:
            live_casino_games[col_index].append({
                "img": c.get("img_vertical"),
                "name": c.get("name"),
                "provider_name": "-",
                "category": c.get("category"),
                "id": c.get("id")
            })

            if len(live_casino_games[col_index]) >= 8:
                col_index += 1
            if col_index == 2:
                break
        except AttributeError or KeyError:
            pass
    resp = flask.make_response(
        flask.render_template("anasayfa-yeni.html", current_user=current_user, providers=providers,
                              games_popular=games_popular, live_casino_games=live_casino_games,
                              sliders_main=sliders_main, sliders_sub=sliders_sub))
    if flask.request.args.get("ref", False):
        resp.set_cookie('referrer', flask.request.args.get("ref"))
    return resp


@app.route("/claim/bet/<bet_coupon_id>")
@login_required
def coupon_result(bet_coupon_id):
    from cloudbet import get_status_of_bet
    bet_coupon = BetCoupon.query.get(bet_coupon_id)
    if not bet_coupon.status == "Oluşturuldu":
        return flask.redirect("/profile")
    total_reward = bet_coupon.total_value
    for i in bet_coupon.all_selects:
        bet_status = get_status_of_bet(i.reference_id)
        if bet_status == "WIN":
            total_reward *= i.odd_locked_in_rate
        elif bet_status == "HALF_WIN":
            total_reward *= i.odd_locked_in_rate / 2
        elif bet_status == "HALF_LOSS":
            total_reward *= 0.5
        elif bet_status == "ACCEPTED" or bet_status == "PENDING_ACCEPTANCE":
            return flask.redirect("/profile")
        elif bet_status == "PARTIAL":
            total_reward = 0
        elif bet_status == "LOSS":
            total_reward = 0
        else:
            return flask.redirect("/profile")

    bet_coupon.status = f"Sonuçlandı | Kazanç: {total_reward}"
    new_transaction = TransactionLog(transaction_amount=float(total_reward),
                                     transaction_type="bet_win", transaction_date=datetime.date.today(),
                                     user_fk=current_user.id, transaction_status="Tamamlandı",
                                     payment_unique_number=f"Spor Bahisi Kazancı - Kupon {bet_coupon_id}")

    db.session.add(new_transaction)

    if current_user.referrer:
        if current_user.referrer.site_partner:
            if current_user.referrer.site_partner.partnership_balance < float(total_reward):
                current_user.referrer.site_partner.partnership_status = "Yetersiz Bakiye"
            else:
                current_user.referrer.site_partner.partnership_balance -= float(total_reward)

    current_user.balance += total_reward
    db.session.commit()
    return flask.redirect("/profile")


@app.route("/fantezi")
def fantezi():
    competitions = Competition.query.filter(
        Competition.start_date >= datetime.datetime.today().date() + datetime.timedelta(days=1))
    filter_q = flask.request.args.get("filter_q", False)
    if filter_q:
        if filter_q == "daily":
            competitions = competitions.filter(Competition.start_date == Competition.end_date)
        elif filter_q == "weekly":
            competitions = competitions.filter(Competition.start_date != Competition.end_date)
        elif filter_q == "high_limit":
            competitions = competitions.filter(Competition.entry_fee > 50)
        elif filter_q == "low_participants":
            competitions = competitions.filter(Competition.max_number_of_participants < 5001)
        elif filter_q == "single_participation":
            competitions = competitions.filter(not Competition.allow_multiple_entries)
        elif filter_q == "multiple_participation":
            competitions = competitions.filter(Competition.allow_multiple_entries)
        elif filter_q == "high_reward":
            competitions = competitions.filter(Competition.highest_prize > 50000)
        elif filter_q == "cheap_entry":
            competitions = competitions.filter(Competition.entry_fee < 20)
        elif filter_q == "seasonal":
            competitions = competitions.filter(Competition.start_date != Competition.end_date)
        else:
            competitions = competitions.filter(Competition.competition_type == filter_q.replace("-", " "))

    resp = flask.make_response(flask.render_template("index.html", current_user=current_user,
                                                     competitions=competitions.all()))
    if flask.request.args.get("ref", False):
        resp.set_cookie('referrer', flask.request.args.get("ref"))

    return resp


@app.route("/competition/<competition_id>")
def competition(competition_id):
    if Competition.query.get(competition_id).total_participants >= \
            Competition.query.get(competition_id).max_number_of_participants:
        return flask.redirect("/")

    if not current_user.is_authenticated:
        return flask.redirect("/login")
    return flask.render_template("competition.html", competition=Competition.query.get(competition_id))


@app.route("/refresh-balance")
@login_required
def refresh_balance():
    return "%.2f" % current_user.balance


@app.route("/deposit/bank", methods=["POST", "GET"])
def deposit_bank():
    if flask.request.method == "POST":
        values = flask.request.values
        if float(values["transaction_amount"]) < 100:
            return flask.redirect("/deposit/bank")
        new_transaction = TransactionLog(transaction_amount=float(values["transaction_amount"]),
                                         transaction_type="yatirim", transaction_date=datetime.date.today(),
                                         user_fk=current_user.id, transaction_status="Ödeme Bekliyor",
                                         payment_unique_number=flask.request.values["name"],
                                         payment_channel="Banka Yatırım Talebi")
        db.session.add(new_transaction)
        db.session.commit()
        get_first_active_method = PaymentSource.query.filter_by(payment_type="bank").filter_by(
            is_active_payment_source=True).first()
        return flask.render_template("bank_deposit.html", fullname=get_first_active_method.account_holder_name,
                                     iban=get_first_active_method.payment_number)
    return flask.render_template("bank_deposit_form.html")


# TO DO: completed backend for vivopay and kralpay, complete frontend for them. Example: lidyacasino.
@app.route("/deposit/papara", methods=["POST", "GET"])
def deposit_papara():
    if flask.request.method == "POST":
        values = flask.request.values
        if float(values["transaction_amount"]) < 100:
            return flask.redirect("/deposit/papara")
        new_transaction = TransactionLog(transaction_amount=float(values["transaction_amount"]),
                                         transaction_type="yatirim", transaction_date=datetime.date.today(),
                                         user_fk=current_user.id, transaction_status="Ödeme Bekliyor",
                                         payment_unique_number=str(shortuuid.ShortUUID().random(length=8)),
                                         payment_channel="Papara Yatırım Talebi")
        db.session.add(new_transaction)
        db.session.commit()
        get_first_active_method = PaymentSource.query.filter_by(payment_type="papara").filter_by(
            is_active_payment_source=True).first()

        return flask.render_template("papara_deposit.html", transaction=new_transaction,
                                     papara_no=get_first_active_method.payment_number,
                                     papara_name=get_first_active_method.account_holder_name)
    return flask.render_template("papara_deposit_form.html")


@app.route("/deposit/payfix", methods=["POST", "GET"])
def deposit_payfix():
    if flask.request.method == "POST":
        values = flask.request.values
        if float(values["transaction_amount"]) < 100:
            return flask.redirect("/deposit/payfix")
        new_transaction = TransactionLog(transaction_amount=float(values["transaction_amount"]),
                                         transaction_type="yatirim", transaction_date=datetime.date.today(),
                                         user_fk=current_user.id, transaction_status="Ödeme Bekliyor",
                                         payment_unique_number=str(shortuuid.ShortUUID().random(length=8)),
                                         payment_channel="Payfix Yatırım Talebi")
        db.session.add(new_transaction)
        db.session.commit()
        get_first_active_method = PaymentSource.query.filter_by(payment_type="payfix").filter_by(
            is_active_payment_source=True).first()

        return flask.render_template("papara_deposit.html", transaction=new_transaction,
                                     papara_no=get_first_active_method.payment_number,
                                     papara_name=get_first_active_method.account_holder_name)
    return flask.render_template("papara_deposit_form.html")


@app.route("/athlete/image/<a_id>")
def athlete_image(a_id):
    athlete = Athlete.query.get(a_id)
    if athlete.image_url:
        return flask.send_file("static/" + athlete.athlete_name + ".png" if os.path.exists(
            "static/" + athlete.athlete_name + ".png") else "/static/player.png")
    return flask.send_file("static/" + athlete.team_name + ".png")


@app.route("/draft/<competition_id>", methods=["POST", "GET"])
def draft(competition_id):
    if not current_user.is_authenticated:
        return flask.redirect("/")

    current_competition = Competition.query.get(competition_id)

    if not current_competition.start_date >= datetime.datetime.today().date() + datetime.timedelta(days=1):
        return "Unauthorized"

    if flask.request.method == "POST":
        if current_user.balance < current_competition.entry_fee:
            return '''
                <script>
                    alert('Yetersiz bakiye')
                    document.location = '/'
                </script>
            '''
        current_user.balance -= current_competition.entry_fee

        values = flask.request.values
        if len(Draft.query.filter_by(user_fk=current_user.id).filter_by(competition_fk=competition_id).all()) > 0 \
                and not current_competition.allow_multiple_entries:
            return '''
                <script>
                    alert('Bu yarışmaya birden fazla kez katılamazsınız.')
                </script>
            '''

        new_draft = Draft(user_fk=current_user.id, draft_name=current_competition.competition_name,
                          competition_fk=competition_id)
        db.session.add(new_draft)
        db.session.commit()

        drafted_athletes = []
        draft_id = new_draft.id

        for i in values.keys():
            if "athlete" in i:
                if values[i]:
                    new_draft = DraftedAthlete(athlete_fk=int(values[i]), draft_fk=draft_id)
                    drafted_athletes.append(new_draft)
                    db.session.add(new_draft)

        total_cost_of_draft = 0

        for i in drafted_athletes:
            total_cost_of_draft += i.athlete.athlete_cost

        if total_cost_of_draft > 50000:
            return "Hatalı Seçim"

        db.session.commit()
        return flask.render_template("completed_draft.html", competition_id=current_competition.id)

    return flask.render_template("draft.html", competition=current_competition,
                                 desktop=flask.request.args.get("desktop", False),
                                 mobile=flask.request.args.get("mobile", False))


@app.route("/static/<filename>")
def static_file(filename):
    if filename == "kadromilyon.png":
        if user_on_mobile():
            return flask.send_file("static/kadromilyon_mobile.png")
    return flask.send_file("static/" + filename)


@app.route("/admin", methods=["POST", "GET"])
def admin():
    if not current_user.is_admin:
        return ""
    return flask.render_template("admin.html")


@app.route("/forgot_password", methods=["POST", "GET"])
def forgot_password():
    query_user = User.query.filter_by(user_uuid=flask.request.args.get("reset_code", "no-uuid")).first()
    if query_user:
        if flask.request.method == "POST":
            query_user.password = bcrypt.generate_password_hash(flask.request.values.get("password"))
            db.session.commit()
            return flask.redirect("/login")
        return flask.render_template("new_password.html")
    else:
        if flask.request.method == "POST":
            email_user = User.query.filter_by(email=flask.request.values.get("email")).first()
            email_user.send_password_reset_email(flask.request.base_url)
            return flask.redirect("/login")
    return flask.render_template("forgot_password.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if flask.request.method == "POST":
        values = flask.request.values
        user_from_email = User.query.filter_by(email=values["email"]).first()
        if user_from_email:
            if bcrypt.check_password_hash(user_from_email.password, values["password"]):
                login_user(user_from_email, remember=False)
                user_from_email.last_login = datetime.datetime.now()
                db.session.commit()
                if flask.request.args.get("continue") == "admin":
                    return flask.redirect("/admin/home")
                return flask.redirect("/")
    return flask.render_template("login.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    from casino_utils import get_providers, get_games
    providers = []
    games_popular = [[], []]
    sliders_sub = []
    sliders_main = []

    for i in os.listdir("img/slider/slider-main"):
        sliders_main.append(f"/img/slider/slider-main/{i}")

    for i in os.listdir("img/slider/slider-sub"):
        sliders_sub.append(f"/img/slider/slider-sub/{i}")

    for c in get_providers():
        providers.append({
            "img_vertical": c.get("logo"),
            "name": c.get("name"),
            "id": c.get("id")
        })
    live_casino_games = [[], []]
    col_index = 0
    for c in get_games(provider_id="22").get("games"):
        try:
            games_popular[col_index].append({
                "img": c.get("img_vertical"),
                "name": c.get("name"),
                "provider_name": "-",
                "category": c.get("category"),
                "id": c.get("id")
            })

            if len(games_popular[col_index]) >= 8:
                col_index += 1
            if col_index == 2:
                break
        except AttributeError or KeyError:
            pass
    col_index = 0

    for c in get_games(provider_id="1").get("games"):
        try:
            live_casino_games[col_index].append({
                "img": c.get("img_vertical"),
                "name": c.get("name"),
                "provider_name": "-",
                "category": c.get("category"),
                "id": c.get("id")
            })

            if len(live_casino_games[col_index]) >= 8:
                col_index += 1
            if col_index == 2:
                break
        except AttributeError or KeyError:
            pass
    if flask.request.method == "POST":
        values = flask.request.values

        new_user = User(
            id=str(uuid4()),
            completed_first_deposit=False,
            casino_bonus_balance=0,
            sports_bonus_balance=0,
            username=values["username"],
            email=values["email"],
            password=bcrypt.generate_password_hash(values["password"]),
            referred_by=flask.request.cookies.get('referrer', None),
            freebet_usable=0,
            freebet=0,
            registration_date=datetime.datetime.now(),
            user_uuid=str(uuid4()),
            ip_address=flask.requests.environ["REMOTE_ADDR"] if not flask.request.environ.get(
                'HTTP_X_FORWARDED_FOR') else flask.request.environ.get('HTTP_X_FORWARDED_FOR')
        )
        db.session.add(new_user)
        db.session.commit()

        if values.get("promo_code"):
            promo_code = PromoCode.query.filter_by(code=values.get("promo_code")).first()
            promo_code = PromoCode.query.filter(PromoCode.code == values.get("promo_code"),
                                                promo_code.n_players_using_promo_code < promo_code.number_of_users).first()
            if promo_code:
                new_assigned_promo_code = AssignedPromoCode(
                    user_fk=new_user.id,
                    promo_code_fk=promo_code.id
                )
                new_bonus_assigned = BonusAssigned(user_fk=new_user.id,
                                                   bonus_fk=promo_code.bonus_fk,
                                                   status="Kullanılabilir",
                                                   bonus_assigned_date=datetime.datetime.today().date(),
                                                   bonus_amount=promo_code.bonus_amount)

                db.session.add(new_bonus_assigned)
                db.session.add(new_assigned_promo_code)

        new_user.user_information.tel_no = flask.request.values["tel_no"]
        db.session.commit()
        login_user(new_user)
        if app.config.get("DO_ROUTE_USERS"):
            data = {
                "user_uuid": new_user.user_uuid,
                "base_url": app.config.get("CASINO_BASE_URL")
            }
            requests.post("https://kadromilyon.com/save_user_to_m2router", data=data)
        return flask.redirect("/profile")
    return flask.render_template("signup.html", sliders_sub=sliders_sub, sliders_main=sliders_main,
                                 games_popular=games_popular, live_casino_games=live_casino_games)


@app.route("/save_user_to_m2router", methods=["POST", "GET"])
def save_user_to_m2router():
    if flask.request.method == "POST":
        new_m2_router = M2CallbackRouter(id=str(uuid4()), user_uuid=flask.request.values["user_uuid"],
                                         base_url=flask.request.values.get("base_url"))
        db.session.add(new_m2_router)
        db.session.commit()
        return "OK"
    return "Forbidden"


@app.route("/admin_portal", methods=["POST", "GET"])
def admin_portal():
    if not current_user.is_admin:
        return flask.redirect("/")

    if flask.request.method == "POST":
        values = flask.request.values
        new_competition = Competition(
            competition_name=values["competition_name"],
            start_date=datetime.datetime.strptime(values["start_date"], '%Y-%m-%d'),
            end_date=datetime.datetime.strptime(values["end_date"], '%Y-%m-%d'),
            entry_fee=float(values["entry_fee"]),
            competition_type=values["competition_type"],
            highest_prize=float(values["highest_prize"]),
            max_number_of_participants=int(values["max_number_of_participants"]),
            prize_winners=int(values["prize_winners"]),
            prize_decrease_multiplier=float(values["prize_decrease_multiplier"]),
            minimum_prize=float(values["minimum_prize"]),
            allow_multiple_entries=bool(values.get("allow_multiple_entries", False))
        )
        db.session.add(new_competition)
        db.session.commit()
        return flask.redirect("/")
    return flask.render_template("admin.html")


@app.route("/loading")
def loading_page():
    return flask.render_template("loading_page.html", route_to=flask.request.args.get("continue"))


@app.route("/bahis")
def bahis():
    loaded = flask.request.args.get("loaded", None)
    if not loaded:
        return flask.redirect("/loading?continue=/bahis?loaded=true")
    offset = int(flask.request.args.get("offset", 0))
    sport = flask.request.args.get("sport", None)
    league = flask.request.args.get("league", None)
    search_q = flask.request.args.get("search_q", None)
    if search_q:
        open_bets = OpenBet.query.filter(OpenBet.bet_ending_datetime > datetime.datetime.now(),
                                         or_(OpenBet.team_1.like('%' + search_q + '%'),
                                             OpenBet.team_2.like('%' + search_q + '%'))).filter_by(
            has_odds=True)
    else:

        open_bets = OpenBet.query.filter(OpenBet.bet_ending_datetime > datetime.datetime.now()).filter_by(
            has_odds=True)

    sports_and_leagues = {}

    for i in open_bets:
        if i.sport not in sports_and_leagues.keys():
            sports_and_leagues[i.sport] = []
        if i.match_league not in sports_and_leagues[i.sport]:
            sports_and_leagues[i.sport].append(i.match_league)

    if sport:
        open_bets = open_bets.filter_by(sport=sport)
    if league:
        open_bets = open_bets.filter_by(match_league=league)

    open_bets = open_bets.all()

    number_of_chunks = range(int(len(open_bets) / 50) + 1)

    return flask.render_template("bahis/bahis-yeni.html", open_bets=open_bets[offset * 50:(offset + 1) * 50],
                                 canli_bahis=False,
                                 number_of_chunks=number_of_chunks, offset=offset,
                                 sports_and_leagues=sports_and_leagues)


@app.route("/canli_bahis")
def canli_bahis():
    loaded = flask.request.args.get("loaded", None)
    if not loaded:
        return flask.redirect("/loading?continue=/canli_bahis?loaded=true")
    offset = int(flask.request.args.get("offset", 0))
    sport = flask.request.args.get("sport", None)
    league = flask.request.args.get("league", None)
    search_q = flask.request.args.get("search_q", None)
    if search_q:
        open_bets = OpenBet.query.filter(OpenBet.bet_ending_datetime <= datetime.datetime.now(),
                                         or_(OpenBet.team_1.like('%' + search_q + '%'),
                                             OpenBet.team_2.like('%' + search_q + '%'))).filter_by(
            live_betting_expired=False).filter_by(has_odds=True)
    else:
        open_bets = OpenBet.query.filter(OpenBet.bet_ending_datetime <= datetime.datetime.now()).filter_by(
            live_betting_expired=False).filter_by(has_odds=True)
    sports_and_leagues = {}

    for i in open_bets:
        if i.sport not in sports_and_leagues.keys():
            sports_and_leagues[i.sport] = []
        if i.match_league not in sports_and_leagues[i.sport]:
            sports_and_leagues[i.sport].append(i.match_league)

    if sport:
        open_bets = open_bets.filter_by(sport=sport)
    if league:
        open_bets = open_bets.filter_by(match_league=league)

    open_bets = open_bets.all()

    number_of_chunks = range(int(len(open_bets) / 50) + 1)

    return flask.render_template("bahis/bahis-yeni.html", open_bets=open_bets[offset * 50:(offset + 1) * 50],
                                 canli_bahis=True,
                                 number_of_chunks=number_of_chunks, offset=offset,
                                 sports_and_leagues=sports_and_leagues)


@app.route("/canli_bahis_mobile")
def canli_bahis_mobile():
    open_bets = OpenBet.query.filter(OpenBet.bet_ending_datetime <= datetime.datetime.now()).filter_by(
        live_betting_expired=False).filter_by(has_odds=True).all()
    sports_leagues = []
    for i in open_bets:
        if i.match_league not in sports_leagues:
            sports_leagues.append(i.match_league)
    return flask.render_template("bahis/bahis-mobile.html", open_bets=open_bets, canli_bahis=True,
                                 sports_leagues=sports_leagues)


@app.route("/bahis/mac/<bahis_id>")
def bahis_mac(bahis_id):
    open_bet = OpenBet.query.get(bahis_id)
    from_frame = flask.request.args.get("iframe", False) == "True"
    return flask.render_template("bahis/bahis_detay_yeni.html", open_bet=open_bet, from_frame=from_frame)


@app.route("/take_bet/<odd_id>")
def take_bet(odd_id):
    if not current_user.is_authenticated:
        return flask.redirect("/login")
    bet_odd = BetOdd.query.get(odd_id)
    from_frame = flask.request.args.get("iframe", False) == "True"
    if not bet_odd.bettable:
        return '''
            <script>
                alert('Bahis kapandı')
                document.location = '/bahis/mac/{bet_odd.bet_option.open_bet_fk}'
            </script>
        '''
    current_coupon = BetCoupon.query.filter_by(user_fk=current_user.id).filter_by(status="Oluşturuluyor").first()
    if not current_coupon:
        current_coupon = BetCoupon(user_fk=current_user.id, status="Oluşturuluyor", total_value=0)
        db.session.add(current_coupon)
        db.session.commit()
    if BetSelectedOption.query.filter_by(bet_odd_fk=odd_id).filter_by(bet_coupon_fk=current_coupon.id).first():
        return flask.redirect("/bahis")
    new_coupon_bet = BetSelectedOption(bet_coupon_fk=current_coupon.id, bet_odd_fk=odd_id,
                                       bet_option_fk=bet_odd.bet_option_fk, reference_id=str(uuid4()),
                                       match_name=bet_odd.bet_option.match_name)

    if len(BetSelectedOption.query.filter_by(bet_coupon_fk=current_coupon.id).filter_by(
            match_name=bet_odd.bet_option.match_name).all()) > 0:
        return f'''
            <script>
                alert('Aynı maçta iki farklı seçenek kupona eklenemez.')
                document.location = '/bahis/mac/{bet_odd.bet_option.open_bet_fk}?iframe={from_frame}'
            </script>
        '''

    db.session.add(new_coupon_bet)
    db.session.commit()
    option_fk = BetOdd.query.get(odd_id).bet_option_fk
    option = BetOption.query.get(option_fk)
    return flask.redirect(f"/bahis/mac/{option.open_bet_fk}?added_new=True&iframe={from_frame}")


@app.route("/remove_bet/<odd_id>")
def remove_bet(odd_id):
    current_coupon = BetCoupon.query.filter_by(user_fk=current_user.id).filter_by(status="Oluşturuluyor").first()
    db.session.delete(
        BetSelectedOption.query.filter_by(bet_odd_fk=odd_id).filter_by(bet_coupon_fk=current_coupon.id).first())
    db.session.commit()
    option_fk = BetOdd.query.get(odd_id).bet_option_fk
    option = BetOption.query.get(option_fk)

    from_frame = flask.request.args.get("iframe", False) == "True"

    if flask.request.args.get("coupon", None):
        return flask.redirect("/coupon")
    return flask.redirect(f"/bahis/mac/{option.open_bet_fk}?iframe={from_frame}")


@app.route("/coupon/removeAll")
def remove_all():
    current_coupon = BetCoupon.query.filter_by(user_fk=current_user.id).filter_by(status="Oluşturuluyor").first()
    for i in current_coupon.all_selects:
        db.session.delete(i)
    db.session.commit()
    return flask.redirect("/coupon")


@app.route("/coupon", methods=["POST", "GET"])
def coupon():
    if not current_user.is_authenticated:
        return flask.redirect("/login")
    if current_user.get_bonuses("sport-betting", "freebet") is not None:
        current_user.freebet = current_user.get_bonuses("sport-betting", "freebet").bonus_amount
        current_user.get_bonuses("sport-betting", "freebet").status = "Kullanıldı"

    current_coupon = BetCoupon.query.filter_by(user_fk=current_user.id).filter_by(status="Oluşturuluyor").first()
    if not current_coupon:
        current_coupon = BetCoupon(user_fk=current_user.id, status="Oluşturuluyor", total_value=0)
        db.session.add(current_coupon)
        db.session.commit()
    changed_odds = []
    for i in BetSelectedOption.query.filter_by(bet_coupon_fk=current_coupon.id):
        if not i.odd or not i.odd.bet_option:
            db.session.delete(i)
            db.session.commit()
            continue
        i.match_name = i.odd.bet_option.match_name
        i.game_name = i.odd.bet_option.game_name
        if i.odd.bettable:
            from cloudbet import cloudbet_instant_odd_update
            prev_val = i.odd.odd
            cloudbet_instant_odd_update(i.odd)
            if not i.odd.odd == prev_val:
                changed_odds.append(i.odd.id)
            i.odd_locked_in_rate = i.odd.odd
        if not i.odd.bettable:
            db.session.delete(i)
            db.session.commit()
            return flask.redirect("/coupon")
    if flask.request.method == "POST":
        sports_bonus_balance = current_user.sports_bonus_balance

        net_change = float(flask.request.values["coupon_value"]) - sports_bonus_balance

        current_user.sports_bonus_balance -= float(flask.request.values["coupon_value"])
        if current_user.sports_bonus_balance < 0:
            current_user.sports_bonus_balance = 0

        if net_change < 0:
            net_change = 0

        new_transaction = TransactionLog(transaction_amount=float(flask.request.values["coupon_value"]),
                                         transaction_type="place_bet", transaction_date=datetime.date.today(),
                                         user_fk=current_user.id, transaction_status="Tamamlandı",
                                         payment_unique_number=f"Spor Bahisi - Kupon {current_coupon.id} - {str(' | '.join([c.odd.bet_option.open_bet_obj.match_league for c in current_coupon.all_selects]))} - {str(' | '.join([c.odd.bet_option.open_bet_obj.sport for c in current_coupon.all_selects]))}")

        db.session.add(new_transaction)

        if current_user.freebet:
            if current_user.balance + current_user.freebet < float(net_change):
                return '''
                    <script>
                        alert('Yetersiz bakiye')
                        document.location = '/coupon'
                    </script>
                '''
        else:
            if current_user.balance < net_change or float(flask.request.values["coupon_value"]) < 10:
                return '''
                    <script>
                        alert('Yetersiz bakiye veya geçersiz miktar')
                        document.location = '/coupon'
                    </script>
                '''

        current_coupon.status = "Oluşturuldu"
        current_coupon.total_value = float(flask.request.values["coupon_value"])

        from cloudbet import place_bet
        for i in current_coupon.all_selects:
            if not place_bet(i.odd, i.reference_id):
                raise ValueError

        if current_user.freebet:
            freebet_amount = current_user.freebet if current_user.freebet <= float(
                flask.request.values["coupon_value"]) else float(flask.request.values["coupon_value"])
            current_user.balance -= (net_change - freebet_amount)
            current_coupon.freebet_amount = freebet_amount
            current_user.freebet -= freebet_amount
        else:
            current_user.balance -= net_change
            current_coupon.freebet_amount = 0

        if current_user.referrer:
            if current_user.referrer.site_partner and current_user.referrer.site_partner.partnership_status == "Aktif":
                current_user.referrer.site_partner.partnership_earnings += float(current_coupon.total_value)

        db.session.commit()
        return flask.redirect("/coupon")
    return flask.render_template("bahis/coupon-new.html", current_coupon=current_coupon, current_user=current_user,
                                 changed_odds=changed_odds, odds_did_change=len(changed_odds) > 0)


@app.route("/double")
@login_required
def double_or_nothing():
    return flask.render_template("double_or_nothing.html")


@app.route("/create_double_or_nothing", methods=["POST", "GET"])
@login_required
def create_double_or_nothing():
    if flask.request.method == "POST":
        new_game = DoubleOrNothing(id=str(uuid4()), current_offer=float(flask.request.values["bet_amount"]))
        if current_user.balance >= new_game.current_offer:
            current_user.balance -= new_game.current_offer
            db.session.add(new_game)
        else:
            return "Inadequate Balance"
        db.session.commit()
        return new_game.id


@app.route("/double_double_or_nothing", methods=["POST", "GET"])
@login_required
def double_double_or_nothing():
    if flask.request.method == "POST":
        current_dn_game = DoubleOrNothing.query.get(flask.request.values["game_id"])
        if random.randint(0, 100) > 52:
            current_dn_game.current_offer *= 2
            db.session.commit()
            return "Double"
        else:
            db.session.delete(current_dn_game)
            db.session.commit()
            return "Nothing"


@app.route("/game/<game_title>")
@login_required
def play_game(game_title):
    return flask.render_template("game.html", game_title=str.capitalize(game_title.replace("_", " ").replace("-", " ")),
                                 game_description=games_and_descriptions.get(game_title), game_url=game_title)


@app.route("/win_double_or_nothing/<game_id>")
@login_required
def win_double_or_nothing(game_id):
    current_game = DoubleOrNothing.query.get(game_id)
    current_user.balance += current_game.current_offer
    db.session.commit()
    return flask.render_template("win_double_or_nothing.html", winnings=current_game.current_offer)


@app.route("/lose_double_or_nothing")
def lose_double_or_nothing():
    return flask.render_template("lose_double_or_nothing.html")


@app.route("/limbo")
@login_required
def limbo():
    return flask.render_template("limbo.html")


@app.route("/limbo_guess_multiplier", methods=["POST", "GET"])
@login_required
def limbo_guess_multiplier():
    if flask.request.method == "POST":
        values = flask.request.values
        if current_user.balance < float(values["bet_amount"]):
            return "Inadequate Balance"
        options = generate_limbo_options()

        multiplier_choice = random.choice(options)

        if float(values["multiplier"]) <= multiplier_choice:

            current_user.balance -= float(values["bet_amount"])
            current_user.balance += float(values["bet_amount"]) * float(values["multiplier"])
        else:
            current_user.balance -= float(values["bet_amount"])

        current_user.received_first_time_bonus = True

        db.session.commit()

        return str(multiplier_choice)


def generate_limbo_options():
    options = []
    for i in range(100, 5000):
        for c in range(int(((100 / i) ** 2) * 100)):
            options.append(i / 100)

    return options


@app.route("/success", methods=["POST", "GET"])
def success_pay_giga():
    print("values")
    print(flask.request.values)
    r = requests.post("https://test.paygiga.com/api/deposit/confirm-status", data={
        {"merchantKey": "UgK3u/eHN6X8UrhwJRSIUT51rLrcJymTK6oHjwvYBlo=",
         "merchantPassword": "d_yTqtIfhn]g7V5A[v==Vp", "id": 45687,
         "transactionId": "954546"}
    })
    return "OK"


@app.route("/fail", methods=["POST"])
def fail_pay_giga():
    print("Fail PayGiga")
    return "OK"


@app.route("/license")
def license_curucao():
    return flask.render_template("license.html", generated_on=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@app.route("/provider-assets/<file_name>")
def provider_assets(file_name):
    return flask.send_file("provider-assets/" + file_name)


@app.route("/provider")
def kmultimate():
    return flask.render_template("provider/index.html")


@app.before_request
def reroute_page():
    if "m2betting" in flask.request.headers['Host']:
        if "provider" not in flask.request.path and "static" not in flask.request.path:
            return flask.redirect("/provider")


@app.route("/casino")
def casino():
    from casino_utils import get_games, get_providers
    games = []
    games_popular = []
    provider_id = flask.request.args.get("provider_id", False)
    provider_name = flask.request.args.get("provider_name", False)
    search_query = flask.request.args.get("search_query")
    providers = []

    if provider_id or search_query:
        if search_query:
            for c in get_games().get("games"):
                if search_query.lower() in c.get("name").lower():
                    games.append({
                        "img_vertical": c.get("img_vertical"),
                        "name": c.get("name"),
                        "provider_name": "-",
                        "category": c.get("category"),
                        "id": c.get("id")
                    })
                    provider_id = "-"
        else:
            for c in get_providers():
                providers.append({
                    "img_vertical": c.get("logo"),
                    "name": c.get("name"),
                    "id": c.get("id")
                })
            for c in get_games(provider_id).get("games"):
                try:
                    games.append({
                        "img_vertical": c.get("img_vertical"),
                        "name": c.get("name"),
                        "provider_name": provider_name,
                        "category": c.get("category"),
                        "id": c.get("id")
                    })
                except AttributeError or KeyError:
                    pass

    else:
        for c in get_providers():
            providers.append({
                "img_vertical": c.get("logo"),
                "name": c.get("name"),
                "id": c.get("id")
            })
        for c in get_games(provider_id="22").get("games"):
            try:
                games_popular.append({
                    "img_vertical": c.get("img_vertical"),
                    "name": c.get("name"),
                    "provider_name": "-",
                    "category": c.get("category"),
                    "id": c.get("id")
                })
                if len(games_popular) > 200:
                    break
            except AttributeError or KeyError:
                pass

    return flask.render_template("casino.html", current_user=current_user, providers=providers, games=games,
                                 provider_id=provider_id,
                                 games_popular=games_popular)


@app.route("/casino/<game_id>")
def casino_game(game_id):
    freespin_bonus = current_user.get_bonuses("casino", "freespin")
    if freespin_bonus:
        current_user.get_bonuses("casino", "freespin").status = "Kullanıldı"
    from casino_utils import get_game_iframe

    return flask.render_template("casino-game.html",
                                 game_iframe=get_game_iframe(game_id, current_user.id, current_user.user_uuid,
                                                             demo="false", bonus=freespin_bonus))


@app.errorhandler(500)
def error_500(e):
    return flask.render_template("iserror.html")


@app.route("/admin/games")
def admin_panel_providers():
    if not current_user.user_has_permission("providers"):
        return flask.redirect("/admin/home")
    from casino_utils import get_providers, get_games
    providers = []
    for c in get_providers():
        providers.append({
            "img_vertical": c.get("logo"),
            "name": c.get("name"),
            "id": c.get("id")
        })
    return flask.render_template("panel/providers.html", providers=providers)


@app.route("/admin/user_details", methods=["POST", "GET"])
def admin_panel_user_profile():
    if not current_user.user_has_permission("players"):
        return flask.redirect("/admin/home")
    available_bonuses = Bonus.query.filter(Bonus.start_date <= datetime.datetime.today().date(),
                                           Bonus.end_date >= datetime.datetime.today().date()).all()

    user = User.query.get(flask.request.args.get("user_id"))
    number_of_users_with_same_ip = len(User.query.filter_by(ip_address=user.ip_address).all())
    transactions = TransactionLog.query.filter_by(user_fk=user.id).all()
    bonus_requests = BonusAssigned.query.filter_by(user_fk=user.id).all()
    withdrawal_requests = WithdrawalRequest.query.filter_by(user_fk=user.id).all()
    coupons = BetCoupon.query.filter_by(user_fk=user.id).all()

    if flask.request.method == "POST":
        if flask.request.values.get("notes", None):
            user.notes = flask.request.values.get("notes")
            db.session.commit()
        elif flask.request.values.get("balance", None):
            user.balance = float(flask.request.values.get("balance", None))
            db.session.commit()
        elif flask.request.values.get("bonus_id"):
            new_bonus_assigned = BonusAssigned(user_fk=user.id, bonus_fk=flask.request.values.get("bonus_id"),
                                               status="Talep Edildi")
            db.session.add(new_bonus_assigned)
            db.session.commit()
            return flask.redirect(f"/admin/user_details?user_id={user.id}")

    return flask.render_template("panel/user_details.html", user=user, transactions=transactions,
                                 bonus_requests=bonus_requests, withdrawal_requests=withdrawal_requests,
                                 coupons=coupons, available_bonuses=available_bonuses,
                                 number_of_users_with_same_ip=number_of_users_with_same_ip)


# TO DO: Affiliate panel and promo code creating. Bonus based on promo code.


@app.route("/admin/partnership", methods=["POST", "GET"])
def admin_panel_partnership():
    if not current_user.user_has_permission("partnerships"):
        return flask.redirect("/admin/home")
    partner = User.query.get(flask.request.args["user_id"])

    if flask.request.method == "POST":
        new_site_partner = SitePartner(
            commission_rate=int(flask.request.values.get("commission_rate")),
            partnership_earnings=0,
            partnership_balance=0,
            id=str(uuid4()),
            partnership_status="Aktif"
        )

        new_referrer = Referrer(
            user_fk=partner.id,
            id=str(uuid4()),
            commission_rate=0
        )
        partner.site_partner_fk = new_site_partner.id

        db.session.add(new_referrer)
        db.session.add(new_site_partner)
        db.session.commit()

        return flask.redirect("/admin/players")

    return flask.render_template("panel/partnership.html", partner=partner)


@app.route("/admin/partnership/balance", methods=["POST", "GET"])
def admin_panel_partnership_operations():
    if not current_user.user_has_permission("partnerships"):
        return flask.redirect("/admin/home")
    partnership = SitePartner.query.get(flask.request.args["partnership_id"])
    if flask.request.method == "POST":
        partnership.partnership_balance += float(flask.request.values["balance_increase"])
        partnership.partnership_status = "Aktif"
        db.session.commit()
        return flask.redirect("/admin/players")
    return flask.render_template("panel/partnership_balance.html", partnership=partnership)


@app.route("/admin/cms", methods=["POST", "GET"])
def admin_panel_cms():
    if not current_user.user_has_permission("cms"):
        return flask.redirect("/admin/home")
    css_dict = []
    with open("css/cms-styles.css", 'r') as file:
        for line in file:
            if ':' in line and ';' in line:
                key, value = line.strip().replace(';', '').split(':', 1)
                key = key.strip().replace('--', '')
                value = value.strip()
                css_dict.append((key, value))
    from admin_utils import list_directory_contents_recursive

    images = list_directory_contents_recursive("img")

    if flask.request.method == "POST":
        if flask.request.values.get("form-type") == "image-update":
            file = flask.request.files.get("image-to-update")
            file.save(flask.request.values.get("file-select"))
        if flask.request.values["form-type"] == "remove-slider":
            os.system(f'rm -f {flask.request.values.get("file-select")}')
        if flask.request.values["form-type"] == "add-slider":
            file = flask.request.files.get("image-to-upload")
            file.save(f'img/slider/{flask.request.values.get("file-select")}/{str(uuid4())}.png')
        if flask.request.values["form-type"] == "update-theme":
            css_dict = {}
            for i in flask.request.values.keys():
                if not i == "form-type" and not i == "option":
                    css_dict[i] = flask.request.values.get(i)
            with open("css/cms-styles.css", 'w') as file:
                file.write(":root {\n")
                for key, value in css_dict.items():
                    file.write(f"    --{key}: {value};\n")
                file.write("}\n")

        return flask.redirect("/admin/cms")

    return flask.render_template("panel/cms.html", css_dict=css_dict, images=images,
                                 option=flask.request.args.get("option"))


@app.route("/admin/update/withdraw")
def update_withdraw():
    if not current_user.user_has_permission("transactions"):
        return flask.redirect("/admin/home")

    withdraw_request = WithdrawalRequest.query.get(flask.request.args.get("withdraw_request_id"))

    if flask.request.args.get("update_to") == "Tamamlandı":
        if "auto_" in withdraw_request.withdraw_type:
            from finance_utils import withdraw_vevopay, withdraw_kralpay
            # Complete implementations for withdrawals
            if "vevopay" in withdraw_request.withdraw_type:
                withdraw_vevopay(withdraw_request)
            if "kralpay" in withdraw_request.withdraw_type:
                withdraw_kralpay(withdraw_request)
            else:
                withdraw_request.user.balance -= withdraw_request.withdrawal_amount
                db.session.commit()

    withdraw_request.status = flask.request.args.get("update_to")
    db.session.commit()

    return flask.redirect("/admin/home")


@app.route("/admin/home")
def admin_panel():
    try:
        if not current_user.user_has_permission("general"):
            return flask.redirect("/")
    except:
        return flask.redirect("/login?continue=admin")
    import admin_utils
    day_difference = int(flask.request.args.get("days", 1))

    start_date = datetime.datetime.today() - datetime.timedelta(days=day_difference)
    end_date = datetime.datetime.today() - datetime.timedelta(days=1)

    total_deposits, total_deposits_percentage_change = admin_utils.calculate_transaction_volume_for_date(
        start_date,
        end_date,
        day_difference
    )
    total_balance, total_balance_percentage_change = admin_utils.calculate_total_balance(), "-"
    logged_in_users, logged_in_users_percentage_change = admin_utils.logged_in_users(
        start_date,
        end_date,
        day_difference
    )
    total_users, total_users_percentage_change = admin_utils.total_users(
        start_date,
        end_date
    )
    total_withdrawals, total_withdrawals_percentage_change = admin_utils.total_withdrawals(
        start_date,
        end_date,
        day_difference
    )
    ggr, ggr_percentage_change = admin_utils.calculate_ggr(
        start_date,
        end_date,
        day_difference
    )
    total_bet, total_bet_percentage_change = admin_utils.total_bet(
        start_date,
        end_date,
        day_difference
    )
    withdrawal_requests = WithdrawalRequest.query.filter(WithdrawalRequest.status != "Tamamlandı"). \
        filter(WithdrawalRequest.status != "Reddedildi").all()
    deposit_requests = TransactionLog.query.filter(TransactionLog.transaction_status == "Ödeme Bekliyor",
                                                   TransactionLog.transaction_type == "yatirim").all()
    number_of_requests = len(withdrawal_requests)

    return flask.render_template(
        "panel/admin.html",
        deposit_requests=deposit_requests,
        withdrawal_requests=withdrawal_requests,
        number_of_requests=number_of_requests,
        total_deposits=total_deposits,
        total_deposits_percentage_change=total_deposits_percentage_change,
        total_balance=total_balance,
        total_balance_percentage_change=total_balance_percentage_change,
        logged_in_users=logged_in_users,
        logged_in_users_percentage_change=logged_in_users_percentage_change,
        total_users=total_users,
        total_users_percentage_change=total_users_percentage_change,
        total_withdrawals=total_withdrawals,
        total_withdrawals_percentage_change=total_withdrawals_percentage_change,
        ggr=ggr,
        new_signups=len(User.query.filter(User.registration_date.between(start_date, end_date)).all()),
        ggr_percentage_change=ggr_percentage_change,
        total_bet=total_bet,
        total_bet_percentage_change=total_bet_percentage_change
    )


# TO DO: Withdrawals with finance.


@app.route("/admin/complete_deposit")
def complete_deposit():
    if not current_user.user_has_permission("transactions"):
        return flask.redirect("/admin/home")
    transaction = TransactionLog.query.get(flask.request.args.get("transaction_id"))
    transaction.transaction_status = "Tamamlandı"
    User.query.get(transaction.user_fk).balance += transaction.transaction_amount
    User.query.get(transaction.user_fk).update_bonus_balance(transaction.transaction_amount)
    db.session.commit()
    return flask.redirect("/admin/home")



@app.route("/admin/cancel_deposit")
def cancel_deposit():
    if not current_user.user_has_permission("transactions"):
        return flask.redirect("/admin/home")
    transaction = TransactionLog.query.get(flask.request.args.get("transaction_id"))
    db.session.delete(transaction)
    db.session.commit()
    return flask.redirect("/admin/home")


@app.route("/admin/games/<provider_id>/<provider_name>")
def admin_panel_provider_details(provider_id, provider_name):
    if not current_user.user_has_permission("providers"):
        return flask.redirect("/admin/home")
    from casino_utils import get_providers, get_games
    from urllib.parse import unquote
    games = []
    for c in get_games(provider_id).get("games"):
        games.append({
            "img_vertical": c.get("img_vertical"),
            "name": c.get("name"),
            "provider_name": provider_name,
            "category": c.get("category"),
            "id": c.get("id"),
            "game_rtp": c.get("basicRTP"),
            "provider_id": provider_id
        })
    return flask.render_template("panel/games.html", games=games, provider_name=unquote(provider_name))


@app.route("/admin/game/<provider_id>/<game_id>")
def admin_panel_game_details(provider_id, game_id):
    if not current_user.user_has_permission("providers"):
        return flask.redirect("/admin/home")
    from casino_utils import get_games
    for c in get_games(provider_id).get("games"):
        if str(game_id) == str(c.get("id")):
            game = {
                "img_vertical": c.get("img_vertical"),
                "name": c.get("name"),
                "category": c.get("category"),
                "id": c.get("id"),
                "game_rtp": c.get("basicRTP")
            }
            return flask.render_template("panel/game.html", game=game)

    return "Game Doesn't Exist"


@app.route("/admin/promo_codes", methods=["POST", "GET"])
def admin_panel_promo_codes():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    bonuses = Bonus.query.all()
    promo_codes = PromoCode.query.all()
    if flask.request.method == "POST":
        values = flask.request.values
        new_promo_code = PromoCode(
            bonus_fk=values.get("bonus"),
            name=values.get("promo_code_name"),
            code=values.get("promo_code"),
            bonus_amount=values.get("bonus_amount"),
            number_of_users=values.get("max_number_of_users")
        )
        db.session.add(new_promo_code)
        db.session.commit()
        return flask.redirect("/admin/promo_codes")
    return flask.render_template("panel/promo_code.html", bonuses=bonuses,
                                 promo_codes=promo_codes)


@app.route("/admin/bonuses/remove")
def admin_panel_remove_bonus():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    db.session.delete(Bonus.query.get(flask.request.args.get("bonus_id")))
    db.session.commit()
    return flask.redirect("/admin/bonuses")


@app.route("/admin/promo_codes/remove")
def admin_panel_remove_promo_code():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    db.session.delete(PromoCode.query.get(flask.request.args.get("code_id")))
    db.session.commit()
    return flask.redirect("/admin/promo_codes")


@app.route("/admin/bonuses", methods=["POST", "GET"])
def admin_panel_bonuses():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    bonuses = Bonus.query.all()
    number_of_bonuses = len(bonuses)
    if flask.request.method == "POST":
        values = flask.request.values
        new_bonus = Bonus(
            bonus_product=values.get("bonus_product"),
            bonus_type=values.get("bonus_type"),
            bonus_name=values.get("bonus_name"),
            minimum_bonus_amount=values.get("minimum_bonus_amount"),
            maximum_bonus_amount=values.get("maximum_bonus_amount"),
            who_can_cancel=values.get("who_can_cancel"),
            on_cancel=values.get("on_cancel"),
            currency=values.get("currency"),
            minimum_deposit=values.get("minimum_deposit", 0),
            maximum_deposit=values.get("maximum_deposit", 999999999),
            minimum_spin=values.get("minimum_spin", 0),
            start_date=datetime.datetime.strptime(values["start_date"], '%Y-%m-%d'),
            end_date=datetime.datetime.strptime(values["end_date"], '%Y-%m-%d'),
            valid_thru=values.get("valid_thru"),
            bonus_description=values.get("bonus_description"),
            round_value=int(values.get("round_value", 0))
        )
        db.session.add(new_bonus)
        db.session.commit()

        file = flask.request.files.get("bonus_image")
        file.save(f"img/{str(new_bonus.id)}.png")
    return flask.render_template("panel/bonus.html", bonuses=bonuses, number_of_bonuses=number_of_bonuses,
                                 form_type=flask.request.args.get("bonus_type", None),
                                 product_type=flask.request.args.get("product_type", None))


@app.route("/admin/bonus_requests", methods=["POST", "GET"])
def admin_panel_bonus_request():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    bonus_requests = BonusAssigned.query.filter_by(status="Talep Edildi").all()
    return flask.render_template("panel/bonus_request.html", bonus_requests=bonus_requests,
                                 number_of_requests=len(bonus_requests))


@app.route("/admin/accept_bonus_request", methods=["POST", "GET"])
def admin_panel_accept_bonus_request():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    subject_bonus_request = BonusAssigned.query.get(flask.request.args["bonus_id"])
    if flask.request.method == "POST":
        subject_bonus_request.status = "Kullanılabilir"
        subject_bonus_request.bonus_assigned_date = datetime.datetime.today().date()
        subject_bonus_request.bonus_amount = float(flask.request.values["bonus_amount"])
        if subject_bonus_request.bonus.bonus_type in ["kayip-bonusu", "deneme-bonusu"]:
            if subject_bonus_request.bonus.bonus_product == "casino":
                subject_bonus_request.user.casino_bonus_balance += subject_bonus_request.bonus_amount
            elif subject_bonus_request.bonus.bonus_product == "sport-betting":
                subject_bonus_request.user.sports_bonus_balance += subject_bonus_request.bonus_amount
        db.session.commit()
        return flask.redirect("/admin/bonus_requests")
    return flask.render_template("panel/accept_bonus_request.html", bonus_request=subject_bonus_request)


@app.route("/admin/decline_bonus_request")
def admin_panel_decline_bonus_request():
    if not current_user.user_has_permission("bonuses"):
        return flask.redirect("/admin/home")
    subject_bonus_request = BonusAssigned.query.get(flask.request.args["bonus_id"])
    subject_bonus_request.status = "Reddedildi"
    db.session.commit()
    return flask.redirect("/admin/bonus_requests")


@app.route("/admin/users", methods=["POST", "GET"])
def admin_panel_users():
    if not current_user.user_has_permission("add_users"):
        return flask.redirect("/admin/home")
    if flask.request.method == "POST":
        user_permission = flask.request.values.get("user_permission")
        if user_permission == "new-class":
            permissions_list = []
            for i in flask.request.values:
                if "permissions_" in i:
                    permissions_list.append(i.replace("permissions_", ""))
            new_user_permission = UserPermissions(
                permission_name=flask.request.values.get("permission_name"),
                permissions_list="&&".join(permissions_list)
            )
            db.session.add(new_user_permission)
            db.session.commit()
        else:
            new_user_permission = UserPermissions.query.get(flask.request.values.get("user_permission"))
        new_user = User(
            id=str(uuid4()),
            email=flask.request.values.get("username"),
            password=bcrypt.generate_password_hash(flask.request.values.get("password")),
            is_admin=True,
            balance=0,
            casino_bonus_balance=0,
            sports_bonus_balance=0
        )
        db.session.add(new_user)
        db.session.commit()

        new_user_assigned_permission = UserAssignedPermission(
            user_fk=new_user.id,
            permission_fk=new_user_permission.id
        )
        db.session.add(new_user_assigned_permission)
        db.session.commit()

        return flask.redirect("/admin/users")

    return flask.render_template("panel/users.html", admin_users=User.query.filter_by(is_admin=True).all(),
                                 permissions=UserPermissions.query.all())


@app.route("/admin/remove_user")
def remove_admin_user():
    if not current_user.user_has_permission("add_users"):
        return flask.redirect("/admin/home")
    db.session.delete(User.query.get(flask.request.args.get("user_id")))
    db.session.commit()
    return flask.redirect("/admin/users")


@app.route("/admin/finance")
def admin_panel_finance():
    if not current_user.user_has_permission("transactions"):
        return flask.redirect("/admin/home")
    transaction_types = ["casino_win", "casino_bet", "yatirim", "çekim", "place_bet", "bet_win", "casino_all"]
    transaction_statuses = ["Tamamlandı", "Ödeme Bekliyor", "Reddedildi", "Oluşturuluyor", "Oluşturuldu",
                            "Talep Edildi", "Aktif"]
    transactions = TransactionLog.query

    if flask.request.args.get("user_id", None):
        transactions = transactions.filter(TransactionLog.user_fk == flask.request.args.get("user_id", None))
    if flask.request.args.get("transaction_status", None):
        transactions = transactions.filter(
            TransactionLog.transaction_status == flask.request.args.get("transaction_status", None))
    if flask.request.args.get("amount_gte", None):
        transactions = transactions.filter(
            TransactionLog.transaction_amount >= flask.request.args.get("amount_gte", None))
    if flask.request.args.get("amount_lte", None):
        transactions = transactions.filter(
            TransactionLog.transaction_amount <= flask.request.args.get("amount_lte", None))
    if flask.request.args.get("date_before", None):
        transactions = transactions.filter(
            TransactionLog.transaction_date <= datetime.datetime.strptime(flask.request.args.get("date_before", None),
                                                                          '%Y-%m-%d'))
    if flask.request.args.get("date_after", None):
        transactions = transactions.filter(
            TransactionLog.transaction_date >= datetime.datetime.strptime(flask.request.args.get("date_after", None),
                                                                          '%Y-%m-%d'))
    if flask.request.args.get("transaction_type", None):
        if flask.request.args.get("transaction_type", None) == "casino_all":
            transactions = transactions.filter(
                TransactionLog.transaction_type.in_(["casino_bet", "casino_win"]))
        else:
            transactions = transactions.filter(
                TransactionLog.transaction_type == flask.request.args.get("transaction_type", None))

    transactions = transactions.all()
    number_of_transactions = len(transactions)
    total_amount = sum([i.transaction_amount for i in transactions])
    return flask.render_template("panel/finance.html", transactions=transactions, total_amount=total_amount,
                                 number_of_transactions=number_of_transactions, transaction_types=transaction_types,
                                 transaction_statuses=transaction_statuses)


@app.route("/admin/payments/deactivate")
def admin_panel_finance_payment_method_deactivate():
    if not current_user.user_has_permission("deposit_methods"):
        return flask.redirect("/admin/home")
    PaymentSource.query.get(flask.request.args.get("payment_method")).is_active_payment_source = False
    db.session.commit()
    return flask.redirect("/admin/deposit-methods")


@app.route("/admin/payments/activate")
def admin_panel_finance_payment_method_activate():
    if not current_user.user_has_permission("deposit_methods"):
        return flask.redirect("/admin/home")
    PaymentSource.query.get(flask.request.args.get("payment_method")).is_active_payment_source = True
    db.session.commit()
    return flask.redirect("/admin/deposit-methods")


@app.route("/admin/deposit-methods", methods=["POST", "GET"])
def admin_panel_finance_deposit_methods():
    if not current_user.user_has_permission("deposit_methods"):
        return flask.redirect("/admin/home")
    manual_payment_sources = PaymentSource.query.all()
    if flask.request.method == "POST":
        new_payment_source = PaymentSource(
            is_active_payment_source=True,
            payment_type=flask.request.values.get("payment_type"),
            payment_number=flask.request.values.get("payment_number"),
            account_holder_name=flask.request.values.get("account_holder_name")
        )
        db.session.add(new_payment_source)
        db.session.commit()
        return flask.redirect("/admin/deposit-methods")
    return flask.render_template("panel/deposit-methods.html", manual_payment_sources=manual_payment_sources)


@app.route("/admin/players")
def admin_panel_players():
    if not current_user.user_has_permission("players"):
        return flask.redirect("/admin/home")
    users = User.query
    if flask.request.args.get("user_ip", None):
        users = users.filter(User.ip_address == flask.request.args.get("user_ip", None))
    users = users.all()
    if flask.request.args.get("promo_code", None):
        users = PromoCode.query.get(flask.request.args.get("promo_code", None)).players_using_promo_code
    number_of_users = len(users)
    return flask.render_template("panel/players.html", users=users, number_of_users=number_of_users)


@app.route("/admin/remove_user")
def remove_user():
    if not current_user.user_has_permission("players"):
        return flask.redirect("/admin/home")
    db.session.delete(User.query.get(flask.request.args["user_id"]))
    db.session.commit()
    return flask.redirect("/admin/players")


@app.route("/css/<filename>")
def css_host(filename):
    return flask.send_file(f"css/{filename}")


@app.route("/js/<filename>")
def js_host(filename):
    return flask.send_file(f"js/{filename}")


@app.route("/fonts/<filename>")
def fonts_host(filename):
    return flask.send_file(f"fonts/{filename}")


@app.route("/plugins/owl/<filename>")
def plugin_host(filename):
    return flask.send_file(f"plugins/owl/{filename}")


@app.route("/plugins/perfect-scrollbar/<filename>")
def plugin_perfect_scrollbar(filename):
    return flask.send_file(f"plugins/perfect-scrollbar/{filename}")


@app.route("/img/<directory>/<filename>")
def img_host_1(directory, filename):
    return flask.send_file(f"img/{directory}/{filename}")


@app.route("/img/<directory>/<directory_2>/<filename>")
def img_host_2(directory, directory_2, filename):
    return flask.send_file(f"img/{directory}/{directory_2}/{filename}")


@app.route("/img/<filename>")
def img_host_3(filename):
    return flask.send_file(f"img/{filename}")


@app.route("/casino-callback/playerDetails")
def casino_player_details():
    m2_callback_router = M2CallbackRouter.query.filter_by(user_uuid=flask.request.args.get("token")).first()
    if m2_callback_router:
        if not m2_callback_router.base_url == app.config.get("CASINO_BASE_URL"):
            return requests.get(m2_callback_router.base_url + "playerDetails", params=flask.request.args).json()
    subject_user = User.query.get(flask.request.args.get("userId"))
    if not subject_user.user_uuid == flask.request.args.get("token"):
        return {
            "status": False,
            "errors": {
                "error": "Authorization Error"
            }
        }
    return flask.jsonify({
        "status": True,
        "userId": subject_user.id,
        "nickname": subject_user.username if subject_user.username else "player",
        "currency": "TRY",
        "language": "tr",
    })


@app.route("/casino-callback//getBalance")
def casino_get_balance():
    m2_callback_router = M2CallbackRouter.query.filter_by(user_uuid=flask.request.args.get("token")).first()
    if m2_callback_router:
        if not m2_callback_router.base_url == app.config.get("CASINO_BASE_URL"):
            return requests.get(m2_callback_router.base_url + "getBalance", params=flask.request.args).json()

    subject_user = User.query.get(flask.request.args.get("userId"))
    if not subject_user.user_uuid == flask.request.args.get("token"):
        return {
            "status": False,
            "errors": {
                "error": "Authorization Error"
            }
        }
    return flask.jsonify({
        "status": True,
        "balance": round(subject_user.balance, 2)
    })


@app.route("/casino-callback/moveFunds", methods=["POST", "GET"])
def casino_result_bet():
    m2_callback_router = M2CallbackRouter.query.filter_by(user_uuid=flask.request.values.get("token")).first()
    if m2_callback_router:
        if not m2_callback_router.base_url == app.config.get("CASINO_BASE_URL"):
            return requests.post(m2_callback_router.base_url + "moveFunds", data=flask.request.values).json()

    subject_user = User.query.get(flask.request.values.get("userId"))
    casino_bonus_balance = subject_user.casino_bonus_balance

    net_change = float(flask.request.values.get("amount")) - casino_bonus_balance

    subject_user.casino_bonus_balance -= float(flask.request.values.get("amount"))
    if subject_user.casino_bonus_balance < 0:
        subject_user.casino_bonus_balance = 0

    if net_change < 0:
        net_change = 0

    if not subject_user.user_uuid == flask.request.values.get("token"):
        return {
            "status": False,
            "errors": {
                "error": "Authorization Error"
            }
        }
    game_info = ""
    provider_id = 0
    from casino_utils import get_games, get_providers

    for c in get_games().get("games"):
        if int(flask.request.values.get('gameId')) == int(c.get("id")):
            game_info = f"{c.get('type')} | {c.get('name')}"
            provider_id = c.get("providerId")

    for c in get_providers():
        if int(c.get("id")) == provider_id:
            provider_id = c.get("name")

    game_info += f" | {provider_id}"

    if flask.request.values.get("eventType") == "Win":
        new_transaction = TransactionLog(transaction_amount=float(flask.request.values.get("amount")),
                                         transaction_type="casino_win", transaction_date=datetime.date.today(),
                                         user_fk=subject_user.id, transaction_status="Tamamlandı",
                                         payment_unique_number=f"Casino Kazancı - Oyun ID: {flask.request.values.get('gameId')} - {game_info}")
        db.session.add(new_transaction)

        subject_user.balance += float(flask.request.values.get("amount"))

        if subject_user.referrer:
            if subject_user.referrer.site_partner:
                if subject_user.referrer.site_partner.partnership_balance < float(flask.request.values.get("amount")):
                    subject_user.referrer.site_partner.partnership_status = "Yetersiz Bakiye"
                    db.session.commit()
                else:
                    subject_user.referrer.site_partner.partnership_balance -= float(flask.request.values.get("amount"))
    if flask.request.values.get("eventType") == "BetPlacing":
        new_transaction = TransactionLog(transaction_amount=float(flask.request.values.get("amount")),
                                         transaction_type="casino_bet", transaction_date=datetime.date.today(),
                                         user_fk=subject_user.id, transaction_status="Tamamlandı",
                                         payment_unique_number=f"Casino Bahisi - Oyun ID: {flask.request.values.get('gameId')} - {game_info}")
        db.session.add(new_transaction)
        subject_user.balance -= net_change

        if subject_user.referrer:
            if subject_user.referrer.site_partner and subject_user.referrer.site_partner.partnership_status == "Aktif":
                subject_user.referrer.site_partner.partnership_earnings += float(net_change)

    db.session.commit()
    return flask.jsonify({
        "status": True,
        "balance": round(subject_user.balance, 2)
    })


@app.route("/promotions")
def promotions():
    bonuses = Bonus.query.filter(Bonus.start_date <= datetime.datetime.today().date(),
                                 Bonus.end_date >= datetime.datetime.today().date()).all()
    return flask.render_template("promotions.html", bonuses=bonuses, current_user=current_user)


@app.route("/promotion")
def promotion():
    bonus = Bonus.query.get(flask.request.args.get("promotion_id"))
    bonus.bonus_description = bonus.bonus_description.replace("\n", "<br>")
    return flask.render_template("promotion-details.html", bonus=bonus, current_user=current_user)


@app.route("/bonus_request")
def bonus_request():
    new_bonus_request = BonusAssigned.query.filter_by(user_fk=current_user.id).filter_by(
        bonus_fk=flask.request.args.get("promotion_id")).filter_by(status="Talep Edildi").first()
    if new_bonus_request:
        return '''
            <script>
                alert('Bu bonusu zaten talep ettiniz.')
                document.location = '/promotions'
            </script>
        '''

    new_bonus_assigned = BonusAssigned(user_fk=current_user.id, bonus_fk=flask.request.args.get("promotion_id"),
                                       status="Talep Edildi")
    db.session.add(new_bonus_assigned)
    db.session.commit()
    return flask.redirect("/promotions")


@app.route("/transaction_callback", methods=["POST", "GET"])
def transaction_callback_vevopay():
    if flask.request.method == "POST":

        values = flask.request.values
        transaction = TransactionLog.query.get(int(values.get("referans", None)))

        subject_user = User.query.get(int(values.get("kullanici_id")))

        if values.get("islem", None) == "yatirimsonuc":
            if values.get("durum", None) == "onay":
                subject_user.balance += transaction.transaction_amount
                subject_user.update_bonus_balance(float(values.get("amount")))

        if values.get("Process", None) == "WithdrawalReturn":
            withdrawal_request = WithdrawalRequest.query.get(values.get("Reference", None))
            subject_user.balance -= transaction.transaction_amount
            withdrawal_request.status = "Tamamlandı"

        if transaction:
            transaction.transaction_status = "Tamamlandı"
        db.session.commit()

        return flask.jsonify({
            "status": True
        })
    return "OK"


@app.route("/api/kralpy/", methods=["POST", "GET"])
def transaction_callback_kralpay():
    if flask.request.method == "POST":

        values = flask.request.values
        if values.get("service") == "info":
            if User.query.get(values.get("user_id")):
                return flask.jsonify({
                    {
                        "code": 200,
                        "message": "Müşteri yatırım gerçekleştirebilir!"
                    }
                })
        if values.get("service") == "deposit" and values.get("status", None) == "S":
            transaction = TransactionLog.query.get(values.get("trx"))
            transaction.transaction_status = "Tamamlandı"
            subject_user = transaction.user
            subject_user.balance += float(values.get("amount"))
            subject_user.update_bonus_balance(float(values.get("amount")))
            db.session.commit()
            return flask.jsonify({
                "code": 200,
                "message": "Müşteri hesabına bakiye eklendi!"
            }
            )

        if values.get("service") == "withdraw" and values.get("status", None) == "C":
            withdrawal_request = WithdrawalRequest.query.get(values.get("trx"))
            subject_user = withdrawal_request.user
            withdrawal_request.status = "Tamamlandı"
            subject_user.balance -= float(values.get("amount"))
            db.session.commit()
            return flask.jsonify({
                "code": 200,
                "message": "Müşteri hesabına bakiye eklendi!"
            }
            )
        return flask.jsonify({
            "code": 999,
            "message": "Bir hata ile karşılaştık."
        })
    return flask.jsonify({
        "code": 999,
        "message": "Bir hata ile karşılaştık."
    })


@app.route("/transaction_return")
def transaction_return():
    return flask.render_template("payment_form_submit.html")

# TO DO: Add bonus taleplerim page to profile also implement trying and loss bonuses
# TO DO: Check casino integration (also with router)
