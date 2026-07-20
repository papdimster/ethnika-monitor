"""Γεωγραφική επισήμανση άρθρων — ΧΩΡΙΣ καμία κλήση API.

Ο κόσμος του beat είναι γεωγραφικά περιορισμένος (~100 σημεία), οπότε
αντί να ρωτάμε ένα μοντέλο "πού αναφέρεται αυτό" (κόστος ανά άρθρο),
κρατάμε στατικό κατάλογο τοποθεσιών με συντεταγμένες και ψάχνουμε απλή
αντιστοίχιση ονομάτων μέσα σε τίτλο+σύνοψη. Μηδενικό κόστος, άμεσο.
"""

# (ονόματα-συνώνυμα..., lat, lon)
# Το πρώτο όνομα είναι το εμφανιζόμενο· τα υπόλοιπα είναι εναλλακτικές
# γραφές/γλώσσες που ψάχνουμε στο κείμενο.
GAZETTEER = [
    # --- Ελληνικά νησιά Ανατολικού Αιγαίου ---
    (["Λέσβος", "Lesvos", "Mytilene", "Μυτιλήνη"], 39.10, 26.55),
    (["Χίος", "Chios"], 38.37, 26.13),
    (["Σάμος", "Samos"], 37.75, 26.98),
    (["Κως", "Kos"], 36.89, 27.29),
    (["Ρόδος", "Rhodes", "Rodos"], 36.43, 28.22),
    (["Καστελλόριζο", "Kastellorizo", "Meis", "Megisti"], 36.15, 29.58),
    (["Λήμνος", "Limnos", "Lemnos"], 39.92, 25.24),
    (["Ικαρία", "Ikaria"], 37.60, 26.18),
    (["Λέρος", "Leros"], 37.13, 26.85),
    (["Πάτμος", "Patmos"], 37.32, 26.55),
    (["Θάσος", "Thasos"], 40.78, 24.71),
    (["Σαμοθράκη", "Samothrace", "Samothraki"], 40.47, 25.53),
    (["Κρήτη", "Crete", "Ηράκλειο", "Iraklio", "Heraklion", "Χανιά", "Chania"], 35.24, 24.81),
    (["Γαύδος", "Gavdos"], 34.83, 24.10),

    # --- Θράκη / Έβρος ---
    (["Αλεξανδρούπολη", "Alexandroupoli", "Alexandroupolis"], 40.85, 25.87),
    (["Κομοτηνή", "Komotini", "Gümülcine"], 41.12, 25.41),
    (["Ξάνθη", "Xanthi", "İskeçe"], 41.14, 24.89),
    (["Έβρος", "Evros", "Meriç"], 41.12, 26.35),
    (["Ορεστιάδα", "Orestiada"], 41.50, 26.53),
    (["Διδυμότειχο", "Didymoteicho"], 41.35, 26.50),

    # --- Ελληνική ενδοχώρα ---
    (["Ελλάδα", "Greece", "Yunanistan"], 39.00, 22.00),  # γενικό
    (["Θράκη", "Thrace", "Trakya"], 41.10, 25.50),  # γενικό, χωρίς συγκεκριμένη πόλη
    (["Αθήνα", "Athens", "Athina"], 37.98, 23.73),
    (["Θεσσαλονίκη", "Thessaloniki", "Salonica"], 40.64, 22.94),
    (["Πειραιάς", "Piraeus"], 37.94, 23.65),

    # --- Κύπρος ---
    (["Κύπρος", "Cyprus", "Kıbrıs"], 34.90, 33.20),  # γενικό, όταν λείπει συγκεκριμένη πόλη
    (["Ψευδοκράτος", "Northern Cyprus", "TRNC", "KKTC", "Turkish Republic of Northern"], 35.30, 33.30),
    (["Λευκωσία", "Nicosia", "Lefkosia"], 35.19, 33.38),
    (["Αμμόχωστος", "Famagusta", "Varosha", "Βαρώσια", "Gazimağusa"], 35.12, 33.94),
    (["Λεμεσός", "Limassol"], 34.68, 33.04),
    (["Λάρνακα", "Larnaca"], 34.92, 33.63),
    (["Πάφος", "Paphos"], 34.78, 32.42),
    (["Κερύνεια", "Kyrenia", "Girne"], 35.34, 33.32),

    # --- Τουρκία ---
    (["Άγκυρα", "Ankara"], 39.93, 32.86),
    (["Κωνσταντινούπολη", "Istanbul", "İstanbul", "Constantinople"], 41.01, 28.98),
    (["Σμύρνη", "Izmir", "İzmir"], 38.42, 27.14),
    (["Αττάλεια", "Antalya"], 36.90, 30.71),
    (["Αδραμύττιο", "Ayvalık", "Aivali"], 39.32, 26.70),
    (["Μαρμαρίς", "Marmaris"], 36.86, 28.27),
    (["Bodrum", "Μπόντρουμ", "Αλικαρνασσός"], 37.03, 27.43),
    (["Çanakkale", "Δαρδανέλλια", "Dardanelles"], 40.15, 26.41),
    (["Mersin"], 36.80, 34.64),
    (["Iskenderun", "Αλεξανδρέττα"], 36.59, 36.17),

    # --- Λιβύη ---
    (["Τρίπολη", "Tripoli"], 32.89, 13.19),
    (["Τομπρούκ", "Tobruk"], 32.08, 23.98),
    (["Βεγγάζη", "Benghazi"], 32.12, 20.07),

    # --- Ανατολική Μεσόγειος / Μέση Ανατολή ---
    (["Κάιρο", "Cairo"], 30.04, 31.24),
    (["Βηρυτός", "Beirut"], 33.89, 35.50),
    (["Δαμασκός", "Damascus"], 33.51, 36.28),
    (["Ιερουσαλήμ", "Jerusalem"], 31.78, 35.22),
    (["Τελ Αβίβ", "Tel Aviv"], 32.08, 34.78),
    (["Χάιφα", "Haifa"], 32.79, 34.99),

    # --- Θαλάσσιοι χώροι / ΑΟΖ σημεία αναφοράς ---
    (["Αιγαίο", "Aegean"], 39.0, 25.5),
    (["Ανατολική Μεσόγειος", "Eastern Mediterranean", "EastMed"], 34.0, 30.0),
    (["Ερυθρά Θάλασσα", "Red Sea"], 20.0, 38.0),
    (["Μαύρη Θάλασσα", "Black Sea", "Karadeniz"], 43.0, 34.0),
    (["Ορμούζ", "Hormuz"], 26.57, 56.25),

    # --- Ευρώπη (θεσμικά κέντρα) ---
    (["Βρυξέλλες", "Brussels"], 50.85, 4.35),
    (["Ουάσιγκτον", "Washington"], 38.91, -77.04),
    (["Βερολίνο", "Berlin"], 52.52, 13.40),
]


def _greek_case_variants(name: str) -> set:
    """Τα ελληνικά κλίνονται — 'στη Σάμο', 'της Γαύδου', 'στην Αμμόχωστο'
    δεν περιέχουν κυριολεκτικά τις ονομαστικές μορφές 'Σάμος'/'Γαύδος'/
    'Αμμόχωστος'. Παράγουμε τις συνηθέστερες πτώσεις μέσω κατάληξης."""
    variants = {name}
    if name.endswith("ος") and len(name) > 3:
        stem = name[:-2]
        variants |= {stem + "ου", stem + "ο", stem + "ε"}
    elif name.endswith("η") and len(name) > 2:
        variants.add(name[:-1] + "ης")
    elif name.endswith("α") and len(name) > 2:
        variants.add(name[:-1] + "ας")
    return variants


def find_locations(text: str) -> list[dict]:
    """Επιστρέφει λίστα {name, lat, lon} για ό,τι αναγνωρίστηκε στο κείμενο."""
    found = []
    seen_names = set()
    for names, lat, lon in GAZETTEER:
        display = names[0]
        if display in seen_names:
            continue
        matched = False
        for name in names:
            if len(name) < 4:
                continue
            candidates = _greek_case_variants(name) if any(
                "\u0370" <= ch <= "\u03ff" for ch in name) else {name}
            if any(c in text for c in candidates):
                matched = True
                break
        if matched:
            found.append({"name": display, "lat": lat, "lon": lon})
            seen_names.add(display)
    return found


# Κατηγορίες που δεν έχει νόημα να μπαίνουν στον χάρτη — αναφέρουν
# συχνά πόλεις (Βερολίνο, Ουάσιγκτον) αλλά για ξένα εσωτερικά θέματα
# άσχετα με το γεωπολιτικό beat.
NO_GEO_CATEGORIES = {"Πράσινη Ενέργεια-Περιβάλλον", "Συντηρητική Ατζέντα"}


def tag_locations(items: list[dict]) -> int:
    """Προσθέτει item['locations'] σε κάθε άρθρο. Επιστρέφει πόσα πήραν
    τουλάχιστον μία τοποθεσία."""
    tagged = 0
    for it in items:
        if it.get("category") in NO_GEO_CATEGORIES:
            continue
        text = f"{it.get('title', '')} {it.get('summary_raw', '')[:300]} {it.get('summary_el', '')}"
        locs = find_locations(text)
        if locs:
            it["locations"] = locs
            tagged += 1
    return tagged
