from pymongo import MongoClient

client = MongoClient('mongodb+srv://habiba:habiba@cluster0.ln5tz.mongodb.net/?retryWrites=true&w=majority') 
db = client['RecommandationSystem']