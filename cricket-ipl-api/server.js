const express = require("express");
const updateGoogleSheet_bat = require("./updateGoogleSheet_bat");
// const updateGoogleSheet_bowl = require("./updateGoogleSheet_bowl");

const app = express();
const PORT = process.env.PORT || 3000;

app.get("/update", async (req, res) => {
    try {
        await updateGoogleSheet_bat();
        res.send("✅ Match data updated in Google Sheets.");
    } catch (error) {
        res.status(500).send("❌ Error updating match data.");
    }
});

app.listen(PORT, () => console.log(`🚀 Server running on port ${PORT}`));
