import pandas as pd
import sys
import os
from pathlib import Path

# Añadir el directorio actual al path para importar los módulos
sys.path.insert(0, str(Path(__file__).parent))

try:
    from modules.etl import load_file, clean_and_enrich, map_columns, quality_report
    print("✅ Módulos cargados correctamente.")
except ImportError as e:
    print(f"❌ Error al cargar módulos: {e}")
    sys.exit(1)

def run_diagnostic():
    # Buscar archivos de datos en el directorio actual (priorizar CSV y Excel)
    extensions = ('.csv', '.xlsx', '.xls', '.pdf', '.docx')
    all_files = [f for f in os.listdir('.') if f.lower().endswith(extensions) 
                 and not f.startswith('~$') 
                 and f not in ('requirements.txt', 'check_data.py')]
    
    # Priorizar CSV sobre otros formatos
    csv_files = [f for f in all_files if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
    files = csv_files if csv_files else all_files

    if not files:
        print("❌ No se encontraron archivos de datos (.csv, .xlsx, .pdf, .docx) en la carpeta.")
        print("Por favor, asegúrate de que tu archivo de reservas esté en esta misma carpeta.")
        return

    target_file = files[0]
    print(f"\n🔍 Analizando archivo: {target_file}")
    print("-" * 50)

    try:
        # 1. Carga Raw
        df_raw = load_file(open(target_file, 'rb'))
        print(f"📊 Columnas encontradas: {list(df_raw.columns)}")
        
        # 2. Mapeo de columnas
        mapping = map_columns(df_raw)
        print("\n🗺️ Mapeo de columnas críticas:")
        for k, v in mapping.items():
            status = "✅" if v else "❌ NO ENCONTRADA"
            print(f"  - {k.ljust(10)} -> {str(v).ljust(20)} {status}")

        # 3. Limpieza y Enriquecimiento
        df_clean = clean_and_enrich(df_raw)
        
        # 4. Reporte de Calidad
        qr = quality_report(df_raw, df_clean)
        
        print("\n📈 Resumen de Calidad:")
        print(f"  - Total filas:         {qr['total_rows']}")
        print(f"  - Reservas 'Booked':   {qr['confirmed']} (Estas son las que el dashboard cuenta)")
        print(f"  - Con importe > 0:     {qr['with_revenue']}")
        print(f"  - Propiedades:         {qr['properties']}")
        print(f"  - Canales:             {qr['channels']}")

        if qr['confirmed'] == 0 and qr['total_rows'] > 0:
            print("\n⚠️ ALERTA: No se detectaron reservas confirmadas.")
            if 'status' in df_clean.columns:
                unique_stats = df_clean['status'].unique()
                print(f"  Estados encontrados en tu archivo: {unique_stats}")
                print("  El sistema solo busca 'Booked'. Debemos actualizar modules/etl.py")

        # 5. Muestra de importes
        if 'amount' in df_clean.columns:
            print("\n💰 Muestra de importes procesados (primeras 5 filas):")
            sample = df_clean[['amount', 'nights', 'price_per_night']].head()
            print(sample)

    except Exception as e:
        print(f"❌ Error durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()
