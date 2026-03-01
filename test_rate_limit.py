import urllib.request
import traceback

def test_rate_limit():
    success_count = 0
    refused_count = 0
    url = "http://localhost:5000/api/queue"
    
    print("Sending 105 requests to", url)
    for i in range(105):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            if response.getcode() == 200:
                success_count += 1
        except urllib.error.HTTPError as e:
            if e.code == 429:
                refused_count += 1
            else:
                print(f"Other HTTP error: {e.code}")
        except Exception as e:
            print(f"Error on request {i}: {e}")
            
    print(f"Successful requests: {success_count}")
    print(f"Rate limited (429) requests: {refused_count}")

if __name__ == '__main__':
    test_rate_limit()
