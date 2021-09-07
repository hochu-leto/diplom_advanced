import sqlite3
from datetime import datetime
from operator import itemgetter
from pprint import pprint
from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

conn = sqlite3.connect("users.db")  # или :memory: чтобы сохранить в RAM
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users
                  (user_id int, member_id int)
               """)
#
cursor.execute("""CREATE TABLE IF NOT EXISTS user
                  ( id int PRIMARY KEY, user_id int, city_id int, 
                    city_title text,sex int, 
                   age_from int, age_to int,
                   count_mem int, offset int)
               """)

'''
Входные данные
-Имя пользователя или его id в ВК, для которого мы ищем пару.
если информации недостаточно нужно дополнительно спросить её у пользователя.

Бот должен искать людей, подходящих под условия, на основании информации о пользователе из VK:
-возраст,(видимо +- 5 от возраста пользователя)
-пол,(противоположный)
-город,(тот же, что и у пользователя)
-семейное положение.(женатиков не предлагать)
У тех людей, которые подошли по требованиям пользователю, 
получать топ-3 популярных фотографии профиля и отправлять их пользователю в чат 
вместе со ссылкой на найденного человека.
Популярность определяется по количеству лайков и комментариев.
'''
question_dict = {
    'от': 'С какого возраста ищем партнёров? Младше 18 лет искать не будем.',
    'до': 'До какого возраста ищем партнёров? Старше 100 лет искать не будем.',
    'город': 'Из какого города нужно найти партнёра? Напиши правильное название города',
    'анкеты': 'Сколько анкет за раз хочешь получать? Число от 1 до 15',
    'пол': 'Выбери пол партнёра - отправь букву "м" или "ж"'
}
user_id = 0
delta_years = 3
token_file = 'token_vk'
with open(token_file) as gitignore:
    token = gitignore.readline().rstrip()
    TOKEN = gitignore.readline().rstrip()

vk = vk_api.VkApi(token=token)
user_vk = vk_api.VkApi(token=TOKEN)


class User:
    sex_text = {2: 'мальчиков',
                1: 'девочек',
                0: 'всех подряд'}

    def __init__(self, user_id):
        self.id = user_id
        response = response_user(self.id)
        self.name = response['first_name']
        self.age = b_date_to_age(response['bdate'].strip())
        if 'country' in response:
            self.country = response['country']['id']
        else:
            self.country = ''
        if not self.check_self_in_db():
            if 'city' in response:
                self.city = response['city']['id']
                self.city_title = response['city']['title']
            else:
                self.city = 0
                self.city_title = ''

            self.sex = response['sex']
            self.find_age_from = self.age - delta_years
            if self.find_age_from < 18:
                self.find_age_from = 18
            self.find_age_to = self.age + delta_years
            self.count_mem = 3
            params = (
                self.id, self.city, self.city_title, self.sex,
                self.find_age_from, self.find_age_to, self.count_mem, 0)
            cursor.execute("INSERT INTO user VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)", params)
            conn.commit()
            write_msg(event.user_id,
                      f'Привет, {self.name}\n Будем искать для тебя {self.sex_text[self.find_sex()]} от {self.find_age_from} '
                      f'до {self.find_age_to} лет\n из города {self.city_title}. Показываю по {self.count_mem} анкеты за раз\n '
                      f'Если хочешь изменить какой-то параметр поиска,\n напиши ключевое слово'
                      f' "пол", "город", "от", "до" или "анкеты"\n Если всё ОК, напиши любое слово кроме ключевого',
                      '')
        else:
            self.sex = self.req('sex')
            self.city = self.req('city_id')
            self.city_title = self.req('city_title')
            self.find_age_to = self.req('age_to')
            self.find_age_from = self.req('age_from')
            self.count_mem = self.req('count_mem')

        sql = f"SELECT member_id FROM users WHERE user_id={self.id}"
        cursor.execute(sql)
        self.last_mem = [row[0] for row in cursor.fetchall()]

    def check_self_in_db(self):
        sql = "SELECT DISTINCT user_id FROM users"
        cursor.execute(sql)
        user_list = [row[0] for row in cursor.fetchall()]
        if self.id not in user_list:
            cursor.execute(f"""INSERT INTO users VALUES ({self.id}, {0})""")
            conn.commit()
            return False
        return True

    def find_sex(self):
        if self.sex == 1:
            find_sex = 2
        elif self.sex == 2:
            find_sex = 1
        else:
            write_msg(self.id, 'Да что ты такое??!\n Иди, с полом своим сначала определись', '')
            find_sex = 0
        return find_sex

    def offset(self):
        params = (
            self.id, self.city, self.sex,
            self.find_age_from, self.find_age_to)
        sql = """SELECT offset FROM user WHERE 'user_id'=? AND 'city_id'=? 
                        AND 'sex'=? AND 'age_from'=? AND 'age_to'=? ORDER BY id DESC LIMIT 1"""
        cursor.execute(sql, params)
        offs = cursor.fetchone()

        if offs:
            return offs[0]
        else:
            return 0

    def req(self, val: str):
        sql = f"SELECT {val} FROM user WHERE {self.id} ORDER BY id DESC LIMIT 1"     #
        cursor.execute(sql)
        ret = cursor.fetchone()
        if ret:
            return ret[0]
        else:
            return 0


def response_user(id):
    return user_vk.method('users.get',
                          {'user_id': id, 'fields': 'bdate, country, city, sex'})[0]


def b_date_to_age(b_date: str):
    b_date = datetime.strptime(b_date, '%d.%m.%Y').date()
    today = datetime.today()
    age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))
    return age


def photo_response(user_id):
    return user_vk.method('photos.get',
                          {'owner_id': user_id, 'count': 100, 'extended': 1,
                           'album_id': 'profile', 'photo_sizes': 1})['items']


class MemberVk:

    def __init__(self, mem_id):
        self.id = mem_id
        response = response_user(self.id)
        self.is_closed = response['is_closed']
        self.url = 'https://vk.com/id' + str(self.id)
        self.name = response['first_name']
        self.age = b_date_to_age(response['bdate'].strip())
        if 'city' in response:
            self.city = response['city']['id']
            self.city_title = response['city']['title']
        else:
            self.city = 0
            self.city_title = ''

    def check_mem(self, list_mem: list, city: int):
        if not self.is_closed and (self.id not in list_mem) and self.city and (self.city == city):
            return True
        else:
            return False

    def search_photo(self):
        search_photo = []
        for photos in photo_response(self.id):
            add_photo = {}
            likomments = (photos['likes']['count'] + photos['comments']['count'])
            add_photo['likomments'] = likomments
            add_photo['photo_id'] = photos['id']
            search_photo.append(add_photo)

        search_photo.sort(key=itemgetter('likomments'), reverse=True)
        return search_photo


def check_answer(ans_for: str, answer: str, user: User):
    if not ans_for:
        return True
    else:
        if ans_for == 'от':
            if answer.isdigit() and 17 < int(answer) < 100:
                user.find_age_from = int(answer)
                if user.find_age_to < user.find_age_from:
                    user.find_age_to = user.find_age_from
                return True
        elif ans_for == 'до':
            if answer.isdigit() and 17 < int(answer) < 100:
                user.find_age_to = int(answer)
                if user.find_age_to < user.find_age_from:
                    user.find_age_from = user.find_age_to
                return True
        elif ans_for == 'пол':
            if answer == 'м':
                user.sex = 1
                return True
            if answer == 'ж':
                user.sex = 2
                return True
        elif ans_for == 'анкеты':
            if answer.isdigit() and 0 < int(answer) < 14:
                user.count_mem = int(answer)
                return True
        elif ans_for == 'город':
            user.city_title = answer
            response = user_vk.method('database.getCities',
                                      {'q': answer, 'count': 1, 'country_id': 1})
            if response['items']:
                user.city = response['items'][0]['id']
            return True

    write_msg(user.id, question_dict[ans_for], '')
    return False


long_poll = VkLongPoll(vk)


def write_msg(user_id, message, attach):
    vk.method('messages.send',
              {'user_id': user_id, 'message': message, 'attachment': attach, 'random_id': randrange(10 ** 7)})


answer_for = ''
for event in long_poll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:
            user = User(event.user_id)
            request = event.text.lower().strip()

            if check_answer(answer_for, request, user):
                if request in question_dict.keys():
                    write_msg(user.id, question_dict[request], '')
                    answer_for = request
                else:
                    members = 0
                    offset = user.offset()
                    print(' offset =  ' + str(offset))
                    answer_for = ''
                    while members < user.count_mem:
                        response = user_vk.method('users.search',
                                                  {'q': ' ', 'count': 1, 'fields': 'bdate, country, city, sex',
                                                   'has_photo': 1, 'status': 6, 'offset': offset,
                                                   'country': user.country,
                                                   'city': user.city, 'sex': user.find_sex(),
                                                   'age_from': user.find_age_from, 'age_to': user.find_age_to})
                        response = response['items']
                        pprint(response)
                        if response:
                            mem = MemberVk(response[0]['id'])
                            offset += 1
                            if mem.check_mem(user.last_mem, user.city):
                                s_photo = mem.search_photo()
                                if len(s_photo) > 2:
                                    attach = ''
                                    for photo in s_photo[:3]:
                                        attach += 'photo' + str(mem.id) + '_' + str(photo['photo_id']) + ','
                                    write_msg(user.id, mem.name + ' ' + str(mem.age) + ' лет\n'
                                              + mem.url, attach)
                                    cursor.execute(f"""INSERT INTO users
                                                      VALUES ({user.id}, {mem.id})"""
                                                   )
                                    conn.commit()
                                    members += 1

                        else:
                            write_msg(user.id, 'Подходящих кандидатур нет, проверь свои данные', '')
                            break
                    params = (user.id,
                              user.city, user.city_title, user.sex,
                              user.find_age_from, user.find_age_to,
                              user.count_mem, offset)
                    sql_update_query = """INSERT INTO user VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)"""
                    cursor.execute(sql_update_query, params)
                    conn.commit()
                    write_msg(event.user_id,
                              f'Напоминаю. Ищем {user.sex_text[user.find_sex()]} от {user.find_age_from} '
                              f'до {user.find_age_to} лет\n из города {user.city_title}. Показываю по {user.count_mem}'
                              f' анкеты за раз\n '
                              f'Если хочешь изменить какой-то параметр поиска,\n напиши ключевое слово'
                              f' "пол", "город", "от", "до" или "анкеты"\n Если продолжаем с этими же '
                              f'параметрами, напиши любое слово кроме ключевого',
                              '')
