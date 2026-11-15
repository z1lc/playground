# Garage Floor Compare: research notes

Research done 2026-11-11 for a 616 sq ft slab-on-grade garage in Atlanta, GA. Every figure the page shows is in `TYPES` in `index.html`, with its sources. This file records how the numbers were chosen and where judgment filled gaps.

## Ground rules

- **Health is long-term.** It scores the finished floor, including a toddler licking it. Install fumes and cure waits are not scored; cure time is shown as a fact.
- **Prices** come from late-2026 search snapshots and maker stores. Retailer pages (Home Depot in particular) block automated fetches, so their prices are search-snippet values. Treat every price as a range to re-check before buying.
- **10-year cost** = upfront midpoint × `ceil(10 / lifespan midpoint)`. Re-coats are priced the same as the first coat. That overstates silane re-coats slightly (often one coat instead of two) and understates failed film coatings, which need stripping first.
- **"Inert once cured"** is an inference for every product. No maker publishes toxicity data for the cured surface; SDSs cover only the liquid.

## Atlanta climate

From the NOAA 1991–2020 normals for Hartsfield (USW00013874), checked directly from the NCEI CSVs:

| Measure | Normal | Source |
|---|---|---|
| July mean max | 90.1 °F | monthly normals |
| January mean min | 35.6 °F | monthly normals |
| Days with max ≥ 90 °F | 47.1 a year | [annual normals](https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/access/USW00013874.csv) |
| Nights with min ≤ 32 °F | 35.7 a year | annual normals |
| Mid-July dew point | about 69 °F | hourly normals |
| Summer morning relative humidity | 86–87 % | [NOAA CCD](https://www.ncei.noaa.gov/sites/default/files/2024-11/relhum23.txt) |

**Takeaway:** humidity and slab moisture stress a garage floor here more than freeze–thaw does. A slab that stays cooler than the summer dew point can sweat under mats.

## Per type: chosen values and reasoning

| Type | Upfront | Lifespan | Health | Durability | Notes |
|---|---|---|---|---|---|
| Bare concrete | $0 | n/a | 3 | 1 | Porous and alkaline (surface pH ~9 once carbonated). It soaks up oil and antifreeze. Ethylene glycol is sweet and toxic (ATSDR), so the risk is a fresh spill, not the concrete itself. |
| Silicate densifier | $85–175 | 10–25 (est.) | 4 (was 5; see Exposure routes) | 3 | Consolideck LS covers 500–800 sq ft/gal in 1 coat; Lithi-Tek 4500 is similar. It reacts into calcium silicate hydrate. NSF R2 registered. Makers call it "permanent"; the 10–25 yr range is ours, so a 10-year window needs only one application. No oil protection (TDS). |
| Silane/siloxane (water-based) | $290–360 | 5–10 | 5 | 3 | SX5000 WB covers 175–225 sq ft/gal per coat, 2 coats → 5.5–7 gal. Maker figures disagree (5–7 vs 7–10 yrs). ODOT bridge-deck silanes were still effective at 12 yrs. 8500: no scaling after 100 freeze–thaw cycles. |
| Densifier + repellent | $200–530 | 5–10 | 5 | 4 | The low end is the one-product Lithi-Tek 9500 (2 gal); the high end is stacking LS + SX5000 WB. The repellent part sets the redo interval. 9500 says to avoid deicing salts. |
| Acrylic sealer | $225–315 | 2–5 | 4 | 2 | AR350: "up to 2–5 years." Its TDS says it "does not stop hot tire pickup" and that rubber-mat plasticizers may bond to it. Dried film is USDA-accepted. Slippery when wet. |
| DIY water-based epoxy kit | $210–280 | 1–4 (est.) | 3 | 2 | EpoxyShield gives 3–3.5 mils dry, ~250 sq ft per pouch; the kit isn't for slabs with moisture problems. No maker lifespan; the range is ours. Health matches pro epoxy (BPA chemistry) but with less material. |
| Pro 100%-solids epoxy | $3,080–4,930 | 10–20 (est.) | 3 | 4 | Atlanta $5–8/sq ft (HomeBlue, weak). Euclid TDS: "will yellow upon prolonged exposure to sunlight"; slab-on-grade needs an uninterrupted vapor barrier; 15–30% elongation. Health: epoxy pipe linings leach trace BPA, more when hot or aged (Rajasärkkä 2016). Some hardeners are 30–60% benzyl alcohol. A dry floor transfers far less than immersion. |
| Polyaspartic flake (pro) | $3,080–5,540 | 15–25 (vendor) | 4 | 5 | $5–9/sq ft (Bob Vila; Atlanta installer quotes $6–12). Simiron TDS: wet DCOF 0.63 with full flake (benchmark 0.42), UV stable, vapor barrier above 3 lb/1000 sq ft/24 h. EPA calls properly cured polyurethanes "relatively inert." Caveat: the base coat may be epoxy. |
| PP snap tiles | $2,770–3,600 | 15–20 | 4 | 4 | Swisstrax $4.49/sq ft, RaceDeck $4.75–5.85. Virgin PP, no plasticizer needed. 20-yr warranties, prorated after yr 5. Not watertight; warranties exclude moisture. Light colors stain under tires. |
| PVC tiles / roll-out mats | $1,600–3,420 | 5–15 | 2 | 3 | G-Floor roll at $2.14/sq ft; ArmorGarage tiles $4.25–5.55. 58% of retail vinyl tiles had phthalates in 2015 (Ecology Center). PVC flooring is linked to BBzP/DEHP in house dust (Bornehag 2005) and to infant urine metabolites (Carlstedt 2013). No garage PVC brand found stating it is phthalate-free. EPA's 2026 TSCA evaluations found no unreasonable consumer risk for five phthalates; both sides are cited. |
| Recycled SBR stall mats | $450–470 / 200 sq ft | 5–10 (est.) | 2 | n/a | Tractor Supply 4×6 ft × ¾ in, ~$50 each, 9 mats. Federal tire-crumb research: zinc averaged ~15,000 mg/kg, plus PAHs and VOCs. Exposure is "likely limited" but this "is not a risk assessment." Benzo[a]pyrene up to 11 mg/kg vs the EU's 1 mg/kg limit for rubber parts that touch skin. CPSC: avoid mouthing crumb rubber. |
| EPDM / virgin rubber mats | $1,600–2,600 / 200 sq ft | 10–20 (est.) | 4 | n/a | PaviGym Endurance (virgin) at $13/sq ft. Many "EPDM" tiles are tire rubber with colored flecks. FloorScore and GREENGUARD (Gold included) both test only VOCs in air; neither covers contact or ingestion (see the rubber gym mats section below). Natural rubber can carry latex allergens. |

## Under rubber mats

- **Film coatings.** Rubber plasticizers and antioxidants can stain or bond to them: see the AR350 TDS and the Ghostshield 930 TDS. Installers exclude plasticizer staining from warranties.
- **Vapor.** Vapor-blocking sealers on slab-on-grade can blister (Prosoco). Breathable penetrating sealers don't trap moisture.
- **Mildew.** Flat-bottom mats trap moisture and mildew. Ribbed undersides and lifting mats a few times a year help.
- **Before committing:**
  - Run the plastic-sheet moisture test (ASTM D4263) in summer.
  - Test the actual mat on a hidden patch of any coating.

## Spot checks (done directly, not via the research agents)

- **NOAA normals:** downloaded the CSVs and confirmed all four temperature figures.
- **Euclid epoxy TDS:** extracted the text and confirmed the yellowing statement, the slab-on-grade vapor-barrier requirement, and 15–30% elongation.
- **Lithi-Tek 4500 TDS:** confirmed "one-time permanent application," "100% breathable," and "does not protect against … oils."
- **EPA tire-crumb page:** confirmed "exposures … are likely limited" and "not a risk assessment."
- **Bornehag 2005:** confirmed the PVC flooring ↔ BBzP/DEHP dust association.

## Gaps

- No cured-surface emission or leaching data for any floor product in a residential garage.
- No independent multi-year lifespans for DIY kits, pro epoxy, or mats; those ranges are marked "est."
- No wet-slip ratings for penetrating sealers, PVC, or mats on a common scale. Penetrating sealers keep the concrete's own grip (ASTM E303 unchanged).

---

# Rubber gym mats (research for a fourth tab)

Researched 2026-11-12. Prices are snapshots from that day. Grades:
- **A:** a full ingredient disclosure (an HPD or Declare label at 100 ppm), or public third-party contaminant data.
- **B:** a verified emissions certification only.
- **C:** the seller's word only.
- **D:** nothing, or contradictory claims.

Unless a line says otherwise, certifications were checked in the certifier's public database: SCS for FloorScore, the HPD Public Repository, and Declare. UL SPOT (GREENGUARD) showed a bot check, so no GREENGUARD claim is verified.

## What a label tells you about a mouthing child

| Label | What it actually tests | Relevance to a crawling or mouthing kid |
|---|---|---|
| REACH Annex XVII entry 50 PAH test | PAH content: ≤1 mg/kg per PAH for skin-contact rubber, ≤0.5 mg/kg for toys and childcare. ECHA's guidance lists yoga mats and sports or playground mats as examples. | **High**, if the report covers this exact product |
| AfPS GS 2019:01 PAK (German GS mark) | PAH content in tiers set for children's products | **High** |
| EN 71-3 / ASTM F963 §4.3.5 | Metals extracted in a simulated stomach-acid solution | **High** (mainly lead) |
| EN 71-12 | Nitrosamines and nitrosatable substances from sulfur-cure accelerators | **High** for sulfur-cured or natural rubber |
| CPSIA total lead (100 ppm) | Total lead | High, but it only applies if the product is marketed for children |
| FloorScore, GREENGUARD, GREENGUARD Gold, CDPH v1.2 | VOCs in air at 23 °C after 14 days | **Low.** Air only, at room temperature. Tire-crumb tiles hold FloorScore certificates. |
| HPD, Declare | Ingredient disclosure at 100 ppm (some HPDs at 1,000 ppm) | **Low for contaminants.** 100 ppm is 100× the PAH limit. Useful for spotting tire content and hazard flags. |
| Prop 65 warning | No test; a legal warning. No retail page named the chemical. | Low; a weak red flag |
| "Non-toxic", "eco-friendly", "odorless", "virgin", "EPDM" | Nothing standard | None on its own |

Sources: ECHA entry 50 guidance; EUR-Lex Reg. 1272/2013; the AfPS GS PAK spec via a Bureau Veritas bulletin; CDPH Standard Method v1.2; the SCS FloorScore program; CPSC; HPD Collaborative; ILFI. Full URLs are in the decoder notes (see "Raw notes" below).

## Material chemistry (finished rubber)

| | Recycled tire SBR + PU binder | Virgin EPDM | Recycled EPDM granules | Natural rubber |
|---|---|---|---|---|
| PAHs | 8-PAH sum medians ~4–28 mg/kg; BaP up to 11 mg/kg | ~1–1.6 mg/kg (16-PAH sum) with paraffinic oil | 15.3 mg/kg (one study) | No mat data |
| Zinc | ~10,000–20,000 mg/kg | median ~4,100 mg/kg | similar | ZnO if sulfur-cured |
| Lead | medians ~21–29 mg/kg, max 308 | 8–12 mg/kg; one infill released 17.3 mg/kg in a stomach-acid test | — | No data |
| Nitrosamines | Possible (thiuram and dithiocarbamate accelerators) | Avoided if peroxide-cured | Unknown | Yes if sulfur-cured; one natural-rubber yoga mat tested high |
| Other | Benzothiazole odor; crumb sheds | Pigments can add chromium (one sample 5,200 mg/kg) | — | Latex protein allergy possible (lower than in dipped goods) |

Heat raised some VOCs about 9× between 23 and 60 °C (Liu 2023). Airing out reduces VOCs but not PAHs or lead.

California OEHHA's March 2026 synthetic-turf risk assessment found "no significant health risks" overall. The exception: spectators aged 0–2 came out "slightly above 1" on the hazard index, driven by swallowing crumb rubber (assumed 153 mg/day) and, for non-cancer effects, by lead. EPA/CDC's 2024 tire-crumb follow-up found about 3% of metals released in simulated gastric fluid (lead mean 2.8%, max 13.5%).

## Products

| Product (where to buy) | Material | $/sq ft | Evidence | Grade |
|---|---|---|---|---|
| Tarkett Johnsonite **Triumph** sports tile (online resellers) | Vulcanized SBR + polyisoprene, 40% post-industrial own scrap, **no tire crumb** | ~$20.50+ | Third-party-verified HPD at 100 ppm (WAP Sustainability), residuals evaluated; Declare; FloorScore SCS-FS-01422. Lists zinc oxide 1–3% and LT-1 process oils ≤3%. Drop-rated; interlocking version lays loose. | A |
| Mohawk **Hero Rubber + Nike Grind** (retailer, quote) | Shoe-sole regrind + EPDM, PU binder, no tires | ~$7.99 (Ninety, snippet) | Self-declared Declare labels at 100 ppm; FloorScore (Original). Not explicitly drop-rated. | A (self-declared) |
| **PaviGym Endurance** 7 mm (Greatmats) | "Virgin rubber" top. Greatmats: "recycled bottom layer", no EPDM. Recycled content is PaviGym's own offcuts, not tires. | $14.58 | Maker statements only; ISO 9001/14001 and CE only | C |
| **Le SOL Elite** 7 mm (Sparks Fitness, Dallas) | "100% Pure Virgin Rubber", vulcanized, Italy | $20.00 | Seller statements only | C |
| **Amorim Nuclear** ⅜ in (Greatmats) | Glued granules: 90% colour granules + 8% recycled black fraction (sold as "virgin") | $14.86 | Amorim holds FloorScore SCS-FS-05532; not confirmed to cover Nuclear | C |
| **Regupol aktivlok** ⅜ in (Rogue) | 82% tire SBR | ~$2.84 | HPD at 1,000 ppm, crumb unscreened; CDPH via ClearChem self-declaration. Light drops, loose-lay. | A (weak) |
| **Regupol aktivpro** 1 in (Rogue) | 88.75% tire SBR, 1.1% EPDM, 10.3% binder, fiberglass layer (LT-1) | ~$7.55 | Same style of HPD; EPD; CDPH TVOC ≤0.5 mg/m³ | A (weak) |
| **Ecore Basic Fit** 8 mm ("Eureka", Greatmats) | ~90% tire crumb | $2.55 | Ecore HPD at 1,000 ppm, self-prepared; FloorScore SCS-FS-01793 | A (weak) |
| **U.S. Rubber Survivor** (Tractor Supply, Atlanta store pickup) | 60–90% tire rubber, 10–20% EPDM fleck, MDI, 0.7–15% process oil | ~$3.24 roll (8 mm) | FloorScore SCS-FS-20033. Its HPD (self-declared, expired 2022-06-20) lists **lead** (LT-1) as an impurity, carbon black, and 6PPD. | B |
| Rubber-Cal **"EPDM 60A"** sheet (Home Depot) | Spec sheet: "10% … EPDM Base, SBR" | $5.22 (¼ in) | Prop 65 warning; nothing else | D |
| Rubber-Cal Eco-Sport, AFM Fit-Lock, REP, Titan (Amazon, own stores) | Recycled or unstated | $2.49–13.63 | AFM claims FloorScore but has **no SCS listing**. REP, Titan and Rubber-Cal pages show Prop 65 warnings without naming the chemical. | D |

**Not practical for a homeowner:**
- Mondo, Dinoflex, Capri, Zandur and Pliteq are quote- or dealer-only. Zandur Nitria (virgin nitrile, full HPD) is glue-down only.
- REGUPOL everroll ultimate (100% virgin EPDM, German approval data showing nitrosamines <11 µg/kg) has no US channel.
- nora has no weight-room product.
- No Atlanta-area dealer was confirmed for any virgin or EPDM line.

**Disclosed hazards worth showing:**
- Ecore Moxie Beast's third-party HPD lists an alternate binder containing medium-chain chlorinated paraffins (Red List).
- Dinoflex's expired HPD lists distillate aromatic extract up to 14.2% (EU Carc. 1B).
- Natural rubber appears in Roppe Spartus, Flexco Tuflex Force and U.S. Rubber crumb, with no latex-protein data.

**Garage warranty catch:** nearly every maker specifies indoor installation at about 60/65–85 °F, often at 40–60% RH. Several exclude UV or humidity damage.

**No product in any channel publishes PAH, EN 71-3 metals or nitrosamine results for the finished mat.** For a mouthing child, the strongest available step is to ask the supplier for those reports.

## Supplier questions

1. **PAHs:** a third-party PAH report for this exact SKU to REACH Annex XVII entry 50 (or AfPS GS PAK), with detection limits.
2. **Composition:** % tire rubber vs other recycled vs virgin, and whether the top surface matches the base.
3. **EPDM:** virgin or recycled? Throughout, a top layer, or flecks?
4. **Cure system:** sulfur or peroxide? Any thiurams or dithiocarbamates? An EN 71-12 nitrosamine report?
5. **Metals:** an EN 71-3 or ASTM F963 report including lead and Cr(VI).
6. **Process oil type:** paraffinic, TDAE or aromatic.
7. **Binder:** aromatic (MDI) or aliphatic, and the cure time before shipping.
8. **Emissions certificate:** the certificate number, so it can be looked up.
9. **Natural rubber:** does it contain any? If so, extractable-protein data.
10. **Cleaners:** which are approved, and which void the warranty.

Red flags in a reply:
- a report for a different product;
- a raw-material spec instead of a finished-product test;
- detection limits above the limit being claimed;
- "non-toxic" offered in place of data.

## Care

- **Before installing:** air the mats out warm, shaded and ventilated for at least 2 weeks. CDPH v1.2 assumes the fast off-gassing is over by day 14. Keep SBR and natural rubber out of long direct sun.
- **Cleaning:** wash with a pH-neutral (7–9), solvent-free cleaner. Avoid petroleum or citrus solvents, high-alkaline degreasers and oil dressings. Damp-mop rather than sweep.
- **In use:** ventilate on hot days, wash hands, and keep a washable, separately certified play mat on top where the baby crawls. The play mat is our inference, not a source recommendation.

## Spot checks (mats)

- **Rubber-Cal "EPDM 60A" spec PDF:** "10% Ethylene Propylene Diene Monomer (EPDM) Base, SBR", plus a Prop 65 warning. Confirmed.
- **Triumph HPD:** 100 ppm threshold, residuals evaluated, verifier WAP Sustainability, zinc oxide listed. Confirmed.
- **U.S. Rubber Survivor HPD:** lead LT-1 impurity, carbon black, self-declared, expiry 2022-06-20. Confirmed.
- **Ecore Moxie Beast HPD:** MCCP (CAS 85535-85-9) listed. Confirmed.
- **OEHHA 2026 final report:** "no significant health risks"; infants' hazard index "slightly above 1", driven by lead; the 153 mg/day ingestion assumption. All confirmed in the PDF the decoder agent saved (OEHHA's site blocks direct fetches).
- **PaviGym:** the Greatmats "recycled bottom layer" and "virgin rubber" datasheet quotes, as recorded by the agent with URLs.

## Raw notes

The per-product research is in three agent files: retail sellers, commercial makers and the label decoder. They were kept in the session scratchpad and are not committed. The tables above condense them.

---

# Exposure routes: air, skin, mouth (2026-11-13)

The owner cares equally about what kids **breathe** (off-gassing after cure, dust, mold), what touches their **skin**, and what reaches their **mouths**. Each type's health details in the app are now split by route. One research pass gathered the facts (raw notes in the session scratchpad, `routes*.md`). The load-bearing items were spot-checked (see the end of this section).

## Score changes

- **Densifier: 5 → 4.** This isn't an air or skin finding; it rests on the porous-surface clause of the rubric.
  - The maker says Lithi-Tek 4500 "Does not prevent equipment leaks or other leaks such as oil".
  - Jansová et al. 2023 found lithium silicate's effect on water uptake "negligible (2–8%) after 24 hours", with porosity "practically unaffected" (https://doi.org/10.1088/1742-6596/2568/1/012004).
  - So spills like antifreeze still soak in where kids crawl. It still dusts less than bare concrete (3), so it lands on 4.
  - Silane and the combo stay at 5: both repel water-based spills, and only oil gets through.
  - **Effect:** the default top match is now Densifier + repellent (87), then silane (83), then densifier (80). The three penetrating sealers are still the top three.
- **All other scores are unchanged.** Pro epoxy stays at 3 with a stated condition: a 3 assumes a benzyl-alcohol-free hardener, or GREENGUARD Gold, AgBB or M1 certification. A conventional hardener with only a CDPH claim is closer to 2 for air.

## Per type (new facts by route)

| Type | Air | Skin | Mouth |
|---|---|---|---|
| Bare concrete | Nothing organic. Dusts; silica only when cut or ground (ready-mix SDS). | Cement burns and Cr(VI) allergy come from **wet** cement (OSHA 3351). | Spills and dust settle and soak in. |
| Densifier | "Only water will evaporate" (Lithi-Tek 4500 SDS). Consolideck LS holds SCS Indoor Advantage Gold. | Liquid pH ~11; scrub off residue. | Like bare concrete with less dust; still porous. NSF R2 means structural surfaces, not food contact. |
| Silane/siloxane | Ethanol by-product, limited in amount (SX5000 WB SDS). | Liquid irritant; nothing on the cured surface. | Oil, fuel and brake fluid still soak in (TDS). |
| Combo (Lithi-Tek 9500) | Lithium silicate + potassium methyl **siliconate** (not silane); "Only water will evaporate". | The concentrate is Skin Corr. 1A; scrub off any over-application residue. | The maker says it doesn't stop oil. |
| Acrylic (AR350) | The 2023 TDS says ventilate ≥7 days for solvent; repeats at every recoat. The "USDA accepted" line was dropped (the program ended in 1999). | Monomers sensitize; the cured film is inert (Cutis 2023). | Low concern. |
| Epoxy kit | SDS lists no benzyl alcohol; no consumer-kit emissions data. | Cured epoxy is non-sensitizing (DermNet, DGUV, Danish EPA); the risk is an off-ratio batch that never cures. | Trace BPA, as before. |
| Pro epoxy | Benzyl alcohol 30–60% in many hardeners. Sikafloor 265 gave off ~5.5 mg/m³ at day 14 and still **passed** CDPH (no criterion for it). The UBA RW II is 4 mg/m³. | Cured is non-sensitizing; applicator cases only. | Ask for benzyl-alcohol-free or GREENGUARD Gold / AgBB / M1. |
| Polyaspartic | Slow solvents (10–25% in the ArmorGarage SDS) and trace HDI; unmeasured on cured floors. A certified example exists (Mapei, SCS IAG). | CDPH-HESIS: cured PU "non-toxic, unless … heated". | The base coat may be epoxy. |
| PP tiles | Maker claims no off-gassing; no certification found. | No plasticizer; PP allergy is rare. | Lithner 2012: 0/5 PP leachates toxic vs 5/5 plasticized PVC. Vinyl-topped PP counts as PVC. |
| PVC | DEHP in air 0.9 → 10 µg/m³ from 23 → 35 °C (Clausen 2012); emits for years. FloorScore excludes phthalates. | TESIE (Hammel 2019): 15× urinary MBzP in all-vinyl homes, 3.5× on hands. Handwashing removes >50%. | Dust ingestion 40–50 mg/day for toddlers (EPA EFH ch. 5). Carlstedt 2013's finding is MBzP only. |
| Tire-rubber mats | Benzothiazole and MIBK; more when hot. | PAHs absorb through skin. PPD antioxidants are allergens (ESCD IPPD leaflet; Hervé-Bazin 1977 for 6PPD). Latex allergen persists in tire tread (Miguel 1996). | As before. |

## Mats additions

- **FloorScore TVOC, from maker-hosted certificates:**
  - Survivor (SCS-FS-20033): ≤0.5 mg/m³.
  - Hero (SCS-FS-07912, Feb 2026–Jan 2027): ≤0.5 mg/m³. It names Original and Nike Grind, not Ninety.
  - Triumph: ≤0.5. Ecore: 0.5–5.0.
- **Verified air-emissions tests: 4 of 13 products** (Triumph, Hero, Ecore Basic Fit, Survivor). No product publishes a skin or mouth test.
- **Label decoder:** each label is now rated per route. Air certificates rate "some" for air (room temperature, VOCs only, no dust) and "none" for skin and mouth. New rows: the French A+ label, "latex-free", and "odorless".

## Attached garage

- Batterman et al. 2007 (*Environ Res* 104:224) studied 15 homes. Garage-to-house airflow averaged 6.5% of each home's air exchange, and "nearly all of the benzene" indoors came from the garage.
- Health Canada's trial (Mallach 2017) found a garage exhaust fan cut indoor benzene 43–62%. Health Canada also recommends sealing the connecting door and the shared wall.
- **Our inference:** these studies measured fuel VOCs, not floor emissions. The pathway applies to any floor off-gassing.

## Spot checks (done directly)

- **Batterman 2007 abstract** (Europe PMC): "6.5±5.3%" and "nearly all of the benzene". Confirmed.
- **Hero FloorScore PDF** (maker-hosted): TVOC "Less than/equal to 0.5 mg/m3", valid Feb 1 2026 to Jan 31 2027, lists Original and Nike Grind. Confirmed.
- **Jansová 2023** (Crossref abstract): "negligible (2–8%) after 24 hours". Confirmed.
- **Triumph FloorScore PDF:** TVOC ≤0.5 mg/m³. Confirmed.
- The research pass separately verified the Sikafloor 265 report, the UBA benzyl-alcohol values, the AR350 TDS versions, Clausen 2012, Hammel 2019, Weschler 2015 and the DermNet epoxy page.

## Gaps

- No emissions data beyond 28 days for epoxy or polyaspartic floors.
- No skin case reports for any cured floor.
- No measurement of densifier dust reduction or residue pH.
- No study of floor emissions moving from a garage into a house.
