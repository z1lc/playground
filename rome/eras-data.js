// Era data + city positions, all in lon/lat (WGS84). The runtime projects
// these via Lambert Conformal Conic to match the pre-baked coastlines in
// world-data.js — same projection params, so everything aligns.

// `eras` lists the eras in which a non-capital city is important enough to
// display. Cities that ever served as a capital (Rome, Constantinople,
// Mediolanum, Ravenna) are always shown — no `eras` field needed for those.
window.__CITIES__ = [
  // Capitals (always visible)
  { name: 'Rome',           lon: 12.4964, lat: 41.9028 },
  { name: 'Constantinople', lon: 28.9784, lat: 41.0082 },
  { name: 'Mediolanum',     lon:  9.1900, lat: 45.4642 },
  { name: 'Ravenna',        lon: 12.2035, lat: 44.4173 },
  // Non-capitals
  { name: 'Carthage',     lon: 10.3236, lat: 36.8585, eras: ['republic', 'empire', 'western', 'eastern'] },
  { name: 'Athens',       lon: 23.7275, lat: 37.9838, eras: ['republic', 'empire', 'eastern'] },
  { name: 'Alexandria',   lon: 29.9187, lat: 31.2001, eras: ['republic', 'empire', 'eastern'] },
  { name: 'Antioch',      lon: 36.1611, lat: 36.2021, eras: ['republic', 'empire', 'eastern'] },
  { name: 'Hierosolyma',  lon: 35.2137, lat: 31.7683, eras: ['republic', 'empire', 'eastern'] },
  { name: 'Massalia',     lon:  5.3698, lat: 43.2965, eras: ['republic', 'empire', 'western'] },
  { name: 'Corduba',      lon: -4.7794, lat: 37.8882, eras: ['republic', 'empire', 'western'] },
  { name: 'Londinium',    lon: -0.1276, lat: 51.5074, eras: ['empire', 'western'] }
];

window.__ERAS__ = [
  {
    id: 'kingdom', name: 'Roman Kingdom', shortName: 'Kingdom',
    startYear: -753, endYear: -509, color: '#8B6914', row: 0,
    bbox: [4, 38, 20, 47],     // Italy + immediate surroundings — show the city-state clearly
    peakDate: 'Final extent · ~509 BC',
    stats: {
      population: '~30,000 (city of Rome)',
      territory: '~2,500 km² (≈ Luxembourg)',
      capitals: [{ name: 'Rome' }],
      languages: ['Old Latin'],
      government: [
        { label: 'Elective monarchy', description: 'Seven kings ruled in succession, chosen by an interrex and confirmed by the curiate assembly. Power was significant but not hereditary, and a king could be overthrown.' }
      ],
      religion: [
        { label: 'Roman polytheism', description: 'Worship of a pantheon led by Jupiter, Juno, and Mars. Ritual practice was deeply civic, run by priestly colleges (pontifices, augurs, vestals) woven into political life.' }
      ],
      monument: [
        { label: 'Cloaca Maxima', description: 'The “Great Drain” — one of the world’s earliest sewer systems, built under the Etruscan kings in the 6th century BC to drain the marsh between the hills. Still in active use today.' }
      ],
      rival: [
        { label: 'Etruscans', region: 'northern Italy', description: 'The dominant civilization of central Italy before Rome. Three of Rome’s seven kings (the Tarquins) were Etruscan; their expulsion in 509 BC ended the monarchy.' },
        { label: 'Sabines', region: 'central Apennines', description: 'Italic neighbors to Rome’s northeast, source of the legendary “Rape of the Sabine Women” under Romulus. Eventually merged into the Roman citizenry.' }
      ],
      leaders: [
        { name: 'Romulus', description: 'Legendary founder and first king (753 BC); created the Senate and Rome’s original institutions after killing his twin Remus over the city’s site.' },
        { name: 'Numa Pompilius', description: 'Second king (715–673 BC); established Rome’s religious calendar and the priestly colleges. Tradition credits him with the temples of Janus and Vesta.' },
        { name: 'Servius Tullius', description: 'Sixth king (575–535 BC); reorganized the army into property classes, instituted the census, and expanded Roman territory across Latium.' },
        { name: 'Tarquinius Superbus', description: 'Seventh and last king (535–509 BC). His tyranny — and the rape of Lucretia by his son — triggered the revolt that ended the monarchy.' }
      ]
    },
    bluf: 'The Roman Kingdom was the foundational era when Rome grew from a mythical settlement on the Tiber into a structured city-state governed by seven kings over roughly 244 years.',
    summary: [
      'According to tradition, Rome was founded in 753 BC by Romulus, who became its first king after killing his twin brother Remus in a dispute over the city’s location. While the historical accuracy of Rome’s earliest kings is debated, archaeological evidence confirms that a significant settlement existed on the Palatine Hill by the 8th century BC. The monarchy established many of Rome’s foundational institutions, including the Senate (originally an advisory council of elders), the division of the populace into patricians and plebeians, and the first religious practices that would persist for centuries.',
      'The seven kings of Rome — Romulus, Numa Pompilius, Tullus Hostilius, Ancus Marcius, Tarquinius Priscus, Servius Tullius, and Tarquinius Superbus — each contributed to the city’s development. Numa established Rome’s religious calendar and priestly colleges. Servius Tullius reorganized the army and created the census. Under the later Etruscan-influenced kings, Rome expanded its territory across Latium and grew into a genuine urban center with monumental architecture, including the first Forum buildings and the great sewer, the Cloaca Maxima.',
      'The monarchy ended in 509 BC when the last king, Tarquinius Superbus ("Tarquin the Proud"), was overthrown in a revolt triggered by the rape of Lucretia by the king’s son. The Romans replaced the monarchy with a republic, vowing never again to be ruled by a king — a sentiment so deeply embedded in Roman culture that it persisted for nearly five centuries and made the word "rex" (king) politically toxic in Roman society.'
    ],
    territory: [
      // Latium / area around Rome
      [[12.20, 42.05], [12.90, 42.00], [13.05, 41.70], [13.10, 41.30], [12.60, 41.28], [12.45, 41.50], [12.25, 41.74], [12.18, 41.88]]
    ]
  },
  {
    id: 'republic', name: 'Roman Republic', shortName: 'Republic',
    startYear: -509, endYear: -27, color: '#C41E3A', row: 0,
    bbox: [-10, 28, 42, 52],   // Mediterranean basin (Iberia → Anatolia, Sahara → Gaul)
    peakDate: 'Peak extent · 44 BC (death of Caesar)',
    stats: {
      population: '~55 million (≈ 25% of world)',
      territory: '~1.9 million km² (≈ Mexico)',
      capitals: [{ name: 'Rome' }],
      languages: ['Latin'],
      government: [
        { label: 'Mixed republic', description: 'Power split among annually elected magistrates (consuls, praetors, etc.), the aristocratic Senate, and popular assemblies. Designed to prevent any one faction from dominating; held together for nearly 500 years.' }
      ],
      religion: [
        { label: 'Roman polytheism', description: 'Inherited from the kings, but the Republic added the elected office of Pontifex Maximus, integrating religion directly into political competition.' }
      ],
      monument: [
        { label: 'Twelve Tables', description: 'Rome’s first written legal code (450 BC), produced after pressure from the plebeians. Established equality before the law and remained the foundation of Roman jurisprudence for centuries.' },
        { label: 'Appian Way', description: 'The first major paved Roman military road (begun 312 BC), running from Rome to Brundisium. Pioneered Roman engineering and the imperial road network that followed.' }
      ],
      rival: [
        { label: 'Carthage', region: 'North Africa', description: 'Phoenician maritime empire centered on modern Tunisia. Three Punic Wars (264–146 BC) ended with Carthage’s destruction; Hannibal’s invasion of Italy nearly broke Rome.' },
        { label: 'Parthia', region: 'Iran / Mesopotamia', description: 'Iranian empire that succeeded the Seleucids in the East. Defeated Crassus at Carrhae (53 BC), ending Roman expansion eastward and remaining Rome’s principal eastern foe for two centuries.' }
      ],
      leaders: [
        { name: 'Scipio Africanus', description: 'General who defeated Hannibal at Zama (202 BC), ending the Second Punic War and breaking Carthage’s power.' },
        { name: 'Gaius Marius', description: 'Reformer who opened the legions to landless citizens (107 BC), creating professional armies loyal to their generals — a structural change that doomed the Republic.' },
        { name: 'Sulla', description: 'Marched on Rome twice (88, 82 BC), the first Roman to do so; ruled as dictator and proscribed his enemies. Set the precedent for later civil-war strongmen.' },
        { name: 'Cicero', description: 'Orator, lawyer, and statesman; consul in 63 BC. His writings preserved Roman political philosophy and shaped later Western rhetoric and law.' },
        { name: 'Julius Caesar', description: 'Conquered Gaul (58–51 BC), crossed the Rubicon, and won the civil war against Pompey. His assassination in 44 BC triggered the wars that ended the Republic.' }
      ]
    },
    bluf: 'The Roman Republic transformed Rome from a regional Italian city-state into the dominant power of the entire Mediterranean world through a unique system of elected magistrates, senatorial governance, and relentless military expansion.',
    summary: [
      'Following the expulsion of the kings, Rome established a system of government based on annually elected magistrates, chief among them two consuls who shared executive power. The early Republic was defined by the Struggle of the Orders, a prolonged political conflict between the patrician aristocracy and the plebeian commoners that gradually expanded political rights through concessions like the creation of tribunes of the plebs and the codification of law in the Twelve Tables (450 BC). This internal political evolution, more than any single military victory, gave the Republic its resilience and ability to mobilize its population for war.',
      'Rome’s expansion was staggering in its scope: first dominating the Italian peninsula through wars against the Samnites, Etruscans, and Greek colonies, then defeating Carthage in three Punic Wars (264–146 BC) to gain control of the western Mediterranean. The destruction of Carthage and Corinth in 146 BC marked Rome’s emergence as an unchallenged superpower. By the late Republic, Roman territory stretched from Spain to Anatolia, with generals like Pompey conquering the eastern Mediterranean and Julius Caesar subjugating Gaul.',
      'Yet the Republic’s very success undermined its institutions. Wealth inequality, the displacement of small farmers by slave-worked latifundia, and the rise of powerful generals with personal armies led to a century of civil wars. The conflicts between Marius and Sulla, Caesar and Pompey, and finally Octavian and Mark Antony tore the Republic apart. When Octavian defeated Antony at Actium in 31 BC and received the title Augustus from the Senate in 27 BC, the Republic effectively ended.'
    ],
    territory: [
      // Italy + Cisalpine Gaul — clean clockwise around the peninsula coastline
      [
        [7.5,44.0], [7.5,45.5], [8.5,46.3], [10.5,46.8], [12.5,46.8],
        [13.8,46.5], [13.5,45.7], [12.5,45.0], [12.5,44.0], [13.5,43.0],
        [14.5,42.0], [16.0,41.5], [17.5,40.7], [18.5,40.0], [18.6,39.9], [18.0,39.8], [17.0,39.5],
        [16.5,39.3], [17.0,38.8], [16.0,38.0], [15.7,38.0], [16.0,39.0], [14.5,40.5], [13.5,41.0],
        [12.0,41.5], [11.0,42.5], [10.0,43.5], [8.5,44.3]
      ],
      // Sicily
      [[12.4,38.0],[13.5,38.4],[15.6,38.4],[15.7,37.0],[14.5,36.6],[12.5,37.5]],
      // Sardinia (Roman from 237 BC)
      [[8.0,41.3], [9.5,41.3], [9.9,40.5], [9.7,39.5], [9.3,39.1], [8.6,38.9], [8.1,39.2], [8.3,40.2]],
      // Corsica (Roman from 237 BC)
      [[8.5,43.0], [9.5,42.9], [9.6,42.2], [9.5,41.6], [9.0,41.4], [8.5,41.5], [8.6,42.3]],
      // Gaul (conquered by Caesar 58-50 BC; all under Roman control by 44 BC)
      [[5.0,52.0], [6.5,53.5], [4.5,54.0], [2.5,51.0], [0.0,49.8], [-1.5,49.0], [-2.0,48.0], [-4.5,48.0], [-5.0,47.0], [-4.0,46.0], [-1.5,43.5], [1.5,43.3], [3.5,43.3], [4.5,43.7], [6.0,43.5], [7.3,43.7], [8.0,44.0], [7.5,46.5], [6.5,49.5]],
      // Iberia
      [[-8.0,42.0],[-6.8,43.2],[-5.5,43.4],[-3.5,43.4],[-1.5,43.3],[0.5,42.7],[3.2,42.5],[3.2,40.0],[0.5,38.5],[-2.0,36.7],[-5.5,36.0],[-7.5,37.0],[-9.0,37.0],[-9.5,38.5],[-9.0,40.5]],
      // North Africa (Mauretania to Egyptian frontier — but NOT Egypt itself)
      [[-1.0,35.3],[1.0,36.5],[5.0,37.0],[8.0,37.3],[10.5,37.3],[11.5,33.5],[15.0,32.5],[20.0,31.0],[24.0,31.0],[25.2,31.2],[25.2,30.5],[23.0,30.0],[20.0,30.2],[15.0,31.0],[11.0,32.0],[8.0,33.0],[4.0,33.5],[0.0,33.5],[-1.5,34.0]],
      // Greece + Balkans (Illyricum, Macedonia, Achaea)
      [[14.0,45.0],[16.0,44.5],[18.0,44.5],[19.5,43.5],[21.5,42.5],[23.5,41.5],[25.5,41.0],[26.5,40.5],[24.0,38.0],[23.0,36.5],[21.5,36.7],[19.5,38.5],[18.5,40.0],[17.0,41.5],[15.0,43.5],[13.5,44.5]],
      // Crete (Roman province from 67 BC)
      [[23.5,35.7],[26.4,35.5],[26.0,34.8],[23.5,35.0]],
      // Asia Minor + Syria — southern boundary at the Egyptian frontier (~Gaza),
      // does NOT extend into Sinai or Egypt (Egypt was Ptolemaic in 44 BC)
      [
        [26.5,40.5], [29.0,41.5], [32.0,42.0], [34.0,42.0], [37.0,41.0],
        [39.0,39.0], [39.0,37.5], [38.0,36.0], [37.0,35.0], [36.5,34.0],
        [36.0,33.0], [35.0,32.0], [33.5,32.5], [30.5,36.5], [28.5,36.5],
        [27.0,37.0], [26.0,38.5], [26.0,39.5]
      ]
    ]
  },
  {
    id: 'empire', name: 'Roman Empire', shortName: 'Empire',
    startYear: -27, endYear: 395, color: '#DAA520', row: 0,
    bbox: [-11, 25, 50, 56],   // Full extent: Britain → Mesopotamia, Sahara → Hadrian's Wall
    peakDate: 'Peak extent · 117 AD (under Trajan)',
    stats: {
      population: '~70 million (≈ 30% of world)',
      territory: '~5 million km² (≈ half the U.S.)',
      capitals: [
        { name: 'Rome', dates: '27 BC – 330 AD' },
        { name: 'Constantinople', dates: '330 – 395 AD' }
      ],
      languages: ['Latin (West)', 'Greek (East)'],
      government: [
        { label: 'Principate', description: 'Augustus’s compromise (from 27 BC): outwardly preserved Republican forms while concentrating real power in the princeps (“first citizen”). Lasted until Diocletian.' },
        { label: 'Dominate', description: 'From Diocletian (284 AD) onward, the emperor was openly addressed as dominus (lord). Court ceremony, bureaucracy, and tax collection were drastically expanded.' }
      ],
      religion: [
        { label: 'Roman polytheism', description: 'Continued from the Republic; emperors were sometimes deified after death, and the imperial cult became a touchstone of loyalty across the provinces.' },
        { label: 'Christianity', description: 'Legalized by Constantine’s Edict of Milan (313 AD); proclaimed the official state religion by Theodosius I in 380. Drove a fundamental cultural transformation.' }
      ],
      monument: [
        { label: 'Colosseum', description: 'The Flavian Amphitheatre, completed 80 AD under Titus. Held ~50,000 spectators for gladiatorial games; the largest ancient amphitheater ever built.' },
        { label: 'Pantheon', description: 'Hadrian’s temple to all gods (~126 AD), with a 43m unreinforced concrete dome — an engineering benchmark unsurpassed for over 1,000 years.' },
        { label: 'Hadrian’s Wall', description: '73-mile fortification across northern Britain (begun 122 AD), marking the empire’s permanent northwest frontier with the Caledonian tribes.' }
      ],
      rival: [
        { label: 'Parthia', region: 'Iran / Mesopotamia', description: 'Iranian empire that had been Rome’s eastern rival since the late Republic. Trajan briefly conquered Mesopotamia in 116 AD before withdrawal.' },
        { label: 'Sassanid Persia', region: 'Iran', description: 'Replaced Parthia as the eastern superpower in 224 AD. Crippled Rome at Edessa (260 AD) by capturing emperor Valerian; persistent rival for four centuries.' }
      ],
      leaders: [
        { name: 'Augustus', description: 'First emperor (27 BC – 14 AD); founded the Principate, consolidated borders, and presided over the start of the Pax Romana — two centuries of relative peace.' },
        { name: 'Trajan', description: 'Optimus Princeps (98–117 AD). Conquered Dacia and Mesopotamia at the empire’s territorial peak; the Forum and Column of Trajan commemorate his campaigns.' },
        { name: 'Hadrian', description: 'Successor to Trajan (117–138 AD); consolidated his predecessor’s gains, withdrew from Mesopotamia, and built the famous wall in Britain. Patron of arts and architecture.' },
        { name: 'Marcus Aurelius', description: 'Last of the “Five Good Emperors” (161–180 AD); fought the Marcomannic Wars on the Danube. Author of the Stoic Meditations.' },
        { name: 'Constantine I', description: 'Reunified the empire (324 AD), legalized Christianity, founded Constantinople (330), and convened the Council of Nicaea (325). Set the eastern empire’s trajectory for the next millennium.' }
      ]
    },
    bluf: 'The Roman Empire represented the zenith of Roman civilization, a period when a single state governed the entire Mediterranean world and beyond, achieving unprecedented levels of urbanization, legal sophistication, and cultural integration across three continents.',
    summary: [
      'Augustus, the first emperor, established the principate — a system that preserved republican forms while concentrating real power in the emperor. The early Imperial period, known as the Pax Romana (27 BC – 180 AD), brought roughly two centuries of relative peace and prosperity to the Mediterranean world. During this era, the empire reached its maximum territorial extent under Emperor Trajan (117 AD), encompassing some 5 million square kilometers from Britain to Mesopotamia. Roman infrastructure — roads, aqueducts, harbors, and cities — knitted this vast territory into a functional whole.',
      'The empire’s population peaked at an estimated 55–70 million people, roughly one-quarter of the world’s population at the time. Cities like Rome (with over 1 million inhabitants), Alexandria, Antioch, and Carthage were among the largest in the world. Latin in the west and Greek in the east served as common languages of administration and culture. The empire facilitated trade networks stretching from Britain to India and China, and its cultural achievements — from the Colosseum and Pantheon to the legal codes later compiled under Justinian — would shape Western civilization for millennia.',
      'The Crisis of the Third Century (235–284 AD) nearly destroyed the empire, with civil wars, plague, and barbarian invasions fragmenting Roman power. Emperor Diocletian (284–305 AD) stabilized the situation through radical reforms, including dividing the empire into eastern and western administrative halves under the Tetrarchy. Constantine the Great reunified the empire, founded Constantinople as a new eastern capital, and legalized Christianity. However, the structural division between east and west deepened, and in 395 AD, upon the death of Emperor Theodosius I, the empire was permanently divided between his two sons.'
    ],
    territory: [
      // Continental: Iberia + Gaul + Italy + Balkans + Dacia + Anatolia + Levant + Egypt + N.Africa + Mesopotamia
      [[-9.5,43.0],[-8.5,44.5],[-1.5,46.0],[0.0,49.5],[2.0,51.0],[4.0,52.0],[6.5,51.5],[8.0,50.0],[10.5,49.0],[13.0,48.5],[17.0,47.7],[21.0,48.0],[26.0,48.0],[28.5,46.0],[30.5,45.5],[35.0,45.0],[40.0,43.5],[42.5,40.5],[44.0,38.5],[46.5,37.0],[44.5,34.5],[47.0,31.0],[44.0,32.0],[37.0,29.5],[34.5,28.0],[33.5,24.0],[31.5,26.5],[27.0,28.0],[25.0,30.5],[15.0,31.0],[10.0,33.0],[0.0,35.0],[-6.0,33.5],[-9.5,33.8],[-9.5,37.0],[-9.0,41.0]],
      // Britannia (south of Hadrian's Wall)
      [[-5.5,50.0],[-4.5,51.5],[-3.5,54.5],[-1.5,55.0],[0.5,54.0],[1.8,52.5],[1.0,51.0],[-0.5,50.5],[-3.5,50.0]]
    ]
  },
  {
    id: 'western', name: 'Western Roman Empire', shortName: 'Western',
    startYear: 395, endYear: 476, color: '#8B0000', row: 0,
    bbox: [-11, 30, 24, 56],   // Western half + Britain
    peakDate: 'Extent c. 418 AD (post-split)',
    stats: {
      population: '~25 million (≈ 13% of world, declining)',
      territory: '~2.4 million km² (≈ Algeria)',
      capitals: [
        { name: 'Mediolanum', dates: '286 – 402 AD' },
        { name: 'Ravenna', dates: '402 – 476 AD' }
      ],
      languages: ['Latin'],
      government: [
        { label: 'Late Dominate', description: 'The autocratic system of Diocletian and Constantine, but in slow disintegration. Western emperors increasingly dominated by their generals (Stilicho, Aetius, Ricimer — often barbarian magistri militum).' }
      ],
      religion: [
        { label: 'Nicene Christianity', description: 'The orthodox Trinitarian Christianity defined at Nicaea (325) and reaffirmed at Constantinople (381); made the official Roman religion by Theodosius in 380.' }
      ],
      monument: [
        { label: 'Notitia Dignitatum', description: 'An illustrated administrative register from c. 400 AD listing every imperial office, military unit, and frontier post — our richest single source on the late Roman state.' }
      ],
      rival: [
        { label: 'Visigoths', region: 'Danube → SW Gaul, Iberia', description: 'Sacked Rome itself in 410 under Alaric — the first time in 800 years — then carved out a kingdom in southern Gaul and Iberia.' },
        { label: 'Vandals', region: 'Rhine → North Africa', description: 'Crossed Gaul, Spain, and into North Africa (429); from Carthage they sacked Rome in 455 and severed the grain supply that fed Italy.' },
        { label: 'Huns', region: 'Eurasian steppe', description: 'Steppe confederation under Attila that pillaged the Balkans and Gaul (440s–453); defeated at the Catalaunian Plains (451) by Aetius and his Visigothic allies.' }
      ],
      leaders: [
        { name: 'Honorius', description: 'Western emperor 393–423; recalled the legions from Britain (~410) and presided over the Visigothic sack of Rome. Ineffectual; effective power lay with his general Stilicho.' },
        { name: 'Valentinian III', description: 'Western emperor 425–455; nominally ruled during the loss of Africa and Aetius’s defeat of Attila. Personally killed Aetius in 454, fatally weakening the west.' },
        { name: 'Flavius Aetius', description: 'Magister militum 433–454; the “last of the Romans.” Repeatedly stitched the western empire together through diplomacy and the victory at the Catalaunian Plains.' },
        { name: 'Romulus Augustulus', description: 'Last western emperor (475–476), a teenage figurehead deposed by the Germanic chieftain Odoacer. His abdication conventionally marks the end of the Western Empire.' }
      ]
    },
    bluf: 'The Western Roman Empire endured a rapid 81-year decline as barbarian migrations, economic collapse, and political instability reduced the once-mighty western half of Rome to a rump state before its final dissolution in 476 AD.',
    summary: [
      'From the moment of its formal separation in 395 AD, the Western Empire faced existential threats that its eastern counterpart largely avoided. The west was more vulnerable to Germanic migrations across the Rhine and Danube frontiers, had a less developed urban economy, and generated less tax revenue. The Visigothic sack of Rome in 410 AD — the first time the city had fallen to a foreign enemy in 800 years — sent shockwaves through the Roman world. St. Jerome famously wrote, "The city which had taken the whole world was itself taken."',
      'The fifth century saw the progressive loss of western provinces: Britain was abandoned around 410 AD, the Vandals seized North Africa (Rome’s crucial grain supply) in 439 AD, and Gaul and Spain fragmented among Visigoths, Burgundians, and Franks. Competent military commanders like Stilicho and Aetius (who defeated Attila’s Huns at the Battle of the Catalaunian Plains in 451 AD) could delay but not reverse the empire’s contraction. By the 460s, the western emperor controlled little more than Italy itself.',
      'The end came in 476 AD when the Germanic chieftain Odoacer deposed the last western emperor, the teenaged Romulus Augustulus, and sent the imperial regalia to Constantinople. While contemporaries did not necessarily view this as the "fall of Rome" — the eastern empire continued and theoretically still claimed authority over the west — it marked the definitive end of centralized Roman governance in western Europe and is conventionally regarded as one of history’s great turning points, ushering in the early medieval period.'
    ],
    territory: [
      // Continental: Iberia → Gaul → Rhine → Alps → Italy → Pannonia/Dalmatia
      // → Adriatic → Sicily → Roman Africa → Atlantic Morocco → Atlantic Iberia.
      // Single clockwise traversal, no self-intersections.
      [
        [-9.5,42.5], [-2.0,43.5], [1.0,46.0], [-5.0,48.5], [0.0,49.5],
        [4.0,51.0], [6.5,51.5], [8.0,50.0], [8.0,47.5], [11.0,47.0],
        [14.0,46.0], [19.0,46.0], [19.0,43.5], [18.0,41.0], [17.0,38.5],
        [15.5,37.0], [12.5,37.5], [10.5,36.5], [11.0,33.0], [16.0,31.5],
        [3.0,30.5], [-3.0,30.5], [-9.5,32.0], [-9.5,36.5], [-9.5,39.5]
      ],
      // Britannia (officially Western until ~410)
      [[-5.5,50.0],[-4.5,53.0],[-2.0,55.5],[0.0,55.5],[1.5,53.0],[1.5,51.5],[-0.5,50.5],[-3.0,50.0]]
    ]
  },
  {
    id: 'eastern', name: 'Eastern Roman Empire', shortName: 'Byzantine',
    startYear: 395, endYear: 1453, color: '#6A0DAD', row: 1,
    bbox: [-9, 24, 46, 49],    // Eastern Med + Justinian reconquests (Italy, N. Africa, SE Spain)
    peakDate: 'Peak extent · ~555 AD (under Justinian)',
    stats: {
      population: '~26 million (≈ 13% of world)',
      territory: '~3.5 million km² (≈ India)',
      capitals: [{ name: 'Constantinople' }],
      languages: ['Greek', 'Latin (until ~610 AD)'],
      government: [
        { label: 'Dominate', description: 'The autocratic late-Roman system inherited from Diocletian and Constantine. Strong central bureaucracy, elaborate court ceremony, and a sacralized emperor.' },
        { label: 'Theme system', description: 'From the 7th century, Heraclius reorganized the empire into themes — military districts where soldiers held land in exchange for service. The foundation of medieval Byzantine power.' }
      ],
      religion: [
        { label: 'Orthodox Christianity', description: 'The eastern Greek-speaking branch of Christianity centered on Constantinople. Diverged from the western Latin Catholic Church over doctrine and authority, formally splitting in the Great Schism of 1054.' }
      ],
      monument: [
        { label: 'Hagia Sophia', description: 'Justinian’s domed cathedral in Constantinople (completed 537 AD). For nearly a thousand years the largest church in the world; an enduring symbol of Byzantine civilization.' },
        { label: 'Corpus Juris Civilis', description: 'Justinian’s compilation of Roman law (529–534), distilling 1,000+ years of jurisprudence into a coherent code. The foundation of civil-law systems across modern Europe.' }
      ],
      rival: [
        { label: 'Sassanid Persia', region: 'Iran', description: 'The eastern superpower since 224 AD. Climactic war 602–628 left both empires exhausted; Persia fell to the Arabs within twenty years.' },
        { label: 'Caliphate', region: 'Arabia / Levant', description: 'Arab Islamic state that conquered Syria, Egypt, and North Africa from Byzantium in the 630s–640s, halving the empire’s territory in a single generation.' },
        { label: 'Ottoman Turks', region: 'Anatolia', description: 'Anatolian Turkish dynasty that gradually swallowed Byzantine territory through the 14th–15th centuries. Took Constantinople in 1453 under Mehmed II, ending the empire.' }
      ],
      leaders: [
        { name: 'Justinian I', description: 'Reigned 527–565. Reconquered Italy, Africa, and southern Spain, codified Roman law, and built the Hagia Sophia. The empire’s greatest reach after the western collapse.' },
        { name: 'Heraclius', description: 'Reigned 610–641. Defeated Sassanid Persia in a desperate war (628), then watched Syria, Palestine, and Egypt fall to the Arabs. Made Greek the official language of state.' },
        { name: 'Basil II', description: '“Bulgar-slayer” (976–1025). Pushed the empire to its greatest extent since Justinian, conquering Bulgaria and stabilizing the eastern frontier.' },
        { name: 'Constantine XI', description: 'Last Byzantine emperor; died fighting at the walls of Constantinople when Mehmed II’s Ottomans took the city on 29 May 1453.' }
      ]
    },
    bluf: 'The Eastern Roman Empire, later known as the Byzantine Empire, preserved and transformed Roman civilization for over a thousand years, serving as Christendom’s bulwark against successive waves of Persian, Arab, and Turkish expansion until its fall to the Ottoman Turks in 1453.',
    summary: [
      'Unlike its western counterpart, the Eastern Empire possessed tremendous structural advantages: wealthier and more urbanized provinces, the virtually impregnable capital of Constantinople (protected by the famous Theodosian Walls and its strategic position on the Bosporus), a more developed bureaucracy, and a strong monetary economy based on the gold solidus — the dollar of the medieval world. Under Emperor Justinian I (527–565 AD), the empire experienced a dramatic resurgence, reconquering North Africa, Italy, and southern Spain, codifying Roman law in the Corpus Juris Civilis (which remains the foundation of civil law in much of Europe today), and constructing the Hagia Sophia.',
      'The centuries following Justinian brought existential crises: devastating wars with Sassanid Persia, the sudden loss of the wealthy eastern provinces (Syria, Egypt, North Africa) to the Arab conquests of the 7th century, and the Iconoclasm controversy that divided Byzantine society. Yet the empire proved remarkably resilient, reinventing itself around its Anatolian and Balkan heartlands. The Macedonian dynasty (867–1056) presided over a cultural and military renaissance, pushing the frontier deep into Syria and the Balkans.',
      'The empire’s long decline began with the catastrophic defeat at Manzikert (1071), which opened Anatolia to Turkish settlement. The Fourth Crusade’s sack of Constantinople in 1204 shattered the empire into competing successor states. Though the Byzantines recaptured their capital in 1261, the restored empire was a shadow of its former self. The final siege by Ottoman Sultan Mehmed II began on April 6, 1453, and the city fell on May 29, ending 1,123 years of continuous Roman governance in the east and marking the conventional end of the Middle Ages.'
    ],
    territory: [
      // Eastern main: Balkans + Anatolia + Levant + Egypt — closes through
      // the Mediterranean east of Italy (so Italy is not enclosed).
      [
        [14.8,44.2], [15.5,45.3], [18.5,45.2], [22.0,44.5], [25.0,44.0], [28.5,43.5],
        [29.0,41.5], [30.0,41.0], [34.0,42.0], [37.5,41.5], [41.0,40.5],
        [42.5,38.5], [40.0,37.0], [37.5,36.5], [36.5,33.5], [35.0,30.0],
        [33.5,28.5], [34.5,24.2], [32.0,22.5], [28.0,22.5], [25.0,22.0],
        [25.8,31.8], [22.5,33.5], [22.0,35.5], [22.0,37.5], [19.5,39.5],
        [17.0,41.0]
      ],
      // Cyrenaica (eastern Libya — reached from Egypt by sea, separate ring)
      [[19.5,31.2],[22.0,31.0],[25.0,31.5],[24.5,32.8],[21.0,33.0],[18.5,32.2]],
      // Italy + Sicily (reconquered Gothic Kingdom 535–554 AD)
      [
        [7.5,44.0], [9.0,45.5], [12.5,46.5], [14.0,46.0], [13.5,45.5],
        [13.5,43.5], [15.0,42.0], [16.5,41.5], [18.5,40.5], [18.0,40.0],
        [16.5,39.5], [16.0,38.0], [15.65,38.25], [14.0,38.2], [12.5,38.0], [12.5,36.7], [14.5,36.6], [15.2,37.0], [15.65,37.5], [15.65,38.25],
        [15.5,40.0], [13.5,41.0], [11.5,42.5],
        [10.0,43.5], [8.5,44.3]
      ],
      // Sardinia + Corsica (reconquered)
      [[8.0,43.3],[9.8,43.3],[9.8,38.8],[8.4,38.8]],
      // Roman Africa (Tunisia + Tripolitania, reconquered from Vandals 533–534)
      [[7.5,37.0],[10.5,37.5],[11.5,36.5],[11.5,34.0],[14.5,32.5],[15.0,33.0],[12.0,32.0],[10.0,33.5],[8.5,34.5]],
      // Spania (reconquered SE Spain coastal strip, ~552 AD)
      [[-5.3,36.2],[-4.5,36.8],[-3.5,37.5],[-2.0,37.8],[-1.0,37.5],[-1.5,37.0],[-2.5,36.5],[-4.0,36.2],[-5.3,36.2]]
    ]
  }
];
