"""Map SEC Form N-PORT holding names to GICS sector via SEC company tickers
and yfinance.

Pipeline per holding:
    name -> normalized name -> ticker (via SEC company-tickers JSON files
    + a small manual override map) -> sector (via yfinance .info)

Caches are stored under raw_responses/:
    sec_company_tickers.json     -- raw SEC dump
    sec_company_tickers_ex.json  -- SEC exchange-listed dump
    ticker_sector.json           -- {ticker: {sector, longName, asOf}}
    name_skiplist.json           -- normalized names known to be non-equity
                                    (money funds etc.) so we don't keep
                                    re-trying them
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import httpx

CT_URL = "https://www.sec.gov/files/company_tickers.json"
CT_EX_URL = "https://www.sec.gov/files/company_tickers_exchange.json"

# Manual overrides for known mismatches (renames, inverted-name SEC entries,
# punctuation issues). Keep the keys in *normalized* form (output of normalize()).
MANUAL_OVERRIDES: dict[str, str] = {
    # Renames / corporate actions
    "MICROSTRATEGY": "MSTR",
    # Inverted "LAST FIRST" SEC entries
    "CHARLES SCHWAB": "SCHW",
    "ROWE PRICE": "TROW",       # SEC: "PRICE T ROWE GROUP"
    # Companies missing from SEC tickers files
    "HOLOGIC": "HOLX",
    "GAMING LEISURE PROPERTIES": "GLPI",
    "CRH": "CRH",
    "OREILLY AUTOMOTIVE": "ORLY",
    "WW GRAINGER": "GWW",
    "HESS": "HES",
    "DISCOVER FINANCIAL SERVICES": "DFS",
    "SCHLUMBERGER": "SLB",
    "DR HORTON": "DHI",
    "LIBERTY MEDIA FORMULA ONE": "FWONK",
    "HARTFORD FINANCIAL SERVICES": "HIG",
}

# Names that should be skipped entirely (cash/money market, security-lending
# subsidiaries, future contracts).
SKIP_NAME_FRAGMENTS: tuple[str, ...] = (
    "MONEY MARKET",
    "LIQUIDITY FUND",
    "CASH FUND",
    "GOVERNMENT FUND",
    "BLACKROCK FUNDING",  # iShares securities-lending subsidiary
    "EMINI",              # S&P futures contracts
)

# yfinance returns "sector" for stocks; this is the GICS-aligned label.
#
# The narrow Information Technology sector excludes a lot of what people
# colloquially call "tech": META, GOOGL, NFLX live in Communication Services
# (since the 2018 GICS reorg), and AMZN/TSLA live in Consumer Cyclical. We
# expose a *broad* tech view that covers the full AI-bubble surface area:
#   - GICS Technology
#   - GICS Communication Services
#   - explicit additions: AMZN, TSLA
# This roughly approximates the pre-2018 Information Technology sector
# definition (with AMZN/TSLA layered in for the AI-narrative reading).
TECH_BROAD_SECTORS = {"Technology", "Communication Services"}
TECH_BROAD_TICKER_OVERRIDES = {"AMZN", "TSLA"}


def is_tech_broad(ticker: str | None, sector: str | None) -> bool:
    if sector in TECH_BROAD_SECTORS:
        return True
    if ticker and ticker in TECH_BROAD_TICKER_OVERRIDES:
        return True
    return False

CORP_SUFFIX_RE = re.compile(
    r"\b(INCORPORATED|INCORPORATION|INC|CORPORATION|CORP|COMPANIES|"
    r"COMPANY|COS|CO|LIMITED|LTD|LLC|PLC|HOLDINGS|HOLDING|GROUP|"
    r"TRUST|NV|SA|SE|SPA|SCA|ASA|OYJ|ABP|AB|AG|KGAA|"
    r"THE|AND|OF)\b"
)


# Curated international name -> yfinance ticker. Extends the SEC US-only
# company-tickers map to cover holdings VT and other global ETFs hold via
# foreign listings (no US ADR or only an illiquid OTC). Prefer US-listed
# tickers when available; fall through to local-exchange tickers (`.KS`,
# `.HK`, `.T`, etc.) only when no US listing exists. Keys are the *normalized*
# form (output of normalize_name).
INTL_NAME_TO_TICKER: dict[str, str] = {
    # Asia tech
    "SAMSUNG ELECTRONICS": "005930.KS",
    "TENCENT": "TCEHY",
    "SK HYNIX": "000660.KS",
    "TOKYO ELECTRON": "TOELY",
    "SOFTBANK": "SFTBY",
    "MEDIATEK": "2454.TW",
    "DELTA ELECTRONICS": "2308.TW",
    "KEYENCE": "KYCCF",
    "FUJITSU": "6702.T",
    "RECRUIT": "6098.T",
    "NINTENDO": "NTDOY",
    "MITSUBISHI ELECTRIC": "6503.T",
    "SHIN ETSU CHEMICAL": "4063.T",
    "PROSUS": "PRX.AS",
    "HON HAI PRECISION INDUSTRY": "2317.TW",
    "MEITUAN": "3690.HK",
    "XIAOMI": "1810.HK",
    "HITACHI": "6501.T",
    "SAP": "SAP",
    "INFINEON TECHNOLOGIES": "IFX.DE",
    "STMICROELECTRONICS": "STM",
    "DASSAULT SYSTEMES": "DSY.PA",
    "TDK": "6762.T",
    "MURATA MANUFACTURING": "6981.T",
    "OMRON": "6645.T",
    "DAIICHI SANKYO": "4568.T",
    "FANUC": "6954.T",
    "KOMATSU": "6301.T",
    "HOYA": "7741.T",
    "BRIDGESTONE": "5108.T",
    "PANASONIC": "6752.T",
    "DAIKIN INDUSTRIES": "6367.T",
    "TAKEDA PHARMACEUTICAL": "TAK",
    "ASTELLAS PHARMA": "4503.T",
    "EISAI": "4523.T",
    "OTSUKA": "4578.T",
    "SEVEN I": "3382.T",
    "DENSO": "6902.T",
    "TOYOTA INDUSTRIES": "6201.T",
    # Europe industrials / consumer / health
    "ROCHE": "ROG.SW",
    "NESTLE": "NESN.SW",
    "SIEMENS": "SIE.DE",
    "AIRBUS": "AIR.PA",
    "SAFRAN": "SAF.PA",
    "ROLLS ROYCE": "RR.L",
    "SCHNEIDER ELECTRIC": "SU.PA",
    "VINCI": "DG.PA",
    "ATLAS COPCO": "ATCO-A.ST",
    "ABB": "ABBN.SW",
    "VOLVO": "VOLV-B.ST",
    "RHEINMETALL": "RHM.DE",
    "ALSTOM": "ALO.PA",
    "LOREAL": "OR.PA",
    "AIR LIQUIDE": "AI.PA",
    "LINDE": "LIN",
    "BAYER": "BAYN.DE",
    "BASF": "BAS.DE",
    "BMW": "BMW.DE",
    "BAYERISCHE MOTOREN WERKE": "BMW.DE",
    "VOLKSWAGEN": "VOW3.DE",
    "MERCEDES BENZ": "MBG.DE",
    "PORSCHE": "P911.DE",
    "RENAULT": "RNO.PA",
    "STELLANTIS": "STLA",
    "FERRARI": "RACE",
    "LVMH MOET HENNESSY LOUIS VUITTON": "MC.PA",
    "LVMH": "MC.PA",
    "HERMES INTERNATIONAL": "RMS.PA",
    "INDUSTRIA DE DISENO TEXTIL": "ITX.MC",
    "INDUSTRIA DISENO TEXTIL": "ITX.MC",
    "FAST RETAILING": "9983.T",
    "ESSILORLUXOTTICA": "EL.PA",
    "PERNOD RICARD": "RI.PA",
    "ADIDAS": "ADS.DE",
    "RECKITT BENCKISER": "RKT.L",
    "HEINEKEN": "HEIA.AS",
    "RYANAIR": "RYAAY",
    "MICHELIN": "ML.PA",
    "DEUTSCHE POST": "DHL.DE",
    "DEUTSCHE TELEKOM": "DTE.DE",
    "TELEFONICA": "TEF.MC",
    "VODAFONE": "VOD",
    "ORANGE": "ORA.PA",
    "TOTALENERGIES": "TTE",
    "ENI": "E",
    "EQUINOR": "EQNR",
    "IBERDROLA": "IBE.MC",
    "ENEL": "ENEL.MI",
    "VEOLIA ENVIRONNEMENT": "VIE.PA",
    "ENGIE": "ENGI.PA",
    # Europe financials
    "ALLIANZ": "ALV.DE",
    "BNP PARIBAS": "BNP.PA",
    "AXA": "CS.PA",
    "ZURICH INSURANCE": "ZURN.SW",
    "DEUTSCHE BANK": "DB",
    "INTESA SANPAOLO": "ISP.MI",
    "UNICREDIT": "UCG.MI",
    "SOCIETE GENERALE": "GLE.PA",
    "NORDEA BANK": "NDA-FI.HE",
    "TOKIO MARINE": "8766.T",
    "DEUTSCHE BOERSE": "DB1.DE",
    "MUNICH RE": "MUV2.DE",
    "MUENCHENER RUECKVERSICHERUNGS GESELLSCHAFT IN MUENCHEN": "MUV2.DE",
    "AVIVA": "AV.L",
    "STANDARD CHARTERED": "STAN.L",
    "BANCO SANTANDER": "SAN",
    "ITAU UNIBANCO": "ITUB",
    # Asia financials
    "AIA": "1299.HK",
    "DBS": "D05.SI",
    "PING AN INSURANCE": "2318.HK",
    "PING AN INSURANCE CHINA": "2318.HK",
    "INDUSTRIAL COMMERCIAL BANK CHINA": "1398.HK",
    "CHINA CONSTRUCTION BANK": "0939.HK",
    "HONG KONG EXCHANGES CLEARING": "0388.HK",
    "MITSUBISHI UFJ": "MUFG",
    "SUMITOMO MITSUI FINANCIAL": "SMFG",
    "MIZUHO FINANCIAL": "MFG",
    # Australia / NZ
    "COMMONWEALTH BANK AUSTRALIA": "CBA.AX",
    "NATIONAL AUSTRALIA BANK": "NAB.AX",
    "ANZ": "ANZ.AX",
    "ANZ GROUP": "ANZ.AX",
    "MACQUARIE": "MQG.AX",
    "QBE INSURANCE": "QBE.AX",
    "WESFARMERS": "WES.AX",
    "WOOLWORTHS": "WOW.AX",
    "TRANSURBAN": "TCL.AX",
    "TELSTRA": "TLS.AX",
    "WOODSIDE ENERGY": "WDS",
    "FORTESCUE": "FMG.AX",
    "BHP": "BHP",
    # UK additional
    "BARCLAYS": "BCS",
    "LLOYDS BANKING": "LYG",
    "GLENCORE": "GLEN.L",
    "ANGLO AMERICAN": "AAL.L",
    "ANTOFAGASTA": "ANTO.L",
    "BUNZL": "BNZL.L",
    # Industrials / mining (Japan misc)
    "MITSUBISHI HEAVY INDUSTRIES": "7011.T",
    "MITSUBISHI": "8058.T",
    "MITSUI": "8031.T",
    # Canada additions
    "ENBRIDGE": "ENB",
    "TC ENERGY": "TRP",
    "TORONTO DOMINION BANK": "TD",
    "ROYAL BANK CANADA": "RY",
    "BANK NOVA SCOTIA": "BNS",
    "BANK MONTREAL": "BMO",
    "CANADIAN IMPERIAL BANK COMMERCE": "CM",
    "BROOKFIELD": "BN",
    "BROOKFIELD ASSET MANAGEMENT": "BAM",
    "CANADIAN NATURAL RESOURCES": "CNQ",
    "SUNCOR ENERGY": "SU",
    "BARRICK GOLD": "GOLD",
    "AGNICO EAGLE MINES": "AEM",
    "MANULIFE FINANCIAL": "MFC",
    "SUN LIFE FINANCIAL": "SLF",
    "TELUS": "TU",
    "BCE": "BCE",
    "CGI": "GIB",
    # India / China ADRs
    "INFOSYS": "INFY",
    "ICICI BANK": "IBN",
    "WIPRO": "WIT",
    "HDFC BANK": "HDB",
    "RELIANCE INDUSTRIES": "RIGD.IL",
    "BAIDU": "BIDU",
    "JD COM": "JD",
    "NETEASE": "NTES",
    "PINDUODUO": "PDD",
    "TRIP COM": "TCOM",
    # Misc
    "NOKIA": "NOK",
    "ERICSSON": "ERIC",
    "ARCELORMITTAL": "MT",
    "ARCELOR MITTAL": "MT",
    "ARM": "ARM",
    "ARM HOLDINGS": "ARM",
    "ASML HOLDING": "ASML",
    "CIE FINANCIERE RICHEMONT": "CFR.SW",
    "RICHEMONT": "CFR.SW",
    "AHOLD DELHAIZE": "ADRNY",
    "MERCADOLIBRE": "MELI",
    "SHOPIFY": "SHOP",
    "NATURA COSMETICOS": "NTCO",
    # Additional fills from the second-pass unclassified list
    "INVESTOR": "INVE-A.ST",
    "BHARTI AIRTEL": "BHARTIARTL.NS",
    "AL RAJHI BANK": "1120.SR",
    "DSV": "DSV.CO",
    "DANONE": "BN.PA",
    "MARUBENI": "8002.T",
    "SWISS RE": "SREN.SW",
    "LONZA": "LONN.SW",
    "NASPERS": "NPN.JO",
    "HYUNDAI MOTOR": "005380.KS",
    "CIE SAINT GOBAIN": "SGO.PA",
    "SAINT GOBAIN": "SGO.PA",
    "RWE": "RWE.DE",
    "GOODMAN": "GMG.AX",
    "SUMITOMO": "8053.T",
    "NEC": "6701.T",
    "SANDVIK": "SAND.ST",
    "BANK CHINA": "3988.HK",
    "SSE": "SSE.L",
    "ALIMENTATION COUCHE TARD": "ATD.TO",
    "JAPAN TOBACCO": "2914.T",
    "SAUDI ARABIAN OIL": "2222.SR",
    "SAUDI ARAMCO": "2222.SR",
    "LEGRAND": "LR.PA",
    "ASM INTERNATIONAL": "ASM.AS",
    "BBVA": "BBVA",
    "BANCO BILBAO VIZCAYA ARGENTARIA": "BBVA",
    "ING GROEP": "ING",
    "POSCO": "PKX",
    "POSCO HOLDINGS": "PKX",
    "SK TELECOM": "SKM",
    "LG ENERGY SOLUTION": "373220.KS",
    "LG ELECTRONICS": "066570.KS",
    "KIA": "000270.KS",
    "TATA CONSULTANCY": "TCS.NS",
    "TATA MOTORS": "TTM",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "RELIANCE INDUSTRIES": "RELIANCE.NS",
    "HENNES MAURITZ": "HM-B.ST",
    "H M HENNES MAURITZ": "HM-B.ST",
    "CARREFOUR": "CA.PA",
    "PUBLICIS": "PUB.PA",
    "STMICRO": "STMPA.PA",
    "ATLASSIAN": "TEAM",
    "ENBRIDGE INC": "ENB",
    "SUNCOR": "SU",
    "TC ENERGY CORP": "TRP",
    "BANCO BRADESCO": "BBD",
    "MTR": "0066.HK",
    "CK HUTCHISON": "0001.HK",
    "CK ASSET": "1113.HK",
    "GALAXY ENTERTAINMENT": "0027.HK",
    "BUDWEISER BREWING": "1876.HK",
    "ANTA SPORTS": "2020.HK",
    "BANCO BPM": "BAMI.MI",
    "FERROVIAL": "FER.AS",
    "INFRASTRUTTURE WIRELESS ITALIANE": "INW.MI",
    "GENERALI": "G.MI",
    "ASSICURAZIONI GENERALI": "G.MI",
    "MEDIATEK INC": "2454.TW",
    "FUJIFILM": "4901.T",
    "KAO": "4452.T",
    "OBAYASHI": "1802.T",
    "SHIMIZU": "1803.T",
    "EBARA": "6361.T",
    "AJINOMOTO": "2802.T",
    "SUNTORY BEVERAGE": "2587.T",
    "JAPAN POST": "6178.T",
    "CHUBU ELECTRIC POWER": "9502.T",
    "TOKYO ELECTRIC POWER": "9501.T",
    "EAST JAPAN RAILWAY": "9020.T",
    "WEST JAPAN RAILWAY": "9021.T",
    "CENTRAL JAPAN RAILWAY": "9022.T",
    "KDDI": "9433.T",
    "ITOCHU": "8001.T",
    "ASAHI": "2502.T",
    "ASAHI GROUP": "2502.T",
    "MS AD INSURANCE": "8725.T",
    "MS AND AD INSURANCE": "8725.T",
    "MITSUBISHI ESTATE": "8802.T",
    "MITSUI FUDOSAN": "8801.T",
    "SUMITOMO REALTY DEVELOPMENT": "8830.T",
    "ORIX": "8591.T",
    "AEON": "8267.T",
    "RAKUTEN": "4755.T",
    "TOKYO GAS": "9531.T",
    "MITSUBISHI CHEMICAL": "4188.T",
    "TORAY INDUSTRIES": "3402.T",
    "ENN ENERGY": "2688.HK",
    "JARDINE MATHESON": "JM.SI",
    "OVERSEA CHINESE BANKING": "O39.SI",
    "UNITED OVERSEAS BANK": "U11.SI",
    "SINGAPORE TELECOMMUNICATIONS": "Z74.SI",
    "BCA": "BBCA.JK",
    "MELROSE INDUSTRIES": "MRO.L",
    "ELEMENT FLEET MANAGEMENT": "EFN.TO",
    "BUREAU VERITAS": "BVI.PA",
    "CAPGEMINI": "CAP.PA",
    "TELEFONAKTIEBOLAGET LM ERICSSON": "ERIC",
    "EDP": "EDP.LS",
    "GAZTRANSPORT TECHNIGAZ": "GTT.PA",
    "SUEZ": "SEV.PA",
    "FRESENIUS MEDICAL CARE": "FMS",
    "FRESENIUS": "FRE.DE",
    "CONTINENTAL": "CON.DE",
    "HENKEL": "HEN3.DE",
    "BEIERSDORF": "BEI.DE",
    "PUMA": "PUM.DE",
    "ZALANDO": "ZAL.DE",
    "DELIVERY HERO": "DHER.DE",
    "EVONIK INDUSTRIES": "EVK.DE",
    "BRENNTAG": "BNR.DE",
    "SARTORIUS": "SRT3.DE",
    "MERCK KGAA": "MRK.DE",
    "SIEMENS HEALTHINEERS": "SHL.DE",
    "SIEMENS ENERGY": "ENR.DE",
    "INTERCONTINENTAL HOTELS": "IHG",
    "GSK PLC": "GSK",
    "BANK IRELAND": "BIRG.IR",
    "BANK IRELAND GROUP": "BIRG.IR",
    "AIB GROUP": "A5G.IR",
    "BANCO BPM SPA": "BAMI.MI",
    "WPP": "WPP.L",
    "HALEON": "HLN",
    "TESCO": "TSCO.L",
    "SAINSBURY J": "SBRY.L",
    "ROLLS ROYCE HOLDINGS": "RR.L",
    "RECKITT": "RKT.L",
    "DIAGEO PLC": "DEO",
    "BARCLAYS PLC": "BCS",
    "LLOYDS BANKING GROUP": "LYG",
    "PRUDENTIAL PLC": "PUK",
    "RIO TINTO PLC": "RIO",
    "BHP GROUP": "BHP",
    "BHP GROUP LIMITED": "BHP",
    "ZIJIN MINING": "2899.HK",
    "BANK CHINA LIMITED": "3988.HK",
    "AGRICULTURAL BANK CHINA": "1288.HK",
    "BANK COMMUNICATIONS": "3328.HK",
    "CITIC SECURITIES": "6030.HK",
    "CHINA MOBILE": "0941.HK",
    "CNOOC": "0883.HK",
    "PETROCHINA": "0857.HK",
    "SINOPEC": "0386.HK",
    "GREE ELECTRIC APPLIANCES INHEI": "000651.SZ",
    "MIDEA": "000333.SZ",
    "WUXI BIOLOGICS": "2269.HK",
    "TECHTRONIC INDUSTRIES": "0669.HK",
    "SUN HUNG KAI PROPERTIES": "0016.HK",
    "POWER ASSETS": "0006.HK",
    "WHARF REIC": "1997.HK",
    "MTR CORP": "0066.HK",
    "CK HUTCHISON HOLDINGS": "0001.HK",
    "BANK MONTREAL CANADA": "BMO",
    "OPEN TEXT": "OTEX",
    "NUTRIEN": "NTR",
    "RESTAURANT BRANDS INTERNATIONAL": "QSR",
    "RB GLOBAL": "RBA",
    "CGI INC": "GIB",
    "CAE": "CAE",
    "INTACT FINANCIAL": "IFC.TO",
    "CANADIAN UTILITIES": "CU.TO",
    "FORTIS": "FTS",
    "EMERA": "EMA.TO",
    "PEMBINA PIPELINE": "PBA",
    "CHEUNG KONG INFRASTRUCTURE": "1038.HK",
    "CHINA RESOURCES BEER": "0291.HK",
    "AGNC INVESTMENT": "AGNC",
    "WHITBREAD": "WTB.L",
    "SCHRODERS": "SDR.L",
    "INFORMA": "INF.L",
    "MARKS SPENCER": "MKS.L",
    "BERKELEY GROUP HOLDINGS": "BKG.L",
    "BAE SYSTEMS": "BA.L",
    "SHELL PLC": "SHEL",
    "BP PLC": "BP",
    "GLAXO": "GSK",
    "VODAFONE GROUP": "VOD",
    # Third-pass additions
    "HOLCIM": "HOLN.SW",
    "NATIONAL BANK CANADA": "NA.TO",
    "CIE DE SAINT GOBAIN": "SGO.PA",
    "ASSA ABLOY": "ASSA-B.ST",
    "ERSTE BANK": "EBKDY",
    "ERSTE GROUP BANK": "EBKDY",
    "CONSTELLATION SOFTWARE": "CSU.TO",
    "CONSTELLATION SOFTWARE CANADA": "CSU.TO",
    "CHUGAI PHARMACEUTICAL": "4519.T",
    "UCB": "UCB.BR",
    "KONINKLIJKE AHOLD DELHAIZE": "AD.AS",
    "EXPERIAN": "EXPN.L",
    "HEIDELBERG MATERIALS": "HEI.DE",
    "MAHINDRA": "M&M.NS",
    "MAHINDRA MAHINDRA": "M&M.NS",
    "SK SQUARE": "402340.KS",
    "TATA CONSULTANCY SERVICES": "TCS.NS",
    "SAUDI NATIONAL BANK": "1180.SR",
    "SAINT GOBAIN": "SGO.PA",
    "BANK LEUMI": "LUMI.TA",
    "BANK LEUMI LE ISRAEL BM": "LUMI.TA",
    "TITAN": "TITAN.NS",
    "ITV": "ITV.L",
    # Mid-cap European fills
    "VOLVO CAR": "VOLCAR-B.ST",
    "BEIJER REF": "BEIJ-B.ST",
    "EVOLUTION": "EVO.ST",
    "EQT": "EQT.ST",
    "INVESTOR AB": "INVE-A.ST",
    "INDUSTRIVARDEN": "INDU-A.ST",
    "SVENSKA HANDELSBANKEN": "SHB-A.ST",
    "ESSITY": "ESSITY-B.ST",
    "TELE2": "TEL2-B.ST",
    "SECURITAS": "SECU-B.ST",
    "DSV PANALPINA": "DSV.CO",
    "AP MOLLER MAERSK": "MAERSK-B.CO",
    "MAERSK": "MAERSK-B.CO",
    "ORSTED": "ORSTED.CO",
    "GENMAB": "GMAB",
    "PANDORA": "PNDORA.CO",
    "VESTAS WIND SYSTEMS": "VWS.CO",
    "ZEALAND PHARMA": "ZEAL.CO",
    "BHP GROUP LTD": "BHP",
    # Misc Asia
    "WUXI APPTEC": "2359.HK",
    "WUXI BIOLOGICS CAYMAN": "2269.HK",
    "MEITUAN DIANPING": "3690.HK",
    "TENCENT MUSIC ENTERTAINMENT": "TME",
    # Brazil
    "VALE": "VALE",
    "PETROLEO BRASILEIRO PETROBRAS": "PBR",
    "PETROBRAS": "PBR",
    "AMBEV": "ABEV",
    # Fourth-pass mid-cap fills
    "AXIS BANK": "AXISBANK.NS",
    "BANK HAPOALIM": "POLI.TA",
    "SANDOZ": "SDZ.SW",
    "SUMITOMO ELECTRIC INDUSTRIES": "5802.T",
    "GRUPO FINANCIERO BANORTE": "GBOOY",
    "BANORTE": "GBOOY",
    "IMPERIAL BRANDS": "IMB.L",
    "DANSKE BANK": "DANSKE.CO",
    "GRUPO MEXICO": "GMEXICO-B.MX",
    "SKANDINAVISKA ENSKILDA BANKEN": "SEB-A.ST",
    "KBC": "KBC.BR",
    "KUWAIT FINANCE HOUSE": "KFH.KW",
    "SWEDBANK": "SWED-A.ST",
    "SEVEN": "3382.T",
    "FIRSTRAND": "FSR.JO",
    "DAI ICHI LIFE": "8750.T",
    "SWISS LIFE": "SLHN.SW",
    "SIKA": "SIKA.SW",
    "HANWHA AEROSPACE": "012450.KS",
    "SOMPO": "8630.T",
    "GIVAUDAN": "GIVN.SW",
    "AMADEUS IT": "AMS.MC",
    "PARTNERS HOLDING": "PGHN.SW",
    "PARTNERS": "PGHN.SW",
    "LARSEN TOUBRO": "LT.NS",
    "COCA COLA EUROPACIFIC PARTNERS": "CCEP",
    "VONOVIA": "VNA.DE",
    "DELL": "DELL",
    # Mid-cap Asia
    "ZIJIN GOLD INTERNATIONAL": "2899.HK",
    "ZIJIN MINING GROUP": "2899.HK",
    "GREE ELECTRIC": "000651.SZ",
    "MIDEA GROUP": "000333.SZ",
    "BANK COMMUNICATIONS": "3328.HK",
    "AGRICULTURAL BANK CHINA": "1288.HK",
    "CITIC": "0267.HK",
    "GALAXY ENTERTAINMENT": "0027.HK",
    "BUDWEISER BREWING APAC": "1876.HK",
    "ANTA SPORTS PRODUCTS": "2020.HK",
    "JAPAN POST HOLDINGS": "6178.T",
    "JAPAN POST INSURANCE": "7181.T",
    "JAPAN POST BANK": "7182.T",
    "FUJIFILM HOLDINGS": "4901.T",
    "MS AND AD INSURANCE": "8725.T",
    "ORIX CORP": "8591.T",
    "AEON CO": "8267.T",
    "RAKUTEN": "4755.T",
    "MITSUI FUDOSAN": "8801.T",
    "MITSUBISHI ESTATE": "8802.T",
    "DAIWA HOUSE INDUSTRY": "1925.T",
    "SEKISUI HOUSE": "1928.T",
    "OBAYASHI": "1802.T",
    "TAISEI": "1801.T",
    "TOKYO ELECTRIC POWER": "9501.T",
    "CHUBU ELECTRIC POWER": "9502.T",
    "KANSAI ELECTRIC POWER": "9503.T",
    "EAST JAPAN RAILWAY": "9020.T",
    "WEST JAPAN RAILWAY": "9021.T",
    "CENTRAL JAPAN RAILWAY": "9022.T",
    "ANA HOLDINGS": "9202.T",
    "JAPAN AIRLINES": "9201.T",
    "DAI NIPPON PRINTING": "7912.T",
    "TOPPAN": "7911.T",
    "SUNTORY BEVERAGE FOOD": "2587.T",
    "AJINOMOTO": "2802.T",
    "KIRIN": "2503.T",
    "JAPAN EXCHANGE": "8697.T",
    "TOYOTA TSUSHO": "8015.T",
    "MARUBENI CORP": "8002.T",
    "ITOCHU CORP": "8001.T",
    "RICOH": "7752.T",
    "CANON": "7751.T",
    "NIDEC": "6594.T",
    "YASKAWA ELECTRIC": "6506.T",
    "SUBARU": "7270.T",
    "SUZUKI MOTOR": "7269.T",
    "MAZDA MOTOR": "7261.T",
    "NISSAN MOTOR": "7201.T",
    "MITSUBISHI MOTORS": "7211.T",
    "ISUZU MOTORS": "7202.T",
    "SHIONOGI": "4507.T",
    "ONO PHARMACEUTICAL": "4528.T",
    "NIPPON STEEL": "5401.T",
    "JFE HOLDINGS": "5411.T",
    "SUMITOMO METAL MINING": "5713.T",
    "INPEX": "1605.T",
    "TOKIO MARINE HOLDINGS": "8766.T",
    "MITSUBISHI ELECTRIC CORP": "6503.T",
    # Korea
    "KIA CORP": "000270.KS",
    "POSCO INTERNATIONAL": "047050.KS",
    "POSCO HOLDINGS INC": "PKX",
    "HYUNDAI MOBIS": "012330.KS",
    "HYUNDAI ENGINEERING CONSTRUCTION": "000720.KS",
    "SAMSUNG SDI": "006400.KS",
    "SAMSUNG BIOLOGICS": "207940.KS",
    "SAMSUNG SDS": "018260.KS",
    "SAMSUNG LIFE INSURANCE": "032830.KS",
    "SAMSUNG C T": "028260.KS",
    "SAMSUNG FIRE MARINE INSURANCE": "000810.KS",
    "KAKAO": "035720.KS",
    "NAVER": "035420.KS",
    "CELLTRION": "068270.KS",
    "AMOREPACIFIC": "090430.KS",
    "LG CHEM": "051910.KS",
    "LG H H": "051900.KS",
    "LG CORP": "003550.KS",
    "KT G": "033780.KS",
    "KB FINANCIAL": "105560.KS",
    "SHINHAN FINANCIAL": "055550.KS",
    "HANA FINANCIAL": "086790.KS",
    "WOORI FINANCIAL": "316140.KS",
    "KOREA ZINC": "010130.KS",
    "POSCO FUTURE M": "003670.KS",
    "ECOPRO": "086520.KQ",
    "ECOPRO BM": "247540.KQ",
    "DOOSAN ENERBILITY": "034020.KS",
    "HD HYUNDAI": "267250.KS",
    "HYBE": "352820.KS",
    # India additions
    "HDFC LIFE INSURANCE": "HDFCLIFE.NS",
    "ICICI PRUDENTIAL LIFE INSURANCE": "ICICIPRULI.NS",
    "STATE BANK INDIA": "SBIN.NS",
    "BHARTI": "BHARTIARTL.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "ASIAN PAINTS": "ASIANPAINT.NS",
    "INFOSYS LIMITED": "INFY",
    "ULTRATECH CEMENT": "ULTRACEMCO.NS",
    "TITAN COMPANY": "TITAN.NS",
    "POWER GRID": "POWERGRID.NS",
    "BAJAJ FINSERV": "BAJAJFINSV.NS",
    "DR REDDYS LABORATORIES": "RDY",
    "DRR REDDYS LABORATORIES": "RDY",
    "DR REDDY S LABORATORIES": "RDY",
    "ZOMATO": "ZOMATO.NS",
    "ETERNAL": "ETERNAL.NS",
    # Mid-cap UK / EU
    "WHITBREAD PLC": "WTB.L",
    "BAE SYSTEMS PLC": "BA.L",
    "TESCO PLC": "TSCO.L",
    "SAINSBURY": "SBRY.L",
    "CENTRICA": "CNA.L",
    "NATIONAL GRID": "NG.L",
    "RIGHTMOVE": "RMV.L",
    "SCOTTISH MORTGAGE INVESTMENT": "SMT.L",
    "RECKITT BENCKISER GROUP": "RKT.L",
    "DIAGEO PLC LIMITED": "DEO",
    "BURBERRY": "BRBY.L",
    "SAGE": "SGE.L",
    "ANGLO AMERICAN PLC": "AAL.L",
    "PRUDENTIAL UK": "PUK",
    # Mid-cap Australia
    "AMCOR": "AMCR",
    "AMP LTD": "AMP.AX",
    "ARISTOCRAT LEISURE": "ALL.AX",
    "ASX LTD": "ASX.AX",
    "AURIZON": "AZJ.AX",
    "BENDIGO ADELAIDE BANK": "BEN.AX",
    "BLUESCOPE STEEL": "BSL.AX",
    "BOQ": "BOQ.AX",
    "BRAMBLES": "BXB.AX",
    "BENDIGO BANK": "BEN.AX",
    "BHP GROUP LIMITED LIMITED": "BHP",
    "CHALLENGER": "CGF.AX",
    "CIMIC GROUP": "CIM.AX",
    "COCHLEAR": "COH.AX",
    "COLES": "COL.AX",
    "CORONADO GLOBAL RESOURCES": "CRN.AX",
    "DEXUS": "DXS.AX",
    "EVOLUTION MINING": "EVN.AX",
    "FLIGHT CENTRE TRAVEL": "FLT.AX",
    "GOODMAN GROUP": "GMG.AX",
    "GPT GROUP": "GPT.AX",
    "HARVEY NORMAN": "HVN.AX",
    "INSURANCE AUSTRALIA": "IAG.AX",
    "JB HI FI": "JBH.AX",
    "MEDIBANK PRIVATE": "MPL.AX",
    "MIRVAC": "MGR.AX",
    "NEWCREST MINING": "NCM.AX",
    "NORTHERN STAR RESOURCES": "NST.AX",
    "OZ MINERALS": "OZL.AX",
    "PILBARA MINERALS": "PLS.AX",
    "QANTAS": "QAN.AX",
    "RAMSAY HEALTH CARE": "RHC.AX",
    "REA GROUP": "REA.AX",
    "RINGS RIO TINTO": "RIO",
    "SANTOS": "STO.AX",
    "SCENTRE": "SCG.AX",
    "SEEK": "SEK.AX",
    "SONIC HEALTHCARE": "SHL.AX",
    "STOCKLAND": "SGP.AX",
    "SUNCORP": "SUN.AX",
    "TABCORP": "TAH.AX",
    "TELSTRA CORP": "TLS.AX",
    "TPG TELECOM": "TPG.AX",
    "WAYPOINT REIT": "WPR.AX",
    "WEST FARMERS": "WES.AX",
    "WORLEY": "WOR.AX",
    "XERO": "XRO.AX",
}


def normalize_name(s: str) -> str:
    """Normalize a company name for lookup. See module docstring."""
    s = s.upper()
    s = s.replace("'", "")
    # Strip trailing state markers like "INC / MA", "/DE", "\DE\"
    s = re.sub(r"\\[A-Z]+\\", " ", s)
    s = re.sub(r"/\s*[A-Z]+\b", " ", s)
    # Punctuation -> space
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    # Multi-word legal suffixes
    s = re.sub(r"\bPUBLIC LIMITED COMPANY\b", " ", s)
    s = re.sub(r"\bLIMITED LIABILITY COMPANY\b", " ", s)
    # Class / Series markers
    s = re.sub(r"\bCLASS [A-Z]\b|\bCL [A-Z]\b|\bSERIES [A-Z]\b", " ", s)
    # Strip single-word suffixes (loop until stable so trailing "GROUP INC" → empty)
    prev = None
    while prev != s:
        prev = s
        s = CORP_SUFFIX_RE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip()
    # Drop standalone single letters (handles "U S BANCORP" → "BANCORP")
    s = re.sub(r"\b[A-Z]\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def is_skippable(name: str) -> bool:
    upper = name.upper()
    return any(frag in upper for frag in SKIP_NAME_FRAGMENTS)


def build_name_to_ticker_map(cache_dir: Path, headers: dict, offline: bool) -> dict[str, str]:
    """Return {normalized_name: ticker}.

    Loads from cache when available; only fetches if cache misses (or --offline
    is set and cache exists).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    ct_cache = cache_dir / "sec_company_tickers.json"
    ex_cache = cache_dir / "sec_company_tickers_ex.json"

    def fetch_or_cached(url: str, cache_path: Path) -> dict:
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        if offline:
            return {}
        resp = httpx.get(url, headers=headers, timeout=30.0)
        resp.raise_for_status()
        cache_path.write_text(resp.text)
        return resp.json()

    ct = fetch_or_cached(CT_URL, ct_cache)
    ex = fetch_or_cached(CT_EX_URL, ex_cache)

    out: dict[str, str] = {}
    # Load exchange-listed file first (more authoritative for active names)
    if isinstance(ex, dict) and "fields" in ex and "data" in ex:
        fields = ex["fields"]
        for row in ex["data"]:
            rec = dict(zip(fields, row))
            norm = normalize_name(rec.get("name", ""))
            if norm and norm not in out:
                out[norm] = rec.get("ticker", "")
    # Fold in company_tickers.json for extras
    if isinstance(ct, dict):
        for entry in ct.values():
            norm = normalize_name(entry.get("title", ""))
            if norm and norm not in out:
                out[norm] = entry.get("ticker", "")
    # International additions override SEC entries because some SEC entries
    # point to OTC ADR tickers that yfinance can't pull sectors for; the
    # foreign-exchange tickers in INTL_NAME_TO_TICKER resolve cleanly.
    out.update(INTL_NAME_TO_TICKER)
    # Manual overrides win
    out.update(MANUAL_OVERRIDES)
    return out


def lookup_ticker(name: str, name_map: dict[str, str]) -> str | None:
    if is_skippable(name):
        return None
    norm = normalize_name(name)
    return name_map.get(norm)


def fetch_sectors_for_tickers(
    tickers: set[str],
    cache_path: Path,
    offline: bool,
    progress_label: str = "sectors",
    max_workers: int = 1,
) -> dict[str, str | None]:
    """For each ticker, return its yfinance sector (cached forever).

    Uses a thread pool because yfinance .info is I/O-bound and Yahoo handles
    moderate concurrency fine. The cache is persisted every save_every
    completions so a Ctrl-C / kill never loses much progress.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    cache: dict[str, dict] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    todo = sorted(t for t in tickers if t and t not in cache)
    print(f"  {progress_label}: {len(cache)} cached, {len(todo)} new")

    if not todo:
        return {t: (cache.get(t) or {}).get("sector") for t in cache}
    if offline:
        print(f"  {progress_label}: --offline, skipping {len(todo)} unfetched tickers")
        return {t: (cache.get(t) or {}).get("sector") for t in cache}

    import yfinance as yf

    rate_limit_backoff = {"value": 1.0}  # mutable so the helper can grow it

    def fetch_one(ticker: str) -> tuple[str, dict]:
        for attempt in range(3):
            try:
                info = yf.Ticker(ticker).info or {}
                rate_limit_backoff["value"] = max(1.0, rate_limit_backoff["value"] * 0.95)
                return ticker, {
                    "sector": info.get("sector"),
                    "longName": info.get("longName") or info.get("shortName"),
                }
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                # Rate-limited / 401 invalid-crumb: back off and retry
                if "Rate limited" in msg or "Too Many Requests" in msg or "Invalid Crumb" in msg or "401" in msg:
                    sleep_for = rate_limit_backoff["value"]
                    rate_limit_backoff["value"] = min(60.0, rate_limit_backoff["value"] * 2)
                    time.sleep(sleep_for)
                    continue
                return ticker, {"sector": None, "longName": None, "error": msg[:120]}
        return ticker, {"sector": None, "longName": None, "error": "rate-limited after retries"}

    save_every = 50
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(fetch_one, t) for t in todo]
        for fut in as_completed(futures):
            ticker, info = fut.result()
            cache[ticker] = info
            completed += 1
            if completed % save_every == 0 or completed == len(todo):
                cache_path.write_text(json.dumps(cache))
                print(f"    {progress_label}: {completed}/{len(todo)} fetched (backoff={rate_limit_backoff['value']:.1f}s)")
    cache_path.write_text(json.dumps(cache))

    return {t: (cache.get(t) or {}).get("sector") for t in cache}


def ticker_is_tech(ticker: str, sector_map: dict[str, str | None]) -> bool:
    return sector_map.get(ticker) in TECH_SECTORS
