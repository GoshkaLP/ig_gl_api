# INSTAGRAM UNOFFICIAL API
###### by GoshkaLP


#### This is a simple module that helps to work with IG features.

### Quick start:
```
from ig_gl_api import GetSession, IgApi
username = "your_username"
password = "your_password"
session = GetSession(username, password).get_token()
api = IgApi(session)
res = api.download_story(username);
```
This expression will return a dictionary with content.

### Available methods at the moment:
- download stories `api.download_story("username")`
- download posts `api.download_post("url")`
- download highlights `api.download_highlight("username")`
- download user's avatar `api.download_avatar("username")`
- convert username to IG user_id `api.get_user_id("username")`
- convert IG user_id to username `api.get_username("user_id")`

### Requirements:
- accessify >= 0.3.1
- bs4 >=0.0.1
- requests >= 2.22.0

### Notes:
If your username and/or password are incorrect, the program will return `ValueError`.
Also, sometimes, Instagram can block your requests.
