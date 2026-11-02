# Compatibility patch for cPanel / hosting environments with PostgreSQL 13+
try:
    from django.db.backends.postgresql.features import DatabaseFeatures
    DatabaseFeatures.minimum_database_version = (13,)
except Exception:
    pass

