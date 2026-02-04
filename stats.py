
from nba_api.stats.endpoints import (leaguedashteamstats, leaguegamefinder)
from nba_api.stats.static import teams
import pandas
import time
import sklearn

from pandas.core.methods.selectn import DataFrame
data = []
target_seasons = ["2015-16","2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]
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

    merged_df['HOME_GAME'] = merged_df['MATCHUP'].apply(lambda x: 1 if " vs. " in x else 0)
    merged_df = merged_df.sort_values(by=["TEAM_ID", "GAME_DATE"])


    # ADD "WL" TO THIS LIST
    features = ["EFG_PCT", "TOV_PCT", "ORB_PCT", "FTR", "WL"]

    rolling_data = merged_df.groupby("TEAM_ID")[features].transform(lambda x: x.shift(1).rolling(10).mean())

    rolling_data = rolling_data.rename(columns={"EFG_PCT": "EFG_PCT_L10","TOV_PCT": "TOV_PCT_L10", "ORB_PCT": "ORB_PCT_L10", "FTR": "FTR_L10", "WL": "WIN_PCT_L10"})
    merged_df = pandas.concat([merged_df, rolling_data], axis = 1)

    cols_to_copy = ["EFG_PCT_L10", "TOV_PCT_L10", "ORB_PCT_L10", "FTR_L10", "WIN_PCT_L10"]
    df_rolling_copy = merged_df[["GAME_ID", "TEAM_ID"] + cols_to_copy]

    df_rolling_copy = df_rolling_copy.rename(columns={
        "TEAM_ID": "OPP_ID",
        "EFG_PCT_L10": "OPP_EFG_PCT_L10",
        "TOV_PCT_L10": "OPP_TOV_PCT_L10",
        "ORB_PCT_L10": "OPP_ORB_PCT_L10",
        "FTR_L10": "OPP_FTR_L10",
        "WIN_PCT_L10": "OPP_WIN_PCT_L10"
    })

    merged_df = pandas.merge(merged_df, df_rolling_copy, on=["GAME_ID", "OPP_ID"])

    merged_df["DIFF_EFG"] = merged_df["EFG_PCT_L10"] - merged_df["OPP_EFG_PCT_L10"]
    merged_df["DIFF_TOV"] = merged_df["TOV_PCT_L10"] - merged_df["OPP_TOV_PCT_L10"]
    merged_df["DIFF_ORB"] = merged_df["ORB_PCT_L10"] - merged_df["OPP_ORB_PCT_L10"]
    merged_df["DIFF_FTR"] = merged_df["FTR_L10"] - merged_df["OPP_FTR_L10"]
    merged_df["DIFF_WIN"] = merged_df["WIN_PCT_L10"] - merged_df["OPP_WIN_PCT_L10"]

    merged_df = merged_df.dropna()
    data[i] = merged_df

feature_cols = ["DIFF_EFG", "DIFF_TOV", "DIFF_ORB", "DIFF_FTR", "DIFF_WIN", "HOME_GAME"]
model = sklearn.linear_model.LogisticRegression(C = 0.1, penalty= "l1", solver = "liblinear")

model.fit(X=data[0][feature_cols], y = data[0]["WL"])

print(model.coef_[0]) #DIFF_EFG, DIFF_WIN, HOME_GAME were the most important features, lasso penalty made every other converge to 0
accuracy = model.score(data[1][feature_cols], data[1]["WL"])
print(accuracy)
probs = model.predict_proba(data[1][feature_cols])

data[1]["PREDICTION"] = probs[:, 1]

view_cols = ["GAME_DATE", "MATCHUP", "WL", "PREDICTION"]
recent_games = data[1][view_cols].sort_values(by="GAME_DATE", ascending=True).tail(10)


print(recent_games)


