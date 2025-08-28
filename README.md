# Fantasy Cricket Team Generator

This project is a comprehensive tool for fantasy cricket enthusiasts, specifically designed for the Indian Premier League (IPL). 
It leverages machine learning models to predict player performance based on a rich set of historical data, recent form, and match-specific conditions. 
The application can generate optimized fantasy teams (Best XI or a 15-player squad) based on these predictions, adhering to standard fantasy sports constraints like budget and player roles.

## Features

- Dual Input Modes:
  - Scraper Mode: Automatically fetches match details, including playing XI, venue, and toss information, using just a match number from Cricbuzz. 
  - Custom Mode: Allows users to manually input all match details for full control and flexibility.

- Machine Learning Predictions: Utilizes pre-trained pycaret models to predict fantasy points for both batsmen and bowlers.
- Advanced Stat Generation: Computes a wide array of historical statistics for each player, including career, venue-specific, innings-specific, and recent form (last 5 matches) stats. 
- Matchup Analysis: Calculates a "matchup score" for each batsman based on the bowling strengths and styles of the opposition team. 
- Fantasy Team Optimization: Uses the PuLP optimization library to solve for the optimal fantasy team based on predicted points, player credits, roles, and team composition rules. 
- Multiple Output Options:
  - Best XI: The single best 11-player team. 
  - Best XI + Backups: A 15-player squad with the optimal 11 players. 
  - Player Rankings: A simple ranked list of all players based on their predicted fantasy points.
