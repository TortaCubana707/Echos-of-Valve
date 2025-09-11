import os 
from dotenv import load_dotenv
 
class AppConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    MYSQL_HOST = os.environ.get("MySQL_HOST")
    MYSQL_USER= os.environ.get("MYSQL_USER")
    MYSQL_PASSWORD= os.environ.get("MYSQL_PASSWORD")
    MYSQL_DB= os.environ.get("MYSQL_DB")