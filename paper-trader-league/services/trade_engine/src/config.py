from decimal import Decimal
import os

DEFAULT_BOTS = [
    ('aurora_quanta', 'Aurora Quanta'),
    ('stormchaser_delta', 'StormChaser Delta'),
    ('mercury_vanta', 'Mercury Vanta'),
]
DEFAULT_SEASON_ID = os.getenv('DEFAULT_SEASON_ID', 'season-001')
DEFAULT_STARTING_BTC = Decimal(os.getenv('DEFAULT_STARTING_BTC', '0.05'))
DEFAULT_FEE_BPS = Decimal(os.getenv('DEFAULT_FEE_BPS', '10'))
DEFAULT_SLIPPAGE_BPS = Decimal(os.getenv('DEFAULT_SLIPPAGE_BPS', '5'))
