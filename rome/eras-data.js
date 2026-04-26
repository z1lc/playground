// Era data + city positions, all in lon/lat (WGS84). The runtime projects
// these via Lambert Conformal Conic to match the pre-baked coastlines in
// world-data.js — same projection params, so everything aligns.

window.__CITIES__ = [
  { name: 'Rome',           lon: 12.4964, lat: 41.9028 },
  { name: 'Constantinople', lon: 28.9784, lat: 41.0082 },
  { name: 'Alexandria',     lon: 29.9187, lat: 31.2001 },
  { name: 'Carthage',       lon: 10.3236, lat: 36.8585 },
  { name: 'Athens',         lon: 23.7275, lat: 37.9838 },
  { name: 'Massalia',       lon:  5.3698, lat: 43.2965 },
  { name: 'Londinium',      lon: -0.1276, lat: 51.5074 },
  { name: 'Corduba',        lon: -4.7794, lat: 37.8882 },
  { name: 'Antioch',        lon: 36.1611, lat: 36.2021 },
  { name: 'Hierosolyma',    lon: 35.2137, lat: 31.7683 },
  { name: 'Ravenna',        lon: 12.2035, lat: 44.4173 },
  { name: 'Mediolanum',     lon:  9.1900, lat: 45.4642 }
];

window.__ERAS__ = [
  {
    id: 'kingdom', name: 'Roman Kingdom', shortName: 'Kingdom',
    startYear: -753, endYear: -509, color: '#8B6914', row: 0,
    bbox: [4, 38, 20, 47],     // Italy + immediate surroundings — show the city-state clearly
    stats: {
      population: '~30,000 (city of Rome)',
      territory: '~2,500 km² (≈ Luxembourg)',
      capitals: [{ name: 'Rome' }],
      leaders: ['Romulus', 'Numa Pompilius', 'Servius Tullius', 'Tarquinius Superbus']
    },
    bluf: 'The Roman Kingdom was the foundational era when Rome grew from a mythical settlement on the Tiber into a structured city-state governed by seven kings over roughly 244 years.',
    summary: [
      'According to tradition, Rome was founded in 753 BC by Romulus, who became its first king after killing his twin brother Remus in a dispute over the city’s location. While the historical accuracy of Rome’s earliest kings is debated, archaeological evidence confirms that a significant settlement existed on the Palatine Hill by the 8th century BC. The monarchy established many of Rome’s foundational institutions, including the Senate (originally an advisory council of elders), the division of the populace into patricians and plebeians, and the first religious practices that would persist for centuries.',
      'The seven kings of Rome — Romulus, Numa Pompilius, Tullus Hostilius, Ancus Marcius, Tarquinius Priscus, Servius Tullius, and Tarquinius Superbus — each contributed to the city’s development. Numa established Rome’s religious calendar and priestly colleges. Servius Tullius reorganized the army and created the census. Under the later Etruscan-influenced kings, Rome expanded its territory across Latium and grew into a genuine urban center with monumental architecture, including the first Forum buildings and the great sewer, the Cloaca Maxima.',
      'The monarchy ended in 509 BC when the last king, Tarquinius Superbus ("Tarquin the Proud"), was overthrown in a revolt triggered by the rape of Lucretia by the king’s son. The Romans replaced the monarchy with a republic, vowing never again to be ruled by a king — a sentiment so deeply embedded in Roman culture that it persisted for nearly five centuries and made the word "rex" (king) politically toxic in Roman society.'
    ],
    territory: [
      // Latium / area around Rome
      [[11.0, 42.7], [12.0, 42.7], [12.8, 42.5], [13.4, 42.0], [13.5, 41.5], [13.0, 41.0], [12.4, 41.0], [11.6, 41.4], [11.0, 41.9]]
    ]
  },
  {
    id: 'republic', name: 'Roman Republic', shortName: 'Republic',
    startYear: -509, endYear: -27, color: '#C41E3A', row: 0,
    bbox: [-10, 28, 42, 52],   // Mediterranean basin (Iberia → Anatolia, Sahara → Gaul)
    stats: {
      population: '~55 million (≈ 25% of world)',
      territory: '~1.9 million km² (≈ Mexico)',
      capitals: [{ name: 'Rome' }],
      leaders: ['Scipio Africanus', 'Gaius Marius', 'Sulla', 'Cicero', 'Julius Caesar']
    },
    bluf: 'The Roman Republic transformed Rome from a regional Italian city-state into the dominant power of the entire Mediterranean world through a unique system of elected magistrates, senatorial governance, and relentless military expansion.',
    summary: [
      'Following the expulsion of the kings, Rome established a system of government based on annually elected magistrates, chief among them two consuls who shared executive power. The early Republic was defined by the Struggle of the Orders, a prolonged political conflict between the patrician aristocracy and the plebeian commoners that gradually expanded political rights through concessions like the creation of tribunes of the plebs and the codification of law in the Twelve Tables (450 BC). This internal political evolution, more than any single military victory, gave the Republic its resilience and ability to mobilize its population for war.',
      'Rome’s expansion was staggering in its scope: first dominating the Italian peninsula through wars against the Samnites, Etruscans, and Greek colonies, then defeating Carthage in three Punic Wars (264–146 BC) to gain control of the western Mediterranean. The destruction of Carthage and Corinth in 146 BC marked Rome’s emergence as an unchallenged superpower. By the late Republic, Roman territory stretched from Spain to Anatolia, with generals like Pompey conquering the eastern Mediterranean and Julius Caesar subjugating Gaul.',
      'Yet the Republic’s very success undermined its institutions. Wealth inequality, the displacement of small farmers by slave-worked latifundia, and the rise of powerful generals with personal armies led to a century of civil wars. The conflicts between Marius and Sulla, Caesar and Pompey, and finally Octavian and Mark Antony tore the Republic apart. When Octavian defeated Antony at Actium in 31 BC and received the title Augustus from the Senate in 27 BC, the Republic effectively ended.'
    ],
    territory: [
      // Italy + Cisalpine Gaul
      [[7.5,44.0],[7.0,44.5],[7.5,45.5],[8.5,46.3],[10.5,46.8],[12.5,46.8],[13.8,46.5],[13.5,45.8],[15.0,44.5],[16.5,43.5],[17.5,41.5],[18.5,40.2],[17.0,39.5],[16.0,37.9],[15.7,38.0],[14.0,40.5],[10.5,42.0],[8.5,40.5],[10.0,43.5],[8.5,44.3]],
      // Sicily
      [[12.4,38.0],[13.5,38.4],[15.6,38.4],[15.7,37.0],[14.5,36.6],[12.5,37.5]],
      // Iberia
      [[-9.3,42.5],[-7.0,43.5],[-3.5,43.4],[-1.5,43.3],[0.5,42.7],[3.2,42.5],[3.2,40.0],[0.5,38.5],[-2.0,36.7],[-5.5,36.0],[-7.5,37.0],[-9.0,37.0],[-9.5,38.5],[-9.3,40.5]],
      // North Africa
      [[-1.0,35.3],[1.0,36.5],[5.0,37.0],[8.0,37.3],[10.5,37.3],[11.5,33.5],[15.0,32.5],[20.0,31.0],[24.0,31.0],[25.5,31.0],[25.5,30.3],[23.0,30.0],[20.0,30.2],[15.0,31.0],[11.0,32.0],[8.0,33.0],[4.0,33.5],[0.0,33.5],[-1.5,34.0]],
      // Greece + Balkans
      [[13.5,46.0],[15.5,45.5],[17.5,45.0],[19.5,43.5],[21.5,42.5],[23.5,41.5],[25.5,41.0],[26.5,40.5],[24.0,38.0],[23.0,36.5],[21.5,36.7],[19.5,38.5],[18.5,40.0],[17.0,41.5],[15.0,43.5],[13.5,44.5]],
      // Asia Minor + Syria + Cyprus
      [[26.5,40.5],[28.5,41.3],[31.5,42.0],[34.0,42.0],[36.5,41.0],[38.5,39.5],[39.0,37.5],[38.0,36.5],[37.5,36.8],[37.0,35.5],[36.5,34.5],[36.0,33.0],[35.5,32.5],[34.5,31.5],[33.5,32.0],[32.5,33.0],[33.0,35.0],[31.0,36.5],[28.5,36.5],[27.0,37.0],[26.0,38.5],[26.0,39.5]]
    ]
  },
  {
    id: 'empire', name: 'Roman Empire', shortName: 'Empire',
    startYear: -27, endYear: 395, color: '#DAA520', row: 0,
    bbox: [-11, 25, 50, 56],   // Full extent: Britain → Mesopotamia, Sahara → Hadrian's Wall
    stats: {
      population: '~70 million (≈ 30% of world)',
      territory: '~5 million km² (≈ half the U.S.)',
      capitals: [
        { name: 'Rome', dates: '27 BC – 330 AD' },
        { name: 'Constantinople', dates: '330 – 395 AD' }
      ],
      leaders: ['Augustus', 'Trajan', 'Hadrian', 'Marcus Aurelius', 'Constantine I']
    },
    bluf: 'The Roman Empire represented the zenith of Roman civilization, a period when a single state governed the entire Mediterranean world and beyond, achieving unprecedented levels of urbanization, legal sophistication, and cultural integration across three continents.',
    summary: [
      'Augustus, the first emperor, established the principate — a system that preserved republican forms while concentrating real power in the emperor. The early Imperial period, known as the Pax Romana (27 BC – 180 AD), brought roughly two centuries of relative peace and prosperity to the Mediterranean world. During this era, the empire reached its maximum territorial extent under Emperor Trajan (117 AD), encompassing some 5 million square kilometers from Britain to Mesopotamia. Roman infrastructure — roads, aqueducts, harbors, and cities — knitted this vast territory into a functional whole.',
      'The empire’s population peaked at an estimated 55–70 million people, roughly one-quarter of the world’s population at the time. Cities like Rome (with over 1 million inhabitants), Alexandria, Antioch, and Carthage were among the largest in the world. Latin in the west and Greek in the east served as common languages of administration and culture. The empire facilitated trade networks stretching from Britain to India and China, and its cultural achievements — from the Colosseum and Pantheon to the legal codes later compiled under Justinian — would shape Western civilization for millennia.',
      'The Crisis of the Third Century (235–284 AD) nearly destroyed the empire, with civil wars, plague, and barbarian invasions fragmenting Roman power. Emperor Diocletian (284–305 AD) stabilized the situation through radical reforms, including dividing the empire into eastern and western administrative halves under the Tetrarchy. Constantine the Great reunified the empire, founded Constantinople as a new eastern capital, and legalized Christianity. However, the structural division between east and west deepened, and in 395 AD, upon the death of Emperor Theodosius I, the empire was permanently divided between his two sons.'
    ],
    territory: [
      // Continental: Iberia + Gaul + Italy + Balkans + Dacia + Anatolia + Levant + Egypt + N.Africa + Mesopotamia
      [[-9.5,43.0],[-8.5,44.5],[-1.5,46.0],[0.0,49.5],[2.0,51.0],[4.0,52.0],[6.5,51.5],[8.0,50.0],[10.5,49.0],[13.0,48.5],[17.0,48.5],[21.0,48.0],[26.0,48.0],[28.5,46.0],[30.5,45.5],[35.0,45.0],[40.0,43.5],[42.5,40.5],[44.0,38.5],[46.5,37.0],[44.5,34.5],[47.0,31.0],[44.0,30.0],[37.0,29.5],[34.5,28.0],[33.5,24.0],[31.5,23.5],[27.0,23.5],[25.0,30.5],[15.0,31.0],[10.0,33.0],[0.0,35.0],[-6.0,34.5],[-9.5,35.5],[-9.5,37.0],[-9.0,41.0]],
      // Britannia (south of Hadrian's Wall)
      [[-5.5,50.0],[-4.5,51.5],[-3.5,54.5],[-1.5,55.0],[0.5,54.0],[1.5,52.5],[1.0,51.0],[-0.5,50.5],[-3.5,50.0]]
    ]
  },
  {
    id: 'western', name: 'Western Roman Empire', shortName: 'Western',
    startYear: 395, endYear: 476, color: '#8B0000', row: 0,
    bbox: [-11, 30, 24, 56],   // Western half + Britain
    stats: {
      population: '~25 million (≈ 13% of world, declining)',
      territory: '~2.4 million km² (≈ Algeria)',
      capitals: [
        { name: 'Mediolanum', dates: '286 – 402 AD' },
        { name: 'Ravenna', dates: '402 – 476 AD' }
      ],
      leaders: ['Honorius', 'Valentinian III', 'Flavius Aetius', 'Romulus Augustulus']
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
    stats: {
      population: '~26 million (≈ 13% of world, under Justinian)',
      territory: '~3.5 million km² (≈ India, under Justinian)',
      capitals: [{ name: 'Constantinople' }],
      leaders: ['Justinian I', 'Heraclius', 'Basil II', 'Constantine XI']
    },
    bluf: 'The Eastern Roman Empire, later known as the Byzantine Empire, preserved and transformed Roman civilization for over a thousand years, serving as Christendom’s bulwark against successive waves of Persian, Arab, and Turkish expansion until its fall to the Ottoman Turks in 1453.',
    summary: [
      'Unlike its western counterpart, the Eastern Empire possessed tremendous structural advantages: wealthier and more urbanized provinces, the virtually impregnable capital of Constantinople (protected by the famous Theodosian Walls and its strategic position on the Bosporus), a more developed bureaucracy, and a strong monetary economy based on the gold solidus — the dollar of the medieval world. Under Emperor Justinian I (527–565 AD), the empire experienced a dramatic resurgence, reconquering North Africa, Italy, and southern Spain, codifying Roman law in the Corpus Juris Civilis (which remains the foundation of civil law in much of Europe today), and constructing the Hagia Sophia.',
      'The centuries following Justinian brought existential crises: devastating wars with Sassanid Persia, the sudden loss of the wealthy eastern provinces (Syria, Egypt, North Africa) to the Arab conquests of the 7th century, and the Iconoclasm controversy that divided Byzantine society. Yet the empire proved remarkably resilient, reinventing itself around its Anatolian and Balkan heartlands. The Macedonian dynasty (867–1056) presided over a cultural and military renaissance, pushing the frontier deep into Syria and the Balkans.',
      'The empire’s long decline began with the catastrophic defeat at Manzikert (1071), which opened Anatolia to Turkish settlement. The Fourth Crusade’s sack of Constantinople in 1204 shattered the empire into competing successor states. Though the Byzantines recaptured their capital in 1261, the restored empire was a shadow of its former self. The final siege by Ottoman Sultan Mehmed II began on April 6, 1453, and the city fell on May 29, ending 1,123 years of continuous Roman governance in the east and marking the conventional end of the Middle Ages.'
    ],
    territory: [
      // Eastern main: Greece + Balkans + Anatolia + Levant + Egypt + Cyrenaica
      [[15.0,44.8],[18.5,45.0],[22.0,44.5],[25.0,44.0],[28.5,43.5],[28.0,41.5],[30.0,41.0],[34.0,42.0],[37.5,41.5],[41.0,40.5],[42.5,38.5],[40.0,37.0],[37.5,36.5],[36.5,33.5],[35.0,30.0],[33.5,28.5],[34.5,24.0],[32.0,22.5],[28.0,22.5],[25.0,22.0],[24.0,30.0],[20.0,32.5],[19.5,30.5],[16.0,30.5],[20.5,33.5],[24.0,36.0],[22.0,37.5],[19.5,39.5],[17.0,41.0]],
      // Italy + Sicily (reconquered)
      [[7.5,44.0],[9.0,45.5],[12.5,46.5],[14.0,46.0],[16.5,45.5],[18.5,42.5],[18.0,40.0],[17.0,38.5],[15.0,37.5],[12.0,37.5],[15.5,38.5],[15.5,40.0],[12.0,41.5],[10.0,43.0],[8.0,43.5]],
      // Sardinia + Corsica (reconquered)
      [[8.0,41.5],[9.8,41.5],[9.8,38.8],[8.4,38.8]],
      // Roman Africa (Tunisia + Tripolitania, reconquered from Vandals)
      [[7.5,37.0],[10.5,37.5],[11.5,36.5],[11.5,34.0],[14.5,32.5],[15.0,30.5],[12.0,32.0],[10.0,33.5],[8.5,34.5]],
      // Spania (reconquered SE Spain)
      [[-6.5,37.0],[-3.5,37.5],[-1.5,38.0],[-0.5,37.5],[-2.5,36.5],[-5.5,36.0]]
    ]
  }
];
