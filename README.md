# OrderYourself

OrderYourself ist eine lokale Haushalts-App für die Frage: **Was essen wir – und was müssen wir dafür im Laden einkaufen?**

## Kernfunktionen

- Rezepte suchen, ansehen und im persönlichen Rezeptbuch speichern
- mehrere Personen pro Haushalt
- gerätebezogene Auswahl der aktuell handelnden Person
- gemeinsamer Einkaufszettel mit Live-Aktualisierung
- Zutaten mehrerer Rezepte automatisch zusammenführen
- kompatible Mengen umrechnen und addieren (`kg/g`, `l/ml`)
- Artikel nach einem plausiblen Laufweg durch den Supermarkt sortieren
- manuelle Ladenbereich-Korrekturen dauerhaft lernen
- nachvollziehen, welche Rezepte und Personen zu einer Position beigetragen haben
- Einkauf gemeinsam abhaken

## Start mit Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Danach: `http://<server>:8000`

Die SQLite-Datenbank liegt persistent unter `./data/`.

## Lokaler Start ohne Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Architektur

Der aktive Kern besteht bewusst nur aus vier Bereichen:

1. **Rezepte** – Suche und lokales Rezeptbuch
2. **Haushalt** – Personen und gemeinsame Vorlieben
3. **Einkaufszettel** – händlerunabhängiger Bedarf
4. **Smart Shopping** – Deduplizierung, Mengenlogik, Ladenbereiche und gelernte Sortierung

Der aktive Ablauf endet bewusst beim gemeinsamen, für den Laden optimierten Einkaufszettel.

## Datenschutz & Datenhaltung

Zugangsdaten, lokale Datenbanken, Browser-Sessions und Cache-Dateien werden nicht versioniert. Der gemeinsame Einkaufszettel und die Haushaltsdaten liegen lokal in SQLite.
