
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.live.nba.endpoints import scoreboard
from datetime import datetime
import pandas
import time
import json
import os
import sklearn
from pandas.core.methods.selectn import DataFrame

#Helper functions
def get_llm_adjustments(json_file_path="data.json"):
    try:
        with open(json_file_path, "r") as f:
            nba_history = json.load(f)
        if not nba_history: return {}
        latest_analytics = nba_history[-1].get("analytic", [])
        team_scores = {}
        for item in latest_analytics:
            team = item.get("team")
            # Safety check: Default to 0.0 if score is missing
            score = item.get("score", 0.0) * 0.10
            team_scores[team] = team_scores.get(team, 0.0) + score
        return team_scores
    except Exception:
        return {}

def apply_hybrid_logic(row):
    base_prob = row['PREDICTION']

    # parse matchup correctly for @ and vs
    if " @ " in row['MATCHUP']:
        away, home = row['MATCHUP'].split(" @ ")
    else:
        home, away = row['MATCHUP'].split(" vs. ")

    home_adj = llm_adjustments.get(home, 0.0)
    away_adj = llm_adjustments.get(away, 0.0)

    # Home news helps home
    total_adj = home_adj - away_adj

    return max(0.0, min(1.0, base_prob + total_adj))
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

#Get today games
board = scoreboard.ScoreBoard()
todays_games = board.games.get_dict()
ghost_rows = [] #filler rows
today_date = datetime.now().strftime("%Y-%m-%d")

for game in todays_games:

    ghost_rows.append({
        "TEAM_ID": game['homeTeam']['teamId'],
        "GAME_ID": game['gameId'],
        "GAME_DATE": today_date,
        "MATCHUP": f"{game['homeTeam']['teamTricode']} vs. {game['awayTeam']['teamTricode']}",
        "WL": None, # <--- IMPORTANT: This tells us it's a prediction game
        "FGM": 0, "FGA": 0, "FG3M": 0, "TOV": 0, "FTA": 0, "OREB": 0
    })
    ghost_rows.append({
        "TEAM_ID": game['awayTeam']['teamId'],
        "GAME_ID": game['gameId'],
        "GAME_DATE": today_date,
        "MATCHUP": f"{game['awayTeam']['teamTricode']} @ {game['homeTeam']['teamTricode']}",
        "WL": None,
        "FGM": 0, "FGA": 0, "FG3M": 0, "TOV": 0, "FTA": 0, "OREB": 0
    })

if ghost_rows:
    test = pandas.concat([test, pandas.DataFrame(ghost_rows)], ignore_index=True)

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

    #Get opponent stats
    df_opponent = df[["GAME_ID", "TEAM_ID", "DREB"]].copy()
    df_opponent = df_opponent.rename(columns={"TEAM_ID": "OPP_ID", "DREB": "OPP_DREB"})

    merged_df = pandas.merge(df, df_opponent, on="GAME_ID")
    merged_df = merged_df[merged_df["TEAM_ID"] != merged_df["OPP_ID"]]
    merged_df["ORB_PCT"] = merged_df["OREB"] / (merged_df["OREB"] + merged_df["OPP_DREB"])
    merged_df['WL_NUM'] = merged_df['WL'].map({'W': 1, 'L': 0}) #None means today games
    merged_df['HOME_GAME'] = merged_df['MATCHUP'].apply(lambda x: 1 if " vs. " in x else 0)
    merged_df = merged_df.sort_values(by=["GAME_DATE", "TEAM_ID"])

    features = ["EFG_PCT", "TOV_PCT", "ORB_PCT", "FTR", "WL_NUM"]
    #rolling mean 10 days
    rolling_data = merged_df.groupby("TEAM_ID")[features].transform(lambda x: x.shift(1).rolling(10).mean())

    rolling_data = rolling_data.rename(columns={"EFG_PCT": "EFG_PCT_L10","TOV_PCT": "TOV_PCT_L10", "ORB_PCT": "ORB_PCT_L10", "FTR": "FTR_L10", "WL_NUM": "WIN_PCT_L10"})
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

    merged_df = merged_df.dropna(subset=["DIFF_EFG"])
    data[i] = merged_df

print(data[1][["GAME_DATE", "MATCHUP", "WL"]].tail(10))
feature_cols = ["DIFF_EFG", "DIFF_TOV", "DIFF_ORB", "DIFF_FTR", "DIFF_WIN", "HOME_GAME"]

#Training data
train_df = data[0].dropna(subset=["WL_NUM"])
model = sklearn.linear_model.LogisticRegression(C=0.1, penalty="l1", solver="liblinear")
model.fit(X=train_df[feature_cols], y=train_df["WL_NUM"])

#Test data, 2025-26 season
test_df = data[1]
todays_predictions = test_df[test_df["WL_NUM"].isna()].copy()

print(model.coef_[0]) #DIFF_EFG, DIFF_WIN, HOME_GAME were the most important features, lasso penalty made every other converge to 0
if not todays_predictions.empty:
    probs = model.predict_proba(todays_predictions[feature_cols])
    todays_predictions["PREDICTION"] = probs[:, 1]


    llm_adjustments = get_llm_adjustments()
    todays_predictions["HYBRID_PRED"] = todays_predictions.apply(apply_hybrid_logic, axis=1)
    print("\n--- Todays predictions ---")
    view_cols = ["GAME_DATE", "MATCHUP", "PREDICTION", "HYBRID_PRED"]
    print(todays_predictions[todays_predictions["HOME_GAME"] == 1][view_cols])

    # save to CSV to predict future accuracy
    csv_path = "/home/shero/PycharmProjects/overunderpredict/tracker.csv"
    final_view = todays_predictions[todays_predictions["HOME_GAME"] == 1][view_cols]
    final_view.to_csv(csv_path, mode='a', header=not os.path.exists(csv_path), index=False)

else:
    print("No games found for today!")





