import hmac
import json
import os
import re
import time
import uuid

import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table(os.environ["TABLE"])


def handler(event, context):
    request = event["requestContext"]
    connection = request["connectionId"]
    route = request["routeKey"]
    now = int(time.time())
    if route == "$disconnect":
        table.delete_item(Key={"kind": "connection", "id": connection})
        return {"statusCode": 200}
    if route == "$connect":
        params = event.get("queryStringParameters") or {}
        if not hmac.compare_digest(params.get("key", "").encode(), os.environ["ROOM_KEY"].encode()):
            return {"statusCode": 403}
        name = params.get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,31}", name):
            return {"statusCode": 400}
        table.put_item(Item={"kind": "connection", "id": connection,
                             "name": name, "expires": now + 7500})
        return {"statusCode": 200}

    sender = table.get_item(Key={"kind": "connection", "id": connection},
                            ConsistentRead=True).get("Item")
    if sender is None or sender["expires"] <= now:
        return {"statusCode": 403}
    try:
        body = json.loads(event.get("body") or "{}")
        message = body.get("message", "").strip() if isinstance(body, dict) and isinstance(body.get("message"), str) else ""
    except ValueError:
        return {"statusCode": 400}
    if not 1 <= len(message) <= 1000:
        return {"statusCode": 400}

    item = {"id": f"{time.time_ns()}-{uuid.uuid4().hex[:8]}",
            "name": sender["name"], "message": message, "sent": now}
    table.put_item(Item={**item, "kind": "message", "expires": now + 86400})
    client = boto3.client("apigatewaymanagementapi",
                          endpoint_url=f"https://{request['domainName']}/{request['stage']}")
    data = json.dumps(item, ensure_ascii=False).encode()
    query = {"KeyConditionExpression": Key("kind").eq("connection"), "ConsistentRead": True}
    while True:
        page = table.query(**query)
        for recipient in page["Items"]:
            if recipient["expires"] <= now:
                continue
            try:
                client.post_to_connection(ConnectionId=recipient["id"], Data=data)
            except client.exceptions.GoneException:
                table.delete_item(Key={"kind": "connection", "id": recipient["id"]})
        if "LastEvaluatedKey" not in page:
            break
        query["ExclusiveStartKey"] = page["LastEvaluatedKey"]
    return {"statusCode": 200}
