import json
import logging
import os

import boto3

AWS_REGION = os.environ["AWS_REGION"]
AWS_ACCOUNT_ID = os.environ["ACCOUNT_ID"]
TARGET_SQS_NAME = os.environ["TARGET_SQS_NAME"]

DELAY_BASE = int(os.environ["DELAY_BASE"])
DELAY_CAP = int(os.environ["DELAY_CAP"])
DELAY_STEP = int(os.environ["DELAY_STEP"])

MAX_RETRIES = int(os.environ["MAX_RETRIES"])

TARGET_SQS_URL = f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{TARGET_SQS_NAME}"


SQS_CLIENT = boto3.client("sqs", region_name=AWS_REGION)

logging.basicConfig(format="%(asctime)s : %(levelname)s : %(message)s", level=logging.INFO)


def lambda_handler(event, context):
    for record in event.get("Records", []):
        replay_count = int(record["messageAttributes"].get("sqsDLQReplayCount", {"stringValue": "0"})["stringValue"])

        if replay_count > MAX_RETRIES:
            logging.critical(f"The maximum retry limit {MAX_RETRIES} is reached. Discarding the message")
            return

        delay_seconds = DELAY_BASE + replay_count * DELAY_STEP
        logging.info(
            f"Replaying the message for reprocessing with delay {delay_seconds}, attempt no: {replay_count + 1}"
        )
        record["messageAttributes"] = {
            "sqsDLQReplayCount": {
                "StringValue": str(replay_count + 1),
                "DataType": "Number",
            }
        }

        SQS_CLIENT.send_message(
            QueueUrl=TARGET_SQS_URL,
            MessageBody=record["body"],
            DelaySeconds=min(delay_seconds, 900),
            MessageAttributes=record["messageAttributes"],
        )
