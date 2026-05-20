import pyodbc
import csv
import os
import sys
import io
from collections import defaultdict

# ─── CONFIGURACIÓN ───────────────────────────────────────────────────
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_SERVER = r".\SQLEXPRESS"
DB_NAME = "datosSQL"
ENCODING = "utf-8-sig"
# ─────────────────────────────────────────────────────────────────────

def conectar_bd():
    conn = pyodbc.connect(
        f"Driver={{SQL Server}};Server={SQL_SERVER};Database={DB_NAME};Trusted_Connection=yes;"
    )
    return conn

def leer_stock_desde_bd(conn):
    """Lee productos + stock desde SQL Server (SOLO SELECT)"""
    query = """
        SELECT a.codigo, a.nombre, a.precio1, a.precio2, a.familia,
               COALESCE(SUM(s.cantidad), 0) AS stock_total
        FROM articulos a
        LEFT JOIN stock_ppp s ON a.codigo = s.articulo
        WHERE a.eliminado = 0 AND a.codigo > 0 AND a.nombre != 'NULO'
        GROUP BY a.codigo, a.nombre, a.precio1, a.precio2, a.familia
        ORDER BY a.codigo
    """
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    return rows

def leer_categorias(conn):
    """Lee categorías desde la tabla familias"""
    query = "SELECT codigo, nombre FROM familias WHERE eliminado = 0 AND codigo > 0"
    cursor = conn.cursor()
    cursor.execute(query)
    return {row.codigo: (row.nombre or "").strip() for row in cursor.fetchall()}

def leer_info_csv(path):
    """Lee un archivo CSV info existente y devuelve dict por código de artículo"""
    info = {}
    if not os.path.exists(path):
        return info
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for col in ["Artículo", "Articulo"]:
                cod = row.get(col, "").strip()
                if cod and cod.isdigit():
                    info[int(cod)] = row
                    break
    return info

def leer_precios_csv(path):
    """Lee un archivo CSV de precios existente"""
    precios = {}
    if not os.path.exists(path):
        return precios
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    # Skip if it's HTML (broken file)
    if content.strip().startswith("<!DOCTYPE"):
        return precios
    lines = content.strip().split("\n")
    if len(lines) < 2:
        return precios
    header = lines[0]
    col_names = [c.strip().strip('"') for c in header.split(",")]
    for line in lines[1:]:
        if not line.strip():
            continue
        # Simple parse: split by comma but handle quotes
        parts = []
        current = ""
        in_quotes = False
        for ch in line:
            if ch == '"':
                in_quotes = not in_quotes
            elif ch == "," and not in_quotes:
                parts.append(current)
                current = ""
            else:
                current += ch
        parts.append(current)
        parts = [p.strip().strip('"') for p in parts]
        if len(parts) >= 2:
            # Try to find Artículo column
            for i, cn in enumerate(col_names):
                if cn in ["Artículo", "Articulo"] and i < len(parts):
                    cod_str = parts[i].strip()
                    if cod_str.isdigit():
                        precios[int(cod_str)] = parts
                    break
    return precios

def formatear_precio(valor):
    """Formatea precio al estilo argentino: entero con separador de miles y decimales"""
    try:
        v = float(valor)
        if v == 0:
            return "0,00"
        entero = int(v)
        decimales = int(round((v - entero) * 100))
        entero_str = f"{entero:,}".replace(",", ".")
        return f"{entero_str},{decimales:02d}"
    except (ValueError, TypeError):
        return "0,00"

def generar_precios_minorista(productos, categorias, repo_dir):
    """Genera precios-min.csv con stock"""
    out_path = os.path.join(repo_dir, "precios-min.csv")
    with open(out_path, "w", encoding=ENCODING, newline="") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(["Rubro", "Artículo", "Nombre", "Bt.LISTA 2", "Stock"])
        familia_anterior = None
        for prod in productos:
            cod = prod.codigo
            nombre = (prod.nombre or "").strip()
            rubro = categorias.get(prod.familia, "SIN CATEGORÍA")
            precio = formatear_precio(prod.precio2)
            stock = max(0, int(prod.stock_total or 0))
            writer.writerow([rubro, str(cod), nombre, precio, str(stock)])

def generar_precios_mayorista(productos, categorias, repo_dir):
    """Genera precios-may.csv con stock"""
    out_path = os.path.join(repo_dir, "precios-may.csv")
    with open(out_path, "w", encoding=ENCODING, newline="") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(["", "", "Rubro", "Artículo", "Nombre", "Bt.LISTA 2", "Stock"])
        for prod in productos:
            cod = prod.codigo
            nombre = (prod.nombre or "").strip()
            rubro = categorias.get(prod.familia, "SIN CATEGORÍA")
            precio = formatear_precio(prod.precio2)
            stock = max(0, int(prod.stock_total or 0))
            writer.writerow(["", "", rubro, str(cod), nombre, precio, str(stock)])

def generar_info_minorista(productos, info_existente, repo_dir):
    """Genera info-min.csv preservando datos existentes + stock"""
    out_path = os.path.join(repo_dir, "info-min.csv")
    fieldnames = ["nombre", "cantidades", "info", "sabores", "imagen", "mix", "Artículo", "Estado", "Stock"]
    with open(out_path, "w", encoding=ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL, extrasaction="ignore")
        writer.writeheader()
        for prod in productos:
            cod = prod.codigo
            nombre = (prod.nombre or "").strip()
            stock = max(0, int(prod.stock_total or 0))
            existente = info_existente.get(cod, {})
            row = {
                "nombre": existente.get("nombre", nombre),
                "cantidades": existente.get("cantidades", "1 UNIDAD"),
                "info": existente.get("info", ""),
                "sabores": existente.get("sabores", ""),
                "imagen": existente.get("imagen", ""),
                "mix": existente.get("mix", ""),
                "Artículo": str(cod),
                "Estado": existente.get("Estado", "🟢 ok"),
                "Stock": str(stock),
            }
            writer.writerow(row)

def generar_info_mayorista(productos, info_existente, repo_dir):
    """Genera info-may.csv preservando datos existentes + stock"""
    out_path = os.path.join(repo_dir, "info-may.csv")
    fieldnames = ["Articulo", "Nombre", "Bulto", "Sabores", "Imagen", "Stock"]
    with open(out_path, "w", encoding=ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL, extrasaction="ignore")
        writer.writeheader()
        for prod in productos:
            cod = prod.codigo
            nombre = (prod.nombre or "").strip()
            stock = max(0, int(prod.stock_total or 0))
            existente = info_existente.get(cod, {})
            row = {
                "Articulo": str(cod),
                "Nombre": existente.get("Nombre", nombre),
                "Bulto": existente.get("Bulto", ""),
                "Sabores": existente.get("Sabores", ""),
                "Imagen": existente.get("Imagen", ""),
                "Stock": str(stock),
            }
            writer.writerow(row)

def main():
    print("Conectando a SQL Server (solo lectura)...")
    try:
        conn = conectar_bd()
    except Exception as e:
        print(f"ERROR: No se pudo conectar a SQL Server: {e}")
        sys.exit(1)

    print("Leyendo productos y stock desde la base de datos...")
    try:
        productos = leer_stock_desde_bd(conn)
        categorias = leer_categorias(conn)
    except Exception as e:
        print(f"ERROR al leer datos: {e}")
        conn.close()
        sys.exit(1)
    finally:
        conn.close()

    print(f"  -> {len(productos)} productos encontrados")
    print(f"  -> {len(categorias)} categorias encontradas")

    # Leer CSVs existentes para preservar info (descripciones, imágenes)
    print("Leyendo CSVs existentes...")
    info_min = leer_info_csv(os.path.join(REPO_DIR, "info-min.csv"))
    info_may = leer_info_csv(os.path.join(REPO_DIR, "info-may.csv"))

    # Generar CSVs actualizados
    print("Generando CSVs actualizados...")
    generar_precios_minorista(productos, categorias, REPO_DIR)
    print("  OK precios-min.csv")
    generar_precios_mayorista(productos, categorias, REPO_DIR)
    print("  OK precios-may.csv")
    generar_info_minorista(productos, info_min, REPO_DIR)
    print("  OK info-min.csv")
    generar_info_mayorista(productos, info_may, REPO_DIR)
    print("  OK info-may.csv")

    print("\nSincronizacion completada con exito.")
    print("   Los archivos CSV se actualizaron con precios y stock.")
    print("   La base de datos NO fue modificada.")

if __name__ == "__main__":
    main()
