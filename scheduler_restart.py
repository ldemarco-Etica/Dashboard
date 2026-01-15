# scheduler_restart.py
import schedule
import time
import os
import sys

def restart_app():
    """Riavvia l'applicazione Streamlit"""
    print(f"🔄 Riavvio automatico alle {time.strftime('%H:%M:%S')}")
    os.execv(sys.executable, ['python'] + sys.argv)

# Schedula riavvii alle 7:30 e 17:30
schedule.every().day.at("07:30").do(restart_app)
schedule.every().day.at("13:25").do(restart_app)
schedule.every().day.at("17:30").do(restart_app)

print("⏰ Scheduler attivo - riavvii programmati alle 7:30 e 17:30")

while True:
    schedule.run_pending()
    time.sleep(60)  # Controlla ogni minuto
