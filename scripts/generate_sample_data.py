# scripts/generate_sample_data.py - Complete Data Generation with All Months

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import random
import os

def create_comprehensive_sample_data():
    """Create comprehensive sample data with all months including September"""
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect('data/app.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS billing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_month TEXT NOT NULL,
        account_id TEXT NOT NULL,
        subscription TEXT NOT NULL,
        service TEXT NOT NULL,
        resource_group TEXT NOT NULL,
        resource_id TEXT NOT NULL,
        region TEXT NOT NULL,
        usage_qty REAL NOT NULL,
        unit_cost REAL NOT NULL,
        cost REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_id TEXT UNIQUE NOT NULL,
        owner TEXT,
        env TEXT,
        tags_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Clear existing data
    cursor.execute('DELETE FROM billing')
    cursor.execute('DELETE FROM resources')
    
    # Generate data for 6 months: May 2024 to October 2024 (including September!)
    months = ['2024-05', '2024-06', '2024-07', '2024-08', '2024-09', '2024-10']
    
    # Define services and their characteristics
    services = {
        'Compute': {'base_cost': 45000, 'variability': 0.3},
        'Storage': {'base_cost': 25000, 'variability': 0.2}, 
        'Database': {'base_cost': 20000, 'variability': 0.25},
        'Networking': {'base_cost': 15000, 'variability': 0.4},
        'AI/ML': {'base_cost': 18000, 'variability': 0.5},
        'Security': {'base_cost': 8000, 'variability': 0.15},
        'Monitoring': {'base_cost': 12000, 'variability': 0.2},
        'Analytics': {'base_cost': 22000, 'variability': 0.35}
    }
    
    # Resource groups
    resource_groups = [
        'prod-app-rg', 'prod-web-rg', 'staging-rg', 'dev-rg', 'analytics-rg', 
        'shared-services-rg', 'security-rg', 'monitoring-rg', 'ml-platform-rg',
        'data-pipeline-rg', 'backup-rg', 'network-rg'
    ]
    
    # Regions
    regions = ['East US', 'West US 2', 'Central US', 'West Europe', 'Southeast Asia', 'UK South']
    
    # Accounts and subscriptions
    accounts = ['acc-prod-001', 'acc-dev-002', 'acc-analytics-003']
    subscriptions = ['sub-main-prod', 'sub-dev-test', 'sub-analytics', 'sub-shared']
    
    print("🔄 Generating comprehensive sample data...")
    
    billing_records = []
    all_resource_ids = set()
    
    # Generate data for each month
    for month_idx, month in enumerate(months):
        print(f"   📅 Generating data for {month}")
        
        # Create growth/decline trend
        if month == '2024-05':  # May - baseline
            growth_factor = 1.0
        elif month == '2024-06':  # June - slight increase
            growth_factor = 1.15
        elif month == '2024-07':  # July - peak
            growth_factor = 1.35
        elif month == '2024-08':  # August - decrease (mentioned in user's data)
            growth_factor = 0.85
        elif month == '2024-09':  # September - recovery/increase
            growth_factor = 1.25
        elif month == '2024-10':  # October - continued growth
            growth_factor = 1.40
        
        month_records = []
        
        # Generate records for each service
        for service, service_config in services.items():
            base_monthly_cost = service_config['base_cost'] * growth_factor
            variability = service_config['variability']
            
            # Number of resources for this service (with some variation)
            num_resources = random.randint(15, 45)
            
            for i in range(num_resources):
                # Generate resource details
                resource_group = random.choice(resource_groups)
                region = random.choice(regions)
                account = random.choice(accounts)
                subscription = random.choice(subscriptions)
                
                # Create unique resource ID
                resource_id = f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/Microsoft.{service.replace('/', '')}/{service.lower()}-{month}-{i:03d}"
                all_resource_ids.add(resource_id)
                
                # Calculate cost with some randomness
                resource_cost = (base_monthly_cost / num_resources) * (1 + random.uniform(-variability, variability))
                resource_cost = max(resource_cost, 1.0)  # Minimum $1
                
                # Generate usage quantity and unit cost
                usage_qty = random.uniform(1, 1000)
                unit_cost = resource_cost / usage_qty
                
                # Create multiple billing records per resource (daily/weekly billing)
                records_per_month = random.randint(4, 30)
                for record_idx in range(records_per_month):
                    daily_cost = resource_cost / records_per_month
                    daily_usage = usage_qty / records_per_month
                    
                    billing_record = (
                        month,
                        account,
                        subscription,
                        service,
                        resource_group,
                        resource_id,
                        region,
                        daily_usage,
                        unit_cost,
                        daily_cost
                    )
                    
                    month_records.append(billing_record)
        
        billing_records.extend(month_records)
        print(f"      ✅ Generated {len(month_records)} billing records")
    
    # Insert billing records in batches
    print(f"💾 Inserting {len(billing_records)} billing records...")
    cursor.executemany('''
        INSERT INTO billing (invoice_month, account_id, subscription, service, resource_group, 
                           resource_id, region, usage_qty, unit_cost, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', billing_records)
    
    # Generate resource metadata
    print("🏷️ Generating resource metadata...")
    resource_records = []
    
    owners = [
        'john.doe@company.com', 'jane.smith@company.com', 'mike.johnson@company.com',
        'sarah.wilson@company.com', 'david.brown@company.com', 'lisa.davis@company.com',
        '', '', ''  # Some resources without owners (for tagging gap analysis)
    ]
    
    environments = ['prod', 'staging', 'dev', 'test', '']
    
    for resource_id in list(all_resource_ids):
        owner = random.choice(owners)
        env = random.choice(environments)
        
        # Create tags JSON
        tags = {}
        if owner:
            tags['owner'] = owner
        if env:
            tags['environment'] = env
        if random.choice([True, False]):
            tags['project'] = random.choice(['webapp', 'analytics', 'ml-platform', 'data-pipeline'])
        if random.choice([True, False]):
            tags['cost-center'] = random.choice(['engineering', 'data-science', 'operations', 'security'])
        
        resource_record = (
            resource_id,
            owner,
            env,
            json.dumps(tags) if tags else '{}'
        )
        resource_records.append(resource_record)
    
    cursor.executemany('''
        INSERT INTO resources (resource_id, owner, env, tags_json)
        VALUES (?, ?, ?, ?)
    ''', resource_records)
    
    # Commit and verify data
    conn.commit()
    
    # Verify data was created
    cursor.execute('SELECT COUNT(*) FROM billing')
    billing_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM resources')
    resource_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT DISTINCT invoice_month FROM billing ORDER BY invoice_month')
    months_in_db = [row[0] for row in cursor.fetchall()]
    
    cursor.execute('''
        SELECT invoice_month, SUM(cost) as total_cost 
        FROM billing 
        GROUP BY invoice_month 
        ORDER BY invoice_month
    ''')
    monthly_totals = cursor.fetchall()
    
    conn.close()
    
    print(f"\n✅ Sample data generation completed!")
    print(f"   📊 Billing records: {billing_count:,}")
    print(f"   🏷️ Resource records: {resource_count:,}")
    print(f"   📅 Months available: {', '.join(months_in_db)}")
    print(f"\n💰 Monthly cost totals:")
    for month, total in monthly_totals:
        print(f"   {month}: ${total:,.2f}")
    
    return True

if __name__ == "__main__":
    create_comprehensive_sample_data()
