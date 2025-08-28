# API Documentation

The web application exposes a single API endpoint to generate team predictions.
```http request
Endpoint: /predict

Method: POST

Content-Type: application/json
```
Description: Triggers the full data processing and prediction pipeline based on the provided match details.

### Request Body

The structure of the request body depends on the input_method.

#### 1. Using scraper method:

This method is simpler and only requires the Cricbuzz match number.

    input_method: "scraper"

    match_number: (string or number) The sequential match number from the Cricbuzz fixtures page.

    output_mode: (string or number) 1 for Best XI, 2 for Best XI + Backups, 3 for Rankings.

Example Payload:
```json
{
    "input_method": "scraper",
    "match_number": "25",
    "output_mode": "2"
}
```

#### 2. Using custom method:

This method requires all match details to be provided manually.

    input_method: "custom"

    output_mode: (string or number) 1, 2, or 3.

    match_details: (object) An object containing the following fields:

        team1: (string) Abbreviation of the first team (e.g., "CSK").

        team2: (string) Abbreviation of the second team (e.g., "MI").

        venue: (string) The full name of the stadium.

        toss_winner: (string) The team that won the toss (e.g., "CSK").

        toss_decision: (string) The choice made after winning the toss ("bat" or "field").

Example Payload:
```json
{
    "input_method": "custom",
    "output_mode": "1",
    "match_details": {
        "team1": "RCB",
        "team2": "SRH",
        "venue": "M.Chinnaswamy Stadium",
        "toss_winner": "SRH",
        "toss_decision": "field"
    }
}
```


### Success Response

    Status Code: 200 OK

    Content: A JSON array of objects, where each object represents a player in the generated team or ranking. The columns will vary based on the output_mode.

#### Example Response (for output_mode 1 or 2):
```json
[
    {
        "C/VC": "captain",
        "player_name": "V Kohli",
        "player_team": "RCB"
    },
    {
        "C/VC": "vice captain",
        "player_name": "H Klaasen",
        "player_team": "SRH"
    },
    {
        "C/VC": null,
        "player_name": "F du Plessis",
        "player_team": "RCB"
    }
]
```


### Error Response

    Status Code: 400 Bad Request (for invalid input) or 500 Internal Server Error (for pipeline failures).

    Content: A JSON object containing an error message.

#### Example Error Response:

```json
{
    "error": "Failed to get match details. The scraper might have failed or input was invalid."
}
```