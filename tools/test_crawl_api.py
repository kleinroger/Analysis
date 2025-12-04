import requests

def test_crawl():
    # First, login to get a session
    s = requests.Session()
    login_url = "http://127.0.0.1:5000/auth/login"
    # Assuming there is an admin user 'admin' with password 'admin' from previous context or defaults
    # If not, we might need to register one or check the database seeding.
    # Let's try a common default or just create a tool to bypass auth if needed, but better to test fully.
    
    # Try to register a test user first to ensure we can login
    register_url = "http://127.0.0.1:5000/auth/register"
    s.post(register_url, data={'username': 'test_crawler', 'password': 'password', 'role': 'user'})
    
    # Login
    resp = s.post(login_url, data={'username': 'test_crawler', 'password': 'password'})
    if resp.url.endswith('/auth/login'):
         print("Login failed")
         return

    print("Login successful")

    # Now test the crawl API
    crawl_url = "http://127.0.0.1:5000/api/crawl"
    resp = s.get(crawl_url, params={'keyword': '成都'})
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Count: {data.get('count')}")
        if data.get('data'):
            print("First item:", data['data'][0]['title'])
    else:
        print(f"Error: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    test_crawl()
