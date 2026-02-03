import sklearn.linear_model
from nba_api.stats.endpoints import (leaguedashteamstats, leaguegamefinder)
from nba_api.stats.static import teams
import pandas
import time
import sklearn

from pandas.core.methods.selectn import DataFrame
data = []
target_seasons = ["2022-23", "2023-24", "2024-25"]
all_games = []
#All team stats
for season in target_seasons:
    game_finder = leaguegamefinder.LeagueGameFinder(season_nullable=season, league_id_nullable= "00", season_type_nullable= "Regular Season")
    games = game_finder.get_data_frames()[0]
    all_games.append(games)
    time.sleep(2)

game_finder = leaguegamefinder.LeagueGameFinder(season_nullable="2025-26", league_id_nullable= "00", season_type_nullable= "Regular Season")
test = game_finder.get_data_frames()[0]
test = test.dropna(subset=['WL'])

print(type(all_games)) #list of dataframes

training = pandas.concat(all_games, ignore_index=True) #merge all dataframes together
data.append(training)
data.append(test)

for i, df in enumerate(data):
    #EFG
    df["EFG_PCT"] = (df["FGM"] + 0.5 * df["FG3M"]) / df["FGA"]
    #TOV_PCT
    df["TOV_PCT"] = df["TOV"] / (df["FGA"] + 0.44 * df["FTA"] + df["TOV"])
    #FTR
    df["FTR"] = df["FTA"] / df["FGA"]

    df_opponent = df[["GAME_ID", "TEAM_ID", "DREB"]].copy()
    df_opponent = df_opponent.rename(columns={"TEAM_ID": "OPP_ID", "DREB": "OPP_DREB"})

    merged_df = pandas.merge(df, df_opponent, on="GAME_ID")

    merged_df = merged_df[merged_df["TEAM_ID"] != merged_df["OPP_ID"]]

    merged_df["ORB_PCT"] = merged_df["OREB"] / (merged_df["OREB"] + merged_df["OPP_DREB"])

    merged_df['WL'] = merged_df['WL'].apply(lambda x: 1 if x == 'W' else 0)

    data[i] = merged_df



