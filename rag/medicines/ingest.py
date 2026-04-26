#Fetches medicine data from OpenFDA and saves each as a separate JSON file.
#Includes Arab/regional brand name mapping

import requests
import json
import time
import os
from tqdm import tqdm

# OUTPUT FOLDER

OUTPUT_DIR = "./data/raw/medication_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# BRAND NAME MAPPING
# generic name → list of Arab/common brand names

BRAND_MAPPING = {
    # Alzheimer's & Memory
    "donepezil":                        ["Aricept"],
    "rivastigmine":                     ["Exelon"],
    "memantine":                        ["Ebixa", "Namenda"],
    "galantamine":                      ["Reminyl"],

    # Mental Health
    "quetiapine":                       ["Seroquel"],
    "risperidone":                      ["Risperdal"],
    "sertraline":                       ["Zoloft"],
    "escitalopram":                     ["Cipralex", "Lexapro"],
    "lorazepam":                        ["Ativan"],
    "diazepam":                         ["Valium"],
    "alprazolam":                       ["Xanax"],
    "olanzapine":                       ["Zyprexa"],
    "haloperidol":                      ["Haldol"],
    "citalopram":                       ["Cipram"],
    "fluoxetine":                       ["Prozac"],
    "venlafaxine":                      ["Effexor"],
    "clonazepam":                       ["Rivotril"],
    "carbamazepine":                    ["Tegretol"],
    "sodium valproate":                 ["Depakine"],
    "pregabalin":                       ["Lyrica"],
    "gabapentin":                       ["Neurontin"],

    # Cardiovascular
    "amlodipine":                       ["Norvasc"],
    "bisoprolol":                       ["Concor"],
    "atorvastatin":                     ["Lipitor"],
    "rosuvastatin":                     ["Crestor"],
    "losartan":                         ["Cozaar"],
    "perindopril":                      ["Coversyl"],
    "furosemide":                       ["Lasix"],
    "clopidogrel":                      ["Plavix"],
    "aspirin":                          ["Aspirin", "Cardioaspirin"],
    "candesartan":                      ["Atacand"],
    "telmisartan":                      ["Micardis"],
    "propranolol":                      ["Inderal"],
    "spironolactone":                   ["Aldactone"],

    # Diabetes
    "metformin":                        ["Glucophage"],
    "gliclazide":                       ["Diamicron"],
    "glimepiride":                      ["Amaryl"],
    "sitagliptin":                      ["Januvia"],
    "insulin glargine":                 ["Lantus"],
    "insulin regular":                  ["Actrapid"],
    "insulin aspart":                   ["Novorapid"],

    # Pain & Inflammation
    "acetaminophen":                    ["Panadol", "Panadol Extra", "Panadol Advance"],
    "ibuprofen":                        ["Brufen", "Advil", "Doloraz"],
    "diclofenac":                       ["Voltaren", "Voltarol"],
    "diclofenac potassium":             ["Cataflam"],
    "naproxen":                         ["Naprosyn"],
    "tramadol":                         ["Tramal"],
    "mefenamic acid":                   ["Ponstan"],

    # Cold & Flu
    "pseudoephedrine":                  ["Sudafed"],
    "dextromethorphan":                 ["Robitussin"],
    "guaifenesin":                      ["Mucinex"],
    "chlorpheniramine":                 ["Piriton"],

    # Stomach & Digestion
    "omeprazole":                       ["Losec", "Omez"],
    "esomeprazole":                     ["Nexium"],
    "ranitidine":                       ["Zantac"],
    "domperidone":                      ["Motilium"],
    "loperamide":                       ["Imodium"],
    "lactulose":                        ["Duphalac"],
    "hyoscine butylbromide":            ["Buscopan"],
    "metoclopramide":                   ["Primperan"],
    "bismuth subsalicylate":            ["Pepto-Bismol"],

    # Allergies
    "cetirizine":                       ["Zyrtec"],
    "loratadine":                       ["Clarityne", "Claritin"],
    "fexofenadine":                     ["Telfast", "Allegra"],
    "desloratadine":                    ["Aerius"],
    "diphenhydramine":                  ["Benadryl"],

    # Antibiotics
    "amoxicillin":                      ["Amoxil", "Ospamox"],
    "amoxicillin clavulanate":          ["Augmentin"],
    "ciprofloxacin":                    ["Ciproxin", "Ciprobay"],
    "azithromycin":                     ["Zithromax", "Zithrox"],
    "metronidazole":                    ["Flagyl"],
    "clarithromycin":                   ["Klacid"],
    "trimethoprim sulfamethoxazole":    ["Septrin", "Bactrim"],
    "cephalexin":                       ["Keflex"],

    # Respiratory
    "salbutamol":                       ["Ventolin"],
    "budesonide":                       ["Pulmicort"],
    "fluticasone salmeterol":           ["Seretide"],
    "ipratropium":                      ["Atrovent"],
    "terbutaline":                      ["Bricanyl"],

    # Thyroid
    "levothyroxine":                    ["Synthroid", "Euthyrox", "Eltroxin"],

    # Skin & Topical
    "betamethasone":                    ["Betnovate"],
    "mometasone":                       ["Elocon"],
    "fusidic acid":                     ["Fucidin"],
    "clotrimazole":                     ["Canesten"],
    "mupirocin":                        ["Bactroban"],
    "povidone iodine":                  ["Betadine"],

    # Eyes
    "latanoprost":                      ["Xalatan"],
    "timolol":                          ["Timoptol"],

    # Vitamins & Supplements
    "vitamin b complex":                ["Neurobion", "Becozyme"],
    "multivitamin":                     ["Supradyn"],
    "ferrous sulfate":                  ["Ferrograd"],
    "folic acid":                       ["Folicin"],
    "melatonin":                        ["Circadin"],

    # Laxatives
    "bisacodyl":                        ["Dulcolax"],
    "polyethylene glycol":              ["Movicol"],

    # ACE Inhibitors
    "lisinopril":                       ["Zestril", "Prinivil"],
    "enalapril":                        ["Vasotec", "Renitec"],
    "ramipril":                         ["Altace", "Tritace"],

    # ARBs
    "valsartan":                        ["Diovan"],

    # Beta Blockers
    "metoprolol":                       ["Lopressor", "Betaloc"],
    "atenolol":                         ["Tenormin"],
    "carvedilol":                       ["Coreg", "Dilatrend"],

    # Calcium Channel Blockers
    "nifedipine":                       ["Adalat"],
    "diltiazem":                        ["Cardizem", "Tildiem"],

    # Diuretics
    "hydrochlorothiazide":              ["HydroDiuril", "Esidrex"],

    # Statins
    "simvastatin":                      ["Zocor"],
    "pravastatin":                      ["Pravachol"],

    # Lipid Lowering
    "ezetimibe":                        ["Zetia", "Ezetrol"],
    "fenofibrate":                      ["Tricor", "Lipanthyl"],
    "gemfibrozil":                      ["Lopid"],

    # Heart
    "digoxin":                          ["Lanoxin"],
    "sacubitril valsartan":             ["Entresto"],
    "amiodarone":                       ["Cordarone"],
    "sotalol":                          ["Betapace", "Sotacor"],

    # Diabetes
    "pioglitazone":                     ["Actos"],
    "rosiglitazone":                    ["Avandia"],
    "glibenclamide":                    ["Daonil", "Euglucon"],
    "saxagliptin":                      ["Onglyza"],
    "liraglutide":                      ["Victoza"],
    "semaglutide":                      ["Ozempic", "Wegovy"],
    "dapagliflozin":                    ["Forxiga", "Farxiga"],
    "empagliflozin":                    ["Jardiance"],
    "insulin":                          ["Lantus", "Humalog", "Novolog", "Humulin"],

    # Respiratory
    "tiotropium":                       ["Spiriva"],
    "montelukast":                      ["Singulair"],
    "theophylline":                     ["Theo-Dur", "Uniphyl"],

    # Antidepressants
    "paroxetine":                       ["Paxil", "Seroxat"],
    "duloxetine":                       ["Cymbalta"],
    "amitriptyline":                    ["Elavil", "Tryptizol"],
    "nortriptyline":                    ["Pamelor", "Allegron"],

    # Epilepsy / Mood
    "levetiracetam":                    ["Keppra"],
    "lamotrigine":                      ["Lamictal"],

    # Parkinson's
    "levodopa carbidopa":               ["Sinemet", "Duopa"],
    "pramipexole":                      ["Mirapex", "Mirapexin"],
    "ropinirole":                       ["Requip"],
    "selegiline":                       ["Eldepryl", "Jumex"],

    # Sleep
    "trazodone":                        ["Desyrel", "Molipaxin"],
    "zolpidem":                         ["Ambien", "Stilnox"],

    # Pain
    "naproxen":                         ["Naprosyn", "Aleve"],
    "morphine":                         ["MS Contin", "Morphgesic"],
    "cyclobenzaprine":                  ["Flexeril"],
    "baclofen":                         ["Lioresal"],
    "methotrexate":                     ["Rheumatrex", "Methofar"],

    # GI
    "pantoprazole":                     ["Protonix", "Pantoloc"],
    "lansoprazole":                     ["Prevacid", "Zoton"],
    "famotidine":                       ["Pepcid"],
    "ondansetron":                      ["Zofran"],

    # Allergy / Steroids
    "fluticasone nasal":                ["Flonase", "Avamys"],
    "prednisone":                       ["Deltasone", "Predsol"],

    # Bone
    "alendronate":                      ["Fosamax"],
    "risedronate":                      ["Actonel"],
    "denosumab":                        ["Prolia", "Xgeva"],
    "calcium":                          ["Caltrate", "Calcium Sandoz"],
    "vitamin d":                        ["Devit", "Vidrop", "Oleovit"],

    # Anticoagulants
    "warfarin":                         ["Coumadin", "Marevan"],
    "apixaban":                         ["Eliquis"],
    "rivaroxaban":                      ["Xarelto"],
    "dabigatran":                       ["Pradaxa"],

    # Supplements
    "vitamin b12":                      ["Neurobion", "Methylcobal"],
    "multivitamins":                    ["Supradyn", "Centrum"],
    "omega-3 fatty acids":              ["Omacor", "Lovaza"],
}

# FDA FETCH

FDA_URL = "https://api.fda.gov/drug/label.json"

def fetch_from_fda(generic_name):
    try:
        params = {
            "search": f'openfda.generic_name:"{generic_name}"',
            "limit": 1
        }
        resp = requests.get(FDA_URL, params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0]

        # Fallback: try brand name search
        params["search"] = f'openfda.brand_name:"{generic_name}"'
        resp = requests.get(FDA_URL, params=params, timeout=10)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return results[0]

    except Exception as e:
        print(f"  [error] {generic_name}: {e}")

    return None


def extract_fields(raw, generic_name, brand_names):
    """Pull only the useful fields from the raw FDA response."""
    def get(field):
        val = raw.get(field, [])
        return val[0].strip() if val else ""

    openfda = raw.get("openfda", {})

    return {
        "generic_name":       generic_name,
        "brand_names":        brand_names,
        "fda_brand_names":    openfda.get("brand_name", []),
        "manufacturer":       openfda.get("manufacturer_name", ["Unknown"])[0] if openfda.get("manufacturer_name") else "Unknown",
        "drug_class":         openfda.get("pharm_class_epc", []),
        "indications":        get("indications_and_usage"),
        "side_effects":       get("adverse_reactions"),
        "warnings":           get("warnings"),
        "precautions":        get("precautions"),
        "contraindications":  get("contraindications"),
        "dosage":             get("dosage_and_administration"),
        "drug_interactions":  get("drug_interactions"),
        "overdose":           get("overdosage"),
        "description":        get("description"),
        "storage":            get("storage_and_handling"),
    }


# MAIN

def main():
    print(f"Fetching {len(BRAND_MAPPING)} medicines from OpenFDA...\n")

    success, failed = [], []

    for generic_name, brand_names in tqdm(BRAND_MAPPING.items(), desc="Downloading"):
        # Skip if already downloaded
        filename = generic_name.replace(" ", "_") + ".json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        if os.path.exists(filepath):
            continue

        raw = fetch_from_fda(generic_name)

        if raw:
            data = extract_fields(raw, generic_name, brand_names)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            success.append(generic_name)
        else:
            # Save a minimal file so you know it was attempted
            minimal = {
                "generic_name":  generic_name,
                "brand_names":   brand_names,
                "fda_found":     False,
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(minimal, f, indent=2, ensure_ascii=False)
            failed.append(generic_name)

        time.sleep(0.4)  # avoid hitting FDA rate limit

    print(f"   Saved to: {OUTPUT_DIR}/")
    print(f"   Successfully fetched: {len(success)}")
    print(f"   Not found on FDA:     {len(failed)}")
    if failed:
        print(f"   Missing: {', '.join(failed)}")


if __name__ == "__main__":
    main()
