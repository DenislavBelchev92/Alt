#!/bin/bash
# Simple PostgreSQL Django Tables Reset Script
# Deletes all Django-related tables that can be safely recreated
# Usage: ./reset_db.sh

set -e  # Exit on any error

echo "🗑️ PostgreSQL Django Reset"
echo "=========================="

# Load environment variables from .env file
# NOT SURE IF NEEDED!!!!
if [[ -f ".env" ]]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if we have the DATABASE_URL
if [[ -z "$DATABASE_URL" ]]; then
    echo "❌ ERROR: DATABASE_URL not found"
    echo "Expected in .env file: DATABASE_URL=postgres://user:password@host:port/database"
    exit 1
fi

echo "Database: $DATABASE_URL"
echo ""
read -p "⚠️  Delete ALL Django tables? This will wipe all data (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🗑️ Dropping all Django tables..."
    
    # Generate and execute DROP commands for all user tables
    psql "$DATABASE_URL" -c "
    DO \$\$ 
    DECLARE 
        table_record RECORD;
    BEGIN 
        FOR table_record IN 
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        LOOP 
            EXECUTE 'DROP TABLE IF EXISTS \"' || table_record.tablename || '\" CASCADE;';
        END LOOP; 
    END \$\$;
    "
    
    echo "✅ All tables dropped!"
    
    # Check if we're in Django project directory
    if [[ -f "manage.py" ]]; then
        echo "🔄 Recreating Django structure..."
        
        # Activate venv if available
        if [[ -f "../venv/bin/activate" ]]; then
            source ../venv/bin/activate
        fi
        
        # Recreate database structure
        python manage.py migrate
        
        # Load skills if command exists
        if python manage.py help load_skills &>/dev/null; then
            echo "📥 Loading skills from YAML..."
            python manage.py load_skills
        fi
        
        echo ""
        echo "✅ Database reset complete!"
        echo "💡 Create admin user: python manage.py createsuperuser"
        
    else
        echo "⚠️ manage.py not found - please run migrations manually"
    fi
    
else
    echo "❌ Operation cancelled"
fi