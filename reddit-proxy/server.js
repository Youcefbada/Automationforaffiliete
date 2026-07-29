const express = require('express');
const axios = require('axios');
const app = express();
const port = process.env.PORT || 3000;

// Set your API key here (or via environment variable)
const API_KEY = process.env.API_KEY || "YOUR_SECRET_KEY";

app.get('/', (req, res) => {
    res.send('Reddit Proxy API is running!');
});

app.get('/reddit', async (req, res) => {
    const sub = req.query.sub;
    const key = req.query.key;

    if (!sub) {
        return res.status(400).json({ error: 'Missing "sub" parameter.' });
    }

    if (key !== API_KEY) {
        return res.status(401).json({ error: 'Unauthorized. Invalid API key.' });
    }

    try {
        const redditUrl = `https://www.reddit.com/r/${sub}/new.json?limit=10`;
        const response = await axios.get(redditUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            timeout: 10000
        });

        // Return the raw Reddit JSON data to the Python bot
        res.json(response.data);
    } catch (error) {
        console.error(`Error fetching r/${sub}:`, error.message);
        res.status(500).json({ 
            error: 'Failed to fetch from Reddit', 
            details: error.response ? error.response.statusText : error.message 
        });
    }
});

app.listen(port, () => {
    console.log(`Reddit Proxy listening on port ${port}`);
});
