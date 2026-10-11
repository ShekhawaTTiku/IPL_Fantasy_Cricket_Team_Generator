<div align="center">

# 🏏 IPL Fantasy Cricket Team Generator

### Match-Aware Player Predictions and Fantasy Squad Optimization

*Build a predicted Best XI, a 15-player squad with its selected XI, or a ranked list from IPL match details and historical player data.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![PyCaret](https://img.shields.io/badge/PyCaret-Predictions-16A085?style=for-the-badge)](https://pycaret.org/)
[![PuLP](https://img.shields.io/badge/PuLP-Team%20Optimization-6A5ACD?style=for-the-badge)](https://github.com/coin-or/pulp)

**[Overview](#-overview) · [Workflow](#-how-it-works) · [Setup](#-installation) · [Usage](#-usage)**

</div>

---

## ✨ Overview

The **IPL Fantasy Cricket Team Generator** combines player performance predictions with a constrained optimization step to help assemble fantasy teams for a match. It builds batting and bowling features from historical match data, calculates batter-versus-bowler matchup information, predicts fantasy points with saved PyCaret models, and selects players under role, credit, and team rules.

Use either a Cricbuzz match number or enter match details manually. The Streamlit app can show match details, the generated team or rankings, and a downloadable CSV.

| 🏏 Match input | 📚 Data | 🧠 Prediction | 📋 Output |
|:---:|:---:|:---:|:---:|
| Cricbuzz scraper or custom teams, venue, and toss | Google Sheets performance and squad data | Saved batting and bowling PyCaret models | Best XI, Best XI + backups, or player rankings |

> Fantasy points are predictions from historical data and project-specific scoring features. They are not guarantees of player performance or an endorsement of any fantasy contest.

---

## 🚀 Features

- 🔀 **Two input modes:** retrieve match details by Cricbuzz fixture number or enter match conditions manually.
- 📈 **Player feature generation:** derive career, venue, innings, recent-form, and match-level features for batters and bowlers.
- ⚔️ **Matchup analysis:** estimate batter matchup scores using opposing bowling profiles.
- 🤖 **Saved model inference:** download batting, bowling, and label-encoder artifacts from the configured Hugging Face repository.
- 🧮 **Constraint-based selection:** optimize predicted points subject to squad size, credits, roles, and team representation.
- 📥 **CSV export:** download the selected team or player ranking from the Streamlit interface.
- 🖥️ **Web and terminal entry points:** use the hosted app or run the Python pipeline locally.

---

## 🔄 How It Works

```text
Choose scraper input or enter match details
                    │
                    ▼
      Load match, historical, and squad data
              from Google Sheets
                    │
                    ▼
  Build batting, bowling, and matchup features
                    │
                    ▼
   Predict fantasy points with saved models
                    │
                    ▼
  Merge predictions with roles and credits
                    │
                    ▼
 Optimize Best XI / 15-player squad / rankings
                    │
                    ▼
     Display results and export as CSV
```

The optimizer maximizes predicted fantasy points. Best XI selection uses an 11-player, 100-credit limit, role-count bounds, and representation from both match teams. Best XI + Backups builds a 15-player squad with an 11-player subset, separate credit limits, and role/team bounds.

---

## 🖥️ Hosted Application

The current project README links to the deployed Streamlit app:

**[Open IPL Fantasy Cricket Team Generator](https://ipl-fantasy-team-predictor.streamlit.app/)**

The hosted deployment requires its own configured secrets and access to the backing Google Sheets and model repository. If the service is unavailable, use the local setup below with credentials you are authorized to use.

---

## ⚙️ Requirements

- Python and packages listed in `requirements.txt`.
- Access to the backing Google Sheets through a Google service account.
- A Hugging Face token with access to the model files in `s1nghayush/FIFS_IPL`.
- Network access for Google Sheets, Hugging Face downloads, and (in scraper mode) Cricbuzz match data.

The model files and source performance sheets are external to this Git repository. The project does not include a locally trained model or a standalone copy of its data.

---

## 📦 Installation

### 1. Clone and Install

```bash
git clone https://github.com/ShekhawaTTiku/IPL_Fantasy_Cricket_Team_Generator.git
cd IPL_Fantasy_Cricket_Team_Generator
python -m venv .venv
```

Activate the environment, then install the pinned project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Configure Credentials

Create a private `.env` file in the project root. Do not commit real credentials.

```dotenv
HUGGING_FACE_TOKEN=your_hugging_face_token
GOOGLE_SERVICE_ACCOUNT_EMAIL=service-account@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_SHEET_ID_MAPPING=your_mapping_and_squad_sheet_id
GOOGLE_SHEET_ID_BAT=your_batting_data_sheet_id
GOOGLE_SHEET_ID_BOWL=your_bowling_data_sheet_id
```

Share the required spreadsheets with the Google service account. The service account is configured for read-only Sheets access. The model loader expects a Hugging Face token with permission to download the project's model repository.

---

## ▶️ Usage

### Streamlit App

```bash
streamlit run streamlit_app.py
```

Choose **Scraper** and provide a match number, or choose **Custom** and set two teams, venue, toss winner, and toss decision. Select an output mode and click **Generate Team**. Results can be downloaded as `team_selection.csv`.

### Terminal Pipeline

```bash
python main.py
```

The terminal flow asks whether to use scraper or custom input and which output mode to generate. Logs and generated prediction/selection files are written locally; the main pipeline creates an `Output/` directory.

### Output Modes

| Mode | Result |
|---|---|
| **Best XI** | One 11-player team optimized under the 100-credit limit. |
| **Best XI + Backups** | A 15-player squad and its selected 11-player team. |
| **Player Rankings** | Players sorted by predicted fantasy points. |

---

## 🧮 Optimization Rules

The rules below reflect the current `scripts/optimiser.py` implementation:

| Constraint | Best XI | 15-player squad |
|---|---:|---:|
| Total players | 11 | 15, including the XI subset |
| Credit cap | 100 | 145 for squad; 100 for XI |
| WK / ALL roles | 1–5 each in XI | 2–7 each in squad |
| BAT / BOWL roles | 2–5 each in XI | 3–7 each in squad |
| Team representation | At least one player per team | At least one per team in XI and three per team in squad |

The rankings mode sorts the available predicted points and does not apply the team-building constraints.

---

## 📁 Project Structure

```text
IPL_Fantasy_Cricket_Team_Generator/
├── streamlit_app.py             # Streamlit interface
├── main.py                      # Terminal pipeline
├── API_doc.md                   # API notes for an earlier web-service interface
├── requirements.txt             # Python dependencies
├── scripts/
│   ├── input_module.py          # Scraper/custom input handling
│   ├── match_scraper.py         # Cricbuzz match details
│   ├── data_loading.py          # Google Sheets access
│   ├── model_loading.py         # Hugging Face model download and loading
│   ├── test_data_gen_bat.py     # Batter feature generation
│   ├── test_data_gen_bowl.py   # Bowler feature generation
│   ├── test_data_gen_matchup.py # Batter/bowler matchup features
│   ├── predict_match.py         # Fantasy point inference
│   ├── optimiser.py             # Team optimization and rankings
│   └── output_module.py        # Output-mode handling
└── Output/                      # Generated locally; ignored by Git
```

---

## ⚠️ Limitations

| Area | Current limitation |
|---|---|
| External dependencies | Match, player, and squad data come from configured Google Sheets; model files are downloaded from Hugging Face. |
| Access | Local runs require valid Google service-account access and an authorized Hugging Face token. |
| Scraper | The scraper depends on the current page structure and fixture URL in `scripts/match_scraper.py`; site changes may require code updates. |
| Model evaluation | This repository does not publish a benchmark table or guarantee current-season predictive accuracy. |
| Fantasy rules | Credit and role constraints are encoded in the optimizer and may not match every contest's current rules. |
| API notes | `API_doc.md` describes a `/predict` endpoint, but the checked-in entry points are the CLI and Streamlit app. |

---

## 🛣️ Future Improvements

- 🗓️ Make the season and fixture source configurable instead of embedding a season-specific URL.
- 📊 Publish a reproducible backtest with season-aware train/test splits and prediction metrics.
- 🧩 Make scoring and fantasy contest constraints configurable.
- 🛡️ Add validation for stale or incomplete spreadsheet data and unavailable model files.
- 📘 Update or remove the API notes so they match the current app entry points.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| **Python / pandas / NumPy** | Data preparation and feature engineering |
| **PyCaret / joblib** | Loading trained batting/bowling models and label encoder |
| **PuLP** | Linear/integer optimization of fantasy teams |
| **Streamlit** | Interactive web interface |
| **gspread / Google service account** | Read historical, performance, and squad sheets |
| **Hugging Face Hub** | Download model artifacts |
| **Requests / BeautifulSoup** | Retrieve match details from Cricbuzz |

---

## 👤 Maintainer

**Digvijay Singh Shekhawat**

[![GitHub](https://img.shields.io/badge/GitHub-@ShekhawaTTiku-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/ShekhawaTTiku)

---

<div align="center">

*Built with 🐍 Python, 📊 data, and 🏏 cricket.*

</div>
