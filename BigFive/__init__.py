from otree.api import *


def _field_value_or_none(model: BasePlayer, field_name: str):
    try:
        return model.field_maybe_none(field_name)  
    except AttributeError:
        return model.__dict__.get(field_name)


def question_context(player: "Player", block_index: int):
    """Build template context for the given question block."""
    total_pages = C.QUESTION_PAGE_COUNT
    questions = []
    for q in C.questions_for_page(block_index):
        selected = _field_value_or_none(player, q['field'])
        questions.append({**q, 'selected': selected})

    progress = None
    if total_pages:
        progress = int(round(block_index / total_pages * 100))

    return dict(
        questions=questions,
        scale_options=C.SCALE_OPTIONS,
        page_number=block_index + 1,
        total_pages=total_pages,
        progress=progress,
    )


def compute_trait_scores(player: "Player"):
    """
    Aggregate per-trait averages handling reverse-coded items.
    Returns a list of dicts with trait, count, missing, total, average, percentage.
    """
    all_traits = []
    for q in C.QUESTIONS:
        t = q['trait']
        if t not in all_traits:
            all_traits.append(t)

    trait_values = {trait: [] for trait in all_traits}
    trait_missing = {trait: 0 for trait in all_traits}

    for q in C.QUESTIONS:
        raw = _field_value_or_none(player, q['field'])
        if raw is None:
            trait_missing[q['trait']] += 1
            continue
        val = float(raw)
        if q.get('reverse', False):
            val = C.SCALE_MIN + C.SCALE_MAX - val
        trait_values[q['trait']].append(val)

    scores = []
    scale_span = (C.SCALE_MAX - C.SCALE_MIN)
    for trait in all_traits:
        values = trait_values[trait]
        if not values:
            scores.append(dict(
                trait=trait, count=0, missing=trait_missing[trait],
                total=None, average=None, percentage=None
            ))
            continue

        total = sum(values)
        avg = total / len(values)
        # 0–100% normieren: min -> 0%, max -> 100%
        pct = ((avg - C.SCALE_MIN) / scale_span) * 100 if scale_span else None

        scores.append(dict(
            trait=trait,
            count=len(values),
            missing=trait_missing[trait],
            total=round(total, 2),
            average=round(avg, 2),
            percentage=round(pct, 1) if pct is not None else None,
        ))

    return scores


class C(BaseConstants):
    NAME_IN_URL = 'bigfive'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1
    PAGE_QUESTION_COUNTS = [6, 5, 5, 5, 5]
    QUESTION_PAGE_COUNT = len(PAGE_QUESTION_COUNTS)
    SCALE_MIN = 1
    SCALE_MAX = 5
    TRAITS = ['Openness', 'Conscientiousness', 'Extraversion', 'Agreeableness', 'Neuroticism', 'RiskTolerance']
    SCALE_OPTIONS = [
        dict(value=1, text='Strongly Disagree', css='strongly-disagree'),
        dict(value=2, text='Disagree', css='disagree'),
        dict(value=3, text='Neutral', css='neutral'),
        dict(value=4, text='Agree', css='agree'),
        dict(value=5, text='Strongly Agree', css='strongly-agree'),
    ]
    QUESTIONS = [
    dict(field='q1', trait='Openness', text='I enjoy exploring new ideas and perspectives.', reverse=False),
    dict(field='q2', trait='Openness', text='I seek out creative experiences in my free time.', reverse=False),
    dict(field='q3', trait='Openness', text='I prefer routine tasks over experimenting with something new.', reverse=True),
    dict(field='q4', trait='Openness', text='I appreciate art, music, or literature.', reverse=False),
    dict(field='q5', trait='Openness', text='I stick with familiar solutions instead of trying untested ones.', reverse=True),
    dict(field='q26', trait='RiskTolerance', text='In general, I am willing to take risks.', reverse=False), # Risk Tolerance Frage

    dict(field='q6', trait='Conscientiousness', text='I pay close attention to details when working on tasks.', reverse=False),
    dict(field='q7', trait='Conscientiousness', text='I keep my workspace and schedule well organized.', reverse=False),
    dict(field='q8', trait='Conscientiousness', text='I leave tasks unfinished when something more interesting comes along.', reverse=True),
    dict(field='q9', trait='Conscientiousness', text='I plan tasks carefully rather than leaving them to chance.', reverse=False),
    dict(field='q10', trait='Conscientiousness', text='I put things off until the last minute.', reverse=True),

    dict(field='q11', trait='Extraversion', text='I feel energized by social gatherings.', reverse=False),
    dict(field='q12', trait='Extraversion', text='I am comfortable starting conversations with new people.', reverse=False),
    dict(field='q13', trait='Extraversion', text='I prefer to stay in the background during social events.', reverse=True),
    dict(field='q14', trait='Extraversion', text='I seek out opportunities to interact with others.', reverse=False),
    dict(field='q15', trait='Extraversion', text='I find it exhausting to be around many people for a long time.', reverse=True),

    dict(field='q16', trait='Agreeableness', text="I am considerate of other people's feelings.", reverse=False),
    dict(field='q17', trait='Agreeableness', text='I am willing to compromise to maintain harmony.', reverse=False),
    dict(field='q18', trait='Agreeableness', text='I find it hard to empathize with others.', reverse=True),
    dict(field='q19', trait='Agreeableness', text='I take time to listen to what others have to say.', reverse=False),
    dict(field='q20', trait='Agreeableness', text='I can be stubborn when I think I am right.', reverse=True),

    dict(field='q21', trait='Neuroticism', text='I worry easily about many things.', reverse=False),
    dict(field='q22', trait='Neuroticism', text='I feel tense when I have many tasks to juggle.', reverse=False),
    dict(field='q23', trait='Neuroticism', text='I remain calm even in stressful situations.', reverse=True),
    dict(field='q24', trait='Neuroticism', text='I find it difficult to relax.', reverse=False),
    dict(field='q25', trait='Neuroticism', text='I bounce back quickly after setbacks.', reverse=True),
    ]   

    @classmethod
    def questions_for_page(cls, page_index: int):
        if page_index < 0 or page_index >= len(cls.PAGE_QUESTION_COUNTS):
            return []
        start = sum(cls.PAGE_QUESTION_COUNTS[:page_index])
        end = start + cls.PAGE_QUESTION_COUNTS[page_index]
        return cls.QUESTIONS[start:end]


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    age = models.IntegerField(min=12, max=99, blank=True)
    gender = models.StringField(choices=['Female', 'Male', 'Non-binary'], blank=True)
    education = models.StringField(choices=[
        'No formal education',
        'Lower secondary school (Hauptschule)',
        'Intermediate secondary school (Realschule / Mittlere Reife)',
        'Upper secondary school (Abitur / Gymnasium)',
        'Vocational training / apprenticeship (Ausbildung)',
        "Bachelor's degree",
        "Master's degree",
        'Doctorate / PhD',
        'Other',
    ], blank=True)
    blackjack_familiarity = models.StringField(choices=[
        'Not familiar at all',
        'Somewhat familiar',
        'Fairly familiar',
        'Very familiar',
    ], blank=True)
    email = models.StringField(blank=True)
    q1 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q2 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q3 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q4 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q5 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q26 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q6 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q7 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q8 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q9 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q10 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q11 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q12 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q13 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q14 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q15 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q16 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q17 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q18 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q19 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q20 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q21 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q22 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q23 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q24 = models.IntegerField(choices=[1, 2, 3, 4, 5])
    q25 = models.IntegerField(choices=[1, 2, 3, 4, 5])


class Intro(Page):
    template_name = 'BigFive/Intro.html'


class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'education', 'blackjack_familiarity']
    template_name = 'BigFive/Demographics.html'

class PageOne(Page):
    form_model = 'player'
    form_fields = ['q1', 'q2', 'q3', 'q4', 'q5', 'q26']
    template_name = 'BigFive/LikertPage.html'

    @staticmethod
    def vars_for_template(player: Player):
        return question_context(player, 0)


class PageTwo(Page):
    form_model = 'player'
    form_fields = ['q6', 'q7', 'q8', 'q9', 'q10']
    template_name = 'BigFive/LikertPage.html'

    @staticmethod
    def vars_for_template(player: Player):
        return question_context(player, 1)


class PageThree(Page):
    form_model = 'player'
    form_fields = ['q11', 'q12', 'q13', 'q14', 'q15']
    template_name = 'BigFive/LikertPage.html'

    @staticmethod
    def vars_for_template(player: Player):
        return question_context(player, 2)


class PageFour(Page):
    form_model = 'player'
    form_fields = ['q16', 'q17', 'q18', 'q19', 'q20']
    template_name = 'BigFive/LikertPage.html'

    @staticmethod
    def vars_for_template(player: Player):
        return question_context(player, 3)


class PageFive(Page):
    form_model = 'player'
    form_fields = ['q21', 'q22', 'q23', 'q24', 'q25']
    template_name = 'BigFive/LikertPage.html'

    @staticmethod
    def vars_for_template(player: Player):
        return question_context(player, 4)

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.vars['bigfive_trait_scores'] = compute_trait_scores(player)


class Transition(Page):
    template_name = 'BigFive/Transition.html'

page_sequence = [Intro, Demographics, PageOne, PageTwo, PageThree, PageFour, PageFive, Transition]
