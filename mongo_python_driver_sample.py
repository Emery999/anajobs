
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
'''
API key for Anthropic Claude - ADD YOUR KEY HERE
Replace this with your actual Claude API key from https://console.anthropic.com/
Format: sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
'''
# connection string for mongodb compass - ADD YOUR CREDENTIALS HERE
# Replace with your actual MongoDB Atlas connection string
# Format: mongodb+srv://username:password@cluster.xxxxx.mongodb.net/
uri = "mongodb+srv://username:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# IP address for anywhere remote access
# add 0.0.0.0/0 (allow all IPs) 

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)