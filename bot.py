# -*- coding: utf-8 -*-
import os
import telebot
import time
import random
import threading
from emoji import emojize
from telebot import types
from pymongo import MongoClient
import traceback

token = os.environ['TELEGRAM_TOKEN']
bot = telebot.TeleBot(token)


client=MongoClient(os.environ['database'])
db=client.robofactory
users=db.users
games=db.games


def medit(message_text,chat_id, message_id,reply_markup=None,parse_mode=None):
    return bot.edit_message_text(chat_id=chat_id,message_id=message_id,text=message_text,reply_markup=reply_markup,
                                 parse_mode=parse_mode)   



@bot.message_handler(commands=['newgame'])
def newgame(m):
    game=games.find_one({'id':m.chat.id})
    if game==None:
        games.insert_one(creategame(m.chat.id))
        bot.send_message(m.chat.id, 'Набор участников открыт! Сражение начнётся через 1 час. /joingame для присоединения.')
    else:
        if m.text.lower()=='/newgame' or m.text.lower()=='/newgame@robofactorybot':
            bot.send_message(m.chat.id, 'Игра уже идёт!')


@bot.message_handler(commands=['joingame'])
def joingame(m):
    game=games.find_one({'id':m.chat.id})
    if game!=None:
        if str(m.from_user.id) not in game['players']:
            try:
                bot.send_message(m.chat.id, 'А теперь напишите мне ваше прозвище на время битвы (команда /setname).')
                games.update_one({'id':game['id']},{'$set':{'players.'+str(m.from_user.id):createplayer(m.from_user)}})
                bot.send_message(m.chat.id, m.from_user.first_name+' вступил(а) в битву! Ожидаем его(её) прозвища (команда /setname). Либо им станет имя игрока.')
            except:
                bot.send_message(441399484, traceback.format_exc())
            

@bot.message_handler(commands=['setname'])
def setname(m):
    x=m.text.split(' ')
    if len(x)>1:
        name=x[1]
        if len(name)<=50:
            game=games.find_one({'id':m.chat.id})
            if game!=None:
                if str(m.from_user.id) in game['players']:
                    if game['started']==False:
                        games.update_one({'id':m.chat.id},{'$set':{'players.'+str(m.from_user.id)+'.gamename':name}})
                        bot.send_message(game['id'], m.from_user.first_name+' теперь имеет прозвище "'+name+'"!')
                    else:
                        bot.send_message(m.chat.id, 'Игра уже идёт! Нельзя менять прозвище!')
    else:
        bot.send_message(m.chat.id, 'Используйте формат:\n/setname *имя*', parse_mode='markdown')
            
        
@bot.message_handler(commands=['act'])
def act(m):
    game=games.find_one({'id':m.chat.id})
    if game!=None:
        mainmenu(game, m.from_user.id)
    else:
        bot.send_message(m.chat.id, 'В этом чате нет запущенной игры.')
 


def mainmenu(game, id):
    kb=types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text='Просмотр строений', callback_data=str(game['id'])+' check_buildings'))
    try:
        bot.send_message(id, 'Главное меню.', reply_markup=kb)
    except:
        bot.send_message(game['id'], 'Сначала откройте со мной личку, '+game['players'][str(id)]['gamename']+'!')

                         
@bot.callback_query_handler(func=lambda call: True)
def call_handler(call):
    game=games.find_one({'id':call.data.split(' ')[0]})
    if game!=None:
        kb=types.InlineKeyboardMarkup()
        if call.from_user.id in game['players']:
            player=game['players'][call.from_user.id]
            if 'check_buildings' in call.data:
                for ids in player['buildings']:
                    b=player['buildings'][ids]
                    kb.add(types.InlineKeyboardButton(text=typetoname(b), callback_data=str(game['id']+' '+'check'+' '+b['code']))
        
  
def typetoname(b):
    x=''
    if b['resource']=='iron':
        x+='🔩'


    if b['type']=='farmer_building':
        x+='Добытчик ресурсов'
    return x
                       
                         
        
def createplayer(user):
    return {
        'id':user.id,
        'gamename':user.first_name,
        'resources':{},
        'robots':{},
        'builds':{},
        'destroyed':{}
    }
                
      
def createuser(user):
    return {
        'id':user.id,
        'name':user.first_name,
        'chat_bonuses':{}
    }
        

def creategame(id, x=1, waittime=60):  # x - сколько дней будет идти игра
    return {
        'id':id,
        'players':{},
        'started':False,
        'starttime':None,
        'duration':x*86400,
        'createtime':time.time(),
        'time_before_start'=waittime
    }


def objectid(game):
    i=0
    for ids in game['players']:
        for idss in game['players'][ids]['robots']:
            i+=1
        for idss in game['players'][ids]['builds']:
            i+=1
        for idss in game['players'][ids]['destroyed']:
            i+=1
    return i
            
        
    
def c_fabric(code, typee, power=1, farmspeed=15):
    return {
        'code':code,
        'resource':typee,
        'type':'farmer_building',
        'lastfarm':0,
        'power':power,
        'farmspeed':farmspeed   #каждые 15 секунд добывает ресурс
    }

def c_fighter_bot(code, hp=300, gamage=50, shootspeed=3):    # shootspeed - раз в сколько секунд стреляет бот
    return {
        'code':code,
        'type':'fighter_bot',
        'hp':hp,
        'damage':damage,
        'shootspeed':shootspeed
    }

def c_farm_bot(code, hp=100, farmspeed=10, power=1):    # farmspeed - раз в сколько секунд бот добывает ресурсы
    return {
        'code':code,
        'type':'farmer_bot',
        'hp':hp,
        'farmspeed':farmspeed,
        'power':power                                  # power - влияет на количество ресурсов
    }

def farm(player, id):
    ctime=time.time()
    for ids in player['buildings']:
        build=player['buildings'][ids]
        if ctime-build['lastfarm']>=build['farmspeed']:
            metal=0
            if build['resource']=='metal':
                metal+=int(build['power']*100)
            if metal>0:
                if 'metal' in player['resources']:
                    x='$inc'
                else:
                    x='$set'
                games.update_one({'id':id},{x:{'players.'+str(player['id'])+'.resources.metal':metal}})
            games.update_one({'id':id},{'$set':{'players.'+str(player['id'])+'.buildings.'+build['code']+'.lastfarm':ctime}})


def farmcheck():
    t=threading.Timer(1, farmcheck)
    t.start()
    ctime=time.time()
    for ids in games.find({}):
        for idss in ids['players']:
            farm(ids['players'][idss], ids['id'])
        
            
     
def timecheck():
    t=threading.Timer(60, timecheck)
    t.start()
    ctime=time.time()
    for ids in games.find({}):
        if ids['started']==False:
            if ctime-ids['createtime']>=ids['time_before_start']:
                games.update_one({'id':ids['id']},{'$set':{'started':True, 'starttime':ctime}})
                bot.send_message(ids['id'], 'Начинается сражение! Ваша цель - набрать к концу игры как можно больше баллов успеха. Вот таблица, '+
                                 'показывающая, как начисляются эти баллы к концу игры:\n(Таблица в разработке). Успехов! Чтобы перейти к '+
                                'управлению своей базой, нажмите /act.')
                botcode=objectid(ids)
                for idss in ids['players']:
                    games.update_one({'id':ids['id']},{'$set':{'players.'+idss['id']+'.robots.'+str(botcode):c_fighter_bot(botcode)}})
                    botcode+=1
                    games.update_one({'id':ids['id']},{'$set':{'players.'+idss['id']+'.builds.'+str(botcode):c_fabric(botcode, 'iron')}})
                    botcode+=1
                    games.update_one({'id':ids['id']},{'$set':{'players.'+idss['id']+'.robots.'+str(botcode):c_farm_bot(botcode)}})
                    botcode+=1
                    games.update_one({'id':ids['id']},{'$set':{'players.'+idss['id']+'.resources.iron':10000}})
                    botcode+=1
        else:
            pass
        
        


timecheck()
farmcheck()

print('7777')
bot.polling(none_stop=True,timeout=600)

