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

OrderYourself ist für UGREEN so konfiguriert, dass **kein Docker-Build und kein buildx-Plugin benötigt wird**. Compose zieht direkt das offizielle Basisimage `python:3.12-slim` und bindet den Projektcode ein.

Empfohlener Start per SSH:

```bash
sh start.sh
```

`start.sh` stoppt alte OrderYourself-Container, lädt `python:3.12-slim`, erstellt den Container neu und startet ihn. Beim ersten Start werden die Python-Abhängigkeiten automatisch in einem persistenten Docker-Volume installiert. Bei unveränderter `requirements.txt` werden sie bei späteren Neustarts nicht erneut installiert.

Danach: `http://<server>:8000`

Die SQLite-Datenbank liegt persistent unter `./data/order_yourself.db`. Der `data/`-Ordner wird beim Neuaufbau des Containers nicht gelöscht.

### UGREEN Docker GUI

1. Aktuellen Repository-Stand herunterladen/entpacken.
2. Die aktuelle `docker-compose.yml` als Compose-Projekt verwenden.
3. Das Projekt **neu erstellen/bereitstellen**; es ist kein Build-Schritt notwendig.
4. Der Container heißt `orderyourself-v2` und verwendet direkt `python:3.12-slim`.

Wenn die GUI vorher `Docker Compose requires buildx plugin to be installed` gezeigt hat, wurde noch eine ältere Compose-Datei mit `build:` verwendet. In der aktuellen `docker-compose.yml` gibt es keinen `build:`-Abschnitt mehr.

## Docker-Aufbau

- `docker-compose.yml`: UGREEN-/NAS-Standardweg ohne Buildx
- `docker-entrypoint.sh`: prüft Python 3.12, verwaltet das persistente venv und startet Uvicorn
- `start.sh`: komfortabler NAS-/SSH-Starter
- `Dockerfile`: bleibt als optionaler klassischer Build-Weg für andere Umgebungen erhalten, wird vom UGREEN-Compose-Stack aber nicht benötigt

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
