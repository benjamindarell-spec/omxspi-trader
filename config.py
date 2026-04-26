OMXSPI_UNIVERSE = [
    # Large cap — Financials
    "SHB-A.ST", "SEB-A.ST", "SWED-A.ST", "NDA-SE.ST", "INVE-B.ST",
    # Large cap — Industrials
    "VOLV-B.ST", "SAND.ST", "ASSA-B.ST", "SKF-B.ST", "ATCO-A.ST",
    "ABB.ST", "ALFA.ST", "CAST.ST", "SSAB-A.ST", "HEXA-B.ST",
    # Large cap — Tech / Telecom
    "ERIC-B.ST", "KINV-B.ST",
    # Large cap — Healthcare
    "AZN.ST",
    # Large cap — Real estate / Diversified
    "LUND-B.ST",
    # Mid cap — Industrials
    "NIBE-B.ST", "HUSQ-B.ST", "PEAB-B.ST", "TREL-B.ST", "BALD-B.ST",
    "MIPS.ST", "BUFAB.ST", "HANZA.ST", "ADDTECH-B.ST",
    # Mid cap — Real estate
    "HUFV-A.ST", "JM.ST", "DIOS.ST",
    # Mid cap — Consumer / Retail
    "BOOZT.ST", "CLAS-B.ST", "BRAV.ST", "CATE.ST", "DUNI.ST",
    # Mid cap — Tech / Software
    "PNDX-B.ST", "LATO-B.ST",
    # Mid cap — Services
    "COOR.ST", "NOTE.ST", "AXFO.ST",
    # Growth / Smaller
    "EVO.ST", "GETI-B.ST", "CAMX.ST", "BEGR.ST",
]

SECTORS: dict[str, str] = {
    "ERIC-B.ST": "Tech",
    "HEXA-B.ST": "Tech",
    "KINV-B.ST": "Tech",
    "PNDX-B.ST": "Tech",
    "LATO-B.ST": "Tech",
    "SWED-A.ST": "Finance",
    "SHB-A.ST": "Finance",
    "SEB-A.ST": "Finance",
    "NDA-SE.ST": "Finance",
    "INVE-B.ST": "Finance",
    "VOLV-B.ST": "Industrial",
    "SAND.ST": "Industrial",
    "ASSA-B.ST": "Industrial",
    "SKF-B.ST": "Industrial",
    "ATCO-A.ST": "Industrial",
    "ABB.ST": "Industrial",
    "ALFA.ST": "Industrial",
    "CAST.ST": "Industrial",
    "SSAB-A.ST": "Industrial",
    "NIBE-B.ST": "Industrial",
    "HUSQ-B.ST": "Industrial",
    "PEAB-B.ST": "Industrial",
    "TREL-B.ST": "Industrial",
    "BALD-B.ST": "Industrial",
    "MIPS.ST": "Industrial",
    "BUFAB.ST": "Industrial",
    "HANZA.ST": "Industrial",
    "ADDTECH-B.ST": "Industrial",
    "AZN.ST": "Healthcare",
    "EVO.ST": "Gaming",
    "GETI-B.ST": "Gaming",
    "HUFV-A.ST": "Real Estate",
    "JM.ST": "Real Estate",
    "DIOS.ST": "Real Estate",
    "LUND-B.ST": "Real Estate",
    "BOOZT.ST": "Consumer",
    "CLAS-B.ST": "Consumer",
    "BRAV.ST": "Consumer",
    "CATE.ST": "Consumer",
    "DUNI.ST": "Consumer",
    "COOR.ST": "Services",
    "NOTE.ST": "Services",
    "AXFO.ST": "Services",
    "CAMX.ST": "Other",
    "BEGR.ST": "Other",
}

# Strategy parameters
STOP_LOSS_PCT = 0.07
TAKE_PROFIT_PCT = 0.15
MOONSHOT_PCT = 0.30
TRAIL_STOP_PCT = 0.10
PORTFOLIO_CAPITAL = 10000
MAX_POSITIONS = 5
MIN_DAILY_VOLUME_SEK = 500_000
MAX_SECTOR_POSITIONS = 2
REBALANCE_DAY = "Monday"

# Signal score thresholds
STRONG_BUY_THRESHOLD = 3.5
BUY_THRESHOLD = 1.5
SELL_THRESHOLD = -1.5
STRONG_SELL_THRESHOLD = -3.5

# Claude model
CLAUDE_MODEL = "claude-sonnet-4-6"

# Email settings — set via environment variables or edit directly
import os
EMAIL_SENDER = os.environ.get("EMAIL_SENDER", "")       # your Gmail address
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")   # Gmail App Password (not your login password)
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "benjamin.darell@gmail.com")
