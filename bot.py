import os
import asyncio
from collections import defaultdict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from openai import OpenAI


TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("Falta TELEGRAM_BOT_TOKEN")

if not OPENROUTER_API_KEY:
    raise ValueError("Falta OPENROUTER_API_KEY")


# OpenRouter usando la interfaz compatible con OpenAI
cliente = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)


# Modelo gratuito
MODELO = "openrouter/free"


# Guardamos los mensajes de cada grupo
mensajes = defaultdict(list)

# Guardamos los grupos donde Desmadrita está presente
grupos = set()


def nombre_usuario(user):
    if user.username:
        return f"@{user.username}"

    return user.full_name or "Usuario"


def preguntar_ia(instrucciones, texto):
    respuesta = cliente.chat.completions.create(
        model=MODELO,
        messages=[
            {
                "role": "system",
                "content": instrucciones,
            },
            {
                "role": "user",
                "content": texto,
            },
        ],
    )

    return respuesta.choices[0].message.content


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜🤖 ¡Hola! Soy Desmadrita, la integrante virtual "
        "de Somos un Desmadre.\n\n"
        "📝 Puedo resumir lo que pasa en el grupo.\n"
        "💬 Si me hablan, también converso. 😏🔥"
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜🤖 DESMADRAITA\n\n"
        "📝 /resumen — hago un resumen del grupo.\n"
        "💬 Mencioname para hablar conmigo.\n"
        "⏰ También hago un resumen automático cada 5 horas."
    )


async def conversar(texto, nombre):
    try:
        instrucciones = (
            "Sos Desmadrita, una integrante virtual femenina "
            "del grupo de Telegram Somos un Desmadre. "
            "Sos divertida, fisgona, simpática y con un poquito "
            "de picante. Hablás en español rioplatense natural. "
            "No seas pesada ni respondas como un robot. "
            "Contestá breve, natural y entretenida. "
            "No inventes información."
        )

        return preguntar_ia(
            instrucciones,
            f"{nombre} te dijo: {texto}",
        )

    except Exception as error:
        print("Error conversando:", error)

        return (
            "😏💜 Se me cruzaron un poquito los cables... "
            "probá de nuevo."
        )


async def guardar_mensaje(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    grupos.add(chat_id)

    user = update.effective_user

    if not user:
        return

    nombre = nombre_usuario(user)

    # Mensajes de texto
    if update.message.text:

        texto = update.message.text

        mensajes[chat_id].append(
            f"{nombre}: {texto}"
        )

        # Desmadrita solamente responde cuando le hablan
        texto_minuscula = texto.lower()

        if (
            "@desmadritabot" in texto_minuscula
            or "desmadrita" in texto_minuscula
        ):
            respuesta = await conversar(
                texto,
                nombre
            )

            await update.message.reply_text(
                respuesta
            )

    # Por ahora guardamos los audios como aviso.
    # La transcripción gratuita la agregaremos después.
    elif update.message.voice:

        mensajes[chat_id].append(
            f"{nombre} 🎙️: [audio enviado]"
        )


async def resumen_grupo(
    chat_id,
    enviar=True,
    bot=None
):
    historial = mensajes.get(chat_id, [])

    if not historial:
        return

    # Últimos 100 mensajes
    ultimos = historial[-100:]

    texto = "\n".join(ultimos)

    try:

        instrucciones = (
            "Sos Desmadrita, la fisgona oficial del grupo "
            "Somos un Desmadre. "
            "Hacé un resumen divertido pero claro de la "
            "conversación. "
            "Mencioná a los participantes por su nombre "
            "cuando sea relevante. "
            "Señalá temas, bromas, discusiones, romances, "
            "chismes o momentos importantes. "
            "No inventes absolutamente nada. "
            "Si solamente hubo conversación normal, decilo "
            "de forma entretenida. "
            "Usá español rioplatense."
        )

        resultado = preguntar_ia(
            instrucciones,
            f"Mensajes del grupo:\n\n{texto}",
        )

        mensaje = (
            "📝💜 RESUMEN DEL DESMADRE\n\n"
            + resultado
        )

        if enviar and bot:
            await bot.send_message(
                chat_id=chat_id,
                text=mensaje
            )

        return mensaje

    except Exception as error:

        print("Error haciendo resumen:", error)

        if enviar and bot:
            await bot.send_message(
                chat_id=chat_id,
                text=(
                    "🤖💜 Se me cruzaron los cables "
                    "haciendo el resumen."
                )
            )


async def comando_resumen(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.effective_chat.id

    if not mensajes.get(chat_id):
        await update.message.reply_text(
            "🤖💜 Todavía no tengo nada para resumir."
        )
        return

    await resumen_grupo(
        chat_id,
        enviar=True,
        bot=context.bot
    )


async def resumen_automatico(
    application: Application
):
    while True:

        # Esperamos 5 horas
        await asyncio.sleep(5 * 60 * 60)

        print("📝 Generando resúmenes automáticos...")

        for chat_id in list(grupos):

            if mensajes.get(chat_id):

                await resumen_grupo(
                    chat_id,
                    enviar=True,
                    bot=application.bot
                )


def iniciar_resumen_automatico(
    application: Application
):
    application.create_task(
        resumen_automatico(application)
    )


def main():

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(iniciar_resumen_automatico)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("ayuda", ayuda)
    )

    app.add_handler(
        CommandHandler("resumen", comando_resumen)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.VOICE,
            guardar_mensaje
        )
    )

    print(
        "💜🤖 Desmadrita está funcionando..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
