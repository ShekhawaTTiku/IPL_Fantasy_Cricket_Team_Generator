require("dotenv").config();
const { GoogleSpreadsheet } = require("google-spreadsheet");
const axios = require("axios");
const fs = require("fs");
const csv = require("csv-parser");
const prompt = require("prompt-sync")();

const csvFilePath = "./map.csv";
const doc = new GoogleSpreadsheet(process.env.GOOGLE_SHEET_ID_BAT);

async function authenticateGoogleSheet() {
    try {
        console.log("🔐 Authenticating Google Sheets...");
        
        if (!process.env.GOOGLE_PRIVATE_KEY || !process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL) {
            throw new Error("Missing Google Service Account credentials in environment variables.");
        }

        await doc.useServiceAccountAuth({
            client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
            private_key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, "\n"),
        });

        await doc.loadInfo();
        console.log(`✅ Connected to Google Sheet: ${doc.title}`);
        return doc.sheetsByIndex[0];
    } catch (error) {
        console.error("❌ Google Sheets Authentication Failed:", error.message);
        process.exit(1);
    }
}

async function fetchMatchDetails(matchId) {
    try {
        console.log(`🔍 Fetching details for Match ID: ${matchId}...`);

        const response = await axios.get(`https://unofficial-cricbuzz.p.rapidapi.com/matches/get-scorecard?matchId=${matchId}`, {
            headers: {
                "X-RapidAPI-Host": "unofficial-cricbuzz.p.rapidapi.com",
                "X-RapidAPI-Key": process.env.RAPIDAPI_KEY,
            },
        });

        return response.data;
    } catch (error) {
        console.error(`❌ Error fetching details for Match ID ${matchId}:`, error.message);
        return null;
    }
}

async function loadPlayerMapping(csvFilePath) {
    return new Promise((resolve, reject) => {
        const playerMapping = {};
        fs.createReadStream(csvFilePath)
            .pipe(csv())
            .on("data", (row) => {
                if (row.key_cricbuzz && row.key_cricinfo) {
                    playerMapping[row.key_cricbuzz.trim()] = row.key_cricinfo.trim();
                }
            })
            .on("end", () => resolve(playerMapping))
            .on("error", (error) => reject(error));
    });
}

async function updateGoogleSheet(matchId) {
    const sheet = await authenticateGoogleSheet();
    const playerMapping = await loadPlayerMapping(csvFilePath);
    let rows = [];

    const data = await fetchMatchDetails(matchId);
    if (!data || !data.scorecard || data.scorecard.length === 0) {
        console.error(`❌ No scorecard data available for Match ID ${matchId}`);
        return;
    }

    for (const innings of data.scorecard) {
        const battingTeam = innings.batTeamName;
        const bowlingTeam = data.scorecard.find(team => team.batTeamName !== battingTeam)?.batTeamName || "Unknown";

        for (const batter of innings.batsman) {
            let bowlerName = null;
            let bowlerId = null;
            let bowlerCricinfoId = null; // New field for bowler's Cricinfo ID
            let wicketType = batter.outDec || "Not Out";
            let wicket_Desc = batter.outDec || "Not Out";
            let is_Out = "False";

            // Determine the type of dismissal and bowler details
            if (wicketType.includes("b ") && !wicketType.includes("c ")) {
                bowlerName = wicketType.split("b ")[1]?.trim();
                wicketType = wicketType.includes("lbw") ? "LBW" : "Bowled";
                is_Out = "True";
            } else if (wicketType.includes("c ") && wicketType.includes(" b ")) {
                bowlerName = wicketType.split(" b ")[1]?.trim();
                wicketType = "Caught";
                is_Out = "True";
            } else if (wicketType.includes("st ")) {
                wicketType = "Stumped";
                is_Out = "True";
            } else if (wicketType.includes("run out")) {
                wicketType = "Run Out";
                is_Out = "True";
            } else if (wicketType.includes("hit wicket")) {
                wicketType = "Hit Wicket";
                is_Out = "True";
            }

            // Find the bowler's ID and Cricinfo ID if bowlerName is available
            if (bowlerName) {
                const bowler = innings.bowler.find(b => 
                    b.name.trim() === bowlerName || b.nickName?.trim() === bowlerName // Match name or nickname
                );
                if (bowler) {
                    bowlerId = bowler.id;
                    bowlerCricinfoId = playerMapping[bowler.id?.toString()] || "N/A"; // Map Cricbuzz ID to Cricinfo ID
                }
            }

            // Handle "Did Not Bat" (DNB) cases
            if (!batter.balls && !batter.runs && !batter.fours && !batter.sixes && !batter.outDec) {
                wicketType = "DNB";
                is_Out = "DNB";
            }

            // Map Cricinfo ID for the batter
            const batterCricinfoId = playerMapping[batter.id?.toString()] || "N/A";

            // Push the row to the rows array
            rows.push({
                date: new Date().toISOString().split("T")[0],
                match_id: matchId,
                batting_team: battingTeam,
                bowling_team: bowlingTeam,
                innings: innings.inningsId,
                batter_id: batter.id, // Cricbuzz ID
                batter_cricinfo_id: batterCricinfoId, // Cricinfo ID
                batter: batter.name,
                runs: batter.runs || 0,
                balls: batter.balls || 0,
                fours: batter.fours || 0,
                sixes: batter.sixes || 0,
                strike_rate: batter.strkRate || 0,
                isOut: is_Out,
                wicket_desc: wicket_Desc,
                wicket_type: wicketType,
                bowler_id: bowlerId, // Cricbuzz ID
                bowler_cricinfo_id: bowlerCricinfoId, // Cricinfo ID
                bowler: bowlerName,
                venue: data.venue,
            });
        }
    }

    await sheet.addRows(rows);
    console.log(`✅ Data for match ${matchId} added successfully!`);
}

// Main function to run the script
async function main() {
    const matchId = prompt("Enter the Match ID: ");
    if (matchId) {
        await updateGoogleSheet(matchId);
    } else {
        console.error("❌ Match ID is required.");
    }
}

main();