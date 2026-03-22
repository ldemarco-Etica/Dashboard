
import os
import subprocess
from pathlib import Path

# Percorso assoluto al file della tua app
app_path = Path(r"C:\Users\luca.demarco\OneDrive - Etica Sgr SpA\Dashboard\Home.py")

# (Opzionale ma consigliato) imposta la working directory sulla cartella del progetto,
# soprattutto se dentro l'app ci sono percorsi relativi (per leggere CSV/Excel, immagini, ecc.)
cwd = app_path.parent

# Avvia Streamlit usando l'interprete Python di VS Code (quello attivo)
subprocess.run(
    ["python", "-m", "streamlit", "run", str(app_path)],
    cwd=cwd
)
