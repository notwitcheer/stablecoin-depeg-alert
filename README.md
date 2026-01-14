# Stablecoin DepegAlert Bot

> **Never miss a stablecoin depeg again**

A Telegram bot that monitors stablecoin pegs in real-time and sends instant alerts when any major stablecoin deviates from $1.00.

## 🎯 Features

- **Real-time monitoring** of 8+ major stablecoins (USDT, USDC, DAI, FRAX, etc.)
- **Instant alerts** when stablecoins deviate >0.5% from peg
- **Smart cooldown** system prevents spam (30min between alerts per coin)
- **Telegram commands** for manual price checking
- **Free & Premium tiers** for different alert sensitivities

## 📊 Monitored Stablecoins

| Tier | Stablecoins | Alert Threshold |
|------|-------------|----------------|
| Free | USDT, USDC, DAI, USDS, FRAX, TUSD, USDP, PYUSD | >0.5% deviation |
| Premium | + 11 additional stablecoins | >0.2% deviation |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Telegram Channel ID for alerts

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd depeg-alert
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate   # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and channel ID
   ```

5. **Run the bot**
   ```bash
   python -m bot.main
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALERT_CHANNEL_ID=-1001234567890

# Optional
PREMIUM_CHANNEL_ID=-1009876543210
WEB_URL=https://stablepeg.xyz
LOG_LEVEL=INFO
```

### Getting Your Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow prompts
3. Save the bot token to your `.env` file

### Getting Channel ID

1. Create a public Telegram channel (e.g., @YourDepegAlerts)
2. Add your bot as an admin
3. Use a tool like [@userinfobot](https://t.me/userinfobot) to get the channel ID
4. Channel IDs are negative numbers (e.g., `-1001234567890`)

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and setup |
| `/status` | Check all stablecoin pegs now |
| `/check USDC` | Check specific stablecoin |
| `/subscribe` | Join alert channels |
| `/help` | Show all commands |

## 🔧 Development

### Project Structure

```
depeg-alert/
├── bot/                 # Telegram bot logic
│   ├── main.py         # Entry point
│   ├── handlers.py     # Command handlers
│   ├── alerts.py       # Alert formatting
│   └── scheduler.py    # Price checking
├── core/               # Core business logic
│   ├── models.py       # Data models
│   ├── prices.py       # API client
│   ├── peg_checker.py  # Peg calculation
│   └── stablecoins.py  # Coin definitions
├── data/               # Data storage
└── config.py          # Configuration
```

### Running Tests

```bash
# Test configuration
python config.py

# Test API connection
python -c "
import asyncio
from core.prices import test_api_connection
print(asyncio.run(test_api_connection()))
"

# Test peg checking
python -c "
import asyncio
from core.peg_checker import check_all_pegs
pegs = asyncio.run(check_all_pegs())
print(f'Checked {len(pegs)} stablecoins')
for p in pegs:
    print(f'{p.symbol}: ${p.price:.4f} ({p.status.value})')
"
```

## 🚀 Deployment

### Option 1: Railway.app (Free Tier)

1. Connect your GitHub repo to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Option 2: Docker

```bash
# Build image
docker build -t depeg-alert .

# Run container
docker run -d --env-file .env depeg-alert
```

### Option 3: VPS

```bash
# On your server
screen -S depegbot
source venv/bin/activate
python -m bot.main
# Press Ctrl+A, D to detach
```

## 📈 Monitoring

The bot logs important events:

- Price check results
- Alert sending
- API errors
- Connection issues

Monitor logs for:
- `✅ Configuration validated successfully`
- `Bot is online and monitoring stablecoins 24/7`
- `Peg check complete: X/Y stable`
- `Alert sent for SYMBOL at $PRICE`

## ⚠️ Rate Limits

- **CoinGecko Free API**: 50 calls/minute
- **Bot usage**: 1 call/minute (well within limits)
- **Alert cooldown**: 30 minutes per coin (prevents spam)

## 🛠️ Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check `TELEGRAM_BOT_TOKEN` is correct
   - Verify bot is started with `/start` command

2. **No alerts being sent**
   - Check `ALERT_CHANNEL_ID` is correct
   - Ensure bot is admin in the channel
   - Verify stablecoins are actually depegging

3. **API errors**
   - Check internet connection
   - Verify CoinGecko API is accessible
   - Check rate limiting

### Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test individual components
python -c "
import asyncio
from core.prices import fetch_prices
prices = asyncio.run(fetch_prices(['usd-coin', 'tether']))
print(prices)
"
```

## 📱 Usage Examples

### Alert Message Format

```
🚨 DEPEG ALERT

🔴 USDT: $0.994 (-0.6%)

📊 All Stablecoins:
⚠️ USDT: $0.994 (-0.6%)
✅ USDC: $1.001 (+0.1%)
✅ DAI: $0.999 (-0.1%)
✅ FRAX: $1.002 (+0.2%)

🕐 14:30 UTC
🔗 stablepeg.xyz
```

### Status Check Response

```
🟢 All Stablecoins Stable

✅ FRAX: $1.002 (+0.2%)
✅ USDC: $1.001 (+0.1%)
✅ USDT: $0.999 (-0.1%)
✅ DAI: $0.999 (-0.1%)

🕐 Updated: 14:30 UTC
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Bot**: Coming soon
- **Channel**: Coming soon
- **Dashboard**: Coming soon
- **Support**: Open an issue on GitHub

---

**Stay safe in DeFi! 🛡️**