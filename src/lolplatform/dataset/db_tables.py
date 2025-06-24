'''
- CREATE POSTGRESS DATASET TABLES IF THEY DONT EXIT

DATA MODEL:
- PLAYERS: tabla con datos de jugadores - nombre, tagline, region, posición, ...
- UNA TABLA PARA CADA TIPO DE COLA, POR EJEMPLO: Soloq5v5_420 (420 es el queue_id de 5v5)

'''

from datetime import datetime, date
import sys
import numpy as np
import pandas as pd

def infer_pg_type(value):
    if isinstance(value, (bool, np.bool_)):  # use np.bool_ instead of deprecated np.bool
        return "BOOLEAN"
    elif isinstance(value, (int, np.integer)):  # handles np.int64 and others
        return "INTEGER"
    elif isinstance(value, (float, np.floating)):  # handles np.float64 and others
        return "DOUBLE PRECISION"
    elif isinstance(value, (datetime, date, pd.Timestamp)):
        return "TIMESTAMP"
    elif isinstance(value, str):
        return "TEXT"
    else:
        return "TEXT"
    
def create_table_from_data(conn, cur, schema_name, table_name, sample_row):
    columns = []
    constraints = []
    normalized_row = {col_name.lower(): value for col_name, value in sample_row.items()}

    for col_name, value in normalized_row.items():
        print("value: ", value[0])
        print("type: ", type(value[0]))
        pg_type = infer_pg_type(value[0])
        columns.append(f"{col_name} {pg_type}")
    # sys.exit()

    # Add primary key on 'player' if present
    if "player" in normalized_row:
        columns = [f"{col} {'PRIMARY KEY' if col.startswith('player ') else ''}".strip() for col in columns]

    # Add foreign key constraint if 'player' exists
    if "player" in normalized_row:
        constraints.append("FOREIGN KEY (player) REFERENCES lolplatform.players(player)")

    columns_sql = ", ".join(columns + constraints)
    sql = f"""
    CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
        {columns_sql}
    );
    """
    cur.execute(sql)
    conn.commit()


def create_schema_if_not_exists(conn, cur, schema_name):
    ''
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.schemata 
            WHERE schema_name = %s
        );
    """, (schema_name,))
    schema_exists = cur.fetchone()[0]
    
    if not schema_exists:
        cur.execute(f"CREATE SCHEMA {schema_name};")
        print(f"Schema '{schema_name}' created.")


def add_missing_columns(conn, cur, schema_name, table_name, sample_row):
    # Fetch existing columns
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s
    """, (schema_name, table_name))
    existing_cols = {row[0] for row in cur.fetchall()}

    normalized_row = {col_name.lower(): value for col_name, value in sample_row.items()}

    for col_name, value in normalized_row.items():
        if col_name not in existing_cols:
            pg_type = infer_pg_type(value)
            sql = f'ALTER TABLE {schema_name}.{table_name} ADD COLUMN {col_name} {pg_type};'
            # print(f"Altering {table_name}, adding column: {col_name} {pg_type}")
            cur.execute(sql)

    conn.commit()


def create_table_if_not_exists(conn, cur, schema_name, table_name, player_table=False, sample_table_row=None):
    # Check if the table already exists
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = %s
        );
    """, (schema_name, table_name))
    table_exists = cur.fetchone()[0]
    print(f'{table_name} exists: {table_exists}')

    if not table_exists:
        print(f"Creating table {schema_name}.{table_name}")
        if player_table:
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} (
                    player VARCHAR(100) PRIMARY KEY,
                    teamposition VARCHAR(50)
                );
            """)
            conn.commit()
        elif sample_table_row is not None:
            # Dynamically create table from sample row
            create_table_from_data(conn, cur, schema_name, table_name, sample_table_row)
        else:
            raise ValueError(f"No creation method defined for table '{schema_name}.{table_name}'")
    else:
        # Table exists - try to add missing columns based on sample_row
        if sample_table_row is not None:
            add_missing_columns(conn, cur, schema_name, table_name, sample_table_row)