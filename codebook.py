"""
Codebook for the CBR-OF Phase 3 stakeholder workshop transcripts.

Each child node has a name, a definition and a list of coding rules. A rule is a
regular expression matched against the lower-cased sentence. Strong rules score 1
and weak rules (prefixed with '~') score WEAK; a sentence is coded at a node when
its score reaches MIN_SCORE. Edit the rules to
refine the coding, then re-run the pipeline.

Themes were derived deductively from the three workshop objectives and refined
inductively from the transcripts.
"""

MIN_SCORE = 1.0      # a sentence is coded at a node when its rule score reaches this value
WEAK = 0.5           # score of a weak rule (pattern starting with '~'); strong rules score 1
# Weak rules are broad words (for example 'rehabilitation' or 'CHP') that appear in many
# sentences about the programme in general; two weak rules, or one strong rule, are needed.

# Sentences matching any of these patterns are treated as facilitation or as presentation
# of earlier study phases and are not coded.
EXCLUDE = [r'\bphase (one|two|1|2)\b', r'\bsticky notes?\b', r'\bposters?\b', r'\b(odds ratio|p[- ]?value|adjusted)\b', r'\d+(\.\d+)?%',
           r'\b(this|our|the) (workshop|session|activity|methodology|exercise)\b', r'\bco[- ]?(creation|design|production|learning)\b',
           r'\b(aim|objectives?) of (this|the|our)\b', r'\bslides?\b', r'\bpresentation\b']
MIN_WORDS = 6         # sentences shorter than this are not coded (backchannel, "Yes. Okay.")

THEMES = [
    ('T1', 'Rehabilitation and prevention across the continuum of care', 'Objective 1: scope, focus and coverage'),
    ('T2', 'The referral loop and continuity of care', 'Objective 1: coverage and referral'),
    ('T3', 'Workforce capacity and training', 'Objective 1: training resources'),
    ('T4', 'Resources, financing and tools', 'Objective 2: resources available and needed'),
    ('T5', 'Sociocultural context: stigma, gender and silence', 'Objective 3: challenges'),
    ('T6', 'Policy, governance and implementation', 'Objective 3: challenges and opportunities'),
    ('T7', 'Survivor voice, empowerment and reintegration', 'Objectives 1 and 3: priorities'),
]

NODES = {
    # ---------------- T1
    'T1.1': ('Repair is not the end: comprehensive rehabilitation',
             'Rehabilitation (pelvic floor physiotherapy, psychosocial, occupational, counselling, reintegration) as part of fistula care beyond surgical repair.',
             [r'~rehabilitat', r'~physiotherap|\bphysios?\b', r'~pelvic floor', r'~psycho(social|logical|therap)', r'~counsel', r'occupational therap',
              r'beyond (the )?(hospital|repair|surgery)', r'not (the|an) (end|closure)', r'job is done', r'restores?\b', r'after work',
              r'integrat\w* (of )?(her|the woman|them|back)', r'corrective surgery']),
    'T1.2': ('Prevention across pregnancy, labour and the postnatal period',
             'Risk identification, partograph or labour guide, facility delivery, contraception, and postnatal reviews as prevention and early detection.',
             [r'~prevent', r'partograph|patrograph|labou?r guide', r'post[- ]?natal|post[- ]?delivery|post[- ]?birth|after deliver', r'contracepti|family planning',
              r'antenatal|\banc\b', r'~high[- ]risk', r'~week (2|two|6|six)\b|\b(two|six) weeks', r'deliver\w* (in|at) (a )?(proper |health)', r'facility deliver|skilled birth',
              r'adolescent', r'labou?r wards?']),
    'T1.3': ('Care before surgery and conservative management',
             'Pre-operative preparation, self-care while waiting for repair, and physiotherapy without surgery.',
             [r'before (the )?surgery|pre[- ]?operative|pre[- ]?op\b', r'as they are waiting|while waiting|waiting for (repair|surgery)', r'(minus|without) surgery', r'conservative']),
    'T1.4': ('Care where women live',
             'Shifting care from referral hospitals to communities and homes, including home-based care.',
             [r'where they are\b', r'where (they|she|women) (live|are living|stay)', r'home[- ]based', r'travel (so|all the way)', r'(reach|visit|feed) (them|these women)',
              r'at (their|the) (home|community) level', r'continue beyond the hospital', r'health facility aspect']),
    'T1.5': ('Long-term follow-up and future pregnancies',
             'Follow-up schedules after repair, monitoring until full recovery, and planned delivery in later pregnancies.',
             [r'~follow[- ]?up', r'(another|next|subsequent|future) pregnanc', r'three months|six months|one year', r'for review', r'recover fully|until they recover',
              r'after the camp', r'continuous process']),
    # ---------------- T2
    'T2.1': ('Community identification and entry points',
             'Who identifies women: CHPs, survivors and champions, family, TBAs, community resource persons, midwives, self-referral.',
             [r'~\bchps?\b|community health (promoter|volunteer|worker)s?', r'traditional birth|\btbas?\b|\btbs\b', r'\bcorps?\b|\bcops\b|community owned resource',
              r'self[- ]referral', r'identif\w* (the |this |these |a )?(high[- ]risk )?(case|woman|women|mother|client|patient|fistula)', r'household visit',
              r'(given )?birth at home', r'women trust', r'first person on the loop', r'bring themselves to the hospital']),
    'T2.2': ('Missed diagnosis and the fourth delay',
             'Women missed at Levels 1 to 3, delays within the health system, diagnosis and screening methods.',
             [r'fourth delay|4th delay', r'delay within', r'miss(ed)? (a lot of )?(these )?(women|mothers|cases)|where we miss', r'~diagnos', r'\bdye\b|methylene', r'speculum',
              r'level (2|3|two|three)\b', r'too late', r'not referring', r'occur silently|not be very obvious', r'present (herself|themselves)']),
    'T2.3': ('Two-way referral tools and linkages',
             'Referral tools, SBAR, referral notes, discharge protocols and linkage between facilities, CHPs and sub-county coordinators.',
             [r'~referr?al (tool|note|form|pathway|system|loop)', r'refer\w* back', r'two[- ]way', r'~linkage|linked to (a )?facility', r'\bsbar\b', r'communication between',
              r'up[- ]?down|bottom[- ]?up|top[- ]?down', r'coordinator', r'escalate', r'continuity of care', r'information telling people']),
    'T2.4': ('Discharge through rehabilitation',
             'Gaps between surgery, physiotherapy and return to the community.',
             [r'~discharg', r'go home and', r'release (them|her) home|released home', r'don.t go through physio|huge gap', r'join us in the hospital',
              r'link between the hospital and the community']),
    'T2.5': ('Ownership, champions and accountability',
             'Unassigned responsibility, fistula champions, and contested professional ownership of rehabilitation.',
             [r'~champion', r'~unassigned|responsibilit', r'not a business of|role of a physiotherapist', r'accountab', r'we don.t have anyone']),
    'T2.6': ('Treatment backlog and recurrence',
             'Unmet need for repair and recurrent fistula.',
             [r'recurren', r'(3,000|1,000) (cases|being)|backlog|only \d[\d,]* being repaired']),
    # ---------------- T3
    'T3.1': ('Knowledge does not translate into practice',
             'Gap between knowledge and practice, outdated or partial knowledge, untrained cadres.',
             [r'knowledge and practice|knowledge does not|into practice', r'(don.t|do not|doesn.t) (know|understand)( so much)? about fistula', r'not every physio',
              r'outdated', r'translated to', r'how many of us are trained', r'not trained', r'knows how to']),
    'T3.2': ('Who should be trained',
             'Multidisciplinary targets: midwives, nurses, doctors, physiotherapists, counsellors, CHAs and CHPs, families and opinion leaders.',
             [r'train\w* (the |all |our )?(chps?|chas?|midwi|nurses|doctors|physio|counsel|community health|health ?care (workers|providers)|everyone|family|opinion leaders|spouse|gps|ceps|church)',
              r'(midwives|obstetricians|physiotherapists?|counsel+ors|psychologists) (on board|should|need|coming in)', r'involve (the )?(counsel|men|everyone)',
              r'who should (we )?train', r'special(ty|i[sz]ed) training', r'involves everyone', r'enhance (the |our )?(knowledge|skills)', r'~(be )?empowered', r'~all levels']),
    'T3.3': ('What training should cover',
             'Proposed content: anatomy, risk factors, three delays, prevention, identification, referral, rehabilitation, psychosocial and economic empowerment.',
             [r'(curriculum|course|training) (will|should) (cover|include|look)', r'risk factors', r'three delays|3 delays', r'early identification', r'train\w* on\b',
              r'~teach', r'~we look at', r'focus on a few']),
    'T3.4': ('How training should be delivered',
             'Short course (BOFC), duration, pre-service and in-service, CPD, cascade training, manuals, segmentation, curricula, examinations, digital learning.',
             [r'short course|\bbofc\b|basic obstetric fistula course', r'one week', r'~curricul', r'~pre[- ]?service|in[- ]?service|on[- ]job', r'cascad|segment', r'manual',
              r'\bcpd\b|continuous professional', r'~\bapp\b', r'medical school|mandatory', r'situational analysis', r'~facilitator', r'education that is in school']),
    'T3.5': ('Professional culture and conduct',
             'Culture change and professionalism in how health workers treat women.',
             [r'culture change|code of conduct|professionalism|positive attitude']),
    # ---------------- T4
    'T4.1': ('Existing services and partners',
             'Facilities, fistula centres, camps, NGOs and partners already supporting fistula care.',
             [r'jamaa|gynocare|guyana care|pumwani|samaritan|amref|wadadi', r'\bngos?\b', r'fistula (camp|centre|center|clinic)|\bcamps?\b', r'we have a clinic',
              r'~(stakeholders|partners)']),
    'T4.2': ('Health insurance (SHA) gaps',
             'Rehabilitation not covered, limited understanding and utilization of SHA packages.',
             [r'~\bsha\b|\bshif\b|insur|\bnhif\b', r'~package', r'sensiti[sz]ed\b', r'not utili[sz]ed']),
    'T4.3': ('Transport and household costs',
             'Distance, fares, incentives and household control of money.',
             [r'~transport', r'\bfares?\b|taxi', r'~travel', r'shillings|\bksh', r'incentive', r'(purse|pass) holders|hold the money|sell a single cow']),
    'T4.4': ('Funding and sustainability',
             'Programme funding, collaborative financing and sustainability.',
             [r'~\bfund', r'~financ', r'\busd\b|dollars', r'sustainab', r'cannot work alone', r'very little money']),
    'T4.5': ('Rehabilitation workforce availability',
             'Availability of physiotherapists and CHP coverage.',
             [r'one physiotherapist|physiotherapists? in all|5,000 people', r'staff shortage|staffing|human resource', r'there but not all']),
    'T4.6': ('Data, tools and digital systems',
             'Lack of rehabilitation data, checklists, outcome tools, assessment templates, CHP tablets, apps, partograph use.',
             [r'~\bdata\b', r'checklist', r'outcome tools?', r'~questionnaire', r'template', r'tablet', r'\bapp\b', r'echis', r'documentation', r'partograph|patrograph']),
    # ---------------- T5
    'T5.1': ('Stigma, isolation and hidden women',
             'Stench, exclusion from church and market, concealment and isolation.',
             [r'stigma', r'stench|smell', r'hidden', r'isolat', r'segregat', r'church doesn.t want', r'not coming out', r'own doing']),
    'T5.2': ('Impact on women, partners and families',
             'Abandonment, multidimensional consequences, effects on husbands and children.',
             [r'husbands?', r'abandon', r'left (us|me|by)', r'suicide', r'orphan', r'disappeared', r'consequences', r'self[- ]esteem', r'whole (family|families)|families as a whole',
              r'take care of themselves', r'violence']),
    'T5.3': ('Men as gatekeepers and allies',
             'Men controlling money, and male involvement in counselling, advocacy and prevention.',
             [r'~\bmen\b', r'\bmales?\b', r'~\bpartners?\b', r'young boys', r'a man has', r'(purse|pass) holders', r'spouse', r'mother[- ]in[- ]law']),
    'T5.4': ('Poverty and the framing of fistula',
             'Fistula and poverty, and the framing of fistula as a disease of the poor.',
             [r'\bpoor\b', r'poverty', r'money in (their|women.s) pockets', r'social status']),
    'T5.5': ('Religion, beliefs and traditional practitioners',
             'Religious responses, religious leaders and traditional birth attendants.',
             [r'church', r'religio', r'\bpray', r'imams?\b|mosque', r'pastor', r'~traditional', r'belief', r'\btbas?\b|\btbs\b', r'opinion leaders']),
    'T5.6': ('Silence, normalization and the need to demystify',
             'Women assuming leakage is normal, lack of community knowledge, and the need to speak openly in local languages.',
             [r'\bnormal\b', r'normali[sz]', r'demystif', r'silen', r'talk about (hiv|it|fistula)', r'speak it out', r'~awareness', r'sensiti[sz]ation', r'vernacular',
              r'local (dialect|language)', r'pamphlet', r'lack of knowledge', r'community education', r'mobili[sz]ation', r'community agenda', r'early signs']),
    # ---------------- T6
    'T6.1': ('Policy exists but implementation fails',
             'Existing frameworks and guidelines not translated into practice.',
             [r'~implement', r'documents into place', r'strategic framework', r'~guideline', r'policies written', r'policy intents', r'~in 2019']),
    'T6.2': ('Rehabilitation absent from policy',
             'Calls to revise policy to include rehabilitation, spouses and communities.',
             [r'(revis|relook)', r'should be a policy|policy should', r'interventions, they are missing']),
    'T6.3': ('Legislative and professional advocacy',
             'Fistula Act, Reproductive Health Bill, professional bodies and unions.',
             [r'fistula act', r'\bbill\b', r'kmpdu|kmbdu', r'professional bod', r'\bunions?\b', r'push it']),
    'T6.4': ('Enabling frameworks',
             'UHC, primary health care, Rehabilitation 2030, disability law and the home-based care policy.',
             [r'\buhc\b|universal health', r'primary health ?care', r'rehabilitation 2030', r'disabilit', r'home[- ]based care']),
    'T6.5': ('County planning and budgets',
             'Inclusion of fistula care in county reproductive health budgets.',
             [r'county (government|budget|integrated|plan)', r'\bcidp\b', r'doing their budgets']),
    # ---------------- T7
    'T7.1': ('Lived experience',
             'Survivors’ accounts of illness, trauma and abandonment.',
             [r'\bi was (married|left)', r'\bour husbands', r'we are also under trauma', r'like me\b', r'no communication between', r'passed it through']),
    'T7.2': ('Survivors as peers and advocates',
             'Peer groups, support groups and survivors as champions.',
             [r'\bpeer', r'support groups?', r'survivor who is a champion']),
    'T7.3': ('Economic empowerment and livelihood',
             'Life skills, gainful activity, market integration and money in women’s hands.',
             [r'economic', r'livelihood', r'life skills', r'gainful', r'into the market', r'money in (their|women.s) pockets', r'vocational', r'~empowerment']),
    'T7.4': ('Survivor-centred, co-created design',
             'Placing survivors at the centre of planning and shared ownership of the programme.',
             [r'key person', r'at the (centre|center)', r'everyone has a say', r'feeling of ownership', r'tell us more', r'cannot work alone']),
}

# Transcription errors: shown in quotations with the intended word in square brackets.
CORRECTIONS = [
    ('Guyana Care', 'Gynocare'), ('Lorette', 'Eldoret'), ('cystic fistula', 'obstetric fistula'), ('CEPs', 'CHPs'), ('CKs', 'CHAs'),
    ('CHS, the CHAS', 'CHAs'), ('GPS', 'unclear'), ('Yasha', 'name unclear'), ('I hate fistula', 'I had fistula'),
    ('Mui', 'Moi'), ('KMBDU', 'KMPDU'), ('Sha', 'SHA'), ('adolescent horse', 'adolescents'),
    ('patrograph', 'partograph'), ('COPS', 'CORPs'), ('TBS', 'TBAs'), ("he's told", "she's told"),
    ('pass holders', 'purse holders'), ('Wadadiya', 'WADADIA'), ('Wadadia', 'WADADIA'), ('sure does not', 'does not'),
]

# Personal names are masked as [name] in every quotation the pipeline outputs.
# Names after a title (Dr, Mr, Mrs, Ms, Madam, Prof, Sister) are masked automatically.
# Other names are read from a plain-text file called names_to_mask.txt (one name per
# line) placed inside the transcripts zip or next to this script. Keep that file out of
# the public repository: a list of participants' names is itself identifying data.
NAME_MASK = []

# Words excluded from the word frequency query in addition to standard English stop words.
EXTRA_STOP = '''okay ok yeah yes thank thanks think know going like really also just said say says will one two get got us maybe want actually basically
right well thing things something way lot even still much many see come came go goes went make made take took give given put look looking let lets
kind sort mean need needs needed time times today now already able use used using done every everyone everybody anything nothing someone somebody
another first second third last next back across around three four five six seven eight nine ten etc per within without whether either neither
able good great new old big small long little sure please sorry hello morning afternoon evening minutes minute room day days else allow started
start call find pick realized realise realize scored feel among whole point points question questions share important continue different idea ideas
review cases ones level levels work group part terms table note phase study participants findings report activity discussion help years aspect may might
thought happens present together learn team talked mentioned better end bring hand cover focus understand people person term speak doing'''.split()
