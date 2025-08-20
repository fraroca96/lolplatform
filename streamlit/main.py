'''
## NOTAS PARA METER/CAMBIAR

- SACAR MUCHAS FUNCIONES DE AQUÍ A OTROS SCRIPTS, YA SEAN DE ESTA CARPETA O FUERA

- TENER EN CUENTA QUE TENDREMOS JUGADORES QUE USAREMOS PARA COMPARAR -> DE ESOS NO QUEREMOS PREVIEW, SOLO PARA COMPARAR

- EN LA PARTE DE VISUALIZACIÓN, DEBE HABER VISUALIZACIONES POR DEFECTO, Y LUEGO 



## 

- CAMBIAR QUE LA ÚLTIMA FECHA LA COMPRUEBE PARA TODOS A LA VEZ, TIENE QUE SER **POR JUGADOR**
(POR EJEMPLO SI DE RAZORK TENEMOS DATOS DE TODOS LOS DÍAS PERO DE UPSET NO, AL HACERLO COMO ESTÁ AHORA SOLO DESCARGA DATOS DE UPSET DESDE ULTIMO DÍA DE RAZORK....)


## ¿ERROR DE CIERRE DE CONNECTION???
'''




from lolplatform.config import log
import traceback
import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime, timedelta, time
from lolplatform.config import queues
from lolplatform.config import players
from lolplatform.dataset.get_riot_data import lolData 
import os
from dotenv import load_dotenv
from lolplatform.config.variables import variables_dict
from lolplatform.dataset.db_tables import create_schema_if_not_exists, create_table_if_not_exists, get_played_champions, get_player_data_db, build_full_sample_row, get_db_connection, initialize_database
from lolplatform.analysis_viz.radar_chart import LoLRadarCompare
from lolplatform.analysis_viz.variable_evol import evol_one_player, evol_two_players_compare
from lolplatform.analysis_viz.variables_win_lose import plot_win_loss_boxplot

import io

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

SCHEMA = "lolplatform"

@st.cache_resource
def initialize_db_once():
    conn = get_db_connection()
    initialize_database(conn)
    return True

def get_last_date_for_queue(conn, queue_name, queue_id, player=None):
    cur = conn.cursor()
    table_name = f"{queue_name.lower()}_{queue_id}"
    try:
        if player is not None:
            conn.rollback()

            # check if player is in table
            exists_query = f"""
            SELECT EXISTS (
                SELECT 1 FROM "{SCHEMA}"."{table_name}" WHERE player = %s
            )
            """
            cur.execute(exists_query, (player,))
            player_in_table = cur.fetchone()[0]
            if player_in_table:
                conn.rollback()
                cur.execute(
                    f'SELECT MAX(match_timestamp) FROM "{SCHEMA}"."{table_name}" WHERE player = %s',
                    (player,)
                )
                result_t = cur.fetchone()

                return result_t[0] if result_t and result_t[0] is not None else None

            else:
                return None

        else:
            conn.rollback()
            cur.execute(f'SELECT MAX(match_timestamp) FROM "{SCHEMA}"."{table_name}"')
            result_t = cur.fetchone()

            cur.execute(
                f'SELECT player FROM "{SCHEMA}"."{table_name}" WHERE match_timestamp = %s',
                (result_t[0],)
            )
            result_p = cur.fetchone()

            return result_t[0], result_p[0] if result_t and result_t[0] is not None else None
        
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


# A small helper function to set active tab
def switch_tab(index):
    st.session_state.active_tab = index


default_radar_vars_capital = ["damagePerMinute", "totalMinionsKilled", "visionScorePerMinute",
                    "teamDamagePercentage", "killParticipation", "goldPerMinute",
                    "laneMinionsFirst10Minutes"]

default_radar_vars = [var.lower() for var in default_radar_vars_capital]

all_vars_capital = variables_dict["valid_variables"] + variables_dict["valid_chal_variables"]
all_vars = [var.lower() for var in all_vars_capital]


def main():
    st.set_page_config(page_title="LoL Data Platform", layout="wide")
    st.title("LoL Data Platform")
    st.image("fnatic_logo.png", width=200)

    # Always fresh connection for this run
    conn = get_db_connection()

    try:
        initialize_db_once()
    except Exception as e:
        st.warning(f"Database initialization warning: {str(e)}")

    st.sidebar.header("Players")
    for player in players.player_dict:
        st.sidebar.write(player)
    # Tabs as radio buttons for persistence
    tab_labels = ["Download", "Players Table", "Queue Tables", "Visualization"]

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = tab_labels[0]

    selected_tab = st.radio("Select tab", tab_labels, index=tab_labels.index(st.session_state.active_tab), horizontal=True)

    if selected_tab != st.session_state.active_tab:
        st.session_state.active_tab = selected_tab

    if st.session_state.active_tab == "Download":
        st.header("Download Data by Queue")
        for queue_name, queue_info in queues.queues_dict.items():
            st.subheader(f"Queue: {queue_name}")
            queue_id = queue_info['queueId']
            last_date, last_player = get_last_date_for_queue(conn, queue_name, queue_id)
            if last_date:
                st.write(f"Last data date in DB: {last_date.strftime('%Y-%m-%d %H:%M:%S')} for {last_player}")
            else:
                st.write("No data found for this queue.")
                start_date = datetime.now() - timedelta(days=30)
                st.write(f"Will download from: {start_date.strftime('%Y-%m-%d')} for all players")

            if st.button("Download data", key=f"download_{queue_name}_{queue_id}"):
                with st.spinner(f"Downloading data for {queue_name}..."):
                    for player in players.player_dict:
                        try:
                            last_date_player = get_last_date_for_queue(conn, queue_name, queue_id, player)
                            if last_date_player:
                                start_date = last_date_player + timedelta(seconds=1)
                            else:
                                start_date = datetime.now() - timedelta(days=30)

                            # Separate connection for downloading
                            with get_db_connection() as download_conn:
                                lol_obj = lolData(player=player, queue=queue_name)
                                lol_obj.init_download_process(start_date=start_date.strftime('%Y-%m-%d'))

                            st.success(f"Downloaded data for {player} - {queue_name}")
                        except Exception as e:
                            st.error(f"Error downloading for {player}, queue {queue_name}: {e}")
                            traceback.print_exc()
        
        st.subheader(f"Data for comparing pro players")
        if st.button("Download data for comparing players", key=f"download_compare"):
            for queue_name, queue_info in queues.queues_dict.items():
                queue_id = queue_info['queueId']
                with st.spinner(f"Downloading data for {queue_name}..."):
                    for player in players.compare_players_dict:
                        try:
                            last_date_player = get_last_date_for_queue(conn, queue_name, queue_id, player)
                            if last_date_player:
                                start_date = last_date_player + timedelta(seconds=1)
                            else:
                                start_date = datetime.now() - timedelta(days=10) # for comparing players only download last 10 days

                            # Separate connection for downloading
                            with get_db_connection() as download_conn:
                                lol_obj = lolData(player=player, queue=queue_name)
                                lol_obj.init_download_process(start_date=start_date.strftime('%Y-%m-%d'))

                            st.success(f"Downloaded data for {player} - {queue_name}")
                        except Exception as e:
                            st.error(f"Error downloading for {player}, queue {queue_name}: {e}")
                            traceback.print_exc()

    elif st.session_state.active_tab == "Players Table":
        st.header("PLAYERS Table Preview")
        df_players = fetch_players_table(conn)
        if df_players.empty:
            st.write("PLAYERS table is empty. Download data to populate it.")
        else:
            st.dataframe(df_players)

    elif st.session_state.active_tab == "Queue Tables":
        st.header("Preview of Queue Tables")
        for queue_name, queue_info in queues.queues_dict.items():
            st.subheader(f"Queue: {queue_name}")
            df_queue = fetch_queue_preview(conn, queue_name, queue_info['queueId'])
            if df_queue.empty:
                st.write(f"No data for {queue_name} yet.")
            else:
                df_queue_show = df_queue.copy()
                first_cols = ['match_timestamp', 'player', 'championname']
                df_queue_show = df_queue_show[first_cols + list(df_queue_show.columns.drop(first_cols))]

                st.dataframe(df_queue_show)

    elif st.session_state.active_tab == "Visualization":
        st.header("Players data visualizations")

        st.subheader("Radar Chart Comparison")

        queue_choice = st.selectbox("Select Queue", list(queues.queues_dict.keys()), key="queue")
        queue_id = queues.queues_dict[queue_choice]["queueId"]
        table_name = f'{queue_choice}_{queue_id}'.lower()
        
        radar_vars = st.multiselect(
            "Select Radar Variables",
            all_vars,
            default=default_radar_vars,
            key="radar_vars"
        )

        number_of_games = st.slider("Number of Games", 10, 500, 100, step=5, key="num_games")

        col1, col2 = st.columns(2)

        with col1:
            player_1 = st.selectbox("Select Player 1", list(players.player_dict.keys()), key="p1")
            player_1_champions = get_played_champions(conn, player_1, table_name = table_name, games = number_of_games)
            player_1_champion = st.selectbox("Champion for Player 1", [""] + player_1_champions, key="p1champ")

        with col2:
            player_2 = st.selectbox("Select Player 2", list(players.compare_players_dict.keys()), key="p2")
            player_2_champions = get_played_champions(conn, player_2, table_name = table_name, games = number_of_games)
            player_2_champion = st.selectbox("Champion for Player 2", [""] + player_2_champions, key="p2champ")

        if st.button("Generate Radar Chart", key="radar_btn"):
            radar = LoLRadarCompare(
                conn=conn,
                player_1=player_1,
                player_2=player_2,
                player_1_champion=player_1_champion or None,
                player_2_champion=player_2_champion or None,
                number_of_games=number_of_games,
                table_name=table_name,
                radar_variables=radar_vars
            )

            fig, ax = radar.init_process()  
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            st.image(buf, width=1000)  

            # st.pyplot(fig)

        st.subheader("Variable evolution comparison")

        queue_choice = st.selectbox("Select Queue", list(queues.queues_dict.keys()), key="queue_evol")
        queue_id = queues.queues_dict[queue_choice]["queueId"]
        table_name = f'{queue_choice}_{queue_id}'.lower()

        two_players = st.checkbox("Compare two players", value=False, key="compare_two_players")

        default_start_date = datetime.now() - timedelta(days=30)
        chosen_start_date = st.date_input("Select Start Date", value=default_start_date, key="start_date")

        chosen_start_date = datetime.combine(chosen_start_date, time.min)

        chosen_variable = st.selectbox(
            "Select Variable",
            all_vars,
            index=all_vars.index("goldPerMinute") if "goldPerMinute" in all_vars else 0,
            key="evol_var"
        )

        if not two_players:
            player_1 = st.selectbox("Select Player 1", list(players.player_dict.keys()), key="p1_evol_1")
            player_1_data = get_player_data_db(conn=conn, player=player_1,table_name=table_name)

            fig, ax = evol_one_player(player=player_1, player_data=player_1_data, start_date=chosen_start_date, variable=chosen_variable)

        else:
            col1, col2 = st.columns(2)

            with col1:
                player_1 = st.selectbox("Select Player 1", list(players.player_dict.keys()), key="p1_evol")
                player_1_data = get_player_data_db(conn=conn, player=player_1,table_name=table_name)

            with col2:
                player_2 = st.selectbox("Select Player 2", list(players.compare_players_dict.keys()), key="p2_evol")
                player_2_data = get_player_data_db(conn=conn, player=player_2,table_name=table_name)

            fig, ax = evol_two_players_compare(player1 = player_1,
                                               player2 = player_2,
                                               player_1_data = player_1_data,
                                               player_2_data = player_2_data,
                                               variable = chosen_variable,
                                               start_date = chosen_start_date)

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        st.image(buf, width=1000)  


        st.subheader("Variable in Win/Loss")

        queue_choice = st.selectbox("Select Queue", list(queues.queues_dict.keys()), key="queue_winloss")
        queue_id = queues.queues_dict[queue_choice]["queueId"]
        table_name = f'{queue_choice}_{queue_id}'.lower()

        default_start_date = datetime.now() - timedelta(days=30)
        chosen_start_date = st.date_input("Select Start Date", value=default_start_date, key="start_date_winloss")

        chosen_start_date = datetime.combine(chosen_start_date, time.min)

        chosen_variable = st.selectbox(
            "Select Variable",
            all_vars,
            index=all_vars.index("goldPerMinute") if "goldPerMinute" in all_vars else 0,
            key="winloss_var"
        )

        player_1 = st.selectbox("Select Player 1", list(players.player_dict.keys()), key="p_winloss")
        player_1_data = get_player_data_db(conn=conn, player=player_1,table_name=table_name)

        fig, ax = plot_win_loss_boxplot(player = player_1, player_data = player_1_data, variable = chosen_variable)

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        st.image(buf, width=1000)  

    conn.close()


if __name__ == "__main__":
    main()
