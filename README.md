# AI Trash Bin

Dieses Projekt implementiert eine interaktive, sprechende Mülltonne, die mithilfe von Google Gemini API und Spracherkennung Müll korrekt einsortiert und den passenden Mülleimer "öffnet".

## Funktionen
- **Spracherkennung**: Erkennung von Spracheingaben des Nutzers.
- **Antwortgenerierung**: Die KI erkennt Müllarten und antwortet entsprechend.
- **Mülleimersteuerung**: Die richtige Tonne wird basierend auf dem erkannten Müll geöffnet.
- **Audioausgabe**: Die KI spricht mit dem Nutzer.

## Anforderungen
- Python 3.9+
- Abhängigkeiten (installierbar mit `pip install -r requirements.txt`):
  - `google-generativeai`
  - `numpy`
  - `sounddevice`
  - `webrtcvad`
  - `python-dotenv`

## Einrichtung
1. **API-Schlüssel einrichten**
   - Erstelle eine `.env`-Datei im Projektverzeichnis.
   - Füge deinen Google Gemini API-Schlüssel hinzu:
     ```
     GENAI_API_KEY=dein_api_schluessel
     ```

2. **Installation der Abhängigkeiten**
   ```sh
   pip install -r requirements.txt
   ```

3. **Starten der Anwendung**
   ```sh
   python main.py
   ```

## Nutzung
- Sprich mit der Mülltonne und nenne einen Müllgegenstand.
- Die KI wird den passenden Mülleimer benennen und öffnen.
- Falls der Müll nicht zugeordnet werden kann, erfolgt eine entsprechende Antwort.

## Steuerung
- Beenden mit `Ctrl + C`.
- Nach jeder Sitzung kann eine neue gestartet werden.

## Lizenz
Dieses Projekt steht unter der MIT-Lizenz.

## Autor
Thiébaud Reimann
