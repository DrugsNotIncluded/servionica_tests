#!/bin/python3

import requests
import argparse
import toml
import subprocess
import time
import datetime
import glob
import zipfile
import os
from email.message import EmailMessage
import smtplib, ssl
from email.mime.text import MIMEText


def parse_args(parser: argparse.ArgumentParser) -> argparse.Namespace:
    parser.add_argument("--config", "-c", help="Config with services list.")
    parser.add_argument("--recheck-config", action=argparse.BooleanOptionalAction, help="If enabled forces config file reread before server check.")
    parser.add_argument("--interval", "-i", help="Server check interval.")
    parser.add_argument("--log-output-dir", "-o", help="Path to log output directory.")
    parser.add_argument("--smtp-login", help="Sender email")
    parser.add_argument("--smtp-password", help="Email password")
    parser.add_argument("--smtp-server", help="SMTP Server")
    return parser.parse_args()


def get_config(path_to_config: str) -> list:
    with open(path_to_config, 'r', newline='') as config_f:
        config = config_f.readlines()
    config = toml.loads(''.join(config))
    return config


def run_exec(command: list) -> dict:
    prc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = prc.communicate()
    return {"stdout": stdout, "stderr": stderr}


def check_server(url: str) -> dict:
    response = requests.get(url)
    return {"reason": response.reason, "status_code": response.status_code, "url": url}


def archive_and_clean(log_dir: str) -> None:
    to_archive = glob.glob(log_dir+"/*.log")
    date = datetime.datetime.now()
    archive_name = date.strftime("%Y_%m_%d-%H_%M")+".zip"
    os.remove(glob.glob(log_dir+"/*.zip")[0])
    with open(log_dir+"/"+archive_name, "w") as zip_f:
        for log in to_archive:
            zip_f.write(log)
            os.remove(log)


def send_email(content: str, sender_email: str, sender_password: str, smtp_server: str, recipient: str) -> None:
    server = smtplib.SMTP(smtp_server, 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    message = MIMEText(content)
    message["Subject"] = "Server access error"
    message["From"] = sender_email
    message["To"] = recipient
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, 465, context=context) as server:
        try:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, message.as_string())
        except Exception as e:
            print(e)


def log_loop(interval: int, log_dir: str, config_file: str, sender_email: str, sender_password: str, smtp_server: str) -> None:
    while 1:
        config = dict(get_config(config_file))
        responses = []
        for service_key in config["Services"]:
            try:
                responses += [check_server(config["Services"][service_key])]
            except Exception as e:
                print(f"Something went wrong: {e}")
        for response in responses:
            if response["status_code"] > 299:
                message = f'Error code {response["status_code"]}:\n Service url: {response["url"]}\n Reason: "{response["reason"]}"'
                print(message)
                send_email(message, sender_email, sender_password, smtp_server, config["Notification"]["Recipient"])
        if len(glob.glob(log_dir+"/*.log")) == 5:
            archive_and_clean(log_dir)
        date = datetime.datetime.now()
        log_name = date.strftime("%Y_%m_%d-%H_%M")+".log"
        with open(log_dir+"/"+log_name, "w") as log_f:
            log_f.write(str(responses))
        time.sleep(int(interval))


def main() -> None:
    parser = argparse.ArgumentParser()
    args = parse_args(parser)
    log_loop(args.interval, args.log_output_dir, args.config, args.smtp_login, args.smtp_password, args.smtp_server)


main()
