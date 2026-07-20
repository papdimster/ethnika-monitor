"""Διασταύρωση πηγών: αν το ίδιο θέμα εμφανίζεται από 2+ διαφορετικές
πηγές στο ίδιο τρέξιμο, ανεβάζουμε τη σοβαρότητα κατά 1 (μέχρι 5) και
σημειώνουμε ποιες πηγές συμφωνούν.

Η αντιστοίχιση ΔΕΝ γίνεται με γενικές λέξεις (οι τίτλοι αναδιατυπώνονται
πολύ ανάμεσα σε πηγές — π.χ. "Erdogan" έναντι "Turkish president" για το
ίδιο πρόσωπο) αλλά με ΟΝΟΜΑΤΑ/ΑΡΙΘΜΟΥΣ (κύρια ονόματα, μοντέλα όπλων,
τοποθεσίες, ημερομηνίες) που παραμένουν σταθερά ανάμεσα σε αναδιατυπώσεις.
"""
import re
from collections import defaultdict

# Λέξεις με κεφαλαίο αρχικό που ΔΕΝ είναι κύρια ονόματα (τίτλοι/ρόλοι/
# συνήθεις λέξεις πρότασης) — τις αγνοούμε για να μην μπερδεύονται με
# πραγματικές οντότητες.
GENERIC_CAPS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "with", "and", "or",
    "president", "minister", "prime", "pm", "government", "official",
    "foreign", "defense", "defence", "news", "report", "reports", "says",
    "said", "new", "greek", "turkish", "greece", "turkey", "cyprus",
    "european", "national", "state", "chief", "leader", "over", "amid",
}


def _entities(text: str) -> set:
    """Κύρια ονόματα (κεφαλαίο αρχικό, όχι γενική λέξη) + αριθμοί/μοντέλα
    (F-35, 2026, S-400) από τίτλο ή/και σύνοψη."""
    tokens = re.findall(r"[A-Za-zΑ-ΩΆ-Ώ][\w\-]*", text)
    ents = set()
    for t in tokens:
        low = t.lower()
        if re.search(r"\d", t):
            ents.add(low)  # F-35, S-400, 2026 κ.λπ. — πάντα διακριτά
        elif t[0].isupper() and len(t) >= 4 and low not in GENERIC_CAPS:
            ents.add(low)
    return ents


def _shared_strong_entity(a: set, b: set) -> bool:
    """True αν μοιράζονται τουλάχιστον μία διακριτή οντότητα (μήκους >=5
    ή με αριθμό μέσα, π.χ. f-35), ή δύο+ οντότητες οποιουδήποτε μήκους."""
    common = a & b
    if len(common) >= 2:
        return True
    if len(common) == 1:
        only = next(iter(common))
        return len(only) >= 5 or any(ch.isdigit() for ch in only)
    return False


def boost_corroborated(items: list[dict]) -> int:
    """Τροποποιεί τα items επιτόπου. Επιστρέφει πόσα αναβαθμίστηκαν.
    Σύγκριση εντός (κατηγορία, γλώσσα) — ελληνικά με ελληνικά, αγγλικά
    με αγγλικά, ώστε να μην χάνεται η αντιστοίχιση λόγω γλώσσας."""
    by_group = defaultdict(list)
    for it in items:
        by_group[(it.get("category"), it.get("lang"))].append(it)

    boosted = 0
    for group in by_group.values():
        tagged = [(_entities(it["title"] + " " + it.get("summary_raw", "")[:200]), it)
                  for it in group]
        n = len(tagged)
        for i in range(n):
            ents_i, it_i = tagged[i]
            if it_i.get("corroborated_by"):
                continue
            matches = {it_i["source"]}
            for j in range(n):
                if i == j:
                    continue
                ents_j, it_j = tagged[j]
                if it_j["source"] not in matches and _shared_strong_entity(ents_i, ents_j):
                    matches.add(it_j["source"])
            if len(matches) >= 2:
                it_i["corroborated_by"] = sorted(matches - {it_i["source"]})
                old_sev = it_i["severity"]
                it_i["severity"] = min(5, old_sev + 1)
                if it_i["severity"] != old_sev:
                    boosted += 1
    return boosted
