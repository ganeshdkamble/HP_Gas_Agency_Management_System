import mysql.connector 
from config import *

def get_connection():
    conn = mysql.connector.connect(
        host = HOST,
        user = USER,
        password = PASSWORD,
        database = DATABASE
    )
    return conn 