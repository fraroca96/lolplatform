import pandas as pd
import matplotlib.pyplot as plt

def plot_win_loss_boxplot(player, player_data, variable):
    """
    Creates a boxplot of the specified variable grouped by the 'win' column in the dataframe.

    Parameters:
    - df: pandas DataFrame containing at least 'win' and the specified variable columns
    - variable: str, the column name to plot the distribution of

    Returns:
    - fig, ax: matplotlib Figure and Axes objects with the boxplot
    """
    df = player_data.copy()
    
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Create boxplot grouped by 'win'
    df.boxplot(column=variable, by='win', ax=ax)
    
    # Set titles and labels
    ax.set_title(f'Distribution of {variable} by Win/Loss for {player}')
    ax.set_xlabel('Win')
    ax.set_ylabel(variable)
    plt.suptitle('')  # Remove automatic title from pandas boxplot
    
    return fig, ax