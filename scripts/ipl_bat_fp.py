import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# ---------------- CONFIG ----------------
SHEET_NAME = 'Sheet1'
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

# ---------------- LOAD GOOGLE SHEET ----------------
def load_google_sheet(sheet_url):
    load_dotenv(dotenv_path="cricket-ipl-api/.env")

    private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCfMj6CXlqkKilX\nywe8SocjseYIqRQ7OpnAQB7Ly/DPbQFF++0Bx+rk7xCg3RAApsxOG6OhsLTmUAdK\nlwn3Un+4WZC/W4A7fkl3dbxubiZMUocCXiIqpF4NEobbms+xYtiywWlyLIKVBXz3\npWPa3iODhKu8BmcV2YBg1r4dyJjdKmOXzqy7a1eNNm8//FlDa67oqSCEcpcGSDlQ\nm8ZL6kyHn9Bnu1qVDFxyVjlfFy70G6A7zYOx1lcgTl9W7SJPWXYF+s7kGuZY0lef\n2GPj7q6qlCFd6Q1qg0tb6shVtiKAYl8rYWn8aFE+TyAFR0UPP6IyAtJW9zmKKrQv\nBKdVO5CZAgMBAAECggEASj7fomOo+GllcLmS+QD1N/OPKjjY46q37E67TibmP4dC\nEcalya/YYD8SzUNsZDFmlYMUdKN6KvPmAqagkkVapbq35FcjXhvO3bT+Va5vlCbl\nKniGjMatyoD6fk8cUEmecPf9Wq9hk2jE2Ka9BGWXwI3OnlmKGEmhMwjUEAXvLS4M\nZuQ7XJephacqYguYxOfiZDmMa8BEnPo4kmIQW6oQrUi8L4kAdxI7nUBQM8O4gN0y\nLvrHJAWuL8O7C2vU9+qRWjUCM28fB68YhdEznTb+4Nc2AYXazOa+oHh6y5dSARy8\nHmYBtGlFoNEfxteyRcZNCUF5hd2b+PoKEffPO6NzdQKBgQDRmK/svjci6pqox6s5\n1Bp8ALs+mzEypRJT9QVIE7JYIzeDiZHnh6NQGRqAkEyjlt+V276VLwAiBLuIhnKF\n9fYW7xeh8+E9Wa40E1mvKyPFljD3zq6kFHLDeK8pwFRCtZCsCfDD51EvUQGyrhP2\naZ1zadVeaM7oB1nbbLGdE0wdMwKBgQDCcQXbBucVCjEroO4oiO7CDWTNVpOHS6c0\naPENWBFBreQ0cTxaZwPU8sZ32rogQJFA3610nUetoPbHPizU64eG0RUKV+3bbX82\nnMViS01AK6D+BFqHdxoKgvaCnehfcw2xMdrq2/gRLvPR7oj4yOxoqTeSik11Bug9\nRkZD/sHjAwKBgQCmRxOKJX1oXeZEb+MPBY3dQldJ26S0IPDhWkjOXZHnCklIOSNf\nIuQU71VvGQsz3MWUBbi0cY0Rb9+297JzRCXvG88L1IakPTlOZuuHZBoE7pn6fiVe\nVjqViHCuFr7CDXiwg1JWmHR3rTRDpIaBvlgC77suIsfCm9JVmW1ux5hisQKBgEAa\nTtnkrq5LC+bcSWfnrP8gt0jS8BQ8psUqi73geN/0WjXH1yPerm64EyJUY+RaJQkE\nNQUrDQR6+qC5KMKRW77gk1Uzo+Ehej0g9hnvxWoQeCUGfmoGo/kvL+Hj+UXugmcW\njpu7JU9U8WEWiOWsJ/RhRUb0fZDFVC9PSb8E8BrNAoGARf8Qmhemf55NFTRsFRdO\nKhDIRUdfmSZGkSjvdgZzMmRwYXiosJJpPUEB5VoDbdxV8mnJdlom4mM/9JuLhhJ8\ni5aOaHBlmXAYIC8Svhja4HVFH9iLrqG772BGH0xzowUPYzYITJedK7iPGptMEAk8\n0nP0fdL2zqDJRn41LTuBqCY=\n-----END PRIVATE KEY-----\n"
    client_email = "ipl-933@ipl-fifs.iam.gserviceaccount.com"
    project_id = "1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0"

    service_account_info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": "dummy_key_id",
        "private_key": private_key,
        "client_email": client_email,
        "client_id": "dummy_client_id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
    }

    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# ---------------- CALCULATE BATTING FANTASY POINTS ----------------
def calculate_batting_fantasy_points(data):
    # Add a derived column 'Duck' for players who scored 0 runs and are out
    data['Duck'] = ((data['runs'] == 0) & (data['isOut'] == True)).astype(int)

    # Base fantasy points calculation
    data['batting_fp'] = (
        data['runs'] * 1 +  # Runs: +1 per run
        data['fours'] * 4 +  # Boundary Bonus: +4 per four
        data['sixes'] * 6 +  # Six Bonus: +6 per six
        data['Duck'] * -2  # Duck: -2 pts
    )

    # Add milestone points based on runs
    def milestone_points(runs):
        if runs >= 100:
            return 16  # 100s: +16 pts
        elif runs >= 75:
            return 12  # 75s: +12 pts
        elif runs >= 50:
            return 8  # 50s: +8 pts
        elif runs >= 25:
            return 4  # 25s: +4 pts
        return 0

    # Apply milestone points
    data['batting_fp'] += data['runs'].apply(milestone_points)

    # Strike rate bonus/penalty
    def strike_rate_points(row):
        if row['balls'] >= 10:  # Check if at least 10 balls were played
            if row['strike_rate'] > 170:
                return 6
            elif 150.01 <= row['strike_rate'] <= 170:
                return 4
            elif 130 <= row['strike_rate'] <= 150:
                return 2
            elif 60 <= row['strike_rate'] < 70:
                return -2
            elif 50 <= row['strike_rate'] < 59.99:
                return -4
            elif row['strike_rate'] < 50:
                return -6
        return 0

    # Apply strike rate points
    data['strikeRate_points'] = data.apply(strike_rate_points, axis=1)
    data['batting_fp'] += data['strikeRate_points']

    # Drop the temporary column if not needed
    data.drop(columns=['strikeRate_points', 'Duck'], inplace=True)
    return data

# ---------------- FILTER DATA ----------------
def filter_data(data, start_date):
    data["date"] = pd.to_datetime(data["date"], format=None, errors="coerce")
    data = data.dropna(subset=["date"])
    return data[data["date"] >= pd.Timestamp(start_date)]

# ---------------- MAIN ----------------
def main():
    sheet_url = "https://docs.google.com/spreadsheets/d/1dumS1w_IQ7pv448tm-RKVqAQTEgOMKw59wf914qLHs0/edit?usp=sharing"
    start_date = "2025-03-22"

    df = load_google_sheet(sheet_url)
    filtered_data = filter_data(df, start_date)
    result = calculate_batting_fantasy_points(filtered_data)
    result.to_csv("batting_fantasy_points.csv", index=False)
    print("Fantasy points calculated and saved to 'batting_fantasy_points.csv'")

if __name__ == "__main__":
    main()