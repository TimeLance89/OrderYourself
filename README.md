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

## NAS / Docker starten

Der empfohlene Weg ist das mitgelieferte Startskript:

```bash
sh start.sh
```

`start.sh` stoppt alte OrderYourself-Container, baut das Image bewusst ohne Cache neu, zieht das Python-3.12-Basisimage frisch, prüft die Python-Version und startet danach den neuen Container.

Der Docker-Stack verwendet absichtlich den eindeutigen Image-Tag `orderyourself:2.0-py312` und den Container-Namen `orderyourself-v2`, damit ältere OrderYourself-Images nicht versehentlich weiterverwendet werden.

Danach: `http://<server>:8000`

Die SQLite-Datenbank liegt persistent unter `./data/order_yourself.db`. Der `data/`-Ordner wird beim Neuaufbau des Containers nicht gelöscht.

### UGREEN Docker GUI

Beim Import als Compose-Projekt die aktuelle `docker-compose.yml` aus diesem Repository verwenden und **neu bauen/erstellen**, nicht nur einen alten Container neu starten. Der neue Stack ist am Container-Namen `orderyourself-v2` erkennbar.

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
