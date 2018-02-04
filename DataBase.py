# -*- coding: utf-8 -*-
import sqlite3
import config


class DataBase:
	"""
	Класс взаимодействия с базой данных
	Create statement:
	CREATE TABLE "users" (
		`id` INTEGER,
		`tags` TEXT DEFAULT "",
		`is_stop` INTEGER DEFAULT 0,
		PRIMARY KEY(`id`) )
	"""
	
	def __init__(self, main_log):
		"""
		:param main_log: экземпляр класса Log
		"""
		self.connection = sqlite3.connect(config.DB_NAME, check_same_thread=False)
		self.cursor = self.connection.cursor()
		self.log = main_log
	
	def add_user(self, id):
		"""
		Добавляет пользователя. Если пользователь существует, то вкючает рассылку
		:param id: id пользователя
		:return: True, если рассылка была отключена, иначе - None
		"""
		try:
			self.cursor.execute("""INSERT OR IGNORE
								INTO users (id, tags)
								VALUES (:id, :empty)""", {"id": id, "empty": ""},)
			self.cursor.execute("UPDATE users SET is_stop=0 WHERE id=:id", {"id": id})
			self.connection.commit()
			return True
		except Exception as e:
			self.log.error(str(e))
			return None
	
	def add_tags(self, id, message):
		"""
		Добавляет теги
		:param id: id пользователя
		:param message: список тегов в виде текста
		:return: list, содержащий обновлённый список тегов, в случае ошибки - None
		"""
		try:
			self.cursor.execute("SELECT tags FROM users WHERE id=:id", {"id": id})
			old_tags = self.cursor.fetchall()[0][0]
			old_tags = set(old_tags.split())
			
			old_tags.update(set(message.split()))
			
			self.cursor.execute("UPDATE users SET tags=:newTags WHERE id=:id",
								{"newTags": " ".join(list(old_tags)), "id": id})
			self.connection.commit()
			
			return list(old_tags)
		except Exception as e:
			self.log.error(str(e))
			return None
	
	def del_tags(self, id, message):
		"""
		Удаляет теги
		:param id: id пользователя
		:param message: список тегов в виде текста
		:return: list, содержащий обновлённый список тегов, в случае ошибки - None
		"""
		try:
			self.cursor.execute("SELECT tags FROM users WHERE id=:id", {"id": id})
			old_tags = self.cursor.fetchall()[0][0]
			old_tags = set(old_tags.split())

			old_tags.difference_update(set(message.split()))
		
			self.cursor.execute("UPDATE users SET tags=:new_tags WHERE id=:id",
								{"new_tags": " ".join(list(old_tags)), "id": id})
			self.connection.commit()
			
			return list(old_tags)
		except Exception as e:
			self.log.error(str(e))
			return None
		
	def get_tags(self, id):
		"""
		Возвращет теги пользователя
		:param id: id пользователя
		:return: list, содержащий список тегов, в случае ошибки - None
		"""
		try:
			self.cursor.execute("SELECT tags FROM users WHERE id=:id", {"id": id})
			tags = self.cursor.fetchall()[0][0]
			tags = list(tags.split())
			
			return tags
		except Exception as e:
			self.log.error(str(e))
			return None
	
	def get_all_users(self):
		"""
		:return: dict вида {"id": ["tag"]},в случае ошибки - None
		"""
		try:
			self.cursor.execute("SELECT id, tags FROM users WHERE is_stop=0")
			data = self.cursor.fetchall()
			users = {}
			for i in data:
				users[i[0]] = i[1].split()
			return users
		except Exception as e:
			self.log.error(str(e))
			return None
		
	def del_all_tags(self, id):
		"""
		Удаляет ВСЕ теги
		:param id: id пользователя
		:return: в случае ошибки - None, иначе - True
		"""
		try:
			self.cursor.execute("UPDATE users SET tags='' WHERE id=:id", {"id": id})
			self.connection.commit()
			return True
		except Exception as e:
			self.log.error(str(e))
			return None
	
	def refresh_tags(self, id, tags):
		"""
		Обновляет теги. Старые при этом стираются
		:param id: id пользователя
		:param tags: list, содержащий теги
		:return: list, содержащий список тегов, в случае ошибки - None
		"""
		try:
			self.cursor.execute("UPDATE users SET tags=:new_tags WHERE id=:id",
								{"new_tags": " ".join(tags), "id": id})
			self.connection.commit()
			return tags
		except Exception as e:
			self.log.error(str(e))
			return None
		
	def turn_mailout_off(self, id):
		"""
		Выключает рассылку
		:param id: id пользователя
		:return: возвращает True, если рассылка была отключена, иначе - None
		"""
		try:
			self.cursor.execute("UPDATE users SET is_stop=1 WHERE id=:id", {"id": id})
			self.connection.commit()
			return True
		except Exception as e:
			self.log.error(str(e))
			return None
