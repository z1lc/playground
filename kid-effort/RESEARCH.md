# Birth to Pre-K Effort Map: research notes

Research done 2026-11-16. Every value the page shows lives in `STAGES` and `LANES` in `index.html`. This file records where each number came from and where judgment filled a gap.

## Ground rules

- **Typical, not checklist, ages.** CDC's 2022 "Learn the Signs. Act Early." milestones mark the age by which about 75% of children can do something (Zubler 2022), not the typical age. For motor skills the page uses WHO Motor Development Study medians and windows. CDC items are used for "by this age, most can…" statements.
- **Healthy, full-term child.** Every range is for a typical child; real kids vary widely.
- **Per-day diaper counts and solo-play times are estimates.** No health authority publishes either (see those lanes below).
- **No "sleep regressions."** No peer-reviewed study supports regressions at fixed ages; a PubMed search for "sleep regression" in infant or toddler studies finds nothing. The page talks about temporary setbacks around milestones and illness instead. The one real signal is that learning to crawl goes with a temporary rise in night waking.
- **No vaccine schedule year.** A federal court suspended CDC's January 2026 schedule revision, and that ruling is under appeal, so the page names visit ages and broad vaccine rounds but never a schedule year.

## The effort score (1–10)

Anchors: **1** = you could leave them alone for up to an hour; **10** = you can't look away for more than a few seconds. The score blends supervision (how closely you must watch) with hands-on work (feeds, changes, nights). Supervision dominates, but a newborn still scores high on hands-on work alone. These scores are judgment calls; no study scores "parenting effort" by age.

| Stage | Score | Why |
|---|---|---|
| 0–3 mo | 8 | Supervision is low: they can't move, and a back-to-sleep crib is safe. Hands-on work is at its maximum: 8–12 feeds, 2–4 night wakings, about 2 hours a day of crying. |
| 3–6 mo | 6 | Nights stretch (0–2 wakings), crying falls, and they'll play on a mat for a few minutes. Rolling makes raised surfaces unsafe. |
| 6–9 mo | 7 | Crawling arrives (WHO median 8.3 mo), everything gets mouthed, and the whole-house proofing has to be done. |
| 9–12 mo | 8 | Pulling up and cruising. The peak of mouthing combined with mobility. |
| 12–18 mo | 9 | Walking alone (WHO median 12.0 mo) roughly doubles their reach. Solo play lasts seconds per toy. |
| 18–24 mo | 10 | Running and climbing, no sense of danger, tantrums in 87% of children. Supervision guidance is "continuous, close" (Morrongiello & Schell 2010). |
| 2–3 y | 7 | Better judgment and words, but tantrums peak (91%) and potty training is a heavy temporary load. |
| 3–4 y | 5 | Day-trained, conversational, can play alone 15–30 minutes. |
| 4 y | 3 | Long stretches of solo play. Supervision is mostly about water, streets and cars. |

## Stage boundaries

Nine stages on a month axis starting at birth: 3-month buckets through the first year, 6-month buckets in the second, then yearly. The last bucket is the wait between the 4th birthday and the first day of Pre-K, so it depends on the due date, which the page lets you set from a link in the intro. The default is the next June 20; it is only saved once you pick a date.

How the page works out the Pre-K start (`prekPlan` in `index.html`):

- **Cutoff:** a child born on or before September 1 (month and day) is 4 by the cutoff in the year they turn 4, and starts Pre-K that August. A child born after September 1 starts the following August.
- **First day:** assumed to be August 1. Each provider sets its own first day; most follow the local school district, which in metro Atlanta starts around then. A later first day only widens the last bar by days.
- **Months:** days from birth to that August 1, divided by 30.44.

What that means by birthday:

- **September 2 to July 31:** turns 4 before Pre-K starts, so the last bar runs from 48 months to the start. For example, June 20 gives 42 days, about 1.4 months; September 9 gives 327 days, about 10.7 months.
- **August 1 to September 1:** starts Pre-K on or just before the 4th birthday (as young as 3 years 11 months). The 3-year stage ends at Pre-K and the 4-year bar disappears.

Within two weeks of September 1, the page warns that arriving early or late changes the Pre-K year.

## Load levels (0–5) per lane

Each cell's shade is a 0–5 load level. Within a lane, levels compare stages against each other; they are not comparable across lanes. 0 = no load, 5 = the heaviest that lane gets.

### Night wakings
- 0–3 mo **2–4×**: feeds every 2–3 h around the clock. In a pooled review, the mean at 0–2 mo is 1.7 wakings, with a range of 0–3.4 (Galland 2012). About half of babies sleep midnight to 5 am by 3 months (Henderson 2010).
- 3–6 mo **0–2×**: the pooled mean is 0.8. The AAP says most formula-fed babies drop middle-of-the-night feeds by 2–4 months. The draft said 1–3×.
- 6–9 mo **0–2×**: in the NICHD cohort at 6 mo, 34% woke their mother every night and 66% about one night a week (Weinraub 2012). The draft said 1–2×.
- 9–12 and 12–18 mo **0–1×**: the pooled mean is 1.1 at 7–11 mo and 0.7 at 1–2 y. At 12 mo, 28% don't sleep 6 h straight (Pennestri 2018).
- 18–24 mo **0–1×**: in the NICHD data, both groups woke about 1 night a week by 24 mo.
- 2–3 y **0–1×**: 36.3% had frequent night waking at 2½ (Petit 2007). The draft said "rare".
- 3–4 y and 4 y **occasional**: frequent waking is still at 13.2% at age 6, sleep terrors are common, and bedwetting wakes parents. No study gives a figure for exactly 3–4½ years, so these two values are interpolated.

Sources:
- AASM consensus: https://pmc.ncbi.nlm.nih.gov/articles/PMC4877308/
- Galland 2012: https://www.nationaljewish.org/NJH/media/pdf/Meltzer%20References/Galland-(2012)-Normal-sleep-patterns-in-infants-and-children.pdf
- AAP: https://www.healthychildren.org/English/ages-stages/baby/sleep/Pages/getting-your-baby-to-sleep.aspx
- AAP: https://www.healthychildren.org/English/ages-stages/baby/formula-feeding/Pages/Amount-and-Schedule-of-Formula-Feedings.aspx
- Henderson 2010: https://pubmed.ncbi.nlm.nih.gov/20974775/
- Pennestri 2018: https://pubmed.ncbi.nlm.nih.gov/30420470/
- Pennestri 2020: https://pubmed.ncbi.nlm.nih.gov/33130350/
- Weinraub 2012: https://pubmed.ncbi.nlm.nih.gov/22448981/
- Petit 2007: https://pubmed.ncbi.nlm.nih.gov/17438080/
- Crawling and night waking: https://pubmed.ncbi.nlm.nih.gov/16207226/ and https://pubmed.ncbi.nlm.nih.gov/25704736/

### Feeding
- Newborn: 8–12 feeds in 24 h (CDC, AAP).
- 3–6 mo **6–12 feeds**:
  - Formula settles into 6–8 feeds, every 3–4 h.
  - Exclusively breastfed babies aged 1–6 mo averaged 11 ± 3 feeds a day (Kent 2006).
  - The draft said 6–8.
- Solids at about 6 months, never before 4 (AAP, CDC). Offer a cup at about 6 months.
- Whole cow's milk from 12 months. Bottle weaning sometime between 12 and 18 months.
- CDC milestones:
  - 9 mo: rakes food.
  - 12 mo: pincer grasp.
  - 18 mo: feeds self with fingers, tries a spoon, drinks from an open cup.
  - 2 y: eats with a spoon.
  - 3 y: uses a fork.
  - 4 y: serves self or pours water with an adult nearby.
- Picky eating: fear of new foods starts at 18–24 mo, and the AAP calls picky eating "very common" from 2 to 4.
- Levels after the first year are judgment: someone still plans and makes every meal.

Sources:
- AAP: https://www.healthychildren.org/English/ages-stages/baby/feeding-nutrition/Pages/how-often-and-how-much-should-your-baby-eat.aspx
- CDC, breastfeeding: https://www.cdc.gov/infant-toddler-nutrition/breastfeeding/how-much-and-how-often.html
- CDC, formula: https://www.cdc.gov/infant-toddler-nutrition/formula-feeding/how-much-and-how-often.html
- Kent 2006: https://pubmed.ncbi.nlm.nih.gov/16510619/
- AAP, solids: https://www.healthychildren.org/English/ages-stages/baby/feeding-nutrition/Pages/Starting-Solid-Foods.aspx
- CDC, solids: https://www.cdc.gov/infant-toddler-nutrition/foods-and-drinks/when-what-and-how-to-introduce-solid-foods.html
- Cleveland Clinic: https://my.clevelandclinic.org/health/articles/9693-feeding-your-baby-the-first-year
- AAP, drinks: https://www.healthychildren.org/English/healthy-living/nutrition/Pages/Recommended-Drinks-for-Young-Children-Ages-0-5.aspx
- AAP, bottle to cup: https://www.healthychildren.org/English/ages-stages/baby/feeding-nutrition/Pages/Discontinuing-the-Bottle.aspx
- AAP, picky eating: https://www.healthychildren.org/English/tips-tools/ask-the-pediatrician/Pages/How-do-I-help-my-picky-eater-try-more-foods.aspx
- CDC milestones: https://www.cdc.gov/act-early/milestones/ (pages for 9 months, 1, 2, 3 and 4 years, and 18 months)

### Diapers → potty
- **Per-day counts are estimates.**
  - AAP, Mayo and Cleveland Clinic give only minimums, used to check intake: 6+ wet diapers a day after day 5, and 3–4+ stools a day for breastfed newborns. That fits 8–12 changes a day at 0–3 mo.
  - No authority publishes counts for later ages, so the 6–8 / 5–7 / 5–6 values are ours.
- Readiness signs appear at 18–24 mo (AAP). Starting intensive training before 27 mo doesn't lead to finishing earlier (Blum 2003).
- Potty training **2–3 y**: US training usually starts between 2 and 3. The median age for daytime dryness is 32.5 mo for girls and 35 mo for boys (Schum 2002). This stage gets level 5 because training is a heavy temporary load.
- 3–4 y **day-trained**: median daytime dryness is about 3½ in Sweden, with night dryness at about 4 (Jansson 2005). The AAP says 40% still wet at night after daytime training.
- 4 y **mostly trained**:
  - Bedwetting is 30% at 4½ y (ALSPAC), 36.5% at 4 (Portugal) and 42.2% at 4½ (Japan), so the page says "about 1 in 3".
  - The draft said "trained".

Sources:
- AAP: https://www.healthychildren.org/English/ages-stages/baby/breastfeeding/Pages/How-to-Tell-if-Baby-is-Getting-Enough-Milk.aspx
- AAP: https://www.healthychildren.org/English/ages-stages/toddler/toilet-training/Pages/The-Right-Age-to-Toilet-Train.aspx
- AAP: https://www.healthychildren.org/English/ages-stages/toddler/toilet-training/Pages/Stages-of-Toilet-Training-Different-Skills-Different-Schedules.aspx
- AAP: https://www.healthychildren.org/English/ages-stages/toddler/toilet-training/Pages/Bedwetting.aspx
- NIDDK: https://www.niddk.nih.gov/health-information/urologic-diseases/bladder-control-problems-bedwetting-children/definition-facts
- Schum 2002: https://pubmed.ncbi.nlm.nih.gov/11875176/
- Blum 2003: https://pubmed.ncbi.nlm.nih.gov/12671117/
- Jansson 2005: https://pubmed.ncbi.nlm.nih.gov/15947669/
- ALSPAC: https://pubmed.ncbi.nlm.nih.gov/18432533/
- Portugal: https://pubmed.ncbi.nlm.nih.gov/34736725/
- Japan: https://pubmed.ncbi.nlm.nih.gov/41250286/

### Naps & schedule
- **Naps per day:**
  - 0–5 mo: pooled mean 3.1 (range 1.2–5.0), so the page says 3–5 and erratic. The draft said 4–6.
  - 6–11 mo: pooled mean 2.2.
  - 12–18 mo: two naps become one.
- **Stopping napping:**
  - Fewer than 2.5% stop before age 2.
  - 33% have stopped by 3, 57% by 36–48 mo, and 80% by 48–60 mo (Staton 2020; Weissbluth 1995).
- **Total sleep (AASM 2016, AAP-endorsed):** 12–16 h at 4–12 mo, 11–14 h at 1–2 y, 10–13 h at 3–5 y. There is no recommendation for 0–4 mo. Newborns sleep about 16–17 h in 1–2 h stretches (AAP).
- **Georgia Pre-K:** its schedule FAQ caps rest time at 60 minutes and gives non-sleepers quiet activities.

Sources:
- Staton 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC9704850/
- Weissbluth 1995: https://pubmed.ncbi.nlm.nih.gov/7792496/
- DECAL schedule FAQ: https://www.decal.ga.gov/documents/attachments/FAQ_for_Daily_Schedule.pdf

### Mobility
- **WHO Motor Development Study medians (10th–90th percentile):**
  - sitting alone: 5.9 mo;
  - standing with help: 7.4 mo;
  - crawling: 8.3 mo (6.6–10.5);
  - walking with help: 9.0 mo;
  - walking alone: 12.0 mo (10.0–14.4; 99th percentile 17.6).
  - 4.3% never crawled.
- **Rolling:** WHO didn't measure it. AAP: both ways "by the end of" 4–7 months. The draft said about 4 mo.
- **Climbing out of the crib:** no source gives an age. The AAP says to move to a bed once they can climb out, reach 35 inches, or the rail is below three-quarters of their height. So the 2–3 y cell no longer states an age.
- **Tricycle:** AAP says a 3-year-old "can ride a tricycle with great ease". The 2022 CDC list dropped the tricycle.
- **CDC milestones:** 18 mo, climbs on and off a couch; 2 y, runs; 4 y, catches a large ball.

Sources:
- WHO percentiles: https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/motor-development-milestones/mm_percentiles_table.pdf?sfvrsn=81f3b60b_5
- WHO windows: https://cdn.who.int/media/docs/default-source/child-growth/child-growth-standards/indicators/motor-development-milestones/who-motor-development-study-windows-of-achievement-for-six-gross-motor-development-milestones.pdf?sfvrsn=3425c1dc_0
- AAP, 4–7 months: https://www.healthychildren.org/English/ages-stages/baby/Pages/Movement-4-to-7-Months.aspx
- AAP, 8–12 months: https://www.healthychildren.org/English/ages-stages/baby/Pages/Movement-8-to-12-Months.aspx
- AAP, big-kid beds: https://www.healthychildren.org/English/healthy-living/sleep/Pages/Big-Kid-Beds-When-To-Make-the-Switch.aspx
- AAP, preschool movement: https://healthychildren.org/English/ages-stages/preschool/Pages/Movement-Milestones-in-Preschoolers.aspx
- CDC milestones: https://www.cdc.gov/act-early/milestones/

### Baby-proofing
- **Safe sleep (AAP, summarizing the 2022 policy):** back to sleep, fitted sheet only, room-share for at least 6 months, nothing inclined more than 10°. The Safe Sleep for Babies Act (2022) banned inclined sleepers and crib bumpers. Stop swaddling at the first sign of rolling.
- **Raised surfaces and the crib:**
  - The AAP says never leave a baby alone on a raised surface and not to rely on the changing-table strap.
  - Remove the crib mobile by 5 months.
  - Lower the mattress before they can sit, and set it to its lowest before they can stand. The draft had the crib drop at 9–12 mo; it moved earlier.
- **Before crawling:**
  - Outlet covers.
  - Cordless window coverings (CPSC).
  - Gates at the top and bottom of stairs. At the top, use only wall-screwed gates (CPSC).
  - Anchor furniture and TVs.
- **Tip-overs (CPSC 2023 report):**
  - 155 child deaths from 2013 to mid-2023.
  - 68% of them were ages 1 to under 3½. TVs were involved in 47% of all tip-over deaths.
  - The STURDY Act stability rule (from Sept 2023) covers only new dressers, so anchoring still matters.
- **Windows:** stops that let a window open no more than 4 inches, or operable guards above the first floor. Screens don't stop falls (CPSC, AAP).
- **Water:** more children aged 1–4 die from drowning than from any other cause (CDC). Pools need a fence on all four sides, at least 4 feet high (AAP).
- **Later ages:** walk around the car before backing out, no playing in the street, and store guns unloaded and locked (AAP, 2–4 years).
- **Timing is judgment.** The AAP ties these tasks to skills (sitting, standing, crawling, climbing), not months. Placing them in stages is ours, including the timing of stove-knob and door-knob covers, the toddler-bed room and "nothing new" at 4. No agency source was found for door-stop (pinch) guards, so the page leaves them out.

Sources:
- CPSC childproofing: https://www.cpsc.gov/safety-education/safety-guides/kids-and-babies/Childproofing-Your-Home
- CPSC window safety: https://www.cpsc.gov/Newsroom/News-Releases/2026/CPSC-Urges-Families-to-Protect-Children-During-National-Window-Safety-Week
- CPSC tip-over report: https://www.cpsc.gov/s3fs-public/2023_Annual_Tip_Over_Report_Posted_2024Feb_FINAL_0.pdf
- CPSC Anchor It: https://www.cpsc.gov/Newsroom/News-Releases/2025/CPSC-AnchorIt-Campaign-Marks-10-Years-Fewer-Furniture-Tip-Overs-Lead-to-Safer-American-Households
- CDC drowning: https://www.cdc.gov/drowning/data-research/facts/index.html
- AAP, baby's room: https://www.healthychildren.org/English/safety-prevention/at-home/Pages/Make-Babys-Room-Safe.aspx
- AAP, safe sleep: https://www.healthychildren.org/English/ages-stages/baby/sleep/Pages/A-Parents-Guide-to-Safe-Sleep.aspx
- AAP, inclined sleepers: https://www.healthychildren.org/English/ages-stages/baby/sleep/Pages/Inclined-Sleepers-and-Other-Baby-Registry-Items-to-Avoid.aspx
- AAP, swaddling: https://www.healthychildren.org/English/ages-stages/baby/diapers-clothing/Pages/Swaddling-Is-it-Safe.aspx
- AAP, home safety: https://www.healthychildren.org/English/safety-prevention/at-home/Pages/home-safety-heres-how.aspx
- AAP, 1–2 years: https://www.healthychildren.org/English/ages-stages/toddler/Pages/Safety-for-Your-Child-1-to-2-Years.aspx
- AAP, 2–4 years: https://www.healthychildren.org/English/ages-stages/toddler/Pages/Safety-for-Your-Child-2-to-4-Years.aspx
- AAP, kitchen: https://www.healthychildren.org/English/safety-prevention/at-home/Pages/Kitchen-Safety.aspx
- AAP, water: https://www.healthychildren.org/English/safety-prevention/at-play/Pages/Water-Safety-And-Young-Children.aspx

### Mouthing & choking
- **CDC milestones:** brings hands to mouth at 4 mo; puts things in the mouth to explore them at 6 mo.
- **How much mouthing:**
  - 0–18 mo: about 32 min a day of non-pacifier object mouthing (Juberg 2001).
  - Up to 24 mo: 81 mouthing events an hour, versus 42 after (Tulve 2002).
  - 19–36 mo: object mouthing falls to about 4 min a day.
- **CPSC small-parts rule:** it covers toys for children under 3. The test cylinder is 2.25 in long and 1.25 in wide; the draft wrongly said 1.25 in all round.
- **AAP foods to hold back until 4 or older:** hot dogs, hard or sticky candy, gum, nuts and seeds, whole grapes, raw carrots and apple chunks, popcorn, chunks of nut butter, marshmallows, meat sticks, and chunks of meat or cheese. Round, firm foods are fine chopped small. Balloons remain a risk until 8.
- **Who dies from choking:** most children who do are under 5, and two-thirds are under 1 (AAP). The draft claimed 3–4-year-olds were most at risk; it was reworded.
- **3–4 y "mostly food":** the draft said "low". Toys are rarely mouthed, but food risk stays until 4.

Sources:
- AAP: https://www.healthychildren.org/English/health-issues/injuries-emergencies/pages/Choking-Prevention.aspx
- CDC MMWR: https://www.cdc.gov/mmwr/preview/mmwrhtml/mm5142a1.htm
- CPSC small parts: https://www.cpsc.gov/FAQ/Small-Parts and https://www.cpsc.gov/s3fs-public/Small-Parts-16-C-F-R-Part-1501-English.pdf
- Juberg 2001 (PMID 11134447)
- Tulve 2002 (PMID 12087432)

### Big feelings
- **Crying:**
  - About 2 h a day over weeks 0–6, falling to about 68 min by 10–12 weeks.
  - There is no universal 6-week peak (Wolke 2017 meta-analysis, 8,690 infants).
  - Colic clusters in the evening and usually stops by 3–4 months (AAP). So "fussy evenings" moved out of 3–6 mo.
- **Stranger wariness and separation anxiety:**
  - Stranger wariness appears by 9 mo (CDC).
  - Separation anxiety starts around 9 mo, peaks between 10 and 18 mo, and fades in the second half of the second year (AAP).
- **Tantrums:**
  - Share of children who have them: 87% at 18–24 mo, 91% at 30–36 mo, 59% at 42–48 mo (Potegal & Davidson 2003, via Hoyniak 2022).
  - Length: the most common is 0.5–1 min, and 75% last 5 minutes or less (Potegal, Kosorok & Davidson 2003).
  - Frequency at 3–5 y: more than 80% have one in a month, fewer than 10% daily (Wakschlag 2012).
- **4 y:** talks about something that happened during the day (CDC). "Can tell you what's wrong" is our phrasing.

Sources:
- AAP colic: https://www.healthychildren.org/English/ages-stages/baby/crying-colic/Pages/Colic.aspx
- AAP 8–12 months: https://www.healthychildren.org/English/ages-stages/baby/pages/Emotional-and-Social-Development-8-12-Months.aspx
- Wolke 2017 (PMID 28385295)
- Hoyniak 2022: https://sites.edb.utexas.edu/wp-content/uploads/sites/179/2022/08/developmental-pathways-from-preschool-temper-tantrums-to-later-psychopathology-1.pdf
- Potegal, Kosorok & Davidson 2003: https://experts.umn.edu/en/publications/temper-tantrums-in-young-children-2-tantrum-duration-and-temporal/
- NIMH on Wakschlag 2012: https://www.nimh.nih.gov/news/science-news/2012/daily-or-severe-tantrums-may-point-to-mental-health-issues

### Solo play
- **Every duration in this lane is our estimate.** No authority publishes how long children can play alone by age.
- The "2–3 minutes per year of age" rule of thumb appears only on blogs, with multipliers from 2 to 5, and cites no study.
- **What does exist:**
  - Tummy time should be closely supervised: 3–5 min, 2–3 times a day, building to 15–30 min a day (AAP).
  - The WHO says not to restrain infants for more than an hour at a time.
  - At home, 13–23-month-olds' median time with a single toy is 9.8 seconds (Herzberg 2022).
  - Focused attention grows from 10 to 26 to 42 months (Ruff & Capozzoli 2003).
- **No supervision standard exists for leaving a toddler alone, even in a childproofed room.** The literature says there are "no clear guidelines", and the expert view is "continuous, close supervision" (Morrongiello & Schell 2010). The AAP's only absolutes are never alone near water or in a car.

Sources:
- AAP tummy time: https://www.healthychildren.org/English/ages-stages/baby/sleep/Pages/back-to-sleep-tummy-to-play.aspx
- WHO: https://www.who.int/news/item/24-04-2019-to-grow-up-healthy-children-need-to-sit-less-and-play-more
- Morrongiello & Schell 2010: https://nj.gov/humanservices/opmrdd/injury/AJLM_ChildInjury_RoleOfSupervisionInPrevention.pdf
- AAP 1–2 years: https://www.healthychildren.org/English/ages-stages/toddler/Pages/Safety-for-your-child-1-to-2-Years.aspx
- Herzberg 2022 (PMID 34515994)
- Ruff & Capozzoli 2003 (PMID 12952400)

### Well-child visits
- **Schedule:** the AAP Bright Futures periodicity schedule (updated February 2025) lists prenatal, newborn, 3–5 days, by 1 month, 2, 4, 6, 9, 12, 15, 18, 24 and 30 months, then 3 and 4 years. The 3–5 day visit should also fall within 48–72 h of hospital discharge.
- **Vaccines:**
  - The 2, 4 and 6 month visits each carry 5–6 vaccines.
  - The 12–15 month window carries MMR, chickenpox, Hib, pneumococcal and hepatitis A.
  - The 4-year visit brings DTaP, polio, MMR and chickenpox boosters.
- **Screenings:** developmental screening at 9, 18 and 30 months; autism screening at 18 and 24 months; anemia and lead checks start at 12 months. Visual acuity screening by chart starts at 3 years.

Sources:
- AAP periodicity schedule: https://downloads.aap.org/AAP/PDF/periodicity_schedule.pdf
- AAP landing page: https://www.aap.org/periodicityschedule
- CDC easy-read schedule: https://www.cdc.gov/vaccines/imz-schedules/child-easyread.html
- CDC child schedule: https://www.cdc.gov/vaccines/hcp/imz-schedules/child-adolescent-age.html
- Contemporary Pediatrics on the 2026 schedule litigation: https://www.contemporarypediatrics.com/view/the-unharmonious-2026-child-and-adolescent-immunization-schedule

## Georgia Pre-K

- **Eligibility:** the child must be four on or before September 1 of the school year. For 2026–27 that means born September 2, 2021 through September 1, 2022.
  - A 2026 law (HB 1193) also lets families enroll at age 5 if the child wasn't served at 4.
  - The page doesn't show this option. It keeps the default path.
- **Cost and funding:** free and funded by the Georgia Lottery for Education. Providers can't charge for the 6.5-hour day; before- and after-care is separate.
- **School day and year:** 6.5 instructional hours a day, at least 180 days a year (1,170 hours). The day starts no earlier than 7:30 am.
- **Who can enroll:** it's universal. Providers can't prioritize by family income, though there may not be enough spaces in every community.
- **How to apply:** there is no statewide application or lottery. Each provider sets its own registration dates and picks either first-come, first-served or its own lottery. The "lottery" in news coverage refers to the funding.
- **Size:** about 71,000 children were served in FY2025. No current funded-slot figure has been published.

Sources:
- https://www.decal.ga.gov/bfts/enrollinginprek.aspx
- https://www.decal.ga.gov/bfts/faq.aspx?cat=Pre-K
- https://www.decal.ga.gov/prek/About.aspx
- https://www.decal.ga.gov/documents/attachments/guidelines.pdf (2026–27 guidelines)
- https://www.decal.ga.gov/documents/attachments/BFTSAnnualReport2025.pdf
- https://www.decal.ga.gov/documents/attachments/preKFactSheet.pdf

## Not shown, for context

- **Car seats:** rear-facing as long as possible, until the seat's maximum height or weight, then a harnessed forward-facing seat at least to age 4 (AAP). See https://www.healthychildren.org/English/safety-prevention/on-the-go/Pages/Car-Safety-Seats-Information-for-Families.aspx
- **Language:**
  - First words around 12 months.
  - At 24 months, 50+ words is a floor, not the norm; under 50 is the "late talker" cutoff (Rescorla 2011).
  - Two- to three-word sentences grow to four to six words over the third year (AAP).

## Palette

Lavender sequential ramp, one hue (OKLCH h≈295). Lightness falls strictly from level 0 to 5, with ΔL ≥ 0.06 between steps, in both modes; checked with the dataviz validator's `--ordinal` mode. Level 0 ("none") intentionally recedes into the surface, which is the validator's one expected fail, so level-0 cells get a hairline border. Every cell also carries a text label. Text on every level clears 5.6:1. The strip's bars clear 3:1 against the page ground in both modes.
