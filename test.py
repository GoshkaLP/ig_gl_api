from ig_gl_api import GetSession, IgApi

sessionid = 'asdasd'
csrftoken = 'asdasd'

session = GetSession(sessionid=sessionid, csrftoken=csrftoken).get_token()
api = IgApi(session)
res = api.download_avatar('jusohatam')
print(res)