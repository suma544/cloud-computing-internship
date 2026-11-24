# AWS deployment verification

Both CloudFormation stacks reached CREATE_COMPLETE in ap-southeast-2 on 24 November 2026. This page records the live checks performed after the deployment guide was prepared.

| Project | Live result |
| --- | --- |
| File storage | The HTTP API returned 401 for an unauthenticated request. Amazon S3 reported versioning enabled. The full signed-in upload and sharing flow is pending. |
| Serverless chat | Two independent WebSocket clients connected, each sent a message, and each received both messages. |
