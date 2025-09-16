import pymysql
from sqlalchemy import create_engine

# ====== KONFIGURASI DATABASE ======
DB_USER = 'root'
DB_PASS = ''
DB_HOST = 'localhost'
DB_PORT = 3306
DB_NAME = 'cluster_db'

# ====== KEBIJAKAN RETENSI DATA (hari) ======
DATA_RETENTION_DAYS = 365  # 1 tahun

def get_engine():
    """Mengembalikan SQLAlchemy engine dengan koneksi tervalidasi."""
    try:
        connection = pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        connection.close()
    except pymysql.err.OperationalError as e:
        if e.args and e.args[0] == 1045:
            raise Exception("❌ Username atau password salah.")
        raise Exception(f"⚠️ Gagal koneksi awal ke MySQL: {str(e)}")

    try:
        engine = create_engine(
            f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
            pool_pre_ping=True, pool_recycle=3600
        )
        return engine
    except Exception as e:
        raise Exception(f"❌ Gagal membuat engine SQLAlchemy: {str(e)}")

def get_db_name():
    return DB_NAME

def get_retention_days():
    return int(DATA_RETENTION_DAYS)