require("dotenv").config();
const { GoogleSpreadsheet } = require("google-spreadsheet");
const axios = require("axios");
const fs = require("fs");
const csv = require("csv-parser");
const getTodayIPLMatchIds = require("./fetchMatchId");

// const csvFilePath = "./map.csv";
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

        // Access sheets by name
        const sheet1 = doc.sheetsByTitle["Sheet1"];
        const sheet2 = doc.sheetsByTitle["Sheet2"];

        if (!sheet1 || !sheet2) {
            throw new Error("One or both sheets (Sheet1, Sheet2) not found in the spreadsheet.");
        }

        return { sheet1, sheet2 };
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

// async function loadPlayerMapping(csvFilePath) {
//     return new Promise((resolve, reject) => {
//         const playerMapping = {};
//         fs.createReadStream(csvFilePath)
//             .pipe(csv())
//             .on("data", (row) => {
//                 if (row.key_cricbuzz && row.key_cricinfo) {
//                     playerMapping[row.key_cricbuzz.trim()] = row.key_cricinfo.trim();
//                 }
//             })
//             .on("end", () => resolve(playerMapping))
//             .on("error", (error) => reject(error));
//     });
// }

async function loadPlayerMappingFromSheet() {
    const mappingSheet = new GoogleSpreadsheet(process.env.GOOGLE_SHEET_ID_MAPPING);

    await mappingSheet.useServiceAccountAuth({
        client_email: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
        private_key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, "\n"),
    });

    await mappingSheet.loadInfo();

    const sheet = mappingSheet.sheetsByTitle["Mapping"]; // or whichever name you're using
    const rows = await sheet.getRows();

    const mapping = {};
    for (const row of rows) {
        if (row.key_cricbuzz && row.key_cricinfo) {
            mapping[row.key_cricbuzz.trim()] = row.key_cricinfo.trim();
        }
    }

    return mapping;
}

async function updateGoogleSheet() {
    const matchData = await getTodayIPLMatchIds();
    if (!matchData || matchData.length === 0) return;

    const { sheet1, sheet2 } = await authenticateGoogleSheet();
    // const playerMapping = await loadPlayerMapping(csvFilePath);
    const playerMapping = await loadPlayerMappingFromSheet();

    let batterRows = [];

    for (const { matchId, venue } of matchData) {
        const data = await fetchMatchDetails(matchId);
        if (!data || !data.scorecard || data.scorecard.length === 0) {
            console.error(`❌ No scorecard data available for Match ID ${matchId}`);
            continue;
        }

        for (const innings of data.scorecard) {
            const battingTeam = innings.batTeamName;
            const bowlingTeam = data.scorecard.find(team => team.batTeamName !== battingTeam)?.batTeamName || "Unknown";

            for (const batter of innings.batsman) {
                let bowlerName = null;
                let bowlerId = null;
                let bowlerCricinfoId = null;
                let wicketType = batter.outDec || "Not Out";
                let wicket_Desc = batter.outDec || "Not Out";
                let is_Out = "False";

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

                if (bowlerName) {
                    const bowler = innings.bowler.find(b =>
                        b.name.trim() === bowlerName || b.nickName?.trim() === bowlerName
                    );
                    if (bowler) {
                        bowlerId = bowler.id;
                        bowlerCricinfoId = playerMapping[bowler.id?.toString()] || "N/A";
                    }
                }

                if (!batter.balls && !batter.runs && !batter.fours && !batter.sixes && !batter.outDec) {
                    wicketType = "DNB";
                    is_Out = "DNB";
                }

                const batterCricinfoId = playerMapping[batter.id?.toString()] || "N/A";

                batterRows.push({
                    date: new Date().toISOString().split("T")[0],
                    match_id: matchId,
                    batting_team: battingTeam,
                    bowling_team: bowlingTeam,
                    innings: innings.inningsId,
                    batter_id: batter.id,
                    batter_cricinfo_id: batterCricinfoId,
                    batter: batter.name,
                    runs: batter.runs || 0,
                    balls: batter.balls || 0,
                    fours: batter.fours || 0,
                    sixes: batter.sixes || 0,
                    strike_rate: batter.strkRate || 0,
                    isOut: is_Out,
                    wicket_desc: wicket_Desc,
                    wicket_type: wicketType,
                    bowler_id: bowlerId,
                    bowler_cricinfo_id: bowlerCricinfoId,
                    bowler: bowlerName,
                    venue: venue.split(",")[0].trim(),
                    league: "IPL",
                });
            }
        }
    }

    // Write same data to both sheets
    await sheet1.addRows(batterRows);
    await sheet2.addRows(batterRows);
    console.log(`✅ Data added to both Sheet1 and Sheet2 successfully!`);
}

updateGoogleSheet();