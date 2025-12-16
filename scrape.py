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
    # China-Verbindungen können wackelig sein
    retry = Retry(connect=5, read=5, backoff_factor=1)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def clean_text(text):
    """Entfernt Zeilenumbrüche, Dollarzeichen und doppelte Leerzeichen."""
    if not text: return ""
    text = text.replace('$', '').replace('\n', ' ').replace('\r', ' ')
    return " ".join(text.split())

def get_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    session = get_session()
    movies = []
    
    # Standard-Datum (Heute), falls wir es nicht von der Seite lesen können
    page_date = datetime.now().strftime("%d.%m.%Y")

    print(f"Lade Daten von {URL}...")
    
    try:
        response = session.get(URL, headers=headers, timeout=60)
        response.encoding = response.apparent_encoding # Encoding fixen
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Datum auslesen (Input Feld)
        try:
            date_input = soup.find('input', {'id': 'txtdate'})
            if date_input and date_input.get('value'):
                # Format: "12 /15 /2025" -> bereinigen zu "12/15/2025"
                raw_date = date_input.get('value').replace(' ', '')
                dt = datetime.strptime(raw_date, '%m/%d/%Y')
                page_date = dt.strftime("%d.%m.%Y")
        except:
            pass

        # 2. Tabelle parsen
        # Wir suchen die Tabelle mit class="person" (aus deinem Quelltext)
        table = soup.find('table', {'class': 'person'})
        if not table:
            print("Keine Tabelle 'person' gefunden.")
            return [], page_date

        rows = table.find_all('tr')
        
        count = 0
        for row in rows:
            if count >= 5: break
            
            cols = row.find_all('td')
            # Eine Datenzeile hat ca. 9 Spalten. Header hat weniger oder mehr Text.
            if len(cols) < 8: continue
            
            # Rank checken (muss eine Zahl sein)
            rank_text = cols[0].text.strip()
            if not rank_text.isdigit(): continue 
            
            # --- DATEN EXTRAHIEREN ---
            
            # 1. RANK
            rank = rank_text
            
            # 2. TITEL (Index 1)
            # Im Quelltext ist der Titel in einem <strong> Tag innerhalb eines <a> Tags
            title_col = cols[1]
            strong_tag = title_col.find('strong')
            if strong_tag:
                title = clean_text(strong_tag.text)
            else:
                title = clean_text(title_col.text)
            
            # 3. DAILY GROSS (Index 2)
            # Im Quelltext steht: <span class="moneyT">$</span>2.48
            # Wir wollen nur die Zahl "2.48"
            daily_raw = clean_text(cols[2].text)
            daily = f"${daily_raw} M"
            
            # 4. TOTAL GROSS (Index 3)
            total_raw = clean_text(cols[3].text)
            total = f"${total_raw} M"
            
            # 5. TAGE (Index 8 - Die letzte Spalte im Quelltext)
            days = clean_text(cols[8].text)

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
            display: flex; align-items: center; justify-content: center; gap: 20px;
        }}
        
        /* CHINESISCHE FLAGGE */
        .flag {{ font-size: 3rem; margin-top: -10px; }}
        
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
        
        /* Rank Box (China Rot) */
        .rank-box {{ border-color: #d40028; align-items: center; }} 
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
    <div class="header">
        <span class="flag">🇨🇳</span> 
        <span>CHINA KINOCHARTS | {date_str}</span>
    </div>
    
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
