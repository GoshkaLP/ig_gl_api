from accessify import protected
from bs4 import BeautifulSoup
from json import loads
from requests import get, Session


class GetSession:
    def __init__(self, username='', password='', sessionid='', csrftoken=''):
        self.username = username
        self.password = password
        self.sessionid = sessionid
        self.csrftoken = csrftoken

    def get_token(self):
        if self.sessionid and self.csrftoken:
            url = 'https://www.instagram.com/accounts/edit/'
            cookies = {'sessionid': self.sessionid,
                       'csrftoken': self.csrftoken}
            req = get(url, cookies=cookies)
            if 'not-logged-in' in req.text:
                raise ValueError('Authorization error. Wrong sessionid and csrftoken cookies.')
            else:
                return cookies
        elif self.username and self.password:
            url = 'https://www.instagram.com/accounts/login/'
            url_main = url + 'ajax/'
            auth = {'username': self.username, 'password': self.password}
            with Session() as s:
                s.headers[
                    'user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                                    'Chrome/70.0.3538.77 Safari/537.36'
                resp = s.get(url)
                s.headers['x-csrftoken'] = resp.cookies['csrftoken']
                s.headers['referer'] = url
                s.headers['cookie'] = 'csrftoken=' + resp.cookies['csrftoken']

                resp = s.post(url_main, data=auth)
            # 1-no errors
            # 2-error
            if resp.json()['status'] == 'fail':
                if resp.json()['message'] == 'checkpoint_required':
                    raise ValueError('Authorization failed. Checkpoint required.')
                elif resp.json()['message'] == 'Please wait a few':
                    raise ValueError('Authorization failed. Please wait a few.')
            elif resp.json()['status'] == 'ok':
                if 'authenticated' in resp.json().keys():
                    if resp.json()['authenticated']:
                        if 'errors' not in resp.json().keys():
                            cookies = {'sessionid': resp.cookies['sessionid'],
                                       'csrftoken': resp.cookies['csrftoken']}
                            return cookies
                    else:
                        raise ValueError('Authorization error. Wrong username or password.')
        else:
            raise ValueError('Authorization failed. Invalid data.')


class IgApi:
    def __init__(self, session):
        self.cookies = session

    @protected
    def sort_script(self, url, type_sort):
        if self.cookies:
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/70.0.3538.77 Safari/537.36',
                'x-csrftoken': self.cookies['csrftoken']}
            req = get(url, cookies=self.cookies, headers=headers)
            soup = BeautifulSoup(req.text, 'html.parser')
            sort = {}
            if 'Page Not Found' not in str(soup.find('title')):
                scripts = soup.find_all('script', type='text/javascript')
                if type_sort == 1:
                    for i in scripts:
                        if 'graphql' in str(i):
                            script = str(i)
                            sort = loads(script[script.find('{'):script.rfind('}') + 1])['entry_data']
                elif type_sort == 2:
                    for i in scripts:
                        if ('additionalDataLoaded' in str(i)) and ('graphql' in str(i)):
                            script = str(i)
                            sort = loads(script[script.find('{'):script.rfind('}') + 1])['graphql']['shortcode_media']
                return sort
            # else:
            #     return {'status': 'failed', 'message': 'wrong url'}
        else:
            raise ValueError('Authorization error. No token provided.')

    @protected
    def check_private_and_subscribe(self, url, type_sort):
        sort = self.sort_script(url, type_sort)
        is_private = None
        sub = None
        if type_sort == 1:
            is_private = sort['ProfilePage'][0]['graphql']['user']['is_private']
            sub = sort['ProfilePage'][0]['graphql']['user']['followed_by_viewer']
        elif type_sort == 2:
            is_private = sort['owner']['is_private']
            sub = sort['owner']['followed_by_viewer']
        return is_private, sub

    def get_user_id(self, user):
        url = 'https://www.instagram.com/' + user
        if self.sort_script(url, 1):
            user_id = self.sort_script(url, 1)['ProfilePage'][0]['graphql']['user']['id']
            return {'status': 'ok', 'user_id': user_id}
        else:
            return {'status': 'failed'}

    def download_story(self, user):
        user_id = self.get_user_id(user)
        if user_id['status'] == 'ok':
            is_private, sub = self.check_private_and_subscribe('https://instagram.com/' + user, 1)
            if (is_private is False) or sub:
                stories_url = 'https://www.instagram.com/graphql/query/'
                params = {'query_hash': '15463e8449a83d3d60b06be7e90627c7',
                          'variables': '{"reel_ids":["' + user_id['user_id'] + '"],"precomposed_overlay":false}'}
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                                         '(KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
                           'x-csrftoken': self.cookies['csrftoken']}
                req = get(stories_url, cookies=self.cookies, params=params, headers=headers)
                text = req.json()['data']['reels_media']
                if text:
                    data = text[0]['items']
                    res = {}
                    for i in data:
                        if i['__typename'] == 'GraphStoryImage':
                            url = i['display_url']
                            if res.get('image_story'):
                                res['image_story'].append(url)
                            else:
                                res.update({'image_story': [url]})
                        elif i['__typename'] == 'GraphStoryVideo':
                            url = i['video_resources'][0]['src']
                            if res.get('video_story'):
                                res['video_story'].append(url)
                            else:
                                res.update({'video_story': [url]})
                    res.update({'status': 'ok'})
                    return res
                else:
                    return {'status': 'failed', 'message': 'no stories'}
            else:
                return {'status': 'failed', 'message': 'private account'}
        else:
            return {'status': 'failed', 'message': 'wrong username'}

    def download_highlight(self, user):
        user_id = self.get_user_id(user)
        if user_id['status'] == 'ok':
            is_private, sub = self.check_private_and_subscribe('https://instagram.com/' + user, 1)
            if (is_private is False) or sub:
                url = 'https://www.instagram.com/graphql/query/'
                params = {'query_hash': '7c16654f22c819fb63d1183034a5162f',
                          'variables': '{"user_id":"' + user_id['user_id'] +
                                       '","include_chaining":false,"include_reel":true,'
                                       '"include_suggested_users":true,'
                                       '"include_logged_out_extras":false,"include_highlight_reels":'
                                       'true}'}
                headers = {
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                  'Chrome/70.0.3538.77 Safari/537.36',
                    'x-csrftoken': self.cookies['csrftoken']}
                req = get(url, cookies=self.cookies, params=params, headers=headers)
                data = req.json()[
                    'data']['user']['edge_highlight_reels']['edges']
                if data:
                    ids = []
                    for i in data:
                        if i['node']['__typename'] == 'GraphHighlightReel':
                            ids.append(i['node']['id'])
                    params['query_hash'] = 'eb1918431e946dd39bf8cf8fb870e426'
                    params['variables'] = '{"highlight_reel_ids":[' + \
                                          ','.join(ids) + \
                                          '],"precomposed_overlay":false,"show_story_viewer_list":true,' \
                                          '"story_viewer_fetch_count":50,"story_viewer_cursor":""}'
                    req = get(url, cookies=self.cookies, params=params, headers=headers)
                    data = req.json()['data']['reels_media']
                    res = {}
                    for i in data:
                        if i['items']:
                            for j in i['items']:
                                if j['__typename'] == 'GraphStoryImage':
                                    url = j['display_url']
                                    if res.get('image_highlight'):
                                        res['image_highlight'].append(url)
                                    else:
                                        res.update({'image_highlight': [url]})
                                elif j['__typename'] == 'GraphStoryVideo':
                                    url = j['video_resources'][0]['src']
                                    if res.get('video_highlight'):
                                        res['video_highlight'].append(url)
                                    else:
                                        res.update({'video_highlight': [url]})
                    res.update({'status': 'ok'})
                    return res
                else:
                    return {'status': 'failed', 'message': 'no highlights'}
            else:
                return {'status': 'failed', 'message': 'private account'}

        else:
            return {'status': 'failed', 'message': 'wrong username'}

    def download_post(self, url):
        if self.sort_script(url, 2):
            is_private, sub = self.check_private_and_subscribe(url, 2)
            if (is_private is False) or sub:
                sort = self.sort_script(url, 2)
                res = {}
                if sort['__typename'] == 'GraphSidecar':
                    for i in sort['edge_sidecar_to_children']['edges']:
                        if i['node']['__typename'] == 'GraphImage':
                            url = i['node']['display_url']
                            if res.get('image_post'):
                                res['image_post'].append(url)
                            else:
                                res.update({'image_post': [url]})
                        elif i['node']['__typename'] == 'GraphVideo':
                            url = i['node']['video_url']
                            if res.get('video_post'):
                                res['video_post'].append(url)
                            else:
                                res.update({'video_post': [url]})
                elif sort['__typename'] == 'GraphImage':
                    url = sort['display_url']
                    if res.get('image_post'):
                        res['image_post'].append(url)
                    else:
                        res.update({'image_post': [url]})
                elif sort['__typename'] == 'GraphVideo':
                    url = sort['video_url']
                    if res.get('video_post'):
                        res['video_post'].append(url)
                    else:
                        res.update({'video_post': [url]})
                res.update({'status': 'ok'})
                return res
            else:
                return {'status': 'failed', 'message': 'private account'}
        else:
            return {'status': 'failed', 'message': 'wrong url'}

    def download_avatar(self, user):
        if self.get_user_id(user):
            url = 'https://instagram.com/' + user
            url = self.sort_script(url, 1)['ProfilePage'][0]['graphql']['user']['profile_pic_url_hd']
            return {'status': 'ok', 'url': url}
        else:
            return {'status': 'failed', 'message': 'wrong username'}

    def get_username(self, user_id):
        url = 'https://www.instagram.com/graphql/query/'
        params = {'query_hash': '7c16654f22c819fb63d1183034a5162f',
                  'variables': '{"user_id":"' + user_id + '","include_reel":true}'}
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/70.0.3538.77 Safari/537.36',
            'x-csrftoken': self.cookies['csrftoken']}
        req = get(url, params=params, headers=headers, cookies=self.cookies)
        if req.json()['data']['user']:
            username = req.json()['data']['user']['reel']['user']['username']
            return {'status': 'ok', 'username': username}
        else:
            return {'status': 'failed', 'message': 'wrong user_id'}
