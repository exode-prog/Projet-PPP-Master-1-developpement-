import json

def handler(event, context):
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Fonction Lambda MCP via LocalStack",
            "note": "Demonstration du cycle de vie ephemere serverless (Sprint 5)"
        })
    }
