# Δελτίο εθνικών θεμάτων — monitoring agent

Agent που παρακολουθεί ελληνικά εθνικά ζητήματα (Ελληνοτουρκικά, Αιγαίο-ΑΟΖ,
Κυπριακό, Θράκη, άμυνα, μεταναστευτικό, ενέργεια) από ελληνικές, τουρκικές και
διεθνείς πηγές. Τα ευρήματα ταξινομούνται από το Claude API (κατηγορία,
σοβαρότητα 1-5, ελληνική σύνοψη, προτεινόμενη γωνία άρθρου) και εμφανίζονται
σε στατικό dashboard.

## Πώς δουλεύει

```
RSS feeds → keyword filter → Claude API (ταξινόμηση) → data/items.json → dashboard
```

- **Συλλογή**: `monitor/collector.py` — feeds από `config/sources.yaml`,
  φίλτρο από `config/keywords.yaml`
- **Ταξινόμηση**: `monitor/classifier.py` — Claude Sonnet, batch των 10
- **Dashboard**: `index.html` — φίλτρα κατηγορίας/σοβαρότητας, αναζήτηση,
  σήμανση τουρκικού αφηγήματος
- **Αυτοματισμός**: GitHub Actions κάθε ώρα (`.github/workflows/monitor.yml`)
- Διατήρηση δεδομένων: 14 ημέρες (αλλάζει στο `monitor/run.py`, `RETENTION_DAYS`)

## Εγκατάσταση (GitHub — προτεινόμενο)

1. Δημιούργησε **private ή public repo** στο GitHub και ανέβασε όλα τα αρχεία.
   Για δωρεάν GitHub Pages το repo πρέπει να είναι public.
2. **Settings → Secrets and variables → Actions → New repository secret**:
   όνομα `ANTHROPIC_API_KEY`, τιμή το API key σου από console.anthropic.com.
3. **Settings → Pages**: Source = *Deploy from a branch*, Branch = `main`,
   φάκελος `/ (root)`.
4. **Actions tab → Ethnika Monitor → Run workflow** για πρώτο χειροκίνητο
   τρέξιμο. Μετά τρέχει μόνος του κάθε ώρα.
5. Το dashboard ανοίγει στο `https://<username>.github.io/<repo>/`.

## Τοπικό τρέξιμο (δοκιμή)

```bash
pip install feedparser pyyaml
export ANTHROPIC_API_KEY=sk-ant-...
python monitor/run.py
python -m http.server 8000   # άνοιξε http://localhost:8000
```

Χωρίς API key ο agent δουλεύει, αλλά τα items μένουν αταξινόμητα.

## Κόστος

Με ~30-80 νέα items/ημέρα και Sonnet, το κόστος API είναι της τάξης λίγων
λεπτών του ευρώ ημερησίως. GitHub Actions και Pages: δωρεάν στα όρια που
χρησιμοποιεί το project.

## Επόμενα βήματα (v2)

- Scraper για NAVTEX Τουρκίας (shodb.gov.tr) και Ελληνικής Υδρογραφικής
- Ανακοινώσεις ΥΠΕΞ / ΓΕΕΘΑ / τουρκικού MSB
- Telegram alerts για ΣΟΒ ≥ 4
- Παρακολούθηση X/Twitter accounts-κλειδιά
- Αρχείο πέραν των 14 ημερών σε SQLite
