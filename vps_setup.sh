#!/bin/bash

# ==========================================
# ALPHATRADE BOT VPS SETUP SCRIPT
# ==========================================

echo "🚀 Iniciando configuración del servidor..."

# 1. Actualizar el sistema
echo "🔄 Actualizando el sistema..."
apt update && apt upgrade -y

# 2. Instalar Node.js y npm (para PM2)
echo "📦 Instalando Node.js y npm..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
# apt install nodejs npm -y (Alternativa si curl no está disponible)

# 3. Instalar PM2 globalmente
echo "⚙️ Instalando PM2..."
npm install pm2 -g

# 4. Instalar Python y venv
echo "🐍 Instalando Python3 y dependencias..."
apt install -y python3 python3-pip python3-venv

# 5. Crear carpeta del proyecto (si no existe)
echo "📁 Configurando carpeta del proyecto..."
mkdir -p /root/alphatrade-bot
cd /root/alphatrade-bot

# 6. Crear entorno virtual
echo "🌐 Creando entorno virtual de Python..."
python3 -m venv venv

# 7. Instrucciones para el despliegue manual o bash
echo "✅ Servidor preparado."
echo "------------------------------------------------"
echo "PRÓXIMOS PASOS:"
echo "1. Sube los archivos del proyecto a /root/alphatrade-bot"
echo "2. Ejecuta: source venv/bin/activate"
echo "3. Ejecuta: pip install -r requirements.txt"
echo "4. Ejecuta: pm2 start main.py --name alphatrade-bot --interpreter=venv/bin/python"
echo "5. Ejecuta: pm2 save && pm2 startup"
echo "------------------------------------------------"
