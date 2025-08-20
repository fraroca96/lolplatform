'''
- CREATE POSTGRESS DATASET TABLES IF THEY DONT EXIT

DATA MODEL:
- PLAYERS: tabla con datos de jugadores - nombre, tagline, region, posición, ...
- UNA TABLA PARA CADA TIPO DE COLA, POR EJEMPLO: Soloq5v5_420 (420 es el queue_id de 5v5)

- ¿OTRA TABLA PLAYERS_COMPARE? CON JUGADORES CON LOS QUE SE COMPARARÁ A LOS NUESTROS
- ¿ESTAMOS BORRANDO YA DATOS A PARTIR DE CIERTA ANTIGÜEDAD? SI NO, HACERLO!! HAY UNA FUNCIÓN EN GET_RIOT_DATA QUE HARÍA ESO (VACÍA)
    .. CREO QUE LA TENDRÍAMOS QUE PONER AQUÍ

- ESTARÍA BIEN GENERAR UN DATAFRAME CON NOMBRE DE JUGADOR Y FECHA DE ÚLTIMA DESCARGA DE DATOS??

'''

from datetime import datetime, date
import sys
import numpy as np
import pandas as pd
from lolplatform.config.players import player_dict, compare_players_dict
from lolplatform.config.variables import variables_dict
from lolplatform.config import queues
from lolplatform.dataset.get_riot_data import lolData
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

SCHEMA = "lolplatform"

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )

def initialize_database(conn):
    cur = conn.cursor()
    try:
        conn.rollback()
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)", (SCHEMA,))
        if not cur.fetchone()[0]:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            conn.commit()

        create_table_if_not_exists(conn=conn, cur=cur, schema_name=SCHEMA, table_name="players", player_table=True)

        for queue_name, queue_info in queues.queues_dict.items():
            tbl = f"{queue_name.lower()}_{queue_info['queueId']}"
            sample_table_row = build_full_sample_row(queue_name)

            create_table_if_not_exists(
                conn=conn,
                cur=cur,
                schema_name=SCHEMA,
                table_name=tbl,
                sample_table_row=sample_table_row
            )
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"DB init error: {e}")
    finally:
        cur.close()


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
        print("col_name: ", col_name)
        print("value: ", value[0])
        print("type: ", type(value[0]))
        pg_type = infer_pg_type(value[0])
        columns.append(f"{col_name} {pg_type}")

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

    if ("player" in normalized_row) and ("match_timestamp" in normalized_row):
        sql_index_creation = f"""
            CREATE INDEX IF NOT EXISTS idx_match_player
            ON {schema_name}.{table_name} (match_timestamp, player);
        """
        cur.execute(sql_index_creation)
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
        
    if player_table:
        player_list = list(player_dict.keys()) + list(compare_players_dict.keys())
        print(player_list)

        # Get the set of players already present in the table
        cur.execute(f"SELECT player FROM {schema_name}.{table_name}")
        present_players = {row[0] for row in cur.fetchall()}  # use set for fast lookup
        print(present_players)

        for pl in player_list:
            if pl not in present_players:
                if pl in list(player_dict.keys()):
                    team_position = player_dict[pl]["teamPosition"]
                else:
                    team_position = compare_players_dict[pl]["teamPosition"]
                    
                sql_insert_player = f"""
                    INSERT INTO {schema_name}.{table_name} (player, teamposition)
                    VALUES (%s, %s)
                """
                cur.execute(sql_insert_player, (pl, team_position)) 
                conn.commit()

    else:
        # Table exists - try to add missing columns based on sample_row
        if sample_table_row is not None:
            add_missing_columns(conn, cur, schema_name, table_name, sample_table_row)

def build_full_sample_row(queue_name):
    example_player = list(player_dict.keys())[0]
    print(f'Building sample row with example player: {example_player} and queue {queue_name}')

    loldataobject_init_db = lolData(player=example_player, queue=queue_name)

    loldataobject_init_db.get_puuid()
    match_id_example = loldataobject_init_db.get_match_id_last_game()[0]

    match_data_example = loldataobject_init_db.get_match_data(match_id=match_id_example)
    match_timestamp_example = datetime.fromtimestamp(timestamp=match_data_example['info']['gameStartTimestamp']/1000).replace(microsecond=0)
    example_player_data = loldataobject_init_db.find_player_data(match_data=match_data_example)
    example_player_data = {key: example_player_data[key] for key in variables_dict["valid_variables"]}
    example_player_data['match_timestamp'] = match_timestamp_example

    example_player_data['player'] = example_player

    sample_row = pd.DataFrame([example_player_data])

    challenges_expanded = sample_row['challenges'].apply(pd.Series)
    challenges_expanded = challenges_expanded[variables_dict["valid_chal_variables"]]
        
    sample_row = pd.concat([sample_row.drop(columns=['challenges']), 
                            challenges_expanded], axis=1)

    
    sample_row = sample_row[sample_row['teamPosition'] == player_dict[example_player]["teamPosition"]]
    sample_row = sample_row[['match_timestamp']+list(sample_row.columns.drop('match_timestamp'))]

    return sample_row


def get_player_data_db(conn, player, player_champion = None, games=50, table_name='ranked_soloq_games_420'):
    cur = conn.cursor()
    schema_name = "lolplatform"
    
    if player_champion is not None:
        query = f"""
            SELECT *
            FROM {schema_name}.{table_name}
            WHERE player = %s AND championname = %s
            LIMIT %s
        """
        cur.execute(query, (player, player_champion, games))
    
    else:
        query = f"""
            SELECT *
            FROM {schema_name}.{table_name}
            WHERE player = %s
            LIMIT %s
        """
        cur.execute(query, (player, games))     
    
    rows = cur.fetchall()
    col_names = [desc[0] for desc in cur.description]
    df = pd.DataFrame(rows, columns=col_names)
    
    return df

def get_played_champions(conn, player, table_name='ranked_soloq_games_420', games=50):
    cur = conn.cursor()
    schema_name = "lolplatform"

    query = f"""
        SELECT DISTINCT championname
        FROM (
            SELECT championname
            FROM {schema_name}.{table_name}
            WHERE player = %s
            ORDER BY match_timestamp DESC
            LIMIT %s
        ) subquery
        ORDER BY championname
    """

    cur.execute(query, (player, games))
    champions = [row[0] for row in cur.fetchall()]
    cur.close()
    return champions