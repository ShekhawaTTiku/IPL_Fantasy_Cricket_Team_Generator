require("dotenv").config();
const { GoogleSpreadsheet } = require("google-spreadsheet");
const axios = require("axios");
const fs = require("fs");
const csv = require("csv-parser");
const getTodayIPLMatchIds = require("./fetchMatchId");

const csvFilePath = "./people.csv";
const doc = new GoogleSpreadsheet(process.env.GOOGLE_SHEET_ID_BOWL);

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

// Load the mapping from people.csv
async function loadPlayerMapping(csvFilePath) {
    return new Promise((resolve, reject) => {
        const playerMapping = new Map();
        fs.createReadStream(csvFilePath)
            .pipe(csv())
            .on("data", (row) => {
                // Use key_cricbuzz as the primary key, fallback to unique_name or name if key_cricbuzz is blank
                const key = row.key_cricbuzz?.trim() || row.unique_name?.trim() || row.name?.trim();
                if (key && row.key_cricinfo) {
                    playerMapping.set(key, row.key_cricinfo.trim());
                }
            })
            .on("end", () => {
                console.log("✅ People mapping loaded successfully.");
                resolve(playerMapping);
            })
            .on("error", (error) => reject(error));
    });
}

async function updateGoogleSheet() {
    const matchData = await getTodayIPLMatchIds(); // Get multiple matches
    if (!matchData || matchData.length === 0) return;

    const sheet = await authenticateGoogleSheet();
    const playerMapping = await loadPlayerMapping(csvFilePath);
    let rows = [];

    for (const { matchId, venue } of matchData) {
        const data = await fetchMatchDetails(matchId);
        if (!data || !data.scorecard || data.scorecard.length === 0) {
            console.error(`❌ No scorecard data available for Match ID ${matchId}`);
            continue;
        }
    
        for (const innings of data.scorecard) {
            const battingTeam = innings.batTeamName;
            const bowlingTeam = data.scorecard.find(team => team.batTeamName !== battingTeam)?.batTeamName || "Unknown";
        
            // Calculate lbw_or_bowled for each bowler
            const lbwOrBowledCount = {};
            for (const batter of innings.batsman) {
                let bowlerId = null;
                let wicketType = batter.outDec || "Not Out";
        
                // Check for "lbw b BowlerName"
                if (wicketType.toLowerCase().includes("lbw b ")) {
                    const bowlerName = wicketType.split("lbw b ")[1]?.trim();
                    const bowler = innings.bowler.find(b => b.name.trim().toLowerCase() === bowlerName.toLowerCase());
        
                    // If not found by full name, try matching by surname
                    if (!bowler) {
                        const surname = bowlerName.split(" ").pop(); // Extract the last word (surname)
                        bowlerId = innings.bowler.find(b => b.name.toLowerCase().includes(surname.toLowerCase()))?.id;
                    } else {
                        bowlerId = bowler.id;
                    }
        
                    wicketType = "LBW";
                }
                // Check for "b BowlerName" (Bowled)
                else if (wicketType.toLowerCase().includes("b ") && !wicketType.toLowerCase().includes("c ")) {
                    const bowlerName = wicketType.split("b ")[1]?.trim();
                    const bowler = innings.bowler.find(b => b.name.trim().toLowerCase() === bowlerName.toLowerCase());
        
                    // If not found by full name, try matching by surname
                    if (!bowler) {
                        const surname = bowlerName.split(" ").pop(); // Extract the last word (surname)
                        bowlerId = innings.bowler.find(b => b.name.toLowerCase().includes(surname.toLowerCase()))?.id;
                    } else {
                        bowlerId = bowler.id;
                    }
        
                    wicketType = "Bowled";
                }
        
                // Increment lbw_or_bowled count for the bowler
                if (bowlerId && (wicketType === "LBW" || wicketType === "Bowled")) {
                    lbwOrBowledCount[bowlerId] = (lbwOrBowledCount[bowlerId] || 0) + 1;
                }
            }
        
            // Fetch batsmen from the opposing innings
    const opposingInnings = data.scorecard.find(team => team.batTeamName === bowlingTeam);
    const opposingBatsmen = opposingInnings ? opposingInnings.batsman : []; // Ensure opposingBatsmen is defined

    // Combine bowlers and opposing batsmen into a single set of players
    const allPlayers = new Map();

    // Normalize and add bowlers
    innings.bowler.forEach(bowler => {
        const normalizedName = bowler.name.trim(); // Use the bowler's name directly
        if (!allPlayers.has(normalizedName)) {
            allPlayers.set(normalizedName, { id: bowler.id, name: normalizedName });
        }
    });

    // Normalize and add opposing batsmen
    opposingBatsmen.forEach(batter => {
        const normalizedName = batter.name.trim(); // Use the batter's name directly
        const existingPlayer = Array.from(allPlayers.values()).find(player => player.id === batter.id);

        // Only add the batter if their ID is not already in the map
        if (!existingPlayer) {
            allPlayers.set(normalizedName, { id: batter.id, name: normalizedName });
        }
    });

    // Process all players
    for (const [normalizedName, playerData] of allPlayers) {
        const bowler = innings.bowler.find(b => b.id === playerData.id);
        const batter = opposingBatsmen.find(b => b.id === playerData.id);

        // Map player ID using bowler or batter data
        const playerId = playerData.id?.toString() || "N/A";

    // Assign stats for bowlers
    const overs = bowler ? parseFloat(bowler.overs) || 0 : 0;
    const runsConceded = bowler ? bowler.runs || 0 : 0;
    const wickets = bowler ? bowler.wickets || 0 : 0;
    const maidens = bowler ? bowler.maidens || 0 : 0;
    const economy = bowler ? parseFloat(bowler.economy) || 0 : 0;
    const ballsBowled = bowler ? bowler.balls || 0 : 0;
    const lbw_or_bowled = bowler ? lbwOrBowledCount[playerId] || 0 : 0;
    const dots = bowler ? bowler.dots || 0 : 0;

    // Add row to the sheet
    rows.push({
        date: new Date().toISOString().split("T")[0],
        match_id: matchId,
        bowling_team: bowlingTeam,
        batting_team: battingTeam,
        bowler_id: playerId,
        bowler: playerData.name, // Ensure this is the player's name
        innings: innings.inningsId,
        overs: overs,
        runs: runsConceded,
        wickets: wickets,
        maiden: maidens,
        eco: economy,
        balls: ballsBowled,
        lbw_or_bowled: lbw_or_bowled,
        dots: dots,
        venue: venue,
        key_cricinfo: playerMapping.get(playerId) || "N/A", // Map key_cricbuzz to key_cricinfo
    });
}
}
}

await sheet.addRows(rows);
console.log(`✅ Data for all matches added successfully!`);
}

updateGoogleSheet();
