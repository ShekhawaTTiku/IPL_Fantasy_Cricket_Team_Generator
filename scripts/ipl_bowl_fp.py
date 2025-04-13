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

# ---------------- CALCULATE BOWLING FANTASY POINTS ----------------
# ---------------- CALCULATE BOWLING FANTASY POINTS ----------------
def calculate_bowling_fantasy_points(data):
    # Calculate wicket points (+30 per wicket)
    data['wicket_points'] = data['wickets'] * 30

    # Calculate bonus for LBW/Bowled (+8 per dismissal)
    data['bonus_lbw_bowled'] = data['lbw_or_bowled'] * 8

    # Calculate 5-wicket milestone bonus
    data['5_wicket_bonus'] = (data['wickets'] >= 5).astype(int) * 12

    # Calculate maiden over bonus (+12 per maiden over)
    data['maiden_over_bonus'] = data['maiden'] * 12

    # Economy rate points calculation function
    def calculate_economy_points(row):
        if row['overs'] < 2:  # Minimum 2 overs condition
            return 0
        eco = row['eco']
        if eco < 5:
            return 6
        elif 5 <= eco <= 5.99:
            return 4
        elif 6 <= eco < 7:
            return 2
        elif 10 <= eco < 11:
            return -2
        elif 11 <= eco < 12:
            return -4
        elif eco >= 12:
            return -6
        return 0  # Default case

    # Apply economy rate points calculation
    data['economy_rate_points'] = data.apply(calculate_economy_points, axis=1)

    # Calculate total bowling fantasy points
    data['bowling_fp'] = (
        data['wicket_points'] +
        data['bonus_lbw_bowled'] +
        data['5_wicket_bonus'] +
        data['maiden_over_bonus'] +
        data['economy_rate_points']
    )

    # Drop temporary columns if not needed
    temp_columns = ['wicket_points', 'bonus_lbw_bowled', '5_wicket_bonus',
                    'maiden_over_bonus', 'economy_rate_points']
    data.drop(columns=temp_columns, inplace=True)

    return data

# ---------------- FILTER DATA ----------------
def filter_data(data, start_date):
    data["date"] = pd.to_datetime(data["date"], format=None, errors="coerce")
    data = data.dropna(subset=["date"])
    return data[data["date"] >= pd.Timestamp(start_date)]

# ---------------- MAIN ----------------
def main():
    sheet_url = "https://docs.google.com/spreadsheets/d/1-RxTFF7yXo8iB7Dl6JxdHQmub7Wr21aZZ2f_k18gwiU/edit?usp=sharing"
    start_date = "2025-03-22"

    df = load_google_sheet(sheet_url)
    filtered_data = filter_data(df, start_date)
    result = calculate_bowling_fantasy_points(filtered_data)
    result.to_csv("bowling_fantasy_points.csv", index=False)
    print("Fantasy points calculated and saved to 'bowling_fantasy_points.csv'")

if __name__ == "__main__":
    main()