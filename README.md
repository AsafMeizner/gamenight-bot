# Discord Mega Bot (Modular)

Features:
- **Secure Encryption**: scrypt + ChaCha20-Poly1305, public encrypted embed with **Decrypt** modal
- **Trivia**: Kahoot-style (timer, speed points), **OpenTDB categories** + autocomplete, local fallback
- **RPS**: Free-join or challenge, private picks, rematch, victory embed
- **TicTacToe**: Button grid, victory embed
- **Truth/Dare**: Reads from `data/`
- **Rice Purity**: Interactive, reads from `data/`
- **Morse**: Encode/Decode
- **Moderation**: server mute/deafen, move voice, jail role timer, etc.
- **Meta**: /help, /ping, /who-am-i

## Setup

1. **Python 3.10+ recommended**  

2. Install deps:

    ```bash
    pip install -r requirements.txt
    ```

3. Create `.env`:

    ```
    DISCORD_TOKEN=YOUR_TOKEN_HERE
    ```

4. Put data files under `data/` (see structure).

5. Run:
    ```bash
    python bot.py
    ```


## Notes
* The bot registers slash commands; first run may take a minute to sync.

* Trivia uses OpenTDB:

    * /trivia questions:10 timer:15 category:"General Knowledge"

    * Category field autocompletes (or use raw ID).

* Encryption:

    * /encrypt seed:"secret" message:"hello" → posts a public embed (with your avatar/name in author), Decrypt button opens a modal and shows the result ephemerally.

    * /decrypt is still available for manual paste.




