import urllib.request, csv, io, gspread, os, re
from google.oauth2.service_account import Credentials

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, "credenciales-sheets.json")
SHEET_ID = "1fyoc0l_WtJ4roRn47xfbf6OyjkfhlMVApCAyfH8YmWE"

print("=== FIX RUBROS: Apps Script -> Test Sheet ===\n")

# 1. Get rubro mapping from Apps Script
print("1. Obteniendo rubros desde Apps Script...")
url_as = 'https://script.google.com/macros/s/AKfycbwpRm16QpdpCNTtRwtmoZsNPesqA3Vfli2LEubvunNiV0lFTH-rKPLNaIpsm531F3c9/exec?callback=recibirPrecios&t=1'
resp = urllib.request.urlopen(url_as)
raw = resp.read().decode('utf-8')
start = raw.index('"')
end = raw.rindex('"')
csv_str = raw[start+1:end]
csv_str = csv_str.replace('\\r\\n', '\n').replace('\\r', '\n').replace('\\"', '"').replace('""', '"')

reader = csv.reader(io.StringIO(csv_str))
next(reader)
art_to_rubro = {}
for row in reader:
    if len(row) > 6 and row[6].strip():
        art = row[6].strip()
        rubro = row[5].strip().upper()
        art_to_rubro[art] = rubro
print(f"   {len(art_to_rubro)} productos mapeados")
rubros_unicos = sorted(set(art_to_rubro.values()))
print(f"   {len(rubros_unicos)} rubros distintos: {rubros_unicos}")

# 2. Connect
print("\n2. Conectando al sheet de prueba...")
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
sh = gspread.authorize(creds).open_by_key(SHEET_ID)
ws = sh.worksheet("precios")

# 3. Read all precios data
print("3. Leyendo columnas F (rubro) del sheet...")
all_data = ws.get_all_values()
header = all_data[0]
print(f"   {len(all_data)} filas totales")

# 4. Build updates for rubro column (F = col 5)
updates = []
fixed = 0
already_ok = 0
not_found = 0
for i, row in enumerate(all_data):
    if i == 0 or len(row) < 7:
        continue
    art = row[6].strip()
    current = row[5].strip()
    if not art and not current:
        continue
    if art in art_to_rubro:
        correct = art_to_rubro[art]
        if current != correct:
            updates.append({"range": f"F{i+1}", "values": [[correct]]})
            fixed += 1
        else:
            already_ok += 1
    else:
        not_found += 1

print(f"   A corregir: {fixed}, ya ok: {already_ok}, sin mapping: {not_found}")

if updates:
    print(f"\n4. Escribiendo {len(updates)} rubros correctos...")
    sh.values_batch_update({"valueInputOption": "USER_ENTERED", "data": updates})
    print("   OK")
else:
    print("\n4. No hay nada que corregir")

print("\n=== LISTO ===")
