from decimal import Decimal
import os

DEFAULT_BOTS = [
    ('solstice_drift', 'Solstice Drift'),
    ('obsidian_flux', 'Obsidian Flux'),
    ('vega_pulse', 'Vega Pulse'),
    ('phantom_lattice', 'Phantom Lattice'),
]
DEFAULT_SEASON_ID = os.getenv('DEFAULT_SEASON_ID', 'season-002')
DEFAULT_STARTING_BTC = Decimal(os.getenv('DEFAULT_STARTING_BTC', '0.05'))

# Coinbase One fee structure with 25% rebate applied
# Spot: 0.025% maker / 0.065% taker → after rebate: 1.875 bps maker / 4.875 bps taker
# All bot market orders are taker; limit orders (if added later) would use maker rate.
DEFAULT_MAKER_FEE_BPS = Decimal(os.getenv('DEFAULT_MAKER_FEE_BPS', '1.875'))
DEFAULT_TAKER_FEE_BPS = Decimal(os.getenv('DEFAULT_TAKER_FEE_BPS', '4.875'))

# Legacy alias — resolves to taker rate (market orders are always taker)
DEFAULT_FEE_BPS = DEFAULT_TAKER_FEE_BPS

DEFAULT_SLIPPAGE_BPS = Decimal(os.getenv('DEFAULT_SLIPPAGE_BPS', '5'))
