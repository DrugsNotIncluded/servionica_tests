#!/bin/python3
import requests
import json5 as json
import csv
import argparse
import paramiko
import itertools

# Что принимаем:
# Порт SSH, Ключи SSH (путь), Список серверов, Куда писать CSVшку, Кому кидать в ТГ, ключ от бот апишки ТГ
# -p/--port , -i/--identity, -f/--servers, -o/--output, --uid, --api
#
# Поочерёдно пытаемся достать файл с сервера, если сервер недоступен, то пишем ошибку в консольку и лог, (лог так же кидаем в тг (?))
# Данные сериализуем в жсонку, затем разделяем на ключи/данные чтобы вытащить заголовок,
# в конце сращиваем все уникальные данные для заголовков, кидаем в список списков все ряды, добавляем первым рядом и заголовком адрес сервера
# пишем в csvшку, проверяем доступен ли TG, если да, то кидаем файл в тг, если нет, то гадим в логи. Кчау)
#
# Реализация стандартной жсонки это мрак блядь, она не умеет жсонки с лишней запятой в конце парсить, берём json5


# Парсим
def parse_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    parser.add_argument("--port", "-p", default=22, help="SSH connection port")
    parser.add_argument("--identity", "-i", help="Use different private key location")
    parser.add_argument("--servers", "-f", help="Path to server list")
    parser.add_argument("--output", "-o", default="./log.csv", help="CSV log output path")
    parser.add_argument("--uid", help="Telegram UID. Can be obtained via @userinfobot")
    parser.add_argument("--api", help="Telegram Bot API token")
    parser.add_argument("--user", "-u", help="Server auth user", default="root")
    return parser.parse_args()


# Тащим файл с сервера и сериализуем
def get_remote_file(server: str, user: str, identity_path: str, port: int, remote_filename_test = '') -> list:
    remote_filename = "/var/log/secure.log"
    # Testing only
    if remote_filename_test != '':
        remote_filename = remote_filename_test
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.load_system_host_keys()
    try:
        ssh_client.connect(server.strip(), username=user, port=int(port), key_filename=identity_path)
    except:
        print("Can't connect to server.")
    command = 'cat ' + remote_filename
    stdin, stdout, stderr = ssh_client.exec_command(command)
    stdout = stdout.readlines()
    stderr = stderr.readlines()
    ssh_client.close()
    json_data = json.loads(stdout)
    return (json_data)


# Записываем csvшку
def write_csv(header: list, rows: list, csv_path: str) -> None:
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, delimiter='|', quotechar=' ', quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


# Отправляем файл
def tg_send_log_file(log_path: str, token: str, uid: int) -> None:
    BOT_ENDPOINT = "https://api.telegram.org/bot"
    action = "/sendDocument"
    with open(log_path, 'rb') as log:
        full_url = BOT_ENDPOINT+token+action
        response = requests.post(full_url, data={'chat_id': uid}, files={'document': log})
        if not response.ok:
            print(response.text)


def get_servers_ip_from_config(config_path: str) -> list:
    with open(config_path, "r") as config_f:
        config = config_f.readlines()
        ret = []
        for ip in config:
            result = {}
            ip = ip.replace("\n", "")
            if ":" in ip:
                adress, port = ip.split(":")
            else:
                adress = ip;
                port = "22"
            result["ip"] = adress
            result["port"] = port
            ret += [result]
        return ret


def main() -> None:
    # Парсим, лепим, пишем
    HEADER = ['server', 'user', 'connect_date', 'status_code']
    parser = argparse.ArgumentParser()
    args = parse_args(parser)
    servers = get_servers_ip_from_config(args.servers)
    rows = []
    for server in servers:
        json_data = get_remote_file(server["ip"], args.user, args.identity, server["port"], "")
        mdata = " ".join([str(item) for item in json_data])
        row = json.loads(mdata.replace('\n', ''))
        for dset in row:
            dset["server"] = server["ip"]
        rows += row
    write_csv(HEADER, rows, args.output)
    # Telegram
    if args.uid and args.api:
        tg_send_log_file(args.output, args.api, args.uid)

main()
