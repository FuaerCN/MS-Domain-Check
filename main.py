from stem import Signal
from stem.control import Controller
from flask import Flask, jsonify
from faker import Faker
import requests
import threading
import re
import os

os.system('nohup tor -f /etc/tor/torrc >/dev/null &')
fake = Faker()
proxies = {'http': 'socks5://127.0.0.1:9150', 'https': 'socks5://127.0.0.1:9150'}
signup_url = 'https://signup.microsoft.com/signup'

def switch_proxy():
    with Controller.from_port(port = 9151) as controller:
        controller.authenticate()
        controller.signal(Signal.NEWNYM)


class MyThread(threading.Thread):
    def __init__(self, func, args=()):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args
    def run(self):
        self.result = self.func(*self.args)
    def get_result(self):
        threading.Thread.join(self)  # 等待线程执行完毕
        try:
            return self.result
        except Exception:
            return None

def get_state(domain):
    url = f'https://login.windows.net/{domain}/.well-known/openid-configuration'
    try:
        page_text = requests.get(url, timeout=20).text
        if 'token_endpoint' in page_text:
            domain_state = True
        else:
            domain_state = False
    except Exception as err:
        print('get_state Error: ' + str(err))
        domain_state = get_state(domain)
        
    return domain_state


def get_admin(domain):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'user-agent': fake.chrome()
    }
    post_data = {
        'SkuId': 'bf666882-9c9b-4b2e-aa2f-4789b0a52ba2',
        'StepsData.Email': 'Yam@' + domain
    }
    try:
        result_text = requests.post(signup_url, headers=headers, data=post_data, proxies=proxies, timeout=20).text
        if "Go back" in result_text:
            domain_admin = False
        else:
            domain_admin = True
    except Exception as err:
        print('get_admin Error: ' + str(err))
        switch_proxy()
        domain_admin = get_admin(domain)
        
    return domain_admin


def get_license(domain):
    try:
        header = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'user-agent': fake.chrome()
        }
        post_data = {
            'SkuId': 'education',
            'StepsData.Email': 'Yam@' + domain
        }
        result_text = requests.post(signup_url, headers=header, data=post_data, proxies=proxies, timeout=20).text
        if "sku_314c4481-f395-4525-be8b-2ec4bb1e9d91" in result_text:
            domain_license = 'Office 365 A1'
        elif "sku_e82ae690-a2d5-4d76-8d30-7c6e01e6022e" in result_text:
            domain_license = 'Office 365 A1 Plus'
        else:
            domain_license = 'unknown'
    except Exception as err:
        print('get_license Error: ' + str(err))
        switch_proxy()
        domain_license = get_license(domain)
    
    return domain_license


def get_azure(domain):
    try:
        url = f'https://az.msaz.workers.dev/domain={domain}'
        result_text = requests.get(url, timeout=20).text
        if "true" in result_text:
            domain_azure = True
        elif "school" in result_text:
            domain_azure = False
        else:
            domain_azure = result_text
    except Exception as err:
        print('get_azure Error: ' + str(err))
        domain_azure = get_azure(domain)
    
    return domain_azure

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config["JSON_SORT_KEYS"] = False

@app.route('/')
def index():
    return 'Index Page'


@app.route('/ms=<domain>')
def ms(domain):
    regexs = re.compile("^(?!-)[A-Za-z0-9-]+([\\-\\.]{1}[a-z0-9]+)*\\.[A-Za-z]{2,6}$")
    if(re.search(regexs, domain)):
        domain_state = get_state(domain)
        if domain_state:
            switch_proxy()
            #创建线程
            more_get_admin = MyThread(get_admin,(domain,))
            more_get_license = MyThread(get_license,(domain,))
            #启动线程
            more_get_admin.start()
            more_get_license.start()
            #线程等待
            more_get_admin.join()
            more_get_license.join()
            #输出线程执行方法后的的返回值
            #print(more_get_admin.get_result())
            domain_data = [domain,
                           domain_state,
                           more_get_admin.get_result(),
                           more_get_license.get_result()
                           ]
        else:
            domain_data = [domain, domain_state]
    else:
        domain_data = [domain,'Invalid Domain Name']
    
    return jsonify(domain_data)


@app.route('/domain=<domain>')
def main(domain):
    regexs = re.compile("^(?!-)[A-Za-z0-9-]+([\\-\\.]{1}[a-z0-9]+)*\\.[A-Za-z]{2,6}$")
    if(re.search(regexs, domain)):
        domain_state = get_state(domain)
        if domain_state:
            switch_proxy()
            #创建线程
            more_get_admin = MyThread(get_admin,(domain,))
            more_get_license = MyThread(get_license,(domain,))
            more_get_azure = MyThread(get_azure,(domain,))
            #启动线程
            more_get_admin.start()
            more_get_license.start()
            more_get_azure.start()
            #线程等待
            more_get_admin.join()
            more_get_license.join()
            more_get_azure.join()
            #输出线程执行方法后的的返回值
            #print(more_get_admin.get_result())
            domain_data = [domain,
                           more_get_azure.get_result(),
                           domain_state,
                           more_get_admin.get_result(),
                           more_get_license.get_result()
                           ]
        else:
            domain_azure = get_azure(domain)
            domain_data = [domain, domain_azure, domain_state]
    else:
        domain_data = [domain,'Invalid Domain Name']
    
    return jsonify(domain_data)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
