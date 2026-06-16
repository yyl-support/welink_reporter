import requests
import os
import json
import re

def send_msg(content, receiver, auth, sender=None):
    url = 'http://xiaoluban.rnd.huawei.com:80/'
    data = {'content': content, 'receiver': receiver, 'auth': auth}
    if sender:
        data['sender'] = sender
    res = requests.post(url=url, json=data)
    if not res.ok:
        print(res.text)


def load_name_to_employee_id_map(data_dir):
    assign_file = os.path.join(data_dir, 'issue_assign.json')
    if not os.path.exists(assign_file):
        return {}
    with open(assign_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {v['name']: v['employee_id'] for v in data.values() if v.get('employee_id')}


def send_personal_messages(inform_path, auth, data_dir):
    with open(inform_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    name_to_employee_id = load_name_to_employee_id_map(data_dir)
    for line in lines:
        line = line.strip()
        if not line or '请@所有人' in line:
            continue
        match = re.match(r'请@([^，,]+)', line)
        if match:
            name = match.group(1).strip()
            if name in name_to_employee_id:
                employee_id = name_to_employee_id[name]
                if employee_id:
                    send_msg(line, employee_id, auth)
