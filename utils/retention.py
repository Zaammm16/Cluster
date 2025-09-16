from sqlalchemy import text

METADATA_TABLE = "_datasets_meta"

def ensure_meta_table(engine):
    """Buat tabel metadata bila belum ada."""
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS `{METADATA_TABLE}` (
              table_name   VARCHAR(128) NOT NULL PRIMARY KEY,
              created_at   DATETIME NOT NULL,
              expires_at   DATETIME NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """))

def register_dataset(engine, table_name: str, retention_days: int = 1):
    """
    Catat/refresh metadata untuk dataset yang baru disimpan/di-overwrite.
    """
    ensure_meta_table(engine)
    with engine.begin() as conn:
        conn.execute(text(f"""
            INSERT INTO `{METADATA_TABLE}` (table_name, created_at, expires_at)
            VALUES (:t, NOW(), DATE_ADD(NOW(), INTERVAL :days DAY))
            ON DUPLICATE KEY UPDATE
              created_at = VALUES(created_at),
              expires_at = VALUES(expires_at)
        """), {"t": table_name, "days": retention_days})

def cleanup_expired_datasets(engine, also_drop_clustered: bool = True):
    """
    Hapus tabel yang sudah lewat expires_at dan bersihkan catatannya.
    Return: list nama tabel yang dihapus.
    """
    ensure_meta_table(engine)
    removed = []
    with engine.begin() as conn:
        rows = conn.execute(text(f"SELECT table_name FROM `{METADATA_TABLE}` WHERE expires_at <= NOW()")).fetchall()
        for (tname,) in rows:
            conn.execute(text(f"DROP TABLE IF EXISTS `{tname}`"))
            if also_drop_clustered:
                conn.execute(text(f"DROP TABLE IF EXISTS `{tname}_clustered`"))
            removed.append(tname)
        if rows:
            conn.execute(text(f"DELETE FROM `{METADATA_TABLE}` WHERE expires_at <= NOW()"))
    return removed

def days_to_expiry(engine, table_name: str) -> int | None:
    """Mengembalikan sisa hari kedaluwarsa; None jika tidak tercatat."""
    ensure_meta_table(engine)
    with engine.connect() as conn:
        row = conn.execute(text(f"""
            SELECT DATEDIFF(expires_at, NOW()) FROM `{METADATA_TABLE}` WHERE table_name=:t
        """), {"t": table_name}).fetchone()
        return int(row[0]) if row and row[0] is not None else None