# -*- coding: utf-8 -*-

import logging
import json
import sys
from rest_api_lib import rest_api, set_env, show_env
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logging.basicConfig(level=logging.WARNING,
                    format=' %(asctime)s - %(levelname)s - %(message)s')
# logging.disable(logging.CRITICAL)
logging.debug("Start of program")

if __name__ == "__main__":
    help_msg = '''\nUsage: 
            选择vManage Server和Tenant
            python3 sdwan_tools.py set env 
            
            获取设备当前配置文件
            python3 sdwan_tools.py show_run device_sn
            例如：python3 sdwan_tools.py show_run 1920C539181628S
            
            导出设备配置，存成json文件
            python3 sdwan_tools.py get device_sn 
            例如：python3 sdwan_tools.py get 1920C539181628S

            修改json文件以后，再运行:
            python3 sdwan_tools.py push device_sn 将新的配置推送给vManage
            例如：python3 sdwan_tools.py push 1920C539181628S
            
            查看当前的vManage Server和Tenant
            python3 sdwan_tools.py show env 

            单租户测试：
            pyhthon3 sdwan_tools.py dpi info\n'''

    if len(sys.argv) < 3:
        print(help_msg)
        # sys.exit(0)
    else:
        action = sys.argv[1]
        target_obj = sys.argv[2]

        current_env = 'current_env.json'

        try:
            with open(current_env, 'r') as f_obj:
                server_info = json.load(f_obj)

        # 如果文件不存在
        except FileNotFoundError:
            msg = "Sorry, the file " + current_env + " does not exist.\n"
            print(msg)
            set_env()
            with open(current_env, 'r') as f_obj:
                server_info = json.load(f_obj)

        SDWAN_SERVER = server_info['server_name']
        SDWAN_IP = server_info['hostname']
        SDWAN_PORT = server_info['port']
        SDWAN_USERNAME = server_info['username']
        SDWAN_PASSWORD = server_info['password']
        if server_info['tenant'] != 'single_tenant_mode':
            TENANT = server_info['tenant'][0]['name']
        else:
            TENANT = 'single_tenant_mode'

        del server_info
        logging.debug(
            "Current environment is : server\t{}\ttenant\t{}".format(SDWAN_IP, TENANT))

        if action in ["dpi", "int"]:

            sdwanp = rest_api(
                vmanage_ip=SDWAN_IP,
                port=SDWAN_PORT,
                username=SDWAN_USERNAME,
                password=SDWAN_PASSWORD,
                tenant=TENANT)
            del SDWAN_PASSWORD
            if TENANT != "single_tenant_mode":
                sdwanp.set_tenant(TENANT)

            if action == 'dpi' and target_obj == 'info':
                response = sdwanp.query_dpi('6')
                print(response.json()['data'])
                # sys.exit(0)

            elif action == 'int' and target_obj == 'stat':
                response = sdwanp.list_all_device()
                device_list_data = response.json()['data']
                response = sdwanp.query_all_int_statistics()
                all_int_data = response.json()['data']
                all_int_stat = []
                for device in device_list_data:
                    if device['reachability'] == 'reachable' and device['device-type'] == 'vedge':
                        for int_stat in all_int_data:
                            if int_stat["vdevice_name"] == device["local-system-ip"]:
                                all_int_stat.append(int_stat)

                with open('all_int_statistics.json', 'w') as file_obj:
                    json.dump(all_int_stat, file_obj)
                for device in device_list_data:
                    system_ip_list = [device['local-system-ip']]
                    if device['reachability'] == 'reachable' and device['device-type'] == 'vedge':
                        response = sdwanp.query_device_int_statistics(
                            system_ip_list)
                        with open(str(system_ip_list[0])+'.json', 'w') as file_obj:
                            json.dump(response.json()[
                                      'data'], file_obj, indent=4)
                # sys.exit(0)
            sdwanp.logout()

        elif action in ["get", "show_run", "push"]:

            sdwanp = rest_api(
                vmanage_ip=SDWAN_IP,
                port=SDWAN_PORT,
                username=SDWAN_USERNAME,
                password=SDWAN_PASSWORD,
                tenant=TENANT)
            del SDWAN_PASSWORD
            if TENANT != "single_tenant_mode":
                sdwanp.set_tenant(TENANT)

            if action == 'show_run':
                response = sdwanp.get_device_running(uuid=target_obj)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('config') and len(data.get('config')) > 0:
                        running_config = response.json()['config']
                        if '/' in target_obj:
                            target_obj = target_obj.replace('/', '_')
                        logging.debug('Start of get_request %s' % target_obj)
                        with open(target_obj + ".txt", 'w') as file_obj:
                            file_obj.write(running_config)
                        print(running_config)
                else:
                    if response.json().get('error') and len(response.json().get('error')) > 0:
                        err_msg = response.json()['error']['details']
                        print(err_msg)
                    else:
                        print("Error:", response.status_code, response.text)

                sdwanp.logout()
                logging.debug("End of program")
                sys.exit(0)

            device_info = sdwanp.get_device_info(target_obj).json()
            if device_info["data"][0]["configOperationMode"] == 'cli':
                if device_info["data"][0].get("vbond"):
                    print("This device currently is in CLI mode.")
                else:
                    print("This device is not activated.")
                try:
                    with open(target_obj + '.json', 'r') as f_obj:
                        data = json.load(f_obj)
                        if data.get("templateId"):
                            templateId = data["templateId"]

                except FileNotFoundError:
                    templateId = sdwanp.select_template(target_obj)

            else:
                templateId = device_info['data'][0]['templateId']
            del device_info

            if action == 'get':
                if templateId != "Bye":
                    response = sdwanp.get_device_cli_data(
                        uuid=target_obj, templateId=templateId)
                    # logout = sdwanp.vmanage_logout()
                # sys.exit(0)
            if action == 'push':
                template_type = sdwanp.get_template_type(templateId)
                preview_config = sdwanp.preview_config(
                    uuid=target_obj, templateId=templateId)
                print(preview_config.text)

                while True:
                    ready_to_go = input(
                        "Please check and confirm the configuration...(y/n):")
                    if ready_to_go == 'y':
                        if template_type == 'file':
                            push_cli_response = sdwanp.push_cli_config(
                                uuid=target_obj, templateId=templateId)
                            job_id = push_cli_response.json()
                        elif template_type == 'template':
                            push_template_response = sdwanp.push_template_config(
                                uuid=target_obj, templateId=templateId)
                            job_id = push_template_response.json()
                        break
                    elif ready_to_go == 'n':
                        print("Job canceled...Exit")
                        sdwanp.logout()
                        sys.exit(0)
                    else:
                        print("Please input y or n.")
                        # ready_to_go = input("Please check and confirm the configuration...(y/n):")

                job_status = sdwanp.check_job(job_id).json()
                print('Job summary', '='*10, '\n Job Status: {status}'.format(
                    status=job_status['data'][0]['status']))
                print('Job activies:')
                for item in job_status['data'][0]['activity']:
                    print(item)

                # sys.exit(0)
            sdwanp.logout()
            logging.debug("End of program")
            sys.exit(0)

        elif action == 'set' and target_obj == 'env':
            server_info = None
            set_env()
            # sys.exit(0)

        elif action == 'show' and target_obj == 'env':
            show_env(SDWAN_SERVER, SDWAN_IP, TENANT)
            # sys.exit(0)

        else:
            print("""输入参数不正确""")
            print(help_msg)
        

logging.debug("End of program")
sys.exit(0)
