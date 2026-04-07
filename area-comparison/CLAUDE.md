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

#### Living Wage
- **Source**: MIT Living Wage Calculator (livingwage.mit.edu)
- **Family configuration**: 2 Adults, 3 Children — shown for both single-earner and dual-earner households
- **Data**: single_income (annual living wage for 1 working adult), dual_income (annual living wage per working adult when both work). Hourly rate × 2,080 hours/year.
- **State data**: FIPS codes — CA=06, NY=36, GA=13, WA=53. URLs: livingwage.mit.edu/states/{FIPS}
- **City data**: Metro (CBSA) codes — SF=41860, NYC=35620, ATL=12060, SEA=42660. URLs: livingwage.mit.edu/metros/{CBSA}
- **Data vintage**: February 2026
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

#### Paid Family Leave
- **Source**: State agency websites — CA Employment Development Department (edd.ca.gov/disability/paid-family-leave), NY Workers' Compensation Board (paidfamilyleave.ny.gov), WA Employment Security Department (paidleave.wa.gov)
- **Data**: paid_leave_weeks (maximum weeks of paid bonding leave for a new child), wage_replacement_pct (% of wages replaced)
- **Notes**: GA has no state program; federal FMLA provides 12 weeks unpaid only. CA wage replacement is income-tiered (70–90% per SB 951, Jan 2025); 70% used as the representative rate for most workers. WA allows up to 16 weeks combined family+medical leave; 12 weeks reflects family leave only.
- **Levels**: State only

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

#### Poverty
- **Source**: Census ACS 2023 (1-year estimates), table S1701 (poverty status)
- **API**: api.census.gov/data/2023/acs/acs1/subject, variables S1701_C03_001E (overall poverty rate) and S1701_C03_002E (under-18 poverty rate)
- **Data**: overall_poverty_rate (% of total population below federal poverty line), child_poverty_rate (% of population under 18 below federal poverty line)
- **State data**: State-level ACS estimates (FIPS: CA=06, NY=36, GA=13, WA=53)
- **City data**: Metro area (MSA) figures for comparability with existing population data (SF-Oakland-Berkeley=41860, NYC-Newark-Jersey City=35620, Atlanta-Sandy Springs-Alpharetta=12060, Seattle-Tacoma-Bellevue=42660)
- **Levels**: State, City

#### Commute
- **Source**: Census Reporter (censusreporter.org), ACS 2024 1-year estimates
- **URLs**: censusreporter.org/profiles/04000US06-california/, etc.
- **Data**: avg_commute_minutes, drive_alone_percent, carpool_percent, public_transit_percent, walk_percent, bike_percent, work_from_home_percent
- **Levels**: State, City

#### Road Quality & Traffic Congestion
- **% Roads in Poor/Mediocre Condition**: TRIP national transportation research nonprofit (tripnet.org), based on FHWA Highway Statistics 2023 (tables HM-63 and HM-64). Percentage of major state- and locally-owned roads and highways rated in poor or mediocre condition (combined). CA: 50% (from "Keeping California Mobile" Sep 2025), NY: 45% (from "New York Transportation by the Numbers" Jan 2025), GA: 23% (from TRIP Key Facts July 2025), WA: 61% (from TRIP Key Facts July 2025). Note: Full reports for CA and NY break out poor (CA 28%, NY 25%) vs. mediocre separately; GA and WA fact sheets only provide the combined figure, so combined "poor or mediocre" is used for all states for consistency.
- **Annual Hours of Delay per Auto Commuter**: Texas A&M Transportation Institute (TTI) Urban Mobility Report 2025 (2024 data). Metro-level congestion data. SF-Oakland: 134 hrs (#2 nationally), NY-Newark: 99 hrs (#3), Atlanta: 87 hrs (#9 tied), Seattle: 87 hrs (#9 tied). Source: static.tti.tamu.edu/tti.tamu.edu/documents/mobility-report-2025.pdf
- **Traffic Fatality Rate per 100K**: NHTSA Fatality Analysis Reporting System (FARS) 2022 (final release). Total traffic fatalities per 100,000 population. State: CA 11.3, NY 6.0, GA 16.5, WA 9.4. City: SF County 5.2 (42 fatalities / 808K pop), NYC 5-borough 2.9 (238 / 8.34M), Fulton County 15.0 (160 / 1.07M), King County 6.6 (150 / 2.27M). Cross-validated against IIHS Fatality Facts state-by-state data. FARS is already used in this project for cyclist fatalities.
- **Levels**: State (poor_road_pct, traffic_fatality_rate), City (annual_delay_hours, traffic_fatality_rate)

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

### Arts & Culture Section

#### Museums
- **Source**: Wikipedia "List of museums in [city]" pages, cross-referenced with TripAdvisor and Google Maps
- **Inclusion criteria**: Nationally/internationally recognized museums with substantial permanent collections or exhibition programs. Includes art, science, natural history, history, and notable specialty museums. Excludes small galleries, house museums, and university-only galleries (though university-affiliated museums with national recognition are included, e.g., Cantor Arts Center, Carlos Museum, Henry Art Gallery).
- **Data**: major_museums (count), museums_per_million (major museums per million metro population), list (array of {name, full, type})
- **Per-capita denominator**: Metro population from existing population.total_population
- **Levels**: City only

#### Performing Arts
- **Source**: Wikipedia, venue websites
- **Inclusion criteria**: Major performing arts venues with 500+ seats used for professional productions — opera houses, symphony halls, large theaters, performing arts centers. Excludes comedy clubs, small black-box theaters, movie theaters, and sports arenas.
- **Data**: major_venues (count), venues_per_million (per million metro population), list (array of {name, type, seats})
- **Notes**: NYC count (55) includes all 41 designated Broadway theaters (each 500+ seats) plus 14 major institutional venues (Lincoln Center complex, Carnegie Hall, BAM, Radio City, etc.). The "Notable" list shows only the most significant venues, not all 55.
- **Levels**: City only

#### Michelin Dining
- **Source**: Michelin Guide (guide.michelin.com), verified via Wikipedia and culinary press
- **Guide coverage**: California (covers SF Bay Area — long-standing), New York (long-standing), American South (covers Atlanta — added 2023). Seattle/Washington State is NOT covered by the Michelin restaurant guide (only hotel keys awarded 2024).
- **Data**: three_star, two_star, one_star, bib_gourmand (raw counts), starred_per_million (total 1+2+3 star per million metro pop), bib_per_million (Bib Gourmand per million metro pop)
- **Data vintage**: 2025 guide year (California ceremony Jun 2025, NYC/Northeast Nov 2024, American South Nov 2025)
- **Notes**: SF Bay Area Bib Gourmand count (~55) is estimated from the California statewide total (~119) using historical Bay Area share (~47%). Seattle shows all zeros with a note that no Michelin restaurant guide covers the metro.
- **Levels**: City only

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

#### Water Quality
- **Contaminants Detected / Above Health Guidelines**: EWG Tap Water Database (ewg.org/tapwater), 2021-2023 testing data. Per-utility contaminant counts. PWS IDs: CA3810001 (SF Regional Water System), NY7003493 (NYC System), GA1210001 (Atlanta), WA5377050 (Seattle Public Utilities). EWG health guidelines are stricter than EPA legal limits; no system exceeds EPA MCLs. Seattle total contaminants count (15) is estimated from individually identified EWG subpages, as the main page was inaccessible.
- **Lead (90th percentile)**: City annual Consumer Confidence Reports (CCRs), required by EPA for all public water systems. SF: 5 ppb (2024 CCR). NYC: 1.9 ppb (2023 sampling in 2024 CCR). ATL: ~8 ppb (Hydroviv analysis of ~2020 sampling data). SEA: 4 ppb (recent monitoring). EPA action level is 15 ppb.
- **Water Hardness**: City CCRs and USGS data. All four cities have soft water (0-60 ppm range). SF: ~25 ppm (Hetch Hetchy blend), NYC: ~31 ppm (1.8 grains/gallon citywide avg), ATL: ~22 ppm, SEA: ~22 ppm.
- **Avg Monthly Water Bill**: City utility rate schedules and survey data (LawnStarter, Bluefield Research). Water + sewer combined for typical single-family residential usage. SF: $142/mo, NYC: $98/mo, ATL: $105/mo, SEA: $53/mo.
- **SDWA Violations / System**: America's Health Rankings (americashealthrankings.org), sourced from EPA SDWIS/ECHO (2024). Average health-based violations per community water system. National average: 2.5. CA: 2.3, NY: 1.9, GA: 2.3, WA: 1.8.
- **Water Sources** (displayed as tooltip on topic header): SF — Hetch Hetchy Reservoir (Sierra Nevada snowmelt, unfiltered). NYC — Catskill/Delaware & Croton Watersheds (unfiltered for Catskill/Delaware). ATL — Chattahoochee River. SEA — Cedar River (~70%) & South Fork Tolt River (~30%), Cascade Range.
- **Levels**: State (SDWA violations only), City (all other metrics)

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

#### Voter Turnout
- **Source (2010-2022)**: UF Election Lab (election.lab.ufl.edu), Dr. Michael McDonald — authoritative VEP (Voting Eligible Population) turnout rates. Downloaded directly from CSV files: Turnout_2022G_v0.1.csv, Turnout_2020G_v1.1.csv, Turnout_2018G_v1.0.csv, Turnout_2016G_v1.0.csv, Turnout_2014G_v1.0.csv, Turnout_2012G_v1.0.csv, Turnout_2010G_v1.0.csv.
- **Source (2002-2008, 2024)**: Ballotpedia (ballotpedia.org/Voter_turnout_in_United_States_elections) — VEP turnout percentages sourced from the US Elections Project.
- **Metric**: VEP turnout = total ballots counted / Voting Eligible Population. VEP excludes non-citizens and ineligible felons from the voting-age population.
- **Chart**: Time series of VEP turnout (2002-2024), presidential elections as solid lines, midterms as dashed lines. Georgia starts at 2004 (2002 data not available from Ballotpedia).
- **Levels**: State only (county-level VEP data not readily available from these sources)

#### State Policy Environment
- **Cannabis Legality**: NORML (norml.org/laws), verified against state statutes. Status categories: Legal (adult-use recreational), Medical Only (medical program only), Decriminalized (reduced penalties), Illegal (criminal penalties). Current as of 2025.
- **Gun Law Grade**: Giffords Law Center Annual Gun Law Scorecard 2024 (giffords.org/lawcenter/resources/scorecard/). Letter grade (A through F) based on comprehensive evaluation of state gun legislation across background checks, permits, extreme risk laws, domestic violence protections, and other policy areas.
- **LGBTQ+ Policy Tally**: Movement Advancement Project (MAP) Equality Maps (lgbtmap.org/equality-maps). Composite score (0–47 possible points) covering non-discrimination laws, religious exemptions, family law, youth protections, healthcare, criminal justice, and identity document policies. Higher = more protective. Current as of 2025.
- **Death Penalty Status**: Death Penalty Information Center (deathpenaltyinfo.org). Categories: Abolished (removed by law or court ruling), Moratorium (executive halt on executions), Active (executions carried out). Current as of 2025.
- **Minimum Paid Sick Days**: National Partnership for Women & Families (nationalpartnership.org) and state labor department websites. Minimum annual paid sick leave days required by state law. States without a mandate show 0.
- **Abortion Access**: Guttmacher Institute (guttmacher.org), Center for Reproductive Rights, and state law tracking. Categories: No Limit (no gestational ban), Viability (~24 weeks), Restricted (banned at or before ~6 weeks). Post-Dobbs (2022) landscape. Current as of 2025.
- **Levels**: State only

### Religion Section

#### Religious Affiliation (Christian, Other Religion, Unaffiliated)
- **Source (states)**: Pew Religious Landscape Study, compiled via uscanadainfo.com (sources: Pew Research Center, US Census, ARDA)
- **Source (cities)**: Pew Religious Landscape Study 2014 and 2023-24 (metro-level data)
- **Data**: christian_percent (all Christian traditions), other_religion_percent (all non-Christian religions: Jewish, Muslim, Hindu, Buddhist, Sikh, etc.), unaffiliated_percent (atheist, agnostic, "nothing in particular")
- **City data**: SF and SEA from Pew 2023-24. NYC from Pew 2014. ATL from Pew 2023-24.
- **Levels**: State, City

#### Religiosity (Importance, Attendance)
- **Source**: Pew Religious Landscape Study 2014 (via Wikipedia "List of U.S. states and territories by religiosity")
- **Data**: religion_important_percent (% saying religion is "very important"), weekly_attendance_percent (% attending weekly or more)
- **Levels**: State only (metro-level religiosity data not reliably available)

#### Religious Diversity Index
- **Method**: Computed using Herfindahl-based formula: RDI = 10 × (1 − Σ(share_i²)) with 4 categories (Protestant, Catholic, Other Religion, Unaffiliated). Scale 0–10, higher = more diverse.
- **State data**: Computed from detailed denomination breakdown (Evangelical, Mainline, Historically Black, Catholic, Other Christian → combined into Protestant and Other Christian)
- **City data**: Computed from Christian/Other/Unaffiliated shares with estimated Protestant/Catholic split
- **Levels**: State, City

### Civic & Community Section

#### Volunteering
- **Source**: AmeriCorps CPS Civic Engagement and Volunteering (CEV) Supplement 2023, conducted by U.S. Census Bureau in partnership with AmeriCorps (September 2023, covering Sep 2022–Sep 2023)
- **Data**: formal_volunteer_rate (% who volunteered through/for an organization), informal_helping_rate (% who helped neighbors informally), avg_hours_per_volunteer (total hours / number of volunteers, computed from state profile data)
- **State profiles**: americorps.gov/about/our-impact/volunteering-civic-life/{state} (ca, ny, ga, wa)
- **API dataset**: data.americorps.gov/resource/4r6x-re58.json ("2017-2023 CEV Findings: State-Level Rates of All Measures")
- **Notes**: Median volunteer hours are only published at the national level (24 hours in 2023). State-level averages are computed from total hours / volunteer count on state profile pages. NY state profile shows 21.7% formal rate vs. 25.5% in the API dataset; state profile value used as it is the official public-facing figure.
- **Levels**: State only

#### Charitable Giving
- **Source**: IRS Statistics of Income (SOI), Tax Year 2022 — Historic Table 2 ("Individual Income Tax Returns with Itemized Deductions")
- **Data**: charitable_pct_agi (total charitable deductions / total AGI across all filers), charitable_return_pct (% of returns claiming charitable deduction)
- **Download**: irs.gov/pub/irs-soi/22in55cmcsv.csv
- **Cross-reference**: Tax Policy Center compilation (taxpolicycenter.org, Tax Year 2021)
- **Notes**: Post-2017 TCJA nearly doubled the standard deduction, dramatically reducing itemizers (~7.6% of returns nationally claim charitable deductions vs. ~30% pre-TCJA). This metric now primarily reflects higher-income giving behavior. CA has unusually high itemization rate (12.4%) driven by high cost of living / property values.
- **Levels**: State only

#### Libraries
- **Source**: IMLS Public Libraries Survey (PLS), Fiscal Year 2022 (released June 2024)
- **Data file**: imls.gov/sites/default/files/2024-06/pls_fy2022_csv.zip, file PLS_FY22_AE_pud22i.csv
- **Data**: library_visits_per_capita (VISITS / POPU_LSA), libraries_per_100k ((CENTLIB + BRANLIB + BKMOB) / POPU_LSA * 100000), library_programs_per_1k (TOTPRO / POPU_LSA * 1000)
- **State data**: Aggregated from all library systems within each state
- **City data**: SF Public Library, NYC (NYPL + Brooklyn PL + Queens Borough PL combined), Atlanta-Fulton County Library System, Seattle Public Library
- **Notes**: NY state programs/1K (18.89) and NYC programs/1K (12.70) are notably high. Seattle programs/1K (1.11) is low — only 849 total programs reported for FY 2022, possibly reflecting reporting methodology or post-COVID recovery timing.
- **Levels**: State, City

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
