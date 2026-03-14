#!/bin/bash

# ==========================================
# ALPHATRADE BOT DEPLOYMENT SCRIPT (LOCAL)
# ==========================================

# Datos del VPS
VPS_IP="147.93.181.40"
VPS_USER="root"
REMOTE_DIR="/root/alphatrade-bot"

echo "📤 Iniciando despliegue hacia $VPS_IP..."

# 1. Comprimir/Subir archivos (Excluyendo basura)
# Nota: Usamos rsync si está disponible, o scp como alternativa básica.
if command -v rsync >/dev/null 2>&1; then
    echo "🔄 Sincronizando archivos con rsync..."
    rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='.git' --exclude='database/alphatrade.db' ./ $VPS_USER@$VPS_IP:$REMOTE_DIR
else
    echo "⚠️ rsync no detectado. Usando scp (esto puede ser más lento)..."
    scp -r ./* $VPS_USER@$VPS_IP:$REMOTE_DIR
fi

echo "✅ Archivos subidos."

# 2. Reiniciar el bot en el servidor mediante SSH
echo "🔄 Reiniciando el proceso del bot en el VPS..."
ssh $VPS_USER@$VPS_IP << 'EOF'
    cd /root/alphatrade-bot
    # Asegurar que las dependencias estén al día
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Reiniciar con PM2
    pm2 restart alphatrade-bot || pm2 start main.py --name alphatrade-bot --interpreter=venv/bin/python
    pm2 save
EOF

echo "🚀 Despliegue completado con éxito."
