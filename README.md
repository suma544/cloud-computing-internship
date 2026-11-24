# Cloud Computing Internship Projects

These two independent AWS SAM projects are prepared for cloud deployment. The repository contains application code and infrastructure templates. Cloud deployment, end-to-end AWS verification and submission are pending.

## Prerequisites

Use an AWS account and a region that supports Cognito, S3, Lambda, API Gateway and DynamoDB. Configure an AWS CLI profile with permissions for the required CloudFormation resources and use AWS SAM CLI and Python 3.12. Review the CloudFormation change sets and AWS costs before confirming deployment. Use synthetic files and messages during verification.

## Cloud-Based File Storage System

Cognito performs OAuth 2.0 authorization code with PKCE. API Gateway validates Cognito JWTs. Lambda derives an S3 prefix from the authenticated user ID. The private S3 bucket uses server-side encryption and versioning. Presigned uploads have a 10 MiB policy limit. A user can share access to an object or a particular version with a 15-minute bearer link.

From `file-storage/` run `sam validate --lint`, `sam build`, and `sam deploy --guided`. Choose a unique lowercase Cognito domain prefix when prompted. In the Cognito user pool, create two demo users, send their temporary credentials privately and let them set their own passwords on first sign-in.

Run `python3 client.py ENDPOINT LOGIN CLIENT_ID` using the stack outputs. Use `upload path/to/demo.txt`, `list`, `versions demo.txt`, `download demo.txt | VERSION_ID`, and `share demo.txt | VERSION_ID`.

For verification, upload the same filename twice with different content. Download each version and compare the bytes. Open a share link in a signed-out browser. Sign in as the second demo user and confirm the first user's objects are absent from the list. A share link confers access to anyone who receives it until it expires.

## Real-Time Chat Application using Serverless

API Gateway WebSocket routes invoke a Lambda function for connection, disconnection and message handling. DynamoDB stores connected users and messages with TTL. The Lambda broadcasts each message to active connections and removes stale connection records when API Gateway reports them.

From `serverless-chat/` run `sam validate --lint`, `sam build`, and `sam deploy --guided`. Use a random room key with at least 24 characters. Handle the guided deployment configuration as confidential because SAM may persist entered parameters. Keep the key out of version control and screenshots. The shared key limits access to this demo room. Keep API request logging free of query strings that contain the key.

Open `index.html` in two browser windows. Enter the stack's WebSocket output, the shared room key, and different names. Send a message in each direction, confirm both browsers receive it immediately, and confirm DynamoDB stores both message records. Try a wrong key and confirm the connection is rejected.

## Submission and cleanup

Publish the source and sanitized verification evidence on GitHub or LinkedIn. Keep the offer letter out of the public repository and attach it only to the private project-verification email. Once Codec verifies the submission, use the course certificate request page.

After verification, use `sam delete` for any stack you no longer need. The file-storage bucket must have all test objects, versions and delete markers removed before deleting its stack. Save any evidence you need before cleanup.
