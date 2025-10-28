#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep 28 08:38:10 2025

@author: lucademarco
"""

import pandas as pd
import os

def create_limiti_cda_file():
    """
    Generates the 'Limiti CDA.xlsx' file from hardcoded data.
    Run this script once to create the necessary configuration file.
    """
    print("Generating CDA limits data...")
    
    limiti_data = [
        {"Fondo": "Etica Azionario", "Requirement": "LIMITI CDA", "che limite è?": "Azioni", "Min (%)": 70, "Max (%)": 100, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo AZ o SE"},
        {"Fondo": "Etica Azionario", "Requirement": "LIMITI CDA", "che limite è?": "Esposizione a mercati emergenti", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Tra le azioni, somma il peso dei titoli che hanno come CodicePaeseEsposizione uno tra i seguenti BR, CN, PL, KR, GR, TW, TR, IN, ZA, ID, MX, PE, PH, CL, CO"},
        {"Fondo": "Etica Azionario", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Azionario", "Requirement": "LIMITI CDA", "che limite è?": "Convertibili", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Al momento non è possibile calcolarlo in automatico dai dati che abbiamo. Lasciamolo in sospeso"},
        {"Fondo": "Etica Azionario", "Requirement": "LIMITI CDA", "che limite è?": "OICR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo FO"},
        
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Azioni", "Min (%)": 40, "Max (%)": 70, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo AZ o SE"},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Duration", "Min (%)": 3, "Max (%)": 9, "che dati usare": "Storico Duration", "Come calcolarlo": "il dato è già calcolato. Dato che non abbiamo il valore per ogni data, suppondendo che l'utente scelga come data di riferimento il giorno X, come valore di duration prendi quello della più vicina data antecedente ad X."},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": 15, "Max (%)": 55, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Convertibili", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Al momento non è possibile calcolarlo in automatico dai dati che abbiamo. Lasciamolo in sospeso"},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "OICR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo FO"},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Rating inferiore ad adeguato", "Min (%)": None, "Max (%)": 15, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori C, D o NR"},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Rating D", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori D"},
        {"Fondo": "Etica Bilanciato", "Requirement": "LIMITI CDA", "che limite è?": "Rating NR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori NR"},
        
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Azioni", "Min (%)": 30, "Max (%)": 60, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo AZ o SE"},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Duration", "Min (%)": 2, "Max (%)": 9, "che dati usare": "Storico Duration", "Come calcolarlo": "il dato è già calcolato. Dato che non abbiamo il valore per ogni data, suppondendo che l'utente scelga come data di riferimento il giorno X, come valore di duration prendi quello della più vicina data antecedente ad X."},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": 20, "Max (%)": 70, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Convertibili", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Al momento non è possibile calcolarlo in automatico dai dati che abbiamo. Lasciamolo in sospeso"},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Esposizione Valutaria alla divisa Euro", "Min (%)": 50, "Max (%)": 105, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceDivisaEsposizione EUR o MUL. Come controllo voglio che il risultato di questa somma deve essere uguale a 1-(somma della altre divise). Le altre divise sono JPY USD GBP SEK CAD CHF DKK NOK AUD SGD KRW HKD. Ci sono un paio di eccezioni: per i ticker 688 HK Equity e 992 HK Equity viene riportato CodiceDivisaEsposizione CNY, ma noi lo riclassifichiamo sotto HKD"},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Rating inferiore ad adeguato", "Min (%)": None, "Max (%)": 15, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori C, D o NR"},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Rating D", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori D"},
        {"Fondo": "Etica Transizione Climatica", "Requirement": "LIMITI CDA", "che limite è?": "Rating NR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori NR"},
        
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Azioni", "Min (%)": 15, "Max (%)": 40, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo AZ o SE"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Duration", "Min (%)": 2, "Max (%)": 9, "che dati usare": "Storico Duration", "Come calcolarlo": "il dato è già calcolato. Dato che non abbiamo il valore per ogni data, suppondendo che l'utente scelga come data di riferimento il giorno X, come valore di duration prendi quello della più vicina data antecedente ad X."},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": 25, "Max (%)": 85, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Convertibili", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Al momento non è possibile calcolarlo in automatico dai dati che abbiamo. Lasciamolo in sospeso"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Esposizione Valutaria alla divisa Euro", "Min (%)": 60, "Max (%)": 105, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceDivisaEsposizione EUR o MUL. Come controllo voglio che il risultato di questa somma deve essere uguale a 1-(somma della altre divise). Le altre divise sono JPY USD GBP SEK CAD CHF DKK NOK AUD SGD KRW HKD. Ci sono un paio di eccezioni: per i ticker 688 HK Equity e 992 HK Equity viene riportato CodiceDivisaEsposizione CNY, ma noi lo riclassifichiamo sotto HKD"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Rating inferiore ad adeguato", "Min (%)": None, "Max (%)": 15, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori C, D o NR"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Rating D", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori D"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "Rating NR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori NR"},
        {"Fondo": "Etica Rendita Bilanciata", "Requirement": "LIMITI CDA", "che limite è?": "OICR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo FO"},
        
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Azioni", "Min (%)": None, "Max (%)": 20, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo AZ o SE"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Duration", "Min (%)": 2, "Max (%)": 8, "che dati usare": "Storico Duration", "Come calcolarlo": "il dato è già calcolato. Dato che non abbiamo il valore per ogni data, suppondendo che l'utente scelga come data di riferimento il giorno X, come valore di duration prendi quello della più vicina data antecedente ad X."},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": 35, "Max (%)": 95, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Convertibili", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Al momento non è possibile calcolarlo in automatico dai dati che abbiamo. Lasciamolo in sospeso"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Esposizione Valutaria alla divisa Euro", "Min (%)": 75, "Max (%)": 105, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceDivisaEsposizione EUR o MUL. Come controllo voglio che il risultato di questa somma deve essere uguale a 1-(somma della altre divise). Le altre divise sono JPY USD GBP SEK CAD CHF DKK NOK AUD SGD KRW HKD. Ci sono un paio di eccezioni: per i ticker 688 HK Equity e 992 HK Equity viene riportato CodiceDivisaEsposizione CNY, ma noi lo riclassifichiamo sotto HKD"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Rating inferiore ad adeguato", "Min (%)": None, "Max (%)": 15, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori C, D o NR"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Rating D", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori D"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "Rating NR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori NR"},
        {"Fondo": "Etica Obbligazionario Misto", "Requirement": "LIMITI CDA", "che limite è?": "OICR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo FO"},
        
        {"Fondo": "Etica Obbligazionario Breve Termine", "Requirement": "LIMITI CDA", "che limite è?": "Duration", "Min (%)": 0.1, "Max (%)": 2.5, "che dati usare": "Storico Duration", "Come calcolarlo": "il dato è già calcolato. Dato che non abbiamo il valore per ogni data, suppondendo che l'utente scelga come data di riferimento il giorno X, come valore di duration prendi quello della più vicina data antecedente ad X."},
        {"Fondo": "Etica Obbligazionario Breve Termine", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": None, "Max (%)": 100, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Obbligazionario Breve Termine", "Requirement": "LIMITI CDA", "che limite è?": "Esposizione Valutaria alla divisa Euro", "Min (%)": 90, "Max (%)": 101, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceDivisaEsposizione EUR o MUL. Come controllo voglio che il risultato di questa somma deve essere uguale a 1-(somma della altre divise). Le altre divise sono JPY USD GBP SEK CAD CHF DKK NOK AUD SGD KRW HKD. Ci sono un paio di eccezioni: per i ticker 688 HK Equity e 992 HK Equity viene riportato CodiceDivisaEsposizione CNY, ma noi lo riclassifichiamo sotto HKD"},
        {"Fondo": "Etica Obbligazionario Breve Termine", "Requirement": "LIMITI CDA", "che limite è?": "Rating inferiore ad adeguato", "Min (%)": None, "Max (%)": 15, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori C, D o NR"},
        {"Fondo": "Etica Obbligazionario Breve Termine", "Requirement": "LIMITI CDA", "che limite è?": "Rating D", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori D"},
        {"Fondo": "Etica Obbligazionario Breve Termine", "Requirement": "LIMITI CDA", "che limite è?": "Rating NR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori NR"},
        
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Azioni", "Min (%)": 10, "Max (%)": 45, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo AZ o SE"},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Duration", "Min (%)": 2, "Max (%)": 9, "che dati usare": "Storico Duration", "Come calcolarlo": "il dato è già calcolato. Dato che non abbiamo il valore per ogni data, suppondendo che l'utente scelga come data di riferimento il giorno X, come valore di duration prendi quello della più vicina data antecedente ad X."},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Obbligazioni", "Min (%)": None, "Max (%)": 90, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo OB"},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Convertibili", "Min (%)": None, "Max (%)": 10, "che dati usare": "files portafoglio", "Come calcolarlo": "Al momento non è possibile calcolarlo in automatico dai dati che abbiamo. Lasciamolo in sospeso"},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Rating inferiore ad adeguato", "Min (%)": None, "Max (%)": 30, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori C, D o NR"},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Rating D", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori D"},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "Rating NR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli obbligazionari che hanno come Rating i valori NR"},
        {"Fondo": "Etica Obiettivo Sociale", "Requirement": "LIMITI CDA", "che limite è?": "OICR", "Min (%)": None, "Max (%)": 5, "che dati usare": "files portafoglio", "Come calcolarlo": "Somma il peso dei titoli che hanno come CodiceTipo FO"}
    ]
    
    df = pd.DataFrame(limiti_data)
    
    # Define the path for the output file
    output_dir = "data/limiti"
    output_path = os.path.join(output_dir, "Limiti_CDA.xlsx")
    
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the DataFrame to an Excel file
    df.to_excel(output_path, index=False)
    
    print(f"✅ Success! File saved to '{output_path}'")

if __name__ == "__main__":
    create_limiti_cda_file()
