from os import environ
SESSION_CONFIGS = [
    dict(
        name='blackjack_demo',
        display_name='Blackjack (Demo)',
        app_sequence=['blackjack_game'],
        num_demo_participants=1,
    ),
    dict(
        name='bigfive_demo',
        display_name='Big Five Personality Test',
        app_sequence=['BigFive'],
        num_demo_participants=1,
    ),
    dict(
        name='bigfive_then_blackjack',
        display_name='Big Five → Blackjack',
        app_sequence=['BigFive', 'blackjack_game'],  # Reihenfolge hier
        num_demo_participants=1,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
)


PARTICIPANT_FIELDS = ['finished']
SESSION_FIELDS = []

LANGUAGE_CODE = 'de'
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True


ROOMS = [
    dict(name='study_room', display_name='Big Five → Blackjack Study'),
]


# Admin-Bereich

ADMIN_USERNAME = environ.get('OTREE_ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')  
AUTH_LEVEL = environ.get('OTREE_AUTH_LEVEL', 'STUDY')

DEMO_PAGE_INTRO_HTML = """
<h3>oTree Demos</h3>
<p>Wähle eine Session, um zu starten.</p>
"""

SECRET_KEY = 'replace-this-with-a-random-secret-key'


INSTALLED_APPS = ['otree']
