#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="odoo"
SERVICE_NAME="odoo"
DATASYNC_TASK_ARN="arn:aws:datasync:us-east-1:021776651623:task/task-0d29d2cc314dbf6fa"
S3_BUCKET="odoo-odoo-custom-121312"
CLOUDFRONT_DOMAIN="d290mq7kqg95wg.cloudfront.net"
ODOO_DB="odoo"

# Function to print step information
print_step() {
    echo -e "\n${YELLOW}==== $1 ====${NC}"
}

# Function to check if command was successful
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Success${NC}"
    else
        echo -e "${RED}✗ Failed${NC}"
        exit 1
    fi
}

# Check if a module name was provided
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}Usage: $0 <module_name>${NC}"
    echo -e "Example: $0 lead_pool"
    exit 1
fi

MODULE_NAME=$1

# Step 1: Check if module exists in S3
print_step "Checking if module exists in S3"
aws s3 ls s3://${S3_BUCKET}/modules/${MODULE_NAME}/ --recursive
if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Module ${MODULE_NAME} not found in S3 bucket${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Module ${MODULE_NAME} found in S3${NC}"
fi

# Step 2: Start DataSync task
print_step "Starting DataSync to copy module files to EFS"
EXECUTION_ARN=$(aws datasync start-task-execution --task-arn ${DATASYNC_TASK_ARN} --query 'TaskExecutionArn' --output text)
check_success
echo "DataSync execution ARN: ${EXECUTION_ARN}"

# Step 3: Wait for DataSync to complete
print_step "Waiting for DataSync task to complete"
STATUS="LAUNCHING"
while [ "$STATUS" != "SUCCESS" ] && [ "$STATUS" != "ERROR" ]; do
    echo "DataSync status: $STATUS"
    sleep 10
    STATUS=$(aws datasync describe-task-execution --task-execution-arn ${EXECUTION_ARN} --query 'Status' --output text)
    if [ "$STATUS" == "ERROR" ]; then
        echo -e "${RED}✗ DataSync task failed${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✓ DataSync completed successfully${NC}"

# Step 4: Force new deployment of the ECS service
print_step "Restarting Odoo service to pick up new module"
aws ecs update-service --cluster ${CLUSTER_NAME} --service ${SERVICE_NAME} --force-new-deployment >/dev/null
check_success

# Step 5: Wait for ECS service to stabilize
print_step "Waiting for ECS service to stabilize"
aws ecs wait services-stable --cluster ${CLUSTER_NAME} --services ${SERVICE_NAME}
check_success

# Step 6: Provide instructions for updating app list in Odoo
print_step "Next steps"
echo -e "1. Wait 1-2 minutes for Odoo to fully start"
echo -e "2. Log in to Odoo at https://${CLOUDFRONT_DOMAIN} with your credentials"
echo -e "3. Go to Apps menu"
echo -e "4. Remove the 'Apps' filter"
echo -e "5. Click on 'Update Apps List' in the top menu"
echo -e "6. Search for '${MODULE_NAME}'"
echo -e "7. Install the module"

echo -e "\n${GREEN}Script completed successfully!${NC}"
echo -e "Your module ${MODULE_NAME} should now be available in Odoo." 