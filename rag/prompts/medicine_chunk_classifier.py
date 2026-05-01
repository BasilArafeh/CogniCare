_BRAND_MAP = (
    "Panadol → acetaminophen, Brufen → ibuprofen, Aricept → donepezil, "
    "Exelon → rivastigmine, Ebixa → memantine, Reminyl → galantamine, "
    "Concor → bisoprolol, Lipitor → atorvastatin, Glucophage → metformin, "
    "Xanax → alprazolam, Valium → diazepam, Crestor → rosuvastatin, "
    "Zoloft → sertraline, Nexium → esomeprazole, Coumadin → warfarin, "
    "Lantus → insulin glargine, Sinemet → levodopa carbidopa, "
    "Tegretol → carbamazepine, Prozac → fluoxetine, Haldol → haloperidol, "
    "Lasix → furosemide, Ativan → lorazepam, Plavix → clopidogrel"
)

_QUERY_PARSE_SYSTEM = f"""\
Analyse this medical question. Output EXACTLY two lines — nothing else.

Line 1: one category word from: side_effects | dosage | administration | interactions_overdose | identity | general
Line 2: comma-separated lowercase generic medicine names, or "none"

Category definitions:
- side_effects      : adverse effects, warnings, precautions, safety profile
- dosage            : dose, frequency, how to take, timing
- administration    : how to apply a patch, cream, injection, or device
- interactions_overdose : drug interactions, overdose, contraindications, crushing/splitting,
                          safety in elderly/pregnant/renal patients
- identity          : what a drug is used for, drug class, mechanism
- general           : anything else

Brand name conversions: {_BRAND_MAP}

Example output:
side_effects
rivastigmine"""
