import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

today = datetime.today().strftime('%Y_%m_%d')

def evol_one_player(player,
                    player_data, 
                    variable,
                    start_date,
                    weekly = False):

    df = player_data.copy()

    df['match_timestamp'] = pd.to_datetime(df['match_timestamp'])
    df['week'] = df['match_timestamp'].dt.to_period('W').astype(str) 
    # df['day'] = df['match_timestamp'].dt.to_period('D').astype(str) 

    # Filter, only when not early surrender?
    df = df[df['gameendedinearlysurrender'] == 0]
    df = df[df['match_timestamp'] >= pd.to_datetime(start_date)]

    # Calculate the number of games per day
    # games_count = df.groupby('day').size().reset_index(name='games_count')

    if not weekly:
        # Group by daily data and calculate mean of the dynamic 'variable' column
        daily_data = df.groupby(['match_timestamp', 'win'])[variable].mean().reset_index()
        # Rename 'match_timestamp' to 'date' for clarity
        daily_data.rename(columns={'match_timestamp': 'date'}, inplace=True)

        # Plotting the data
        fig, ax = plt.subplots(figsize=(20, 10))

        # Scatter plot for daily data points (mean per day)
        sns.lineplot(
            data=daily_data,
            x=[i for i in range(len(daily_data))],
            y=variable,
            marker='o',
            hue = 'win',
            linestyle='--'
        )

        # Customize the plot
        ax.set_title(f'{variable.capitalize()} - {player.capitalize()}', fontsize=14)
        ax.set_xlabel('Games', fontsize=12)
        ax.set_ylabel(variable.capitalize(), fontsize=12)

        ax.legend(fontsize=10)
        ax.grid(True)

        # Save the figure to a file
        fig.tight_layout()  # Make sure everything fits

        return fig, ax

    else:
        ## Weekly figure
        # Group by week and calculate mean of the variable (assists in this case)
        weekly_data = df.groupby('week')[variable].mean().reset_index()

        # Convert 'week' to datetime format for plotting purposes (start of the week)
        # Use the first day of the week (start of the period) for plotting
        weekly_data['week_start'] = pd.to_datetime(weekly_data['week'].str.split('/').str[0])

        # Calculate rolling mean for weekly data
        weekly_data['rolling_mean'] = weekly_data[variable].rolling(window=4, min_periods=1).mean()  # Adjust window size as needed

        # Calculate win percentage per week (calculate the mean of 'win' per week)
        win_percentage = df.groupby('week')['win'].mean().reset_index()

        # Convert win percentage to a human-readable format (multiply by 100)
        win_percentage['win_percentage'] = win_percentage['win'] * 100

        # Calculate the number of games per week
        games_count = df.groupby('week').size().reset_index(name='games_count')

        # Merge win percentage and games count into the weekly data
        weekly_data = pd.merge(weekly_data, win_percentage[['week', 'win_percentage']], on='week', how='left')
        weekly_data = pd.merge(weekly_data, games_count[['week', 'games_count']], on='week', how='left')

        # Plotting the data
        fig, ax = plt.subplots(figsize=(12, 6))

        # Line plot for rolling mean
        sns.lineplot(data=weekly_data, x='week_start', y='rolling_mean', marker='o', label='Rolling Mean', ax=ax)

        # Add original mean values as points
        sns.scatterplot(data=weekly_data, x='week_start', y=variable, color='red', label='Weekly Mean', ax=ax)


        # Add annotations for win percentage and number of games
        for i, row in weekly_data.iterrows():
            ax.annotate(
                f"{row['win_percentage']:.1f}%",  # Format the win percentage to 1 decimal place
                (row['week_start'], row['rolling_mean']),  # Position the annotation at the rolling mean point
                textcoords="offset points",  # Offset to avoid overlapping the point
                xytext=(0, 10),  # Offset the annotation a bit above the point
                ha='center',  # Horizontal alignment of the text
                fontsize=9,  # Font size of the annotation
                color='black'  # Color of the annotation
            )
            # Add the number of games annotation above the win percentage
            ax.annotate(
                f"G: {row['games_count']}",  # Display number of games
                (row['week_start'], row['rolling_mean']),  # Position the annotation at the rolling mean point
                textcoords="offset points",  # Offset to avoid overlapping the win percentage annotation
                xytext=(0, 20),  # Offset the annotation further above the win percentage
                ha='center',  # Horizontal alignment of the text
                fontsize=9,  # Font size of the annotation
                color='blue'  # Color of the annotation for games count
            )

        # Customize the plot
        ax.set_title(f'{variable.capitalize()} - {player.capitalize()}', fontsize=14)
        ax.set_xlabel('Week', fontsize=12)
        ax.set_ylabel(variable.capitalize(), fontsize=12)
        ax.set_xticks(weekly_data['week_start'])  # Set the positions of the x-ticks
        ax.set_xticklabels(weekly_data['week_start'].dt.strftime('%Y-%m-%d'), rotation=45, ha='right')  # Set the labels and rotate them

        ax.legend(fontsize=10)
        ax.grid(True)

        # Save the figure to a file
        fig.tight_layout()  # Make sure everything fits

        return fig, ax

def evol_two_players_compare(player1,
        player2,
        player_1_data,
        player_2_data,
        variable,
        start_date):
    
    df1 = player_1_data.copy()    

    df1['match_timestamp'] = pd.to_datetime(df1['match_timestamp'])
    # df1['day'] = df1['match_timestamp'].dt.to_period('D').astype(str) 

    # Filter, only when not early surrender?
    df1 = df1[df1['gameendedinearlysurrender'] == 0]
    df1 = df1[df1['match_timestamp'] >= pd.to_datetime(start_date)]

    # Calculate the number of games per day
    # games_count = df1.groupby('day').size().reset_index(name='games_count')

    # Group by daily data and calculate mean of the dynamic 'variable' column
    daily_data1 = df1.groupby(['match_timestamp', 'win'])[variable].mean().reset_index()
    # Rename 'match_timestamp' to 'date' for clarity
    daily_data1.rename(columns={'match_timestamp': 'date'}, inplace=True)

    # Plotting the data
    fig, ax = plt.subplots(figsize=(20, 10))

    # Scatter plot for daily data points (mean per day)
    sns.lineplot(
        data=daily_data1,
        x=[i for i in range(len(daily_data1))],
        y=variable,
        marker='o',
        linestyle='--',
        ax=ax,
        label=player1
    )

    df2 = player_2_data.copy()

    df2['match_timestamp'] = pd.to_datetime(df2['match_timestamp'])
    df2['week'] = df2['match_timestamp'].dt.to_period('W').astype(str) 
    # df2['day'] = df2['match_timestamp'].dt.to_period('D').astype(str) 

    # Filter, only when not early surrender?
    df2 = df2[df2['gameendedinearlysurrender'] == 0]
    df2 = df2[df2['match_timestamp'] >= pd.to_datetime(start_date)]

    # Calculate the number of games per day
    # games_count = df2.groupby('day').size().reset_index(name='games_count')

    # Group by daily data and calculate mean of the dynamic 'variable' column
    daily_data2 = df2.groupby(['match_timestamp', 'win'])[variable].mean().reset_index()
    # Rename 'match_timestamp' to 'date' for clarity
    daily_data2.rename(columns={'match_timestamp': 'date'}, inplace=True)

    # Scatter plot for daily data points (mean per day)
    sns.lineplot(
        data=daily_data2,
        x=[i for i in range(len(daily_data2))],
        y=variable,
        marker='o',
        # hue='win',
        linestyle='--',
        ax=ax,
        label=player2
    )

    # Customize the plot
    ax.set_title(f'{variable.capitalize()} - {player1.capitalize()} vs {player2.capitalize()}', fontsize=14)
    ax.set_xlabel('Games', fontsize=12)
    ax.set_ylabel(variable.capitalize(), fontsize=12)

    ax.legend(fontsize=10)
    ax.grid(True)

    # Save the figure to a file
    fig.tight_layout()  # Make sure everything fits

    return fig, ax



# if __name__ == '__main__':

#     player1 = 'socorrow'
#     player2 = 'chains'
#     variable = 'teamDamagePercentage'
#     start_date = '2025-01-01'

#     evol_one_player(player=player1,
#          variable=variable)
#     evol_two_players_compare(player1=player1,
#                              player2=player2,
#                              start_date=start_date,
#          variable=variable)