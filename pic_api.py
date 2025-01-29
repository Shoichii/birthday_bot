import requests
import env


def random_image():
    '''Получение рандомной картинки по API'''
    url = (f"https://api.unsplash.com/photos/random?client_id={env.CLIENT_ID_UNSPLASH_SERVICE}"
           "&collections=9155171")
    print(url)
    headers = {'Authorization': 'key'}
    response = requests.request("GET", url, headers=headers)
    return response.json()['urls']['regular']
