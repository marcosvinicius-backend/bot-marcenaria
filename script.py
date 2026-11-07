import os
import sqlite3
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
ID_ADMINISTRADOR = int(os.getenv("ID_ADMIN", 0))

TEXTOS_FUNIL = {
    "boas_vindas": "Olá! Bem-vindo à Marcenaria. Qual ambiente você deseja planejar?",
    "pergunta_arquiteto": "Você já possui um projeto pronto feito por Arquiteto?",
    "pergunta_investimento": "Qual é a faixa estimada de investimento planejada?",
    "pergunta_visita": "Gostaria de marcar uma visita técnica para medição?",
    "agradecimento_cliente": "Perfeito! Muito obrigado pelas informações. Um de nossos consultores de projetos já recebeu os seus dados e entrará em contato para desenharmos o seu ambiente dos sonhos! 📐✨"
}

bot = telebot.TeleBot(TOKEN)

def inicializar_banco():
    conexao = sqlite3.connect("marcenaria_leads.db")
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, nome TEXT, telefone TEXT, 
            ambiente TEXT, projeto TEXT, investimento TEXT, visita TEXT, score INTEGER, 
            temperatura TEXT, data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estados (
            chat_id TEXT PRIMARY KEY, etapa TEXT, ambiente TEXT, projeto TEXT, investimento TEXT, visita TEXT
        )
    """)
    conexao.commit()
    conexao.close()

inicializar_banco()

def atualizar_estado(chat_id, campo, valor):
    conexao = sqlite3.connect("marcenaria_leads.db")
    cursor = conexao.cursor()
    cursor.execute("INSERT OR IGNORE INTO estados (chat_id, etapa) VALUES (?, 'AMBIENTE')", (str(chat_id),))
    cursor.execute(f"UPDATE estados SET {campo} = ? WHERE chat_id = ?", (valor, str(chat_id)))
    conexao.commit()
    conexao.close()

def obtener_estado(chat_id):
    conexao = sqlite3.connect("marcenaria_leads.db")
    cursor = conexao.cursor()
    cursor.execute("SELECT etapa, ambiente, projeto, investimento, visita FROM estados WHERE chat_id = ?", (str(chat_id),))
    resultado = cursor.fetchone()
    conexao.close()
    if resultado:
        return {
            "etapa": resultado[0], "ambiente": resultado[1], "projeto": resultado[2],
            "investimento": resultado[3], "visita": resultado[4]
        }
    return None

@bot.message_handler(commands=["meuid"])
def obter_meu_id(message):
    bot.reply_to(message, f"Seu ID administrativo é: {message.chat.id}")

@bot.message_handler(commands=["start"])
def boas_vindas(message):
    chat_id = message.chat.id
    conexao = sqlite3.connect("marcenaria_leads.db")
    cursor = conexao.cursor()
    cursor.execute("INSERT OR REPLACE INTO estados (chat_id, etapa) VALUES (?, 'AMBIENTE')", (str(chat_id),))
    conexao.commit()
    conexao.close()

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Cozinha Planejada", callback_data="amb_cozinha"),
        types.InlineKeyboardButton("Quarto / Closet", callback_data="amb_quarto"),
        types.InlineKeyboardButton("Painel / Sala", callback_data="amb_sala"),
        types.InlineKeyboardButton("Banheiro / Lavabo", callback_data="amb_banheiro"),
        types.InlineKeyboardButton("Área Gourmet", callback_data="amb_gourmet"),
        types.InlineKeyboardButton("Home Office", callback_data="amb_office"),
        types.InlineKeyboardButton("Casa Completa", callback_data="amb_casa_toda"),
        types.InlineKeyboardButton("Outros", callback_data="amb_outros")
    )
    bot.send_message(chat_id, TEXTOS_FUNIL["boas_vindas"], reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def processar_botoes(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    data = call.data
    estado = obtener_estado(chat_id)
    if not estado: return

    if data.startswith("amb_"):
        atualizar_estado(chat_id, "ambiente", data.replace("amb_", ""))
        conexao = sqlite3.connect("marcenaria_leads.db")
        conexao.execute("UPDATE estados SET etapa = 'PROJETO' WHERE chat_id = ?", (str(chat_id),))
        conexao.commit()
        conexao.close()

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Sim, já tenho projeto", callback_data="proj_sim"),
                   types.InlineKeyboardButton("Não, preciso de desenho", callback_data="proj_nao"))
        bot.send_message(chat_id, TEXTOS_FUNIL["pergunta_arquiteto"], reply_markup=markup)

    elif data.startswith("proj_"):
        atualizar_estado(chat_id, "projeto", "Sim" if "sim" in data else "Não")
        conexao = sqlite3.connect("marcenaria_leads.db")
        conexao.execute("UPDATE estados SET etapa = 'INVESTIMENTO' WHERE chat_id = ?", (str(chat_id),))
        conexao.commit()
        conexao.close()

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Até R$ 15.000", callback_data="inv_15k"),
                   types.InlineKeyboardButton("De R$ 15.000 a R$ 35.000", callback_data="inv_35k"),
                   types.InlineKeyboardButton("Acima de R$ 35.000", callback_data="inv_alto"))
        bot.send_message(chat_id, TEXTOS_FUNIL["pergunta_investimento"], reply_markup=markup)

    elif data.startswith("inv_"):
        valor_inv = "Até 15k" if "15k" in data else "15k a 35k" if "35k" in data else "Acima de 35k"
        atualizar_estado(chat_id, "investimento", valor_inv)
        conexao = sqlite3.connect("marcenaria_leads.db")
        conexao.execute("UPDATE estados SET etapa = 'VISITA' WHERE chat_id = ?", (str(chat_id),))
        conexao.commit()
        conexao.close()

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Sim, agendar medição", callback_data="vis_sim"),
                   types.InlineKeyboardButton("Não, apenas orçamento", callback_data="vis_nao"))
        bot.send_message(chat_id, TEXTOS_FUNIL["pergunta_visita"], reply_markup=markup)

    elif data.startswith("vis_"):
        atualizar_estado(chat_id, "visita", "Sim" if "sim" in data else "Não")
        conexao = sqlite3.connect("marcenaria_leads.db")
        conexao.execute("UPDATE estados SET etapa = 'COLETA_NOME' WHERE chat_id = ?", (str(chat_id),))
        conexao.commit()
        conexao.close()
        bot.send_message(chat_id, "Para finalizar, digite o seu **Nome Completo**:")


@bot.message_handler(func=lambda message: True)
def processar_textos(message):
    chat_id = message.chat.id
    if message.text.startswith("/"): return

    estado = obtener_estado(chat_id)
    if not estado or estado["etapa"] != "COLETA_NOME":
        bot.send_message(chat_id, "⚠️ Por favor, utilize apenas as opções nos botões acima para responder.")
        return

    nome_cliente = message.text
    score = 0
    if estado["projeto"] == "Sim": score += 30
    if estado["visita"] == "Sim": score += 40
    if estado["investimento"] == "15k a 35k":
        score += 20
    elif estado["investimento"] == "Acima de 35k":
        score += 30

    temperatura = "QUENTE" if score >= 70 else "MORNO" if score >= 40 else "FRIO"

    conexao = sqlite3.connect("marcenaria_leads.db")
    cursor = conexao.cursor()
    cursor.execute("""
                   INSERT INTO leads (chat_id, nome, telefone, ambiente, projeto, investimento, visita, score,
                                      temperatura)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """, (str(chat_id), nome_cliente, "Não solicitado", estado["ambiente"], estado["projeto"],
                         estado["investimento"], estado["visita"], score, temperatura))
    cursor.execute("DELETE FROM estados WHERE chat_id = ?", (str(chat_id),))
    conexao.commit()
    conexao.close()

    bot.send_message(chat_id, TEXTOS_FUNIL["agradecimento_cliente"])

    if ID_ADMINISTRADOR != 0:
        ficha = (
            f"🎯 **NOVO LEAD CADASTRADO** 🎯\n\n"
            f"👤 **Nome:** {nome_cliente}\n"
            f"🛋️ **Ambiente:** {estado['ambiente']}\n"
            f"📐 **Projeto Pronto:** {estado['projeto']}\n"
            f"💰 **Investimento:** {estado['investimento']}\n"
            f"🚗 **Visita Técnica:** {estado['visita']}\n\n"
            f"📊 **Score:** {score} pontos\n"
            f"🔥 **Classificação:** {temperatura}"
        )
        try:
            bot.send_message(ID_ADMINISTRADOR, ficha, parse_mode="Markdown")
        except Exception as e:
            print(f"Erro ao notificar admin: {e}")


print("Bot Marcenaria Atualizado e Pronto...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
