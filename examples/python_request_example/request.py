import requests
r = requests.get("http://localhost:5000")

print (r.json()["msg"])
print (r.json()["date"])

