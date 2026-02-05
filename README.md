# NBA Game Predictor

Hybrid prediction system for NBA games combining statistical modeling with real-time news sentiment.

## How it works

1. **Web scraper** pulls latest NBA headlines from RealGM
2. **LLM processor** scores news sentiment per team (injuries, trades, etc.) using Llama 3.3 70B via Groq
3. **Predictor** runs logistic regression on 10 seasons of historical data, then adjusts with sentiment scores

## Features I built

- Four Factors feature engineering (EFG%, TOV%, ORB%, FTR) with 10-game rolling averages
- Opponent-adjusted differentials to capture relative team strength
- L1 regularization for automatic feature selection — turns out shooting efficiency and home court matter most
- Daily pipeline automation via bash script

## Tech stack

- Python, pandas, scikit-learn
- BeautifulSoup for scraping
- Groq API (Llama 3.3 70B) for sentiment
- nba_api for historical stats

## Run it

```bash
# install deps
pip install -r requirements.txt

# add your Groq API key to .env
echo "GROQ_API_KEY=your_key_here" > .env

# run the pipeline
./run_daily.sh
