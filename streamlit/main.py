from lolplatform.config import log
import traceback
import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
from lolplatform.config import queues
from lolplatform.config import player_data
from lolplatform.dataset.get_riot_data import lolData 
import os
from dotenv import load_dotenv
from lolplatform.config.variables import variables_dict
from lolplatform.dataset.db_tables import create_schema_if_not_exists, create_table_if_not_exists

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

SCHEMA = "lolplatform"

## SI NO FUNCIONA, PODEMOS SACAR LA SAMPLE_ROW DE INFER_TYPE!!!
## SACANDO UNA FILA DESCARGANDO USANDO FUNCIONES DE GET_RIOT_DATA.PY!!! 
## PENSARLO UN POCO!!!
def build_full_sample_row(queue_name):
    example_player = list(player_data.player_dict.keys())[0]
    print(f'Building sample row with eample player: {example_player} and queue {queue_name}')

    loldataobject_init_db = lolData(player=example_player, queue=queue_name)

    loldataobject_init_db.get_puuid()
    match_id_example = loldataobject_init_db.get_match_id_last_game()[0]
    # print('match_id_example: ', match_id_example)

    match_data_example = loldataobject_init_db.get_match_data(match_id=match_id_example)
    # print('Match data example :', match_data_example)
    match_timestamp_example = datetime.fromtimestamp(timestamp=match_data_example['info']['gameStartTimestamp']/1000).replace(microsecond=0)
    example_player_data = loldataobject_init_db.find_player_data(match_data=match_data_example)
    # print('example_player_data :', example_player_data)
    example_player_data = {key: example_player_data[key] for key in variables_dict["valid_variables"]}
    example_player_data['match_timestamp'] = match_timestamp_example

    example_player_data['player'] = example_player

    sample_row = pd.DataFrame([example_player_data])
    # print('Sample row: ', sample_row)

    challenges_expanded = sample_row['challenges'].apply(pd.Series)
    challenges_expanded = challenges_expanded[variables_dict["valid_chal_variables"]]
        
    sample_row = pd.concat([sample_row.drop(columns=['challenges']), 
                            challenges_expanded], axis=1)

    
    sample_row = sample_row[sample_row['teamPosition'] == player_data.player_dict[example_player]["teamPosition"]]
    sample_row = sample_row[['match_timestamp']+list(sample_row.columns.drop('match_timestamp'))]

    return sample_row


@st.cache_resource
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
        st.error(f"DB init error: {e}")
    finally:
        cur.close()

@st.cache_resource
def initialize_db_once():
    conn = get_db_connection()
    initialize_database(conn)
    return True

def get_last_date_for_queue(conn, queue_name, queue_id):
    cur = conn.cursor()
    try:
        conn.rollback()
        table_name = f"{queue_name.lower()}_{queue_id}"
        cur.execute(f'SELECT MAX(match_timestamp) FROM "{SCHEMA}"."{table_name}"')
        result = cur.fetchone()
        return result[0] if result and result[0] is not None else None
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"Error fetching last date for {queue_name}: {e}")
        return None
    finally:
        cur.close()

def fetch_players_table(conn):
    cur = conn.cursor()
    try:
        conn.rollback()
        cur.execute(f'SELECT * FROM "{SCHEMA}"."players"')
        cols = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        return pd.DataFrame(data, columns=cols)
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"Error fetching PLAYERS table: {e}")
        return pd.DataFrame()
    finally:
        cur.close()

def fetch_queue_preview(conn, queue_name, queue_id):
    cur = conn.cursor()
    try:
        conn.rollback()
        table_name = f"{queue_name.lower()}_{queue_id}"
        cur.execute(f'SELECT * FROM "{SCHEMA}"."{table_name}" ORDER BY match_timestamp DESC LIMIT 20')
        cols = [desc[0] for desc in cur.description]
        data = cur.fetchall()
        return pd.DataFrame(data, columns=cols)
    except psycopg2.Error as e:
        conn.rollback()
        st.error(f"Error fetching preview for {queue_name}: {e}")
        return pd.DataFrame()
    finally:
        cur.close()

def main():
    st.set_page_config(page_title="LoL Data Platform", layout="wide")
    st.title("LoL Data Platform")
    st.image("fnatic_logo.png", width=200)

    conn = get_db_connection()

    # Cached init so DB schema/tables aren't rechecked every time
    try:
        initialize_db_once()
    except Exception as e:
        st.warning(f"Database initialization warning: {str(e)}")

    st.sidebar.header("Players")
    for player in player_data.player_dict:
        st.sidebar.write(player)

    tabs = st.tabs(["Download", "Players Table", "Queue Tables"])

    with tabs[0]:
        st.header("Download Data by Queue")
        for queue_name, queue_info in queues.queues_dict.items():
            st.subheader(f"Queue: {queue_name}")
            queue_id = queue_info['queueId']
            last_date = get_last_date_for_queue(conn, queue_name, queue_id)
            if last_date:
                st.write(f"Last data date in DB: {last_date.strftime('%Y-%m-%d %H:%M:%S')}")
                start_date = last_date + timedelta(seconds=1)
            else:
                st.write("No data found for this queue.")
                start_date = datetime.now() - timedelta(days=30)
                st.write(f"Will download from: {start_date.strftime('%Y-%m-%d')}")

            if st.button(f"Download data for {queue_name} from {start_date.strftime('%Y-%m-%d')}"):
                with st.spinner(f"Downloading data for {queue_name}..."):
                    for player in player_data.player_dict:
                        try:
                            download_conn = get_db_connection()
                            lol_obj = lolData(player=player, queue=queue_name)
                            lol_obj.init_download_process(start_date=start_date.strftime('%Y-%m-%d'))
                            download_conn.close()
                            st.success(f"Downloaded data for {player} - {queue_name}")
                        except Exception as e:
                            st.error(f"Error downloading for {player}, queue {queue_name}: {e}")
                            traceback.print_exc()

    with tabs[1]:
        st.header("PLAYERS Table Preview")
        df_players = fetch_players_table(conn)
        if df_players.empty:
            st.write("PLAYERS table is empty. Download data to populate it.")
        else:
            st.dataframe(df_players)

    with tabs[2]:
        st.header("Preview of Queue Tables")
        for queue_name, queue_info in queues.queues_dict.items():
            st.subheader(f"Queue: {queue_name}")
            df_queue = fetch_queue_preview(conn, queue_name, queue_info['queueId'])
            if df_queue.empty:
                st.write(f"No data for {queue_name} yet.")
            else:
                st.dataframe(df_queue)

if __name__ == "__main__":
    main()
