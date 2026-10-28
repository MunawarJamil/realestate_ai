from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    LOST = "lost"
    CLOSED = "closed"


class LeadIntent(StrEnum):
    BUY = "buy"
    RENT = "rent"
    INVEST = "invest"
    SELL = "sell"


class LeadScoreCategory(StrEnum):
    HOT = "hot"      # Score >= 85
    WARM = "warm"    # 70 <= Score < 85
    COLD = "cold"    # Score < 70



    
    