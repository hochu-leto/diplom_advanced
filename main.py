from datetime import datetime
from operator import itemgetter
from pprint import pprint
from random import randrange
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

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
# token = input('Token: ')
find_sex = 0
delta_years = 3
token_file = 'token_vk'
with open(token_file) as gitignore:
    token = gitignore.readline().rstrip()
    TOKEN = gitignore.readline().rstrip()

# print(token)
vk = vk_api.VkApi(token=token)
user_vk = vk_api.VkApi(token=TOKEN)
longpoll = VkLongPoll(vk)
offset = 0

def write_msg(user_id, message, attach):
    vk.method('messages.send', {'user_id': user_id, 'message': message, 'attachment': attach, 'random_id': randrange(10 ** 7)})


for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        if event.to_me:
            request = event.text
            response = vk.method('users.get', {'user_id': event.user_id, 'fields': 'bdate, country, city, sex'})
            user_b_date = response[0]['bdate'].strip()
            user_b_date = datetime.strptime(user_b_date, '%d.%m.%Y').date()
            today = datetime.today()
            user_age = today.year - user_b_date.year - ((today.month, today.day) < (user_b_date.month, user_b_date.day))
            if user_age < 18:
                write_msg(event.user_id, 'Это бот знакомств для взрослых, подрасти маленько', '')
            find_age_from = user_age - delta_years
            if find_age_from < 18:
                find_age_from = 18
            user_country = response[0]['country']['id']
            user_city = response[0]['city']['id']
            user_sex = response[0]['sex']

            if user_sex == 1:
                find_sex = 2
            elif user_sex == 2:
                find_sex = 1
            else:
                write_msg(event.user_id, 'Да что ты такое??!\n Иди, с полом своим сначала определись', '')


            members = []

            while len(members) < 10:
                print(len(members))
                response = user_vk.method('users.search', {'q': ' ', 'count': 5, 'fields': 'bdate', 'has_photo': 1,
                                                           'status': 6, 'offset': offset,
                                                           'country': user_country, 'city': user_city, 'sex': find_sex,
                                                           'age_from': find_age_from, 'age_to': user_age + delta_years})

                for mem in response['items']:
                    offset += 1
                    print(mem['first_name'] + ' - ' + str(mem['is_closed']) + ' - ' + str(mem['id']) + ' - ' + mem['bdate'])
                    member = {}
                    if not mem['is_closed']:
                        photo_response = user_vk.method('photos.get', {'owner_id': mem['id'], 'count': 100, 'extended': 1,
                                                                       'album_id': 'wall', 'photo_sizes': 1})
                        search_photo = []
                        for photos in photo_response['items']:
                            add_photo = {}
                            likomments = (photos['likes']['count'] + 1) * (photos['comments']['count'] + 1)
                            for photos_sizes in photos['sizes']:
                                if photos_sizes['type'] == 'p':
                                    # pprint(photos)
                                    add_photo['url'] = photos_sizes['url']
                                    add_photo['likomments'] = likomments
                                    add_photo['photo_id'] = photos['id']
                                    break
                            if add_photo:
                                search_photo.append(add_photo)
                        search_photo.sort(key=itemgetter('likomments'), reverse=True)
                        if len(search_photo) > 2:
                            member['name'] = mem['first_name']
                            member_bdate = datetime.strptime(mem['bdate'], '%d.%m.%Y').date()
                            today = datetime.today()
                            member['age'] = today.year - member_bdate.year - (
                                        (today.month, today.day) < (member_bdate.month, member_bdate.day))
                            member['photos'] = search_photo[:3]
                            member['url'] = 'https://vk.com/id' + str(mem['id'])
                            member['mem_id'] = mem['id']
                            attach = ''
                            for photo in member['photos']:
                                attach += 'photo' + str(mem['id']) + '_' + str(photo['photo_id']) + ','
                            write_msg(event.user_id, mem['first_name'] + ' ' + str(member['age']) + ' лет\n'
                                      + member['url'], attach)
                            members.append(member)добавил