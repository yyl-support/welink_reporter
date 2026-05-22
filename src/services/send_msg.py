import requests
import os

def send_msg(content, receiver, auth, sender=None):
    url = 'http://xiaoluban.rnd.huawei.com:80/'
    data = {'content': content, 'receiver': receiver, 'auth': auth}
    if sender:
        data['sender'] = sender
    res = requests.post(url=url, json=data)
    if not res.ok:
        print(res.text)

if __name__ == '__main__':
    '''
    准备工作
    1、安装依赖库:pip install requests prettytable
    2、发送“获取发送token“给小鲁班，获取认证token，赋值给下面的auth变量
    '''
    personal_auth = 'y00896582_JNMBax6AEejqdICHmLY4yG2iTKtR3SXf'  # 填写从小鲁班那里获取的token
    receiver_uid = '726620333427171979'  # 填写自己的uid，首字母+工号：“a00123456”

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    inform_path = os.path.join(project_root, 'data', 'welink_inform.txt')
    with open(inform_path, 'r', encoding='utf-8') as f:
        content = f.read()

    send_msg(content, receiver_uid, personal_auth)