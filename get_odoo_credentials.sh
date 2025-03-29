#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BLUE='\033[0;34m'

# Configuration
CLOUDFRONT_DOMAIN="d290mq7kqg95wg.cloudfront.net"
ODOO_DB="odood"
SECRET_ID="odoo-root-user"

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

# Step 1: Retrieve secret from AWS Secrets Manager
print_step "Retrieving Odoo credentials from AWS Secrets Manager"
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id ${SECRET_ID} --query 'SecretString' --output text)
check_success

# Step 2: Parse JSON to get username and password
USERNAME=$(echo $SECRET_JSON | jq -r '.username')
PASSWORD=$(echo $SECRET_JSON | jq -r '.password')

if [ -z "$USERNAME" ] || [ -z "$PASSWORD" ]; then
    echo -e "${RED}✗ Failed to parse credentials from secret${NC}"
    exit 1
fi

# Step 3: Display credentials
print_step "Odoo Credentials"
echo -e "${BLUE}HOST_URL=${NC}https://${CLOUDFRONT_DOMAIN}"
echo -e "${BLUE}DB_NAME=${NC}${ODOO_DB}"
echo -e "${BLUE}DB_USERNAME=${NC}${USERNAME}"
echo -e "${BLUE}DB_PASSWORD=${NC}${PASSWORD}"

# Step 4: Create a .env file (optional)
if [ "$1" == "--save" ]; then
    print_step "Saving credentials to .env file"
    echo "HOST_URL=https://${CLOUDFRONT_DOMAIN}" > .env.odoo
    echo "DB_NAME=${ODOO_DB}" >> .env.odoo
    echo "DB_USERNAME=${USERNAME}" >> .env.odoo
    echo "DB_PASSWORD=${PASSWORD}" >> .env.odoo
    echo -e "${GREEN}✓ Credentials saved to .env.odoo file${NC}"
    echo -e "You can load these credentials with: source .env.odoo"
fi

echo -e "\n${GREEN}Script completed successfully!${NC}"
echo -e "You can use these credentials to access your Odoo instance." 