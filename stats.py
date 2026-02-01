from nba_api.stats.endpoints import (leaguedashteamstats, leaguegamefinder)
from nba_api.stats.static import teams
import pandas
import time
import scikit-learn

from pandas.core.methods.selectn import DataFrame

target_seasons = ["2022-23", "2023-24", "2024-25"]
all_games = []
#All team stats
for season in target_seasons:
    game_finder = leaguegamefinder.LeagueGameFinder(season_nullable=season, league_id_nullable= "00", season_type_nullable= "Regular Season")
    games = game_finder.get_data_frames()[0]
    all_games.append(games)
    time.sleep(2)

print(type(all_games)) #list of dataframes

df = pandas.concat(all_games, ignore_index=True) #merge all dataframes together
print(df.head())
print(df.columns)

df_opponent = df[["GAME_ID", "TEAM_ID", "DREB"]]

#Effective field goal percentage
df["EFG_PCT"] = (df["FGM"] + 0.5 * df["FG3M"])/ df["FGA"]

#Turnover (TOV%)
df["TOV_PCT"] = df["TOV"] + (df["FGA"] + 0.44 * df["FTA"] + df["TOV"])

#Offensive Rebound (ORB%)
df_opponent = df_opponent.rename(columns={"TEAM_ID": "OPP_ID", "DREB": "OPP_DREB"})

merged_df = pandas.merge(df, df_opponent, on="GAME_ID")

df = merged_df[merged_df["TEAM_ID"] != merged_df["OPP_ID"]]

df["ORB_PCT"] = df["OREB"] / (df["OREB"] + df["OPP_DREB"])

df["FTR"] = df["FTA"] / df["FGA"]

print(df.iloc[0])


