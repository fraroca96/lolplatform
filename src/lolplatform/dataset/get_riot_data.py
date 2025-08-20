import numpy as np 
import pandas as pd 
import os
import requests
import json
#Time is important to ensure our loops can be slept to avoid going over our API call rate limit
import time
import csv
from datetime import datetime
import argparse
import ast  # For safely converting string input to a tuple
import sys
from dotenv import load_dotenv
from lolplatform.config.players import player_dict, compare_players_dict
from lolplatform.config.queues import queues_dict
from lolplatform.config.variables import variables_dict
import psycopg2
from lolplatform.config import log
from lolplatform.utils import generate_date_tuples
from psycopg2.extras import execute_values
import warnings

warnings.filterwarnings("ignore")


def get_db_columns(cur, schema_name, table_name):
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (schema_name, table_name))
    return [row[0] for row in cur.fetchall()]


rename_map = {
    'championName': 'championname',
    'baronKills': 'baronkills',
    'damageDealtToBuildings': 'damagedealttobuildings',
    'damageDealtToObjectives': 'damagedealttoobjectives',
    'damageSelfMitigated': 'damageselfmitigated',
    'firstBloodAssist': 'firstbloodassist',
    'firstBloodKill': 'firstbloodkill',
    'firstTowerAssist': 'firsttowerassist',
    'firstTowerKill': 'firsttowerkill',
    'gameEndedInEarlySurrender': 'gameendedinearlysurrender',
    'gameEndedInSurrender': 'gameendedinsurrender',
    'goldEarned': 'goldearned',
    'individualPosition': 'individualposition',
    'inhibitorsLost': 'inhibitorslost',
    'longestTimeSpentLiving': 'longesttimespentliving',
    'neutralMinionsKilled': 'neutralminionskilled',
    'objectivesStolen': 'objectivesstolen',
    'teamEarlySurrendered': 'teamearlysurrendered',
    'teamPosition': 'teamposition',
    'timeCCingOthers': 'timeccingothers',
    'timePlayed': 'timeplayed',
    'totalAllyJungleMinionsKilled': 'totalallyjungleminionskilled',
    'totalDamageDealtToChampions': 'totaldamagedealttochampions',
    'totalDamageTaken': 'totaldamagetaken',
    'totalEnemyJungleMinionsKilled': 'totalenemyjungleminionskilled',
    'totalMinionsKilled': 'totalminionskilled',
    'totalTimeCCDealt': 'totaltimeccdealt',
    'totalTimeSpentDead': 'totaltimespentdead',
    'turretsLost': 'turretslost',
    'visionScore': 'visionscore',
    'visionWardsBoughtInGame': 'visionwardsboughtingame',
    'wardsKilled': 'wardskilled',
    'wardsPlaced': 'wardsplaced',
    'damagePerMinute': 'damageperminute',
    'damageTakenOnTeamPercentage': 'damagetakenonteampercentage',
    'dodgeSkillShotsSmallWindow': 'dodgeskillshotssmallwindow',
    'dragonTakedowns': 'dragontakedowns',
    'epicMonsterKillsWithin30SecondsOfSpawn': 'epicmonsterkillswithin30secondsofspawn',
    'gameLength': 'gamelength',
    'goldPerMinute': 'goldperminute',
    'hadOpenNexus': 'hadopennexus',
    'initialCrabCount': 'initialcrabcount',
    'jungleCsBefore10Minutes': 'junglecsbefore10minutes',
    'killAfterHiddenWithAlly': 'killafterhiddenwithally',
    'killParticipation': 'killparticipation',
    'killsNearEnemyTurret': 'killsnearenemyturret',
    'laneMinionsFirst10Minutes': 'laneminionsfirst10minutes',
    'maxKillDeficit': 'maxkilldeficit',
    'moreEnemyJungleThanOpponent': 'moreenemyjunglethanopponent',
    'quickFirstTurret': 'quickfirstturret',
    'quickSoloKills': 'quicksolokills',
    'riftHeraldTakedowns': 'riftheraldtakedowns',
    'scuttleCrabKills': 'scuttlecrabkills',
    'skillshotsDodged': 'skillshotsdodged',
    'skillshotsHit': 'skillshotshit',
    'soloKills': 'solokills',
    'takedownOnFirstTurret': 'takedownonfirstturret',
    'takedownsAfterGainingLevelAdvantage': 'takedownsaftergainingleveladvantage',
    'takedownsBeforeJungleMinionSpawn': 'takedownsbeforejungleminionspawn',
    'takedownsFirstXMinutes': 'takedownsfirstxminutes',
    'teamDamagePercentage': 'teamdamagepercentage',
    'teamElderDragonKills': 'teamelderdragonkills',
    'teamRiftHeraldKills': 'teamriftheraldkills',
    'turretTakedowns': 'turrettakedowns',
    'visionScorePerMinute': 'visionscoreperminute',
    'alliedJungleMonsterKills': 'alliedjunglemonsterkills',
    'baronTakedowns': 'barontakedowns',
    'buffsStolen': 'buffsstolen',
    'completeSupportQuestInTime': 'completesupportquestintime',
    'controlWardsPlaced': 'controlwardsplaced',
    'player': 'player'
}


class lolData():
    def __init__(self, player, queue, region="europe", mass_region = 'EUROPE'):
        r'''
        Function to initialize the object of the class.

        Args
            player:
        '''
        load_dotenv()

        self.player = player
        self.region = region
        self.mass_region = mass_region

        self.queue = queue
        self.queue_id = queues_dict[self.queue]["queueId"]

        self.data_path = os.environ.get("DATA_PATH", "")
        self.riot_api_key = os.environ.get("RIOT_API_KEY", "")

        if self.player in player_dict:
            self.summoner_name = player_dict[self.player]["summoner_name"]
            self.summoner_tagline = player_dict[self.player]["summoner_tagline"]
            self.player_rol = player_dict[self.player]["rol"]
            self.player_teamPosition = player_dict[self.player]["teamPosition"]
        else:
            self.summoner_name = compare_players_dict[self.player]["summoner_name"]
            self.summoner_tagline = compare_players_dict[self.player]["summoner_tagline"]
            self.player_rol = compare_players_dict[self.player]["rol"]
            self.player_teamPosition = compare_players_dict[self.player]["teamPosition"]    


        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            dbname=os.getenv("DB_NAME")
        )
        self.cur = self.conn.cursor()

        self.schema = "lolplatform"
        self.variables = variables_dict

    def get_puuid(self):
        r'''
        '''
        api_url = (
            "https://" + 
            self.region +
            ".api.riotgames.com/riot/account/v1/accounts/by-riot-id/" +
            self.summoner_name +
            '/'+self.summoner_tagline+
            "?api_key=" +
            self.riot_api_key
        )
        
        resp = requests.get(api_url)
        player_info = resp.json()
        puuid = player_info['puuid']
        
        self.puuid = puuid


    def get_match_id_last_game(self):
        '''
        
        '''
        api_url = (
            "https://" +
            self.mass_region +
            ".api.riotgames.com/lol/match/v5/matches/by-puuid/" +
            self.puuid + 
            "/ids?start=0" + 
            "&count=" +
            str(1) + 
            "&queueId=" + 
            str(self.queue_id) + 
            "&api_key=" + 
            self.riot_api_key
        )
        
        resp = requests.get(api_url)
        match_id_last_game = resp.json()

        return match_id_last_game


    def get_match_ids_by_date_range(self):
        '''
        '''
        api_url = (
            "https://" +
            self.mass_region +
            ".api.riotgames.com/lol/match/v5/matches/by-puuid/" +
            self.puuid + 
            "/ids?startTime="+
            str(self.timestamp_start) +
            "&endTime="+
            str(self.timestamp_end)+
            "&start=0" + 
            "&count=" +
            str(100) + 
            "&queueId=" +
            str(self.queue_id) + 
            "&api_key=" + 
            self.riot_api_key
        )

        resp = requests.get(api_url)
        match_ids_date_range = resp.json()

        self.match_ids_date_range = match_ids_date_range


    def get_match_data(self, match_id):
        '''
        '''
        api_url = (
            "https://" + 
            self.mass_region + 
            ".api.riotgames.com/lol/match/v5/matches/" +
            match_id + 
            "?api_key=" + 
            self.riot_api_key
        )
        
        # we need to add this "while" statement so that we continuously loop until it's successful
        while True:
            resp = requests.get(api_url)
            
            #Riot servers have a rate limit that return an error code when the limit is hit. Whenever we see a 429, we'll sleep for 10 seconds and then restart from the top of the "while" loop
            if resp.status_code == 429:
                print("Rate Limit hit, sleeping for 10 seconds")
                time.sleep(10)
                # continue means start the loop again
                continue
                
            # if resp.status_code isn't 429, then we carry on to the end of the function and return the data
            match_data = resp.json()
            return match_data
        

    ##Given the match data and a players puuid, return the data about just them
    def find_player_data(self, match_data):
        '''
        '''
        participants = match_data['metadata']['participants']
        player_index = participants.index(self.puuid)
        player_data = match_data['info']['participants'][player_index]
        return player_data


    ## Gather all data and return desired variables
    def get_all_player_data_date_range(self):
        '''
        Function to...

        Args
            variables: which variables do we need
                => Need to be the same name as in the extracted info!
        '''

        self.get_puuid()
        self.get_match_ids_by_date_range()
        data = dict()

        for var in self.variables["valid_variables"]:
            data[var] = []
        data['match_timestamp'] = []
        data['player'] = []

        # match_number = 1   
        self.df_all_player_data_date_range = pd.DataFrame(data) 
        if len(self.match_ids_date_range) != 0:
            for match_id in self.match_ids_date_range:
                # print(match_id)

                # run the two functions to get the player data from the match ID
                match_data = self.get_match_data(match_id)
                match_timestamp = datetime.fromtimestamp(timestamp=match_data['info']['gameStartTimestamp']/1000).replace(microsecond=0)
                player_data = self.find_player_data(match_data)

                player_data = {key: player_data[key] for key in self.variables["valid_variables"]}
                player_data['match_timestamp'] = match_timestamp

                player_data['player'] = self.player

                self.df_all_player_data_date_range = pd.concat([self.df_all_player_data_date_range,
                                                                pd.DataFrame([player_data])]) # to preserve the challenges dict format in the dataframe
                # No tenemos que dropear variables, porque si hay diferentes variables salen NaN!
                # match_number += 1
            
            # Expand the challenges columns

            challenges_expanded = self.df_all_player_data_date_range['challenges'].apply(pd.Series)
            challenges_expanded = challenges_expanded[self.variables["valid_chal_variables"]]
            self.df_all_player_data_date_range = pd.concat([self.df_all_player_data_date_range.drop(columns=['challenges']), 
                                                            challenges_expanded], axis=1)
            
            # We only take data of the rol of the player
            # I.E, if a MID player plays some games in TOP we dont count them (or do we?)
            self.df_all_player_data_date_range = self.df_all_player_data_date_range[self.df_all_player_data_date_range['teamPosition'] == self.player_teamPosition]
            self.df_all_player_data_date_range = self.df_all_player_data_date_range.sort_values('match_timestamp', ascending = False)
            self.df_all_player_data_date_range = self.df_all_player_data_date_range[['match_timestamp']+list(self.df_all_player_data_date_range.columns.drop('match_timestamp'))]

            for col in self.df_all_player_data_date_range.columns:
                # Check if there are any actual booleans in the column
                if self.df_all_player_data_date_range[col].apply(lambda x: isinstance(x, bool)).any():
                    self.df_all_player_data_date_range[col] = self.df_all_player_data_date_range[col].astype(bool)

        else:
            print(f"No matches in this period for {self.player}")



    def save_data(self):
        ''
        print(f"DEBUG: schema={self.schema}, table_name={self.table_name}")
        print(f"DEBUG: Checking DB connection and cursor...")

        # Test if connection/cursor is still valid
        try:
            self.cur.execute("SELECT 1")
        except Exception as e:
            print("ERROR: Cursor/connection not valid:", e)

        columns = list(self.df_all_player_data_date_range.columns)
        values = [tuple(row) for row in self.df_all_player_data_date_range.to_numpy()]  # Handles all data types
  
        col_str = ', '.join(columns)
        
        # Normalize DataFrame columns to lowercase
        self.df_all_player_data_date_range.columns = [col.lower() for col in self.df_all_player_data_date_range.columns]

        # Get DB columns
        db_columns = get_db_columns(self.cur, self.schema, self.table_name)
        db_columns = get_db_columns(self.cur, self.schema, self.table_name)

        # Add any missing DB columns to DataFrame with default None
        for col in db_columns:
            if col not in self.df_all_player_data_date_range.columns:
                self.df_all_player_data_date_range[col] = None
        
        self.df_all_player_data_date_range.rename(columns=rename_map, inplace=True)

        # Now reorder columns in DB order
        self.df_all_player_data_date_range = self.df_all_player_data_date_range[db_columns]

        df_columns = list(self.df_all_player_data_date_range.columns)

        if set(df_columns) != set(db_columns):
            print("Warning: DataFrame columns do not match DB columns.")
            print("DB columns:", db_columns)
            print("DataFrame columns:", df_columns)


        insert_sql = f"INSERT INTO {self.schema}.{self.table_name} ({col_str}) VALUES %s"

        try:
            execute_values(self.cur, insert_sql, values)
            self.conn.commit()  # Assuming you also have self.conn
        except Exception as e:
            self.conn.rollback()
            print("Error inserting DataFrame:", e)


    def crop_tables(self):
        ''


    def batch_download(self, batch_start_date, batch_end_date):
        ''''''

        self.table_name = f"{self.queue}_{self.queue_id}".lower()

        self.batch_start_date = batch_start_date
        self.batch_end_date = batch_end_date

        self.timestamp_start = int(datetime.fromisoformat(self.batch_start_date).timestamp())
        self.timestamp_end = int(datetime.fromisoformat(self.batch_end_date).timestamp())

        self.get_all_player_data_date_range()

        self.save_data()

        
    def init_download_process(self, start_date):
        ''


        self.start_date = start_date
        self.date_tuples = generate_date_tuples(start_time=self.start_date)

        print(self.date_tuples)
        # sys.exit()

        for date_tuple in self.date_tuples:
            try:
                self.batch_download(batch_start_date=date_tuple[0],
                                    batch_end_date=date_tuple[1])
                
            except Exception as e:
                print(f"ERROR for player {self.summoner_name} ->", e)
        
    
        self.crop_tables() # sólo mantenemos datos de como mucho hace un año
