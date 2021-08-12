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
token = input('Token: ')

vk = vk_api.VkApi(token=token)
longpoll = VkLongPoll(vk)


def write_msg(user_id, message):
    vk.method('messages.send', {'user_id': user_id, 'message': message,  'random_id': randrange(10 ** 7),})


for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:

        if event.to_me:
            request = event.text

            if request == "привет":
                write_msg(event.user_id, f"Хай, {event.user_id}")
            elif request == "пока":
                write_msg(event.user_id, "Пока((")
            else:
                write_msg(event.user_id, "Не поняла вашего ответа...")