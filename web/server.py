import os
from aiohttp import web
import aiohttp
import hashlib
from urllib.parse import urlencode, urlunsplit
import dateutil.parser

MARVEL_API_ENDPO123INT = os.getenv('MARVEL_API_ENDPOINT', 'gateway.marvel.com')
PUBLIC_API_KEY = os.getenv('PUBLIC_API_KEY')
PRIVATE_API_KEY = os.getenv('PRIVATE_API_KEY')

# HARDCODED
LIMIT = 12

'''
Эти захардкоженные значения которые определяют интерпретацию поставленной задачи. В частности наиболее недавними
комиксами мы считаем те которые недавно поступили в продажу. Наиболее недавними событиями которые недавно начались,
а наиболее недавними авторами тех у кого информация была обновлена недавно.
'''

COMIC_FORMAT = 'comic'
COMIC_ORDER_BY = '-onsaleDate'
EVENTS_ORDER_BY = '-startDate'
CREATORS_ORDER_BY = '-modified'

UNSPLIT_TEMPLATE = [
    'https',
    'gateway.marvel.com',
    '/v1/public/characters',
    None,
    '']

METHOD_TEMPLATE = '/v1/public/{}'


def calc_hash(ts):
    string_to_hash = str(ts) + PRIVATE_API_KEY + PUBLIC_API_KEY
    return hashlib.md5(string_to_hash.encode('utf-8')).hexdigest()


async def fetch_method(session, method, parameters_update, ts):
    parameters = {"apikey": PUBLIC_API_KEY,
                  'ts': ts,
                  'hash': calc_hash(ts),
                  }

    parameters.update(parameters_update)

    parameters_url = urlencode(parameters)

    unsplit = UNSPLIT_TEMPLATE.copy()

    unsplit[2] = METHOD_TEMPLATE.format(method)
    unsplit[3] = parameters_url

    url = urlunsplit(unsplit)

    async with session.get(url) as response:
        return await response.json()


def ok(response_dict, count=0):
    return response_dict['code'] == 200 and response_dict['status'] == 'Ok' and response_dict['data']['count'] >= count


def comma_join(int_iter):
    return ','.join(str(i) for i in int_iter)


def extract_ids(response_dict):
    return [result['id'] for result in response_dict['data']['results']]


def creator_modified(creator):
    return dateutil.parser.parse(creator['modified'])


async def fetch_all(session, name, ts):
    hero_info = await fetch_method(session, 'characters', {'name': name}, ts)

    if not ok(hero_info, count=1):
        return

    hero_id = hero_info['data']['results'][0]['id']

    comics_info = await fetch_method(session, 'characters/{}/comics'.format(hero_id),
                                     {'format': COMIC_FORMAT, 'orderBy': COMIC_ORDER_BY, 'limit': LIMIT}, ts)
    events_info = await fetch_method(session, 'characters/{}/events'.format(hero_id),
                                     {'orderBy': EVENTS_ORDER_BY, 'limit': LIMIT}, ts)

    comics_ids = comma_join(extract_ids(comics_info))
    events_ids = comma_join(extract_ids(events_info))

    #TODO Hardcode limit for comics and events as Marvel API doesn't accept more than 10 in such request

    comic_creators_info = await fetch_method(session, 'creators',
                                             {'events': comics_ids[:10], 'orderBy': CREATORS_ORDER_BY, 'limit': LIMIT}, ts)
    events_creators_info = await fetch_method(session, 'creators',
                                              {'events': events_ids[:10], 'orderBy': CREATORS_ORDER_BY, 'limit': LIMIT}, ts)

    creators = sorted(comic_creators_info['data']['results'] + events_creators_info['data']['results'],
                      key=creator_modified)

    return {
        "copyright": hero_info['copyright'],
        "attributionText": hero_info["attributionText"],
        "attributionHTML": hero_info["attributionHTML"],
        'comics': comics_info['data'],
        'events': events_info['data'],
        'creators': {
            "offset": 0,
            "limit": 12,
            "total": len(creators[:12]),
            "count": len(creators[:12]),
            "results": creators
        }

    }


async def fetch_hero(name, ts):
    async with aiohttp.ClientSession() as session:
        hero_info = await fetch_all(session, name, ts)
        return hero_info


async def handle(request):
    ts = round(request.loop.time())

    name = request.match_info.get('name', "Anonymous")
    data = await fetch_hero(name, ts)
    return web.json_response(data)


app = web.Application()
app.add_routes([web.get('/{name}', handle)])

web.run_app(app)
