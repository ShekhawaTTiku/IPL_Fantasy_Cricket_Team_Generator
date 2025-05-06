require("dotenv").config();
const axios = require("axios");

// Define month names globally
const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Function to get today's date in the correct format
const getFormattedDate = () => {
    const today = new Date();
    const day = today.getDate();
    const month = monthNames[today.getMonth()];
    const year = today.getFullYear();
    // return `${day} ${month} ${year}`; // Uncomment for dynamic date
     return "6 May 2025"; // Hardcoded for testing
};

async function getTodayIPLMatchId() {
    try {
        console.log("🔍 Fetching recent matches...");

        const response = await axios.get("https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent", {
            headers: {
                "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com",
                "X-RapidAPI-Key": process.env.RAPIDAPI_KEY,
            },
        });

        const matches = response.data.typeMatches; // Top-level array containing match types

        const todayDate = getFormattedDate();
        console.log(`🔍 Looking for IPL 2025 matches on: ${todayDate}`);

        let matchDetails = [];

        // Loop through different match types
        for (const matchType of matches) {
            for (const series of matchType.seriesMatches) {
                if (series.seriesAdWrapper?.seriesName === "Indian Premier League 2025") {
                    for (const match of series.seriesAdWrapper.matches) {
                        // Convert timestamp to a readable date format
                        const matchDate = new Date(parseInt(match.matchInfo.startDate));
                        const formattedMatchDate = `${matchDate.getDate()} ${monthNames[matchDate.getMonth()]} ${matchDate.getFullYear()}`;

                        if (formattedMatchDate === todayDate) {
                            const matchId = match.matchInfo.matchId;
                            const venue = match.matchInfo.venueInfo.ground;
                            matchDetails.push({ matchId, venue });
                            console.log(`✅ Found IPL Match: ID: ${matchId}, Venue: ${venue}`);
                        }
                    }
                }
            }
        }

        if (matchDetails.length === 0) {
            console.log("❌ No IPL matches found for today.");
            return null;
        }

        return matchDetails; // Return an array of matches

    } catch (error) {
        console.error("❌ Error fetching match IDs:", error.message);
        return null;
    }
}

module.exports = getTodayIPLMatchId;
