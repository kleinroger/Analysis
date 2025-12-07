from app import create_app, db
from app.models import SourceBinding, CrawlRule
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    columns = inspector.get_columns('source_bindings')
    col_names = [c['name'] for c in columns]
    print(f"SourceBinding columns: {col_names}")
    
    if 'source_domain' in col_names:
        print("Verification Passed: source_domain field exists.")
    else:
        print("Verification Failed: source_domain field missing.")
        
    # Check constraints
    # specific checking of constraints via alchemy inspector can be complex depending on driver, 
    # but we can check if we can insert duplicates
    
    try:
        # Clean up
        SourceBinding.query.delete()
        CrawlRule.query.delete()
        db.session.commit()
        
        # Create a rule
        rule = CrawlRule(site_name="TestSite", domain="test.com")
        db.session.add(rule)
        db.session.commit()
        
        # Create binding
        b1 = SourceBinding(source_name="TestSite", source_domain="test.com", rule_id=rule.id)
        db.session.add(b1)
        db.session.commit()
        print("Created first binding.")
        
        # Try create duplicate binding
        try:
            b2 = SourceBinding(source_name="TestSite", source_domain="test.com", rule_id=rule.id)
            db.session.add(b2)
            db.session.commit()
            print("Verification Failed: Duplicate binding allowed.")
        except Exception as e:
            db.session.rollback()
            print(f"Verification Passed: Duplicate binding prevented. Error: {e}")
            
        # Try create same source different domain
        try:
            b3 = SourceBinding(source_name="TestSite", source_domain="other.com", rule_id=rule.id)
            db.session.add(b3)
            db.session.commit()
            print("Verification Passed: Same source different domain allowed.")
        except Exception as e:
            print(f"Verification Failed: Same source different domain prevented. Error: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")
