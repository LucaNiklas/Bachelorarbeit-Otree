from otree.api import *
import random, json
from time import time

doc = """Blackjack (1 Spieler vs. Dealer), 10 Runden."""


PIP_LAYOUT = {
    'A': [(50, 50)],
    '2': [(50, 23), (50, 77)],
    '3': [(50, 22), (50, 50), (50, 78)],
    '4': [(32, 25), (68, 25), (32, 75), (68, 75)],
    '5': [(32, 25), (68, 25), (50, 50), (32, 75), (68, 75)],
    '6': [(32, 25), (68, 25), (32, 50), (68, 50), (32, 75), (68, 75)],
    '7': [(32, 25), (68, 25), (32, 50), (68, 50), (32, 75), (68, 75), (50, 35)],
    '8': [(32, 25), (68, 25), (32, 50), (68, 50), (32, 75), (68, 75), (50, 35), (50, 65)],
    '9': [(32, 25), (68, 25), (32, 50), (68, 50), (32, 75), (68, 75), (50, 35), (50, 65), (50, 50)],
    '10': [(32, 20), (68, 20), (32, 38), (68, 38), (32, 56), (68, 56), (32, 74), (68, 74), (50, 30), (50, 66)],
}


def card_to_meta(card, hidden=False):
    suits_red = {'♥', '♦'}
    if hidden or not card:
        return dict(rank='', suit='', is_red=False, hidden=True, pips=[], face_label='', is_ace=False)
    suit = card[-1]
    rank = card[:-1]
    pips = PIP_LAYOUT.get(rank, [])
    face_label = rank if rank in {'J', 'Q', 'K'} else ''
    if not pips and rank == 'A':
        pips = PIP_LAYOUT['A']
    return dict(
        rank=rank,
        suit=suit,
        is_red=(suit in suits_red),
        hidden=False,
        pips=[dict(x=x, y=y) for x, y in pips],
        face_label=face_label,
        is_ace=(rank == 'A'),
    )


def outcome_to_code(outcome_text):
    text = (outcome_text or '').strip().lower()
    mapping = {
        'you won (blackjack)': 'blackjack',
        'you won': 'win',
        'you lost': 'lose',
        'push': 'push',
    }
    if text in mapping:
        return mapping[text]
    if 'blackjack' in text and 'won' in text:
        return 'blackjack'
    if 'won' in text:
        return 'win'
    if 'lost' in text:
        return 'lose'
    if 'push' in text:
        return 'push'
    return ''

class Constants(BaseConstants):
    name_in_url = 'blackjack_game'
    players_per_group = None
    num_rounds = 10
    DEALER_STAND_ON = 17
    START_BALANCE = cu(100)
    NUM_DECKS = 6

class Group(BaseGroup): 
    pass

class Player(BasePlayer):
    balance = models.CurrencyField(initial=Constants.START_BALANCE)
    bet_size = models.CurrencyField(min=1, initial=1)
    outcome = models.StringField(choices=['win','lose','push','blackjack'], blank=True)
    decision = models.LongStringField(blank=True)
    deviation_from_optimal = models.BooleanField(initial=False)

    deck_json = models.LongStringField()
    player_hand_json = models.LongStringField()
    dealer_hand_json = models.LongStringField()
    player_stood = models.BooleanField(initial=False)
    player_busted = models.BooleanField(initial=False)
    dealer_done = models.BooleanField(initial=False)
    has_hit = models.BooleanField(initial=False)
    decision_response_time = models.FloatField(initial=0)
    final_player_cards_json = models.LongStringField(blank=True)
    final_dealer_cards_json = models.LongStringField(blank=True)
    final_player_ranks_csv = models.LongStringField(blank=True)
    final_dealer_ranks_csv = models.LongStringField(blank=True)
    bankroll_after_round = models.CurrencyField(blank=True)

    def summary_round(self):
        return self.participant.vars.get('summary_round', Constants.num_rounds)

    # ---------- Hilfsfunktionen ----------
    def current_balance(self):
        return self.balance

    def _new_deck(self):
        ranks = ['A'] + [str(n) for n in range(2, 11)] + ['J','Q','K']
        suits = ['♠','♥','♦','♣']
        single_deck = [f'{r}{s}' for r in ranks for s in suits]
        shoe = single_deck * Constants.NUM_DECKS
        random.shuffle(shoe)
        return shoe

    def _load(self, field): return json.loads(getattr(self, field))
    def _save(self, field, value): setattr(self, field, json.dumps(value))

    def _get_shoe(self):
        stored = self.participant.vars.get('blackjack_shoe')
        return list(stored) if stored else []

    def _store_shoe(self, deck):
        self.participant.vars['blackjack_shoe'] = list(deck)

    def _load_deck_state(self):
        return self._load('deck_json')

    def _save_deck_state(self, deck):
        self._save('deck_json', deck)
        self._store_shoe(deck)

    @staticmethod
    def _card_value(rank):
        if rank in ['J','Q','K']: return 10
        if rank == 'A': return 11
        return int(rank)

    @classmethod
    def hand_total_and_soft(cls, hand):
        total = 0
        aces = 0
        for card in hand:
            rank = card[:-1]
            if rank == 'A':
                total += 11
                aces += 1
            elif rank in ['J', 'Q', 'K']:
                total += 10
            else:
                total += int(rank)
        soft = False
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        if aces > 0:
            soft = True
        return total, soft

    @staticmethod
    def format_currency(value):
        try:
            numeric = float(value)
        except Exception:
            return str(value)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.2f}"

    @staticmethod
    def format_currency(value):
        try:
            numeric = float(value)
        except Exception:
            return str(value)
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.2f}"

    @classmethod
    def hand_value(cls, hand):
        ranks = [c[:-1] for c in hand]
        total, aces = 0, 0
        for r in ranks:
            v = cls._card_value(r)
            total += v
            if r == 'A': aces += 1
        while total > 21 and aces > 0:
            total -= 10; aces -= 1
        return total

    @staticmethod
    def is_blackjack(hand):
        if len(hand) != 2: return False
        ranks = [c[:-1] for c in hand]
        return 'A' in ranks and any(r in ['10','J','Q','K'] for r in ranks if r != 'A')

    def optimal_actions(self, hand, dealer_upcard, can_double):
        if not hand or not dealer_upcard:
            return {'stand'}
        total, is_soft = self.hand_total_and_soft(hand)
        dealer_rank = dealer_upcard[:-1]
        if dealer_rank in {'J', 'Q', 'K'}:
            dealer_rank = '10'

        def can(action):
            if action != 'double':
                return {action}
            return {'double'} if can_double else {'hit'}

        if total >= 21:
            return {'stand'}

        if is_soft:
            if total >= 20:
                return {'stand'}
            if total == 19:
                return {'stand'}
            if total == 18:
                if dealer_rank in {'2', '7', '8'}:
                    return {'stand'}
                if dealer_rank in {'3', '4', '5', '6'}:
                    return can('double') if can_double else {'stand'}
                return {'hit'}
            if total == 17:
                if dealer_rank in {'3', '4', '5', '6'}:
                    return can('double')
                return {'hit'}
            if total == 16:
                if dealer_rank in {'4', '5', '6'}:
                    return can('double')
                return {'hit'}
            if total == 15:
                if dealer_rank in {'4', '5', '6'}:
                    return can('double')
                return {'hit'}
            if total == 14:
                if dealer_rank in {'5', '6'}:
                    return can('double')
                return {'hit'}
            if total == 13:
                if dealer_rank in {'5', '6'}:
                    return can('double')
                return {'hit'}
            return {'hit'}

        # hard totals
        if total >= 17:
            return {'stand'}
        if total == 16:
            return {'stand'} if dealer_rank in {'2', '3', '4', '5', '6'} else {'hit'}
        if total == 15:
            return {'stand'} if dealer_rank in {'2', '3', '4', '5', '6'} else {'hit'}
        if total == 14:
            return {'stand'} if dealer_rank in {'2', '3', '4', '5', '6'} else {'hit'}
        if total == 13:
            return {'stand'} if dealer_rank in {'2', '3', '4', '5', '6'} else {'hit'}
        if total == 12:
            return {'stand'} if dealer_rank in {'4', '5', '6'} else {'hit'}
        if total == 11:
            if dealer_rank == 'A':
                return {'hit'}
            return can('double')
        if total == 10:
            if dealer_rank in {'2', '3', '4', '5', '6', '7', '8', '9'}:
                return can('double')
            return {'hit'}
        if total == 9:
            if dealer_rank in {'3', '4', '5', '6'}:
                return can('double')
            return {'hit'}
        return {'hit'}

    def action_is_optimal(self, action_key, hand, dealer_upcard, can_double):
        return action_key in self.optimal_actions(hand, dealer_upcard, can_double)

    def action_is_optimal(self, action_key, hand, dealer_upcard, can_double):
        return action_key in self.optimal_actions(hand, dealer_upcard, can_double)

    # ---------- Spiel-Logik ----------
    def start_round(self):
        deck = self._get_shoe()
        if len(deck) < 15:
            deck = self._new_deck()
        player = [deck.pop(), deck.pop()]
        dealer = [deck.pop(), deck.pop()]
        self._save_deck_state(deck)
        self._save('player_hand_json', player)
        self._save('dealer_hand_json', dealer)
        self.player_stood = False
        self.player_busted = False
        self.dealer_done = False
        self.has_hit = False
        self.outcome = ''
        self.decision = ''
        self.deviation_from_optimal = False
        self.deviation_from_optimal = False
        self.payoff = cu(0)
        self.decision_response_time = 0
        self.final_player_cards_json = ''
        self.final_dealer_cards_json = ''
        self.final_player_ranks_csv = ''
        self.final_dealer_ranks_csv = ''
        self.bankroll_after_round = self.balance
        self.participant.vars.pop(f'decision_start_{self.round_number}', None)

        # Einsatz vom Guthaben abziehen (kommt vom Slider)
        self.balance -= self.bet_size

        if self.is_blackjack(player) or self.is_blackjack(dealer):
            self.dealer_done = True
            self._settle()

    def player_hit(self):
        deck = self._load_deck_state()
        player = self._load('player_hand_json')
        player.append(deck.pop())
        self._save_deck_state(deck)
        self._save('player_hand_json', player)
        self.has_hit = True
        value = self.hand_value(player)
        if value > 21:
            self.player_busted = True
            self.player_stood = True
            self.dealer_done = True
            self._settle()
            return
        if value == 21:
            self.player_stood = True
            self.dealer_play()
            self._settle()

    def player_stand(self): self.player_stood = True

    def player_double(self):
        if self.has_hit:
            return
        if self.balance >= self.bet_size:
            self.balance -= self.bet_size
            self.bet_size *= 2
            self.player_hit()
            self.player_stood = True

    def dealer_play(self):
        if self.player_busted:
            self.dealer_done = True; return
        deck = self._load_deck_state()
        dealer = self._load('dealer_hand_json')
        while self.hand_value(dealer) < Constants.DEALER_STAND_ON:
            dealer.append(deck.pop())
        self._save_deck_state(deck)
        self._save('dealer_hand_json', dealer)
        self.dealer_done = True

    def _settle(self):
        player = self._load('player_hand_json')
        dealer = self._load('dealer_hand_json')
        pv, dv = self.hand_value(player), self.hand_value(dealer)
        self.dealer_done = True
        self.final_player_cards_json = json.dumps(player)
        self.final_dealer_cards_json = json.dumps(dealer)
        self.final_player_ranks_csv = ', '.join(c[:-1] for c in player)
        self.final_dealer_ranks_csv = ', '.join(c[:-1] for c in dealer)

        if self.is_blackjack(player) and not self.is_blackjack(dealer):
            self.outcome = 'You won (Blackjack)'; self.payoff = self.bet_size * 2.5
            self.balance += self.payoff
            self.bankroll_after_round = self.balance
            return
        if self.is_blackjack(dealer) and not self.is_blackjack(player):
            self.outcome = 'You lost'; self.payoff = cu(0)
            self.bankroll_after_round = self.balance
            return
        if self.player_busted:
            self.outcome = 'You lost'; self.payoff = cu(0)
            self.bankroll_after_round = self.balance
            return
        if dv > 21 or pv > dv:
            self.outcome = 'You won'; self.payoff = self.bet_size * 2
            self.balance += self.payoff
            self.bankroll_after_round = self.balance
            return
        if pv < dv:
            self.outcome = 'You lost'; self.payoff = cu(0)
            self.bankroll_after_round = self.balance
            return
        self.outcome = 'Push'; self.payoff = self.bet_size
        self.balance += self.payoff
        self.bankroll_after_round = self.balance

class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            for p in self.get_players():
                p.participant.vars.pop('summary_round', None)
                p.balance = Constants.START_BALANCE
                p.participant.vars['blackjack_shoe'] = p._new_deck()

# -------------------- Seiten --------------------

class Intro(Page):
    @staticmethod
    def is_displayed(player: Player): return player.round_number == 1
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            balance_display=Player.format_currency(player.balance),
        )

class BetPage(Page):
    form_model = 'player'
    form_fields = ['bet_size']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number <= player.summary_round() and player.balance > 0

    @staticmethod
    def vars_for_template(player: Player):
        if player.round_number > 1:
            previous_round = player.in_round(player.round_number - 1)
            player.balance = previous_round.balance
        if player.bet_size > player.balance:
            player.bet_size = player.balance
        return dict(
            balance_display=Player.format_currency(player.balance),
            max_bet=player.balance,
            show_bet_intro=(player.round_number == 1),
            start_balance_display=Player.format_currency(Constants.START_BALANCE),
            total_rounds=Constants.num_rounds,
        )

    @staticmethod
    def error_message(player: Player, values):
        if values['bet_size'] < 1 or values['bet_size'] > player.balance:
            return 'Bet size must be between 1 and your current balance.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.start_round()

class Decision(Page):
    @staticmethod
    def is_displayed(player: Player):
        # Seite nur anzeigen, solange Spieler noch aktiv ist
        return (
            player.round_number <= player.summary_round()
            and not player.player_stood
            and not player.dealer_done
        )

    @staticmethod
    def vars_for_template(player: Player):
        ph = player._load('player_hand_json')
        dh = player._load('dealer_hand_json')
        dealer_initial = [card_to_meta(dh[0])]
        if len(dh) > 1:
            dealer_initial.append(card_to_meta('', hidden=True))
        start_key = f'decision_start_{player.round_number}'
        if start_key not in player.participant.vars:
            player.participant.vars[start_key] = time()
        return dict(
            balance_display=Player.format_currency(player.balance),
            player_hand=ph,
            player_hand_json=json.dumps(ph),
            dealer_hand_json=json.dumps(dh),
            dealer_upcard=dh[0],
            player_cards_meta=[card_to_meta(c) for c in ph],
            dealer_cards_meta_initial=dealer_initial,
            value_player=Player.hand_value(ph),
            bet_display=Player.format_currency(player.bet_size),
            can_double=(not player.has_hit and player.balance >= player.bet_size),
            round_number=player.round_number,
            total_rounds=Constants.num_rounds,
        )

    @staticmethod
    def live_method(player: Player, data):
        action = data.get('action') if isinstance(data, dict) else data
        start_key = f'decision_start_{player.round_number}'
        if start_key not in player.participant.vars:
            player.participant.vars[start_key] = time()

        if isinstance(data, dict) and data.get('__next'):
            return {player.id_in_group: dict(__next=True)}

        def record_action(action_key):
            label_map = {'hit': 'Hit', 'stand': 'Stand', 'double': 'Double'}
            current_hand = player._load('player_hand_json')
            dealer_hand = player._load('dealer_hand_json')
            dealer_upcard = dealer_hand[0] if dealer_hand else ''
            can_double_now = (not player.has_hit and player.balance >= player.bet_size)
            if not player.action_is_optimal(action_key, current_hand, dealer_upcard, can_double_now):
                player.deviation_from_optimal = True
            history = []
            if player.decision:
                history = [item.strip() for item in player.decision.split(',') if item.strip()]
            history.append(label_map.get(action_key, action_key.title()))
            player.decision = ', '.join(history)

        def state(done=False, reveal_dealer=False, error=None):
            player_hand = player._load('player_hand_json')
            dealer_hand = player._load('dealer_hand_json')
            payload = dict(
                balance_display=Player.format_currency(player.balance),
                bet_display=Player.format_currency(player.bet_size),
                player_hand=player_hand,
                value_player=Player.hand_value(player_hand),
                has_hit=player.has_hit,
                can_double=(not player.has_hit and player.balance >= player.bet_size),
            )
            if reveal_dealer or player.player_busted:
                payload.update(
                    dealer_hand=dealer_hand,
                    value_dealer=Player.hand_value(dealer_hand),
                    outcome=player.outcome,
                    payoff_display=Player.format_currency(player.payoff),
                )
            else:
                payload.update(dealer_upcard=dealer_hand[0])
            if error:
                payload['error'] = error
            if done:
                start_ts = player.participant.vars.pop(start_key, None)
                if start_ts:
                    player.decision_response_time = time() - start_ts
                player.bankroll_after_round = player.balance
                payload['done'] = True
                payload['__next'] = True
            return {player.id_in_group: payload}

        if action == 'status':
            return state()

        if action == 'hit':
            record_action('hit')
            player.player_hit()
            if player.player_busted or player.dealer_done:
                return state(done=True, reveal_dealer=True)
            return state()

        if action == 'stand':
            record_action('stand')
            player.player_stand()
            player.dealer_play()
            player._settle()
            return state(done=True, reveal_dealer=True)

        if action == 'double':
            if player.has_hit:
                return state(error='Double is only allowed before your first hit.')
            if player.balance < player.bet_size:
                return state(error='Insufficient balance to double.')
            record_action('double')
            player.player_double()
            if not player.dealer_done:
                player.dealer_play()
                player._settle()
            return state(done=True, reveal_dealer=True)

        return {player.id_in_group: dict()}


class Dealer(Page):
    @staticmethod
    def is_displayed(player: Player):
        return (
            player.round_number <= player.summary_round()
            and player.player_stood
            and not player.dealer_done
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.dealer_play()
        player._settle()

    @staticmethod
    def vars_for_template(player: Player):
        dh = player._load('dealer_hand_json')
        return dict(
            balance_display=Player.format_currency(player.balance),
            dealer_hand=' '.join(dh),
            value_dealer=Player.hand_value(dh),
        )

class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return (
            player.round_number <= player.summary_round()
            and player.dealer_done
        )
    @staticmethod
    def vars_for_template(player: Player):
        ph, dh = player._load('player_hand_json'), player._load('dealer_hand_json')
        outcome_text = player.outcome or ''
        outcome_code = outcome_to_code(outcome_text)
        class_map = {
            'win': 'bj-status__success',
            'blackjack': 'bj-status__success',
            'lose': 'bj-status__fail',
        }
        return dict(
            balance_display=Player.format_currency(player.balance),
            player_hand=ph, dealer_hand=dh,
            value_player=Player.hand_value(ph),
            value_dealer=Player.hand_value(dh),
            outcome=outcome_text,
            outcome_code=outcome_code,
            outcome_class=class_map.get(outcome_code, ''),
            payoff=player.payoff,
            bet_size=player.bet_size,
            player_cards_meta=[card_to_meta(c) for c in ph],
            dealer_cards_meta=[card_to_meta(c) for c in dh],
            bet_display=Player.format_currency(player.bet_size),
            payoff_display=Player.format_currency(player.payoff),
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if player.balance <= 0 and 'summary_round' not in player.participant.vars:
            player.participant.vars['summary_round'] = player.round_number
        if player.round_number < Constants.num_rounds:
            next_player = player.in_round(player.round_number + 1)
            next_player.balance = player.balance

class Summary(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == player.summary_round()

    @staticmethod
    def vars_for_template(player: Player):
        final_balance = player.balance
        net_result = final_balance - Constants.START_BALANCE
        summary_round = player.summary_round()
        eliminated_round = None
        if final_balance <= 0 or summary_round < Constants.num_rounds:
            eliminated_round = summary_round
        final_balance_value = float(final_balance)
        net_result_value = float(net_result)
        return dict(
            final_balance=final_balance,
            final_balance_value=final_balance_value,
            final_balance_display=Player.format_currency(final_balance),
            net_result=net_result,
            net_result_value=net_result_value,
            net_result_display=Player.format_currency(net_result),
            eliminated_round=eliminated_round,
            rounds_played=summary_round,
            total_rounds=Constants.num_rounds,
        )


page_sequence = [Intro, BetPage, Decision, Dealer, Results, Summary]
