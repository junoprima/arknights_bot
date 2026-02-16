#!/bin/bash

# miHoYo Bot Deployment Script - SQLite Version
# Optimized for 1GB RAM DigitalOcean servers

set -e

echo "🚀 miHoYo Bot Deployment Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running on supported system
check_system() {
    print_step "Checking system requirements..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check available memory
    TOTAL_MEM=$(free -m | awk 'NR==2{printf "%d", $2}')
    if [ "$TOTAL_MEM" -lt 512 ]; then
        print_warning "Low memory detected ($TOTAL_MEM MB). Consider upgrading your server."
    else
        print_status "System memory: $TOTAL_MEM MB"
    fi

    print_status "System requirements check passed"
}

# Setup environment file
setup_environment() {
    print_step "Setting up environment configuration..."

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_status "Created .env file from example"
        else
            print_error ".env.example file not found"
            exit 1
        fi
    else
        print_status ".env file already exists"
    fi

    # Check for required environment variables
    if ! grep -q "DISCORD_BOT_TOKEN=" .env || grep -q "your_discord_bot_token_here" .env; then
        print_warning "Please configure DISCORD_BOT_TOKEN in .env file"
        echo "You can get your bot token from: https://discord.com/developers/applications"
    fi

    # Generate encryption key if not set
    if ! grep -q "ENCRYPTION_KEY=" .env || grep -q "your_fernet_encryption_key_here" .env; then
        print_step "Generating encryption key..."
        ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
        if [ -n "$ENCRYPTION_KEY" ]; then
            sed -i "s/your_fernet_encryption_key_here/$ENCRYPTION_KEY/" .env
            print_status "Encryption key generated and set"
        else
            print_warning "Could not generate encryption key automatically. Please set ENCRYPTION_KEY manually."
        fi
    fi
}

# Create necessary directories
create_directories() {
    print_step "Creating necessary directories..."

    mkdir -p data logs backups
    chmod 755 data logs backups

    print_status "Directories created successfully"
}

# Run migration if needed
run_migration() {
    print_step "Checking for Firebase migration..."

    if [ -f "firebase_key.json" ] && [ -f "utils/firestore.py" ]; then
        echo "Firebase configuration detected. Would you like to migrate data? (y/n)"
        read -r MIGRATE_CHOICE

        if [ "$MIGRATE_CHOICE" = "y" ] || [ "$MIGRATE_CHOICE" = "Y" ]; then
            print_status "Running Firebase to SQLite migration..."
            python3 database/migration.py

            if [ $? -eq 0 ]; then
                print_status "Migration completed successfully"
            else
                print_error "Migration failed. Please check logs."
                exit 1
            fi
        else
            print_status "Skipping migration"
        fi
    else
        print_status "No Firebase configuration found - fresh installation"
    fi
}

# Build and deploy containers
deploy_containers() {
    print_step "Building and deploying containers..."

    # Stop existing containers
    docker-compose -f docker-compose.new.yml down --remove-orphans 2>/dev/null || true

    # Build new images
    print_status "Building Docker images..."
    docker-compose -f docker-compose.new.yml build --no-cache

    # Start containers
    print_status "Starting containers..."
    docker-compose -f docker-compose.new.yml up -d

    # Wait for services to be ready
    print_status "Waiting for services to start..."
    sleep 10

    # Check container health
    BOT_STATUS=$(docker-compose -f docker-compose.new.yml ps bot | grep -c "Up" || echo "0")
    SCHEDULER_STATUS=$(docker-compose -f docker-compose.new.yml ps scheduler | grep -c "Up" || echo "0")

    if [ "$BOT_STATUS" -eq 1 ] && [ "$SCHEDULER_STATUS" -eq 1 ]; then
        print_status "All containers are running successfully"
    else
        print_error "Some containers failed to start. Check logs with: docker-compose -f docker-compose.new.yml logs"
        exit 1
    fi
}

# Setup database admin interface (optional)
setup_admin_interface() {
    echo "Would you like to enable the database admin interface? (y/n)"
    read -r ADMIN_CHOICE

    if [ "$ADMIN_CHOICE" = "y" ] || [ "$ADMIN_CHOICE" = "Y" ]; then
        print_step "Setting up database admin interface..."
        docker-compose -f docker-compose.new.yml --profile admin up -d db_admin
        print_status "Database admin interface available at: http://your-server-ip:8080"
        print_warning "Remember to secure this interface in production!"
    fi
}

# Display deployment information
show_deployment_info() {
    print_step "Deployment completed successfully! 🎉"
    echo ""
    echo "=================================="
    echo "📋 DEPLOYMENT SUMMARY"
    echo "=================================="
    echo "🤖 Bot Status: Running"
    echo "⏰ Scheduler Status: Running"
    echo "💾 Database: SQLite (/app/data/mihoyo_bot.db)"
    echo "📁 Data Directory: ./data"
    echo "📄 Logs Directory: ./logs"
    echo ""
    echo "🔧 USEFUL COMMANDS:"
    echo "View logs: docker-compose -f docker-compose.new.yml logs -f"
    echo "Restart bot: docker-compose -f docker-compose.new.yml restart bot"
    echo "View containers: docker-compose -f docker-compose.new.yml ps"
    echo "Stop all: docker-compose -f docker-compose.new.yml down"
    echo ""
    echo "🎮 NEXT STEPS:"
    echo "1. Add your bot to Discord servers"
    echo "2. Use /add_cookie to add game accounts"
    echo "3. Set up webhooks with /setup_webhook (optional)"
    echo "4. Monitor logs for daily check-ins"
    echo ""
    echo "📚 For support, visit: https://github.com/junoprima/miHoYo_bot"
}

# Main deployment flow
main() {
    echo "Starting deployment process..."
    echo ""

    check_system
    setup_environment
    create_directories
    run_migration
    deploy_containers
    setup_admin_interface
    show_deployment_info

    print_status "Deployment completed successfully! 🚀"
}

# Run main function
main "$@"