#!/bin/bash
# Lance LocalStack et (re)crée la fonction Lambda si besoin, puis invoque.
set -e
cd "$(dirname "$0")/.."

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

docker compose -f docker-compose.localstack.yml up -d
sleep 5

if ! awslocal lambda get-function --function-name mcp-lambda-function >/dev/null 2>&1; then
  echo "Creation de la fonction mcp-lambda-function..."
  awslocal lambda create-function \
    --function-name mcp-lambda-function \
    --runtime python3.12 --handler handler.handler \
    --zip-file fileb://localstack-lambda/function.zip \
    --role arn:aws:iam::000000000000:role/lambda-role
  for i in {1..20}; do
    STATE=$(awslocal lambda get-function --function-name mcp-lambda-function --query 'Configuration.State' --output text)
    [ "$STATE" = "Active" ] && break
    sleep 3
  done
fi

echo "Invocation..."
awslocal lambda invoke --function-name mcp-lambda-function /tmp/lambda_output.json
cat /tmp/lambda_output.json
echo ""
