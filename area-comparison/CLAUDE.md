# Area Comparison

This is a tool that compares statistical information between the states California, New York, and Georgia; the cities San Francisco, New York City, and Atlanta; and neighborhoods North Panhandle+Anza Vista, Greenwich Village, and Virginia Highland+Morningside - Lenox Park. The tool allows you to expand/collapse different 'rows', corresponding to things like population density or educational attainment. At the top, you can select the granularity (state/city/neighborhood). The source of the data comes from various online sources, first scraped and then extracted. For cities that have data for multiple neighborhoods, combine them into a single 'mega neighborhood'.

## Data Sources by Metric

### Demographics Section

#### Population, Age, Race & Ethnicity, National Origin, Marital Status
- **Source**: Statistical Atlas (statisticalatlas.com)
- **Method**: HTML pages scraped via `fetch_data.py`, data extracted via Claude Sonnet API calls
- **Levels**: State, City (metro for Atlanta), Neighborhood
- **URLs**: See list at bottom of this file
- **Notes**: City populations use metro area figures from Wikipedia for comparability (SF-Oakland-Berkeley MSA, NYC-Newark-Jersey City MSA, Atlanta-Sandy Springs-Alpharetta MSA). Neighborhood data combines paired neighborhoods (NP+AV, VH+ML) via population-weighted averaging. Mixed+Other race is the sum of mixed and other categories. Separated/Divorced/Widowed is combined. National origin top_origins percentages are expressed as % of total population (not % of foreign born).

#### Net Domestic Migration
- **Source**: Census Bureau Population Estimates Program (PEP), Vintage 2024
- **Data**: Net domestic migration rate per 1,000 population (July 2023–July 2024). Negative = more people leaving for other US locations than arriving. Excludes international migration.
- **State data**: Direct from PEP state-level tables (NST-EST2024-ALLDATA.csv, field RDOMESTICMIG2024)
- **City data**: County-level PEP (CO-EST2024-ALLDATA.csv). SF County, NYC 5 boroughs summed, Fulton County for ATL, King County for SEA.
- **Levels**: State, City

#### Population Growth
- **Source**: FRED (Federal Reserve Economic Data)
- **Series**: State: CAPOP, NYPOP, GAPOP. City: CASANF0POP (SF County), NYNEWY1POP+NYKING7POP+NYQUEE1POP+NYBRON5POP+NYRICH5POP (NYC 5 boroughs summed), GAFULT1POP (Fulton County)
- **Method**: FRED API with key, annual frequency, decennial Census years only (1970-2020) to avoid intercensal estimate discontinuities
- **Levels**: State, City
- **Index**: Normalized to 100 at 1970

### Economy Section

#### Household Income
- **Source**: Statistical Atlas
- **Method**: Same as demographics scraping
- **Levels**: State, City, Neighborhood

#### Minimum Wage
- **Source**: minimumwage.com, state/city labor department websites
- **Levels**: State, City

#### Cost of Living (Price Level / RPP)
- **Source**: FRED Regional Price Parities
- **Series**: Metro: RPPALL41860 (SF), RPPALL35620 (NYC), RPPALL12060 (ATL). State: CARPPALL, NYRPPALL, GARPPALL
- **Method**: FRED API, 2024 values
- **Levels**: State, City

#### Inequality (Gini Coefficient)
- **Source**: Census ACS (widely reported values)
- **Levels**: State, City

#### Tax Burden
- **Source**: SmartAsset tax calculators, state tax authority websites
- **Notes**: Income tax is top marginal state+city. Sales tax is combined state+local. Property tax is effective rate. Capital gains matches income rate for all three states.
- **Levels**: City only

#### Tech & Startups
- **VC Funding**: Crunchbase/Carta reports (2024)
- **Unicorns**: Failory/Crunchbase
- **SWE Compensation**: Levels.fyi (median and 90th percentile total comp)
- **Patents**: USPTO FY2024 state-level filings
- **Fortune 500 HQs**: Wikipedia List of largest companies
- **Levels**: City only

#### Educational Attainment, Employment Status
- **Source**: Statistical Atlas
- **Method**: Same as demographics scraping
- **Levels**: State, City, Neighborhood

#### Commute
- **Source**: Census Reporter (censusreporter.org), ACS 2024 1-year estimates
- **URLs**: censusreporter.org/profiles/04000US06-california/, etc.
- **Data**: avg_commute_minutes, drive_alone_percent, carpool_percent, public_transit_percent, walk_percent, bike_percent, work_from_home_percent
- **Levels**: State, City

### Lifestyle Section

#### Weather & Time
- **Source**: WeatherSpark (weatherspark.com)
- **URL**: https://weatherspark.com/compare/y/557~23912~15598/Comparison-of-the-Average-Weather-in-San-Francisco-New-York-City-and-Atlanta
- **Data**: Monthly average high/low temps (°F), arid_percent (% days with dew point below 65°F), clear_sky_percent (% time clear/mostly clear/partly cloudy), dry_days_per_month (30 minus rainy days)
- **Levels**: City only

#### Walkability
- **Source**: WalkScore (walkscore.com)
- **Method**: WebFetch of individual neighborhood/city pages
- **Data**: Walk Score, Transit Score, Bike Score (0-100 each)
- **Neighborhood notes**: NP+AV averaged from individual neighborhood scores. GV uses West Village as proxy (WalkScore doesn't have a Greenwich Village page). VH+ML averaged from individual scores.
- **Levels**: City, Neighborhood
- **Bike Network Score**: PeopleForBikes Bicycle Network Analysis 2025 (cityratings.peopleforbikes.org). BNA score (0-100) + percentile among 2,901 cities. City only.
- **Cyclist Fatality Rate**: Annualized cyclist fatalities per 10K bike commuters. Fatalities from NHTSA FARS 2014-2023 (10-year sum). Commuter denominator from Census ACS. City only. Atlanta data includes FARS bulk CSV data for years not in the 500K+ city fact sheet table.

#### Parks & Green Space
- **Source**: Trust for Public Land ParkScore 2025 (parkscore.tpl.org)
- **Data**: ParkScore rank and rating (0-100), % residents within 10-min walk of park, parkland as % of city area
- **Tree Canopy Coverage**: Percentage of city land area covered by tree canopy. Sources: city urban forest assessments (SF Planning Department, NYC Urban Forest Plan, Georgia Tech Urban Tree Canopy Assessment, City of Seattle 2021 Tree Canopy Assessment) and Tree Equity Score (treeequityscore.org).
- **Levels**: City only

#### Sports
- **Teams**: Common knowledge, verified against Wikipedia
- **Attendance**: ESPN (NFL/NBA/MLB), Wikipedia (NHL/MLS). Most recent full regular season averages. Multi-team cities use average across teams.
- **Levels**: City only

#### K-12
- **HS Graduation Rate**: 4-year adjusted cohort graduation rate. State: NCES / state DOE. City: district-level (SFUSD, NYC Public Schools, Atlanta Public Schools).
- **Pre-K Enrollment**: % of 4-year-olds in state-funded pre-K. Source: NIEER State of Preschool Yearbook 2024.
- **NAEP Scores**: Average scale scores from National Assessment of Educational Progress (2024). 4th and 8th grade, math and reading. State: all 3 states. City: NYC and Atlanta via TUDA program; SF not available (SFUSD not a TUDA participant).
- **Let Grow Ratings**: Two categorical ratings from Let Grow (letgrow.org/states/): CPS/Neglect Law Survey (when CPS can intervene) and Criminal Law Survey (laws enforced by police/courts). Three-level scale: "protects" (green, law protects children's independence), "discretion" (beige, law is open-ended), "punitive" (red, law is punitive toward independence). GA has "protects" on both (2025 Reasonable Childhood Independence law). CA, NY, WA all have "discretion" on both.
- **Levels**: State (all metrics), City (graduation rate + NAEP where available)

#### College Affordability (under Universities > Public)
- **Avg Net Price**: Average annual net price at public 4-year institutions after grants/scholarships, enrollment-weighted. Source: College Scorecard (2022-23).
- **Avg Student Debt**: Median federal loan debt at graduation from public 4-year institutions. Source: College Scorecard (2022-23).
- **Levels**: State only

#### Universities
- **Rankings**: US News Best National Universities 2025. Schools not in national rankings have estimated ranks marked with `est:true` and displayed in italics with "~" prefix.
- **Enrollment**: Undergraduate and graduate enrollment (Fall 2024) from US News and institutional websites, shown in tooltip on hover.
- **Cost**: Annual cost of attendance (tuition + fees + room & board, in-state for public, no aid) for 2024-2025, from university websites. Shown in tooltip.
- **Structure**: Split into Public and Private sub-sections, top 3 each. Only schools with undergraduate programs; no HBCUs. Out-of-state schools in a metro (e.g. Rutgers in NYC) marked with asterisk.
- **Levels**: State, City

#### Health
- **AQI**: EPA Annual AQI by County 2024 (CSV: aqs.epa.gov/aqsweb/airdata/annual_aqi_by_county_2024.zip). State values are median of county medians. City values use county data (SF County, 5-borough avg for NYC, Fulton County for ATL).
- **Obesity/Overweight/Smoking/Drinking/Exercise/Sedentary**: CDC BRFSS 2023 via API (data.cdc.gov/resource/hn4x-zwk7.json), stratificationcategory1='Total'
- **Drug Overdose Death Rate**: CDC NCHS Quarterly Vital Statistics (data.cdc.gov, dataset 489q-934x). Age-adjusted rate per 100,000, 12 months ending Q1 2023. ICD-10 codes X40-X44, X60-X64, X85, Y10-Y14.
- **Firearm Death Rate**: Same CDC NCHS source. Age-adjusted rate per 100,000. ICD-10 codes W32-W34 (accidental), X72-X74 (suicide), X93-X95 (homicide), Y22-Y24 (undetermined), Y35.0 (legal intervention). All intents combined.
- **Levels**: State (all metrics), City (AQI only)

#### Healthcare
- **Life Expectancy**: State: Wikipedia List of U.S. states by life expectancy (2021). City: County Health Rankings (county-level).
- **Physicians per 100K**: HRSA State of the Health Workforce Report 2024
- **Uninsured Rate**: Census ACS. State-level from SHADAC 2024 ACS report. City-level from county ACS data.
- **Infant Mortality**: March of Dimes PeriStats (2023)
- **Levels**: State (all), City (life expectancy + uninsured + AQI only)

#### Natural Hazard Risk
- **Source**: FEMA National Risk Index (NRI) v1.20 (December 2025), hazards.fema.gov/nri
- **Data**: Composite Risk Index (0–100 percentile among US counties) plus individual hazard scores for Earthquake, Wildfire, Flooding (inland), Hurricane, and Tornado. null values for hazards that don't apply to a region (e.g., Hurricane is null for CA and WA).
- **State data**: Unweighted averages of all county scores within each state.
- **City data**: County-level scores. SF County, 5-borough average for NYC, Fulton County for ATL, King County for SEA.
- **Method**: Queried via ArcGIS REST API at services.arcgis.com.
- **Levels**: State, City

### Infrastructure Section

#### Homeownership Rate
- **Source**: Census ACS table B25003 (Tenure), 2023 ACS 5-Year estimates
- **Data**: Percentage of occupied housing units that are owner-occupied.
- **State/City data**: Census ACS place-level and state-level estimates.
- **Neighborhood data**: Estimated from Statistical Atlas neighborhood-level data and Census tract aggregation. NP+AV population-weighted average (~14% NoPa, ~34% AV). Mercer Island uses place-level data.
- **Levels**: State, City, Neighborhood

#### Housing
- **Home Price Index (cities)**: FRED FHFA All-Transactions House Price Index. Series: SFXRSA, NYXRSA, ATXRSA. Normalized to 100 at year 2000, annual values 2000-2024.
- **Home Price Index (neighborhoods)**: Zillow ZHVI (all homes, middle tier). Downloaded CSV: Neighborhood_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv. RegionIDs: NP 417522, AV 417521, GV 195133, VH 275890, ML 274592. Normalized to 100 at 2000, annual Jan values 2000-2025. NP+AV and VH+ML averaged.
- **Rent Index (cities)**: FRED CPI Rent of Primary Residence (SA). Series: CUUSA422SEHA (SF), CUUSA101SEHA (NYC), CUUSA319SEHA (ATL). Normalized to 100 at 2000.
- **CAGR**: Computed from index start/end values over 24-25 years.
- **Typical Home Values (neighborhoods)**: Zillow ZHVI bedroom-specific CSVs, average of last 12 months. 2BR: Neighborhood_zhvi_bdrmcnt_2_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv. 3BR: bdrmcnt_3. 4BR: bdrmcnt_4. NP+AV and VH+ML averaged where both available. AV missing from 3BR (uses NP only). NP+AV both missing from 4BR.
- **Levels**: City (price+rent index, CAGR), Neighborhood (price index, CAGR, 2BR/3BR/4BR values)

#### Airports
- **Source**: Wikipedia (passenger counts, international percentages from airport annual reports and BTS)
- **Data**: Per-airport code, full name, total passengers (millions), international percent (2024)
- **Levels**: City only

#### Crime
- **Source**: Wikipedia compilation of FBI UCR data (2023)
- **Data**: Violent crime rate per 100K, property crime rate per 100K (2023)
- **Levels**: City only

#### Homelessness
- **Source**: HUD Point-in-Time (PIT) Count, January 2024 (hudexchange.info/resource/3031/pit-and-hic-data-since-2007/)
- **Data**: Total homeless count (pit_count), homeless per 10K population (per_10k), % unsheltered (unsheltered_pct).
- **CoC mapping**: SF = CA-501, NYC = NY-600, Atlanta = GA-500, Seattle/King County = WA-500.
- **State data**: State-level aggregates from HUD data / AHAR 2024.
- **City data**: CoC-level PIT counts. Per-10K rates use metro population as denominator (from existing DATA), so city rates may be understated since CoCs cover smaller areas than full metros.
- **Notes**: PIT count is a single-night snapshot (last 10 days of January) and is an inherent undercount. NY has very high count (158K) but very low unsheltered % (3.6%) due to right-to-shelter mandate.
- **Levels**: State, City

#### Internet / Broadband
- **Source**: FCC Broadband Data Collection (BDC) via broadbandmap.fcc.gov, BroadbandNow (broadbandnow.com)
- **Data**: broadband_pct (% of locations with 100+ Mbps download access), fiber_pct (% of locations with fiber-optic internet access).
- **Levels**: State, City

#### Public Transit
- **Source**: National Transit Database (NTD), agency reports (MTA, SFMTA, BART, MARTA), 2024 data
- **Transit Score**: WalkScore transit score (0-100), same source as Walkability section
- **Mode breakdown**: Per-mode rows (Heavy Rail, Light Rail, Commuter Rail, Bus) showing system name and annual ridership in millions. Tooltips on system names show full names; tooltips on ridership show route miles/stations (rail) or routes (bus).
- **Notes**: SF: BART (heavy rail) + Muni Metro (light rail) + Muni Bus. NYC: Subway (heavy rail) + LIRR + Metro-North (commuter rail) + MTA Bus. ATL: MARTA Rail (heavy rail) + MARTA Bus. Raw numbers shown without per-capita normalization due to inconsistent service area boundaries.
- **Levels**: City (all), Neighborhood (transit score only)

### Politics Section

#### Presidential Elections
- **Source**: Wikipedia individual state/city election pages
- **State data**: CA from individual year pages (2024_United_States_presidential_election_in_California, etc.). NY from United_States_presidential_elections_in_New_York. GA from United_States_presidential_elections_in_Georgia.
- **City data**: SF from CA Secretary of State historical county data. NYC from Wikipedia Politics_of_New_York_City. ATL from Wikipedia Fulton_County,_Georgia#Politics.
- **Range**: 1988-2024 (10 elections)
- **Levels**: State, City

#### Congressional Delegation
- **Source**: Wikipedia congressional delegation pages + individual Congress pages
- **House seats**: From Wikipedia United_States_congressional_delegations_from_California/New_York/Georgia
- **Senate seats**: From Wikipedia List_of_United_States_senators_from_California/New_York/Georgia
- **Range**: 107th-119th Congress (2001-2025)
- **Levels**: State only

## Statistical Atlas Source URLs

https://statisticalatlas.com/neighborhood/Georgia/Atlanta/Morningside---Lenox-Park/Overview
https://statisticalatlas.com/neighborhood/Georgia/Atlanta/Virginia-Highland/Overview
https://statisticalatlas.com/neighborhood/California/San-Francisco/North-Panhandle/Overview
https://statisticalatlas.com/neighborhood/California/San-Francisco/Anza-Vista/Overview
https://statisticalatlas.com/neighborhood/New-York/New-York/Greenwich-Village/Overview

https://statisticalatlas.com/place/New-York/New-York/Overview
https://statisticalatlas.com/place/California/San-Francisco/Overview
https://statisticalatlas.com/metro-area/Georgia/Atlanta/Overview

https://statisticalatlas.com/state/California/Overview
https://statisticalatlas.com/state/New-York/Overview
https://statisticalatlas.com/state/Georgia/Overview

Topics scraped per area: Population, Race-and-Ethnicity, Household-Income, Educational-Attainment, Employment-Status, Age-and-Sex, Marital-Status, National-Origin
