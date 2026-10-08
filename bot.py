import os
import tempfile
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Guardamos los mensajes recibidos por cada grupo
mensajes = defaultdict(list)


def nombre_usuario(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name or "Usuario"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜🤖 ¡Hola! Soy Desmadrita, la integrante virtual "
        "de Somos un Desmadre.\n\n"
        "📝 Puedo resumir lo que pasa en el grupo.\n"
        "🎙️ Puedo convertir audios en texto.\n"
        "💬 Y si me hablan, también converso. 😏🔥"
    )


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💜🤖 DESMADRAITA\n\n"
        "📝 /resumen — Resumo lo que pasó.\n"
        "💬 Mencioname para hablar conmigo.\n"
        "🎙️ Mandame un audio y lo paso a texto."
    )


async def guardar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    nombre = nombre_usuario(user)

    if update.message.text:
        texto = update.message.text

        mensajes[chat_id].append(
            f"{nombre}: {texto}"
        )

        # Desmadrita solo responde cuando le hablan
        if (
            "@desmadritabot" in texto.lower()
            or "desmadrita" in texto.lower()
        ):
            respuesta = await conversar(texto, nombre)
            await update.message.reply_text(respuesta)

    elif update.message.voice:
        await procesar_audio(update, chat_id, nombre)


async def procesar_audio(update: Update, chat_id, nombre):
    try:
        archivo_telegram = await update.message.voice.get_file()

        with tempfile.NamedTemporaryFile(
            suffix=".ogg", delete=False
        ) as archivo:
            ruta = archivo.name

        await archivo_telegram.download_to_drive(ruta)

        with open(ruta, "rb") as audio:
            transcripcion = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio
            )

        texto = transcripcion.text

        mensajes[chat_id].append(
            f"{nombre} 🎙️: {texto}"
        )

        await update.message.reply_text(
            f"🎙️ {nombre} dijo:\n{texto}"
        )

        os.remove(ruta)

    except Exception as e:
        print("Error procesando audio:", e)


async def conversar(texto, nombre):
    try:
        respuesta = client.responses.create(
            model="gpt-5-mini",
            instructions=(
                "Sos Desmadrita, una integrante virtual femenina "
                "del grupo de Telegram Somos un Desmadre. "
                "Sos divertida, fisgona, simpática y con un poquito "
                "de picante. Hablás en español rioplatense de forma "
                "natural. No seas pesada ni respondas como un robot. "
                "Contestá de forma breve y entretenida."
            ),
            input=f"{nombre} te dijo: {texto}"
        )

        return respuesta.output_text

    except Exception as e:
        print("Error conversando:", e)
        return "😏💜 Uy, me quedé pensando... probá de nuevo."


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    historial = mensajes.get(chat_id, [])

    if not historial:
        await update.message.reply_text(
            "🤖💜 Todavía no tengo nada para resumir."
        )
        return

    ultimos = historial[-100:]

    texto = "\n".join(ultimos)

    try:
        respuesta = client.responses.create(
            model="gpt-5-mini",
            instructions=(
                "Sos Desmadrita, la fisgona oficial de un grupo "
                "llamado Somos un Desmadre. "
                "Hacé un resumen divertido pero claro de la "
                "conversación. Mencioná a los participantes por "
                "su nombre cuando sea relevante. Señalá temas, "
                "chismes, discusiones, bromas, romances o momentos "
                "importantes. No inventes nada que no aparezca "
                "en los mensajes."
            ),
            input=f"Estos son los mensajes del grupo:\n\n{texto}"
        )

        await update.message.reply_text(
            "📝💜 RESUMEN DEL DESMADRE\n\n"
            + respuesta.output_text
        )

    except Exception as e:
        print("Error haciendo resumen:", e)
        await update.message.reply_text(
            "🤖💜 Se me cruzaron los cables. Intentá de nuevo."
        )


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("Falta TELEGRAM_BOT_TOKEN")

    if not OPENAI_API_KEY:
        raise ValueError("Falta OPENAI_API_KEY")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ayuda", ayuda))
    app.add_handler(CommandHandler("resumen", resumen))

    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.VOICE,
            guardar_mensaje
        )
    )

    print("💜🤖 Desmadrita está funcionando...")
    app.run_polling()


if __name__ == "__main__":
    main()
