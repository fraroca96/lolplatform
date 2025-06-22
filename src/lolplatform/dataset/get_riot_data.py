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
from dotenv import load_dotenv # type: ignore
from lolplatform.config.player_data import name_dict

class lolData():
    def __init__(self, player, region="europe"):
        r'''
        Function to initialize the object of the class.

        Args
            player:
        '''
        load_dotenv()

        self.player = player
        self.region = region
        
        self.data_path = os.environ.get("DATA_PATH", "")
        self.riot_api_key = os.environ.get("RIOT_API_KEY", "")

        self.summoner_name = name_dict[player]["summoner_name"]
        self.summoner_tagline = name_dict[player]["summoner_tagline"]


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
            self.api_key
        )
        
        resp = requests.get(api_url)
        player_info = resp.json()
        puuid = player_info['puuid']
        
        # print(puuid)
        self.puuid = puuid


