import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from datetime import datetime
import re

# URL der EntGroup China Box Office Seite
URL = "http://english.entgroup.cn/boxoffice/cn/daily/"

def get_session():
    """Erstellt eine robuste Browser-Session."""
    session = requests.Session()
    # China-Verbindungen können wackelig sein, daher mehr Retries
    retry = Retry(connect=5, read=5, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def clean_text(text):
    """Entfernt Zeilenumbrüche und doppelte Leerzeichen."""
    if not text: return ""
    text = text.replace('\n', ' ').replace('\r', ' ')
    return " ".join(text.split())

def get_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    session = get_session()
    movies = []
    page_date = datetime.now().strftime("%d.%m.%Y") # Default: Heute

    print(f"Lade Daten von {URL}...")
    
    try:
        response = session.get(URL, headers=headers, timeout=60)
        # EntGroup hat manchmal Encoding Probleme, wir zwingen UTF-8 oder Auto
        response.encoding = response.apparent_encoding 
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Versuchen das Datum von der Seite zu lesen (input value="12/15/2025")
        try:
            date_input = soup.find('input', {'id': 'txtDate'})
            if date_input and date_input.get('value'):
                raw_date = date_input.get('value') # Format MM/DD/YYYY
                dt = datetime.strptime(raw_date, '%m/%d/%Y')
                page_date = dt.strftime("%d.%m.%Y")
        except:
            pass # Fallback auf Heute

        # 2. Tabelle suchen (meistens id="table1" oder einfach die Haupttabelle)
        # EntGroup nutzt oft IDs, aber wir suchen generisch nach der Tabelle mit den BoxOffice Daten
        table = soup.find('table')
        if not table:
            print("Keine Tabelle gefunden.")
            return [], page_date

        rows = table.find_all('tr')
        
        count = 0
        for row in rows:
            if count >= 5: break
            
            cols = row.find_all('td')
            # Die Tabelle hat viele Spalten: Rank, Title, Gross(M), Cume(M), ..., Days
            # Wir brauchen ca. 9 Spalten
            if len(cols) < 8: continue
            
            # Rank checken
            rank_text = cols[0].text.strip()
            if not rank_text.isdigit(): continue # Header überspringen
            
            # --- DATEN EXTRAHIEREN ---
            
            # Spalte 1: Rank
            rank = rank_text
            
            # Spalte 2: Title (steht oft neben einem Bild)
            # Wir holen nur den Text, bereinigt
            title = clean_text(cols[1].text)
            
            # Spalte 3: Daily Gross (M) -> z.B. "$ 2.48"
            daily_raw = cols[2].text.strip().replace('$', '')
            daily = f"${daily_raw} M"
            
            # Spalte 4: Total Gross (M) -> z.B. "$ 507.15"
            total_raw = cols[3].text.strip().replace('$', '')
            total = f"${total_raw} M"
            
            # Spalte 9 (Index 8): Days -> z.B. "20"
            days = cols[8].text.strip()

            movies.append({
                'rank': rank,
                'title': title,
                'days': days,
                'daily': daily,
                'total': total
            })
            count += 1
            
        print(f"Erfolgreich {len(movies)} Filme aus China geladen.")
        return movies, page_date

    except Exception as e:
        print(f"Fehler: {e}")
        return [], page_date

def generate_html(movies, date_str):
    
    html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>China Box Office</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;800;900&display=swap" rel="stylesheet">
    <style>
        body {{ background-color: #000000; color: #ffffff; font-family: 'JetBrains Mono', monospace; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; min-height: 100vh; }}
        
        .header {{ 
            font-size: 2.5rem; font-weight: 900; text-transform: uppercase; 
            margin-bottom: 30px; letter-spacing: 2px; text-align: center; 
            border-bottom: 2px solid #333; padding-bottom: 10px; width: 100%; max-width: 1200px; 
        }}
        
        .grid-wrapper {{ width: 100%; max-width: 1200px; display:flex; flex-direction:column; gap:15px; }}

        .row-container {{ 
            display: grid; 
            grid-template-columns: 80px 1.5fr 100px 1fr 1fr; 
            gap: 15px; 
            height: 100px; 
        }}
        
        .box {{ 
            border: 2px solid #fff; border-radius: 8px; 
            display: flex; flex-direction: column; justify-content: center; 
            padding: 0 15px; background: #0a0a0a; 
            min-width: 0; /* Wichtig für Text-Overflow */
        }}
        
        .rank-box {{ border-color: #d40028; align-items: center; }} /* Rot für China */
        .rank-val {{ color: #d40028; font-size: 3.5rem; font-weight: 900; line-height: 1; text-shadow: 0 0 15px rgba(212, 0, 40, 0.4); }}
        
        .title-box {{ border-color: #ffffff; justify-content: center; }}
        .movie-title {{ 
            font-size: 1.5rem; font-weight: 800; text-transform: uppercase; 
            line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; 
            display: block; width: 100%;
        }}
        
        .days-box {{ border-color: #666; align-items: center; }}
        .days-val {{ font-size: 2rem; font-weight: 800; }}
        .days-label {{ font-size: 0.6rem; color: #888; text-transform: uppercase; margin-top: 5px; }}
        
        /* Daily (Neon Grün) */
        .daily-box {{ border-color: #39FF14; align-items: flex-end; }}
        .label-green {{ color: #39FF14; font-size: 0.7rem; font-weight: 800; margin-bottom: 2px; }}
        .val-big {{ font-size: 2rem; font-weight: 800; line-height: 1; }}
        
        /* Total (Neon Blau) */
        .total-box {{ border-color: #00F0FF; align-items: flex-end; }}
        .label-blue {{ color: #00F0FF; font-size: 0.7rem; font-weight: 800; margin-bottom: 2px; }}
        
        @media (max-width: 800px) {{
            .row-container {{ grid-template-columns: 60px 1fr; height: auto; padding-bottom: 20px; border-bottom:1px solid #333; }}
            .rank-box {{ grid-row: 1 / 3; height: 100%; }}
            .title-box {{ height: 60px; }}
            .days-box, .daily-box, .total-box {{ height: 70px; }}
        }}
    </style>
</head>
<body>
    <div class="header">CHINA KINOCHARTS | {date_str}</div>
    <div class="grid-wrapper">
    """

    if not movies:
        html += """
        <div style="border:1px solid red; padding:20px; text-align:center;">
            <h2 style="color:red">KEINE DATEN</h2>
            <p>EntGroup.cn antwortet nicht oder Struktur geändert.</p>
        </div>
        """
    else:
        for m in movies:
            html += f"""
            <div class="row-container">
                <div class="box rank-box"><div class="rank-val">{m['rank']}</div></div>
                
                <div class="box title-box" title="{m['title']}">
                    <div class="movie-title">{m['title']}</div>
                </div>
                
                <div class="box days-box"><div class="days-val">{m['days']}</div><div class="days-label">TAGE</div></div>
                
                <div class="box daily-box">
                    <div class="label-green">UMSATZ HEUTE</div>
                    <div class="val-big">{m['daily']}</div>
                </div>
                
                <div class="box total-box">
                    <div class="label-blue">GESAMT</div>
                    <div class="val-big">{m['total']}</div>
                </div>
            </div>
            """

    html += """
    </div>
    <div style="margin-top:20px; font-size:0.7rem; color:#444;">Quelle: EntGroup China</div>
</body>
</html>
    """
    
    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("index.html geschrieben.")
    except Exception as e:
        print(f"Fehler beim Schreiben: {e}")

if __name__ == "__main__":
    data, date_val = get_data()
    generate_html(data, date_val)
