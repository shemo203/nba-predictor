#!/bin/bash

cd /home/shero/PycharmProjects/overunderpredict/

source .venv/bin/activate

echo "--- Starting Pipeline: $(date) ---"
python 01_web_scraper.py
python 02_processor.py
python 03_predict.py
echo "--- Pipeline Finished ---"