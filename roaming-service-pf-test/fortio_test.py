import http.client
import json
import os
import subprocess
from datetime import datetime

def assemble_command(api_name, thread_count=1, duration="10s", target_qps=0):
    apis = get_api()
    if api_name in apis:
        api_desc = apis[api_name]
    else:
        print(f"api {api_name} not exist")
        return

    command_string = f"fortio " + \
                     f" load " + \
                     f" -timeout 30s" + \
                     f" -qps {target_qps}" + \
                     f" -c {thread_count} " + \
                     f" -t {duration} "

    # append headers
    if 'headers' in api_desc:
        for header in api_desc['headers']:
            command_string += header

    # append json filename param
    time_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_file_name = os.path.join(f"{time_str}-{api_name}-thread_count@{thread_count}-duration@{duration}-qps@{target_qps}.json")
    log_file_name = os.path.join(f"{time_str}-{api_name}-thread_count@{thread_count}-duration@{duration}-qps@{target_qps}.log.txt")
    command_string += f" -json {json_file_name}"

    # add cert file if exist
    if 'cert' in api_desc:
        command_string += f" -cert {api_desc['cert']} "

    command_string += f" \"{api_desc['endpoint']}\""

    # print(command_string)
    print(f"nohup {command_string} > {log_file_name} 2>&1 &")

    return command_string

def execute_fortio_load_test(api_name, thread_count=1, duration="10s", target_qps=0):
    command_string = assemble_command(api_name, thread_count, duration, target_qps)
    print(command_string)
    if args.execute:
        p = subprocess.Popen(command_string, shell=True, stdout=subprocess.PIPE)
        p.stdout.read()
        print(p.returncode)

def get_api():
    ad_grant_type = "client_credentials"
    ad_client_id = "46e460c2-c56c-416b-b9ca-00cd5f53b43a"
    ad_client_secret = "znp8Q~at_6yknQ5NRBbx3Ua04ItJA78wnvdrdcxD"
    ad_scope = "api%3A%2F%2F23be01d5-7b7a-462c-9238-93ecfd78b584%2F.default"

    def get_azure_ad_access_token():
        conn = http.client.HTTPSConnection("login.microsoftonline.com")
        payload = f'grant_type={ad_grant_type}' + \
                  f'&client_id={ad_client_id}' + \
                  f'&client_secret={ad_client_secret}' + \
                  f'&scope={ad_scope}'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        conn.request("POST", "/f25493ae-1c98-41d7-8a33-0be75f5fe603/oauth2/v2.0/token", payload, headers)
        res = conn.getresponse()
        return json.loads(res.read().decode("utf-8"))['access_token']

    azure_ad_token = get_azure_ad_access_token()

    roaming_api_host = "https://roaming-service-qa-eu.volvo.com"
    api_charging_location_endpoint = "/api/charging-location"
    roaming_liveness = "/health/liveness"

    ibm_apic_client_id = "83806586ab370ac5544a16a1970fa6c9"  # replace ibm apic client id before test

    return {
        "filter_charging_location_apic_gateway": {
            "endpoint": "https://apitest-awe.volvo.com/vgcq/external/ve-emsp-findcharger?north_east_point=-80,-80&south_west_point=-75,-75",
            "cert": os.path.join(os.getcwd(), "certs/apigwtestawesvc.it.volvo.com.crt "),
            "headers": [
                f" -H \"Authorization: Bearer {azure_ad_token}\" ",
                f" -H \"X-IBM-Client-Id: {ibm_apic_client_id}\" "
            ]
        },
        "get_charger_location_by_id_apic_gateway": {
            "endpoint": "https://apitest-awe.volvo.com/vgcd/external/ve-emsp-charging-location/5374",
            "cert": os.path.join(os.getcwd(), "certs/apigwtestawesvc.it.volvo.com.crt "),
            "headers": [
                f" -H \"Authorization: Bearer {azure_ad_token}\" ",
                f" -H \"X-IBM-Client-Id: d15466307109e2a1688870b1b13837df\" "
            ]
        },
        "filter_charging_location_direct": {
            "endpoint": roaming_api_host + api_charging_location_endpoint + "?north_east_point=-80,-80&south_west_point=-75,-75",
            "cert": os.path.join(os.getcwd(), "certs/roaming-service-qa-eu.volvo.com.crt "),
            "headers": [
                f" -H \"Authorization: Bearer {azure_ad_token}\" ",
            ]
        },
        "get_charger_location_by_id_direct": {
            "endpoint": roaming_api_host + api_charging_location_endpoint + "/5374",
            "cert": os.path.join(os.getcwd(), "certs/roaming-service-qa-eu.volvo.com.crt "),
            "headers": [
                f" -H \"Authorization: Bearer {azure_ad_token}\" ",
            ]
        },
        "roaming_liveness": {
            "endpoint": roaming_api_host + roaming_liveness,
            "cert": os.path.join("certs/roaming-service-qa-eu.volvo.com.crt ")
        },
    }

if __name__ == "__main__":
    import time
    import argparse

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--apis', nargs='+', type=str, help='which api will be do fortio test, split with ,.')
    parser.add_argument('--rounds', type=int, help='count of test round.', default=3)
    parser.add_argument('--thread_count', type=int, help='number of threads', default=1)
    parser.add_argument('--duration', type=int, help='duration of the test in seconds', default=10)
    parser.add_argument('--qps', type=int, help='target qps', default=1)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    apis = args.apis
    rounds = args.rounds
    thread_count = args.thread_count
    duration = args.duration
    qps = args.qps

    for i in range(rounds):
        for api in apis:
            execute_fortio_load_test(api, thread_count=thread_count, duration=f"{duration}s", target_qps=qps)
            time.sleep(1)
