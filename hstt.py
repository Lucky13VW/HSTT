# -*- coding: utf-8 -*-

from flask import Flask,g
from views.admin import admin
from views.wcapp import wcapp

app = Flask(__name__)
app.register_blueprint(admin)
app.register_blueprint(wcapp)
# Blueprint can be registered many times
#app.register_blueprint(simple_page, url_prefix='/pages')

db_hs_config = {
    'user': 'vw',
    'password': 'letmein',
    'database': 'hs_timetable',
    'charset': 'utf8'
}    

WC_AppID='wx71112abdd32f1e55'
WC_AppSecret='6db14bb92d4b061ba7a6ee876cd2aee7'


app.config.update(dict(
    DATABASE= db_hs_config,
    DEBUG=True,
    SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/',
    WC_TPL_MSG_ID='1JLDtKxWcuK9cvEOn5-MEhm-BCxvJ-UZQd5pW-POav8',
    WC_URL_Login='https://api.weixin.qq.com/sns/jscode2session?appid={0}&secret={1}&grant_type=authorization_code&js_code='.format(WC_AppID,WC_AppSecret),
    WC_URL_Token='https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={0}&secret={1}'.format(WC_AppID,WC_AppSecret),
    WC_URL_SEND_TPL_MSG='https://api.weixin.qq.com/cgi-bin/message/wxopen/template/send?access_token=ACCESS_TOKEN'
))

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'hs_tt_db'):
        #print('close db')
        g.hs_tt_db.close()

if __name__ == '__main__':
    #app.run()
    app.run(host='0.0.0.0',port=8080)
