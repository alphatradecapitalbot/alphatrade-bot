require('dotenv').config()

const { Telegraf, Markup } = require('telegraf')

const bot = new Telegraf(process.env.BOT_TOKEN)

// Main Menu Keyboard
const mainMenu = Markup.keyboard([
  ['🌐 Abrir Plataforma'],
  ['💰 Depositar USDT', '📊 Mi inversión'],
  ['💸 Retirar', '👥 Referidos']
]).resize();

bot.start(async (ctx) => {
  try {
    const id = ctx.from.id
    console.log("User started:", id)

    await ctx.reply(
      "🚀 Bienvenido a AlphaTrade\n\nPresiona para entrar 👇",
      mainMenu
    )

  } catch (err) {
    console.log("ERROR:", err)
  }
})

// Handle "🌐 Abrir Plataforma" button from main menu
bot.hears('🌐 Abrir Plataforma', async (ctx) => {
  try {
    const telegram_id = ctx.from.id
    const url = `http://147.93.181.40:3000/?user_id=${telegram_id}`

    await ctx.reply(
      "🚀 Accede a la plataforma aquí 👇",
      Markup.inlineKeyboard([
        [Markup.button.url("🎰 Entrar a la plataforma", url)]
      ])
    )
  } catch (err) {
    console.log("ERROR HEARING WEB:", err)
  }
})

bot.launch()

console.log("BOT RUNNING")
