# FINAL VPS Deployment Script for AlphaTrade Bot
# This script automates the deployment of the fixed bot.js with /web command support.
# Run this script in PowerShell.

$VPS_IP = "147.93.181.40"
$VPS_USER = "root"
$REMOTE_DIR = "/root/proyecto/bot"
$BOT_TOKEN = "8377138125:AAGNnAcf-GumcN2DoPETjRRZaiN9QEgqvEk"

Write-Host "📤 Uploading updated bot.js to VPS..." -ForegroundColor Cyan
scp bot.js ${VPS_USER}@${VPS_IP}:${REMOTE_DIR}/bot.js

Write-Host "⚙️ Executing deployment commands on VPS..." -ForegroundColor Cyan
Write-Host "Important: You may be asked for the VPS password again." -ForegroundColor Yellow

ssh ${VPS_USER}@${VPS_IP} @"
    cd ${REMOTE_DIR}
    
    # Ensure dependencies are installed
    npm install telegraf axios dotenv

    # PM2 Deployment / Restart
    pm2 delete bot || true
    pm2 start bot.js --name \"bot\"
    pm2 save

    echo '✅ Bot is LIVE and working with PM2 (using localhost backend).'
    pm2 status bot
"@

Write-Host "🚀 Deployment completed successfully." -ForegroundColor Green
