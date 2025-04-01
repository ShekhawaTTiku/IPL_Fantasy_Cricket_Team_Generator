const express = require("express");
const updateGoogleSheet_bat = require("./updateGoogleSheet_bat");
// const updateGoogleSheet_bowl = require("./updateGoogleSheet_bowl");

const app = express();
const PORT = process.env.PORT || 3000;

app.get("/update", async (req, res) => {
    try {
        console.log("🔄 Updating batting data...");
        await updateGoogleSheet_bat();
        console.log("✅ Batting data updated.");

        // console.log("🔄 Updating bowling data...");
        // await updateGoogleSheet_bowl();
        // console.log("✅ Bowling data updated.");

        res.send("✅ Match data updated in Google Sheets.");
    } catch (error) {
        console.error("❌ Error updating match data:", error);
        res.status(500).send(`❌ Error updating match data: ${error.message}`);
    }
});


app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
