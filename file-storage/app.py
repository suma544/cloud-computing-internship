import json
import os
import re

import boto3

s3 = boto3.client("s3")
bucket = os.environ["BUCKET"]


def reply(code, data):
    return {"statusCode": code, "headers": {"content-type": "application/json"},
            "body": json.dumps(data, default=str)}


def handler(event, context):
    claims = event["requestContext"]["authorizer"]["jwt"]["claims"]
    prefix = claims["sub"] + "/"
    params = event.get("queryStringParameters") or {}
    action = params.get("action", "list")
    if action == "list":
        options = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 100}
        if params.get("cursor"):
            options["ContinuationToken"] = params["cursor"]
        result = s3.list_objects_v2(**options)
        return reply(200, {"files": [
            {"name": item["Key"][len(prefix):], "bytes": item["Size"]}
            for item in result.get("Contents", [])
        ], "cursor": result.get("NextContinuationToken")})

    name = params.get("name", "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]{0,127}", name):
        return reply(400, {"error": "Use a filename of 1–128 letters, numbers, spaces, dots, underscores or hyphens."})
    key = prefix + name
    if action == "versions":
        result = s3.list_object_versions(Bucket=bucket, Prefix=key, MaxKeys=100)
        return reply(200, {"versions": [
            {"id": item["VersionId"], "modified": item["LastModified"], "latest": item["IsLatest"]}
            for item in result.get("Versions", []) if item["Key"] == key
        ]})
    if action == "upload":
        form = s3.generate_presigned_post(
            bucket, key, Conditions=[["content-length-range", 1, 10 * 1024 * 1024]],
            ExpiresIn=300,
        )
        return reply(200, form)
    if action in {"download", "share"}:
        options = {"Bucket": bucket, "Key": key,
                   "ResponseContentDisposition": "attachment"}
        if params.get("version"):
            options["VersionId"] = params["version"]
        seconds = 900 if action == "share" else 60
        url = s3.generate_presigned_url("get_object", Params=options, ExpiresIn=seconds)
        return reply(200, {"url": url, "expires_in": seconds})
    return reply(400, {"error": "Unknown action"})
