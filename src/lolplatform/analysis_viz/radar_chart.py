from lolplatform.analysis_viz.statsbomb_radar import *
from lolplatform.config.players import player_dict, compare_players_dict
from lolplatform.dataset.db_tables import get_player_data_db

class LoLRadarCompare:
    def __init__(self, conn, player_1, player_2, player_1_champion = None, player_2_champion = None, number_of_games = 50, 
                 table_name = 'ranked_soloq_games_420', 
                 radar_variables = ["damagePerMinute","totalMinionsKilled","visionScorePerMinute",
                                    "teamDamagePercentage","killParticipation",
                                    "goldPerMinute","laneMinionsFirst10Minutes"]):
        '''
        Function to initialize the object of the LoLRadarCompare class.

        Args
            conn: database connection
            player_1: (comes from player_dict)
            player_2: (comes from compare_players_dict)
            player_1_champion: 
            player_2_champion:
            number_of_games: 
        '''

        self.conn = conn 

        self.player_1 = player_1
        self.player_2 = player_2

        self.player_1_champion = player_1_champion
        self.player_2_champion = player_2_champion

        self.games = number_of_games

        if self.player_1_champion != self.player_2_champion:
            print('Careful, you are going to compare stats from playing different champions! \n-> {} with {}, and {} with {}'.format(self.player_1,
                                                                                                                                     self.player_1_champion,
                                                                                                                                     self.player_2,
                                                                                                                                     self.player_2_champion))

        self.table_name = table_name
        self.radar_variables = [var.lower() for var in radar_variables]

    def init_process(self):
        '''
        Function to start the process

        Args

        '''

        ## Data of players from their names
        self.player_rol_1 = player_dict[self.player_1]['rol']
        self.player_rol_2 = compare_players_dict[self.player_2]['rol']

        self.player_1_data = get_player_data_db(conn=self.conn,
                                                player = self.player_1,
                                                player_champion = self.player_1_champion,
                                                games = self.games,
                                                table_name = self.table_name)
        
        self.player_2_data = get_player_data_db(conn=self.conn,
                                                player = self.player_2,
                                                player_champion = self.player_2_champion,
                                                games = self.games,
                                                table_name = self.table_name)

        fig, ax = create_radar_chart(player_1_data=self.player_1_data,
                           player_2_data=self.player_2_data,
                           player_1_name=self.player_1,
                           player_2_name=self.player_2,
                           player_champion_1=self.player_1_champion,
                           player_champion_2=self.player_2_champion,
                           variables=self.radar_variables,
                           last_games=False)

        return fig, ax


# if __name__ == '__main__':

#     ## Players we want to compare:
#     player_1 = 'socorrow'
#     player_2 = 'Dr Mango'

#     player_champion_1 = 'Caitlyn'
#     player_champion_2 = 'Caitlyn'

#     lol_radar = LoLRadarCompare(player_1 = player_1,
#                                   player_2 = player_2,
#                                   player_1_champion = player_champion_1,
#                                   player_2_champion = player_champion_2)

#     lol_radar.init_process()



