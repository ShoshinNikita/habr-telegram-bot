# -*- coding: utf-8 -*-

# Default libraries
import urllib.request
import time
import re
import json
from threading import Thread
from datetime import datetime

# Additional libraries
import telebot
import feedparser
from bs4 import BeautifulSoup

# Files of project
import config
from DataBase import DataBase
from Log import Log


bot = telebot.TeleBot(token=config.BOT_TOKEN)
logAdapter = Log()
dbAdapter = DataBase(main_log=logAdapter)


# Check
def parse_summary(summary):
	soup = BeautifulSoup(summary, "html.parser")
	new_summary = str(soup.text).replace("\n", " ")
	new_summary = re.findall(r"^.{1,400}\.", new_summary)[0]
	new_summary = re.sub("Читать дальше", "", new_summary)
	return new_summary
	

def send_articles():
	while True:
		logAdapter.event("Send articles")
		try:
			# Загрузка времени последней статьи
			file = open("last_article_info.json", "r+")
			last_article_info = json.loads(file.read())
			file.close()
			last_article_time = datetime.strptime(last_article_info["last_time"], "%Y-%m-%d %H:%M:%S")
			
			users = dbAdapter.get_all_users()
			
			articles_list = feedparser.parse(config.SITE_ADDRESS)["entries"]
			
			# Предотвращение ситуации, когда список статей пуст. Возникает из-за ошибки при парсинге
			if len(articles_list) > 0:
				for article in articles_list:
					article_time = datetime.strptime(article["published"], "%a, %d %b %Y %H:%M:%S %Z")
					# Проверка, новая ли статья
					if last_article_time >= article_time:
						break
					
					# Создание сообщения, которое будет отправлено
					message_text = "<b>" + article["title"] + "</b>" + "\n"
					message_text += parse_summary(article["summary"])
					message_text += " <a href='" + article["link"] + "'>Читать дальше</a>"
	
					article_tags = []
					for i in article["tags"]:
						tag = i["term"].lower()
						tag = tag.replace(" ", "_")
						article_tags.append(tag)
	
					# Отправка
					for user in users:
						common_tags = [i for i in users[user] if i in article_tags]
						if len(users[user]) == 0 or len(common_tags) != 0:
							try:
								bot.send_message(user, message_text, parse_mode="HTML")
							except Exception as e:
								logAdapter.error(str(e))
				
				# Сохранение времени поселдней опубликованой(!) статьи. Формируется из времени первой статьи в списке
				new_article_time = datetime.strptime(articles_list[0]["published"], "%a, %d %b %Y %H:%M:%S %Z")
				last_article_info["last_time"] = str(new_article_time)
				file = open("last_article_info.json", "w")
				file.write(json.dumps(last_article_info))
				file.close()
			else:
				logAdapter.error("Empty 'entries'")
				
		except Exception as e:
			logAdapter.error(str(e))

		# Проверка новых статей каждые config.COOLDOWN секунд
		time.sleep(config.COOLDOWN)


@bot.message_handler(commands=["start"])
def start(message):
	result = dbAdapter.add_user(message.chat.id)
	if result is None:
		bot.send_message(message.chat.id, config.ERROR_MESSAGE)
	else:
		bot.send_message(message.chat.id, "Привет, " + message.from_user.first_name + "\nВведи /help для справки.")


@bot.message_handler(commands=["stop"])
def stop(message):
	result = dbAdapter.turn_mailout_off(message.chat.id)
	if result is None:
		bot.send_message(message.chat.id, config.ERROR_MESSAGE)
	else:
		bot.send_message(message.chat.id, "Рассылка приостановлена.")


@bot.message_handler(commands=["help"])
def help(message):
	bot.send_message(message.chat.id, config.HELP_TEXT)


@bot.message_handler(commands=["my_tags"])
def show_tags(message):
	result = dbAdapter.get_tags(message.chat.id)
	if result is None:
		bot.send_message(message.chat.id, config.ERROR_MESSAGE)
	elif len(result) == 0:
		bot.send_message(message.chat.id, "Тегов нет")
	else:
		bot.send_message(message.chat.id, "Список тегов:\n" + "\n".join(result))


@bot.message_handler(commands=["add_tags"])
def add_new_tags(message):
	text = message.text[10:].lower()
	if len(text) == 0:
		bot.send_message(message.chat.id, "Ошибка: список тегов пуст")
	elif len(text) >= 300:
		bot.send_message(message.chat.id, "Ошибка: список тегов слишком большой. Добавляйте теги постепенно.")
	else:
		result = dbAdapter.add_tags(message.chat.id, text)
		
		if result is None:
			bot.send_message(message.chat.id, config.ERROR_MESSAGE)
		else:
			bot.send_message(message.chat.id, "Теги добавлены. Обновленный список тегов:\n" + "\n".join(result))


@bot.message_handler(commands=["copy_tags"])
def copy_tags(message):
	user_url = message.text[11:]
	habr_regex = "https://habrahabr.ru/users/[\w\s_]+/"

	if user_url == "" or not re.match(habr_regex, user_url):
		bot.send_message(message.chat.id, "Ошибка: нужна ссылка на профиль")
	else:
		regex = 'profile-section__user-hub[\w\sА-Яа-я<>+*.-=&?^%$#@!\\"]+</a>'
		try:
			user_profile_site = urllib.request.urlopen(user_url, timeout=5).read().decode("utf-8")
		except Exception as e:
			logAdapter.error(str(e))
			bot.send_message(message.chat.id, config.ERROR_MESSAGE)
		else:
			row_tags = re.findall(regex, user_profile_site)
			tags = []
			for i in row_tags:
				i = i[:-4]
				i = i[28:]
				i = i.replace(" ", "_")
				tags.append(i.lower())
			
			result = dbAdapter.refresh_tags(message.chat.id, tags)
			if result is None:
				bot.send_message(message.chat.id, config.ERROR_MESSAGE)
			elif len(result) == 0:
				bot.send_message(message.chat.id, "Обновленный список тегов: пусто")
			else:
				bot.send_message(message.chat.id, "Обновленный список тегов:\n" + "\n".join(result))


@bot.message_handler(commands=["del_tags"])
def delete_tags(message):
	text = message.text[10:].lower()
	
	if len(text) == 0:
		bot.send_message(message.chat.id, "Ошибка: список тегов пуст")
	else:
		result = dbAdapter.del_tags(message.chat.id, text)
		
		if result is None:
			bot.send_message(message.chat.id, config.ERROR_MESSAGE)
		elif len(result) != 0:
			bot.send_message(message.chat.id, "Теги удалены. Обновленный список тегов:\n" + "\n".join(result))
		else:
			bot.send_message(message.chat.id, "Тегов нет")


@bot.message_handler(commands=["del_all_tags"])
def delete_all_tags(message):
	result = dbAdapter.del_all_tags(message.chat.id)
	if result is None:
		bot.send_message(message.chat.id, config.ERROR_MESSAGE)
	else:
		bot.send_message(message.chat.id, "Список тегов пуст")


send_articles_thread = Thread(target=send_articles)
send_articles_thread.start()


# Start bot
while True:
	try:
		logAdapter.event("Launch bot")
		bot.threaded = False
		bot.skip_pending = True
		bot.polling()
	except Exception as e:
		logAdapter.error(str(e))
		bot.stop_polling()
