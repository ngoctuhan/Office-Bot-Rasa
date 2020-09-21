import json
import mysql.connector as mysql_db

from config import *


class DAOUser:
    def __init__(self):
        return
        # with open(PATH_CONFIG, "r") as file_config:
        #     config = json.load(file_config).get("database")
        #     self.connect_infor = mysql_db.connect(host=config.get("host"), username=config.get("username"),
        #                                           password=config.get("password"),
        #                                           db=config.get("db"),
        #                                           port=config.get("port"))
        
        # self.connect_infor.autocommit = True
        # with open(PATH_CONFIG_USER_INFO, "r") as file_slot:
        #     self.reader_config_slots = json.load(file_slot)

    def get(self, sender_id):
        return {}
        # list_slots = [key for key in self.reader_config_slots]
        # answer = {}
        # keyword = ",".join(list_slots)
        # if len(list_slots) > 0:
        #     self.connect_infor.ping(reconnect=True)
        #     mycursor = self.connect_infor.cursor()

        #     sql = f"SELECT {keyword} FROM "
        #     sql += "informuser" + " WHERE id_conversation like %s"

        #     mycursor.execute(sql, [sender_id])
        #     myresult = mycursor.fetchall()
        #     if myresult is not None and len(myresult) > 0:
        #         for x in myresult:
        #             for i, name in enumerate(list_slots):
        #                 answer[name] = x[i]
        #     else :
        #         answer = self.reader_config_slots
        #     mycursor.close()
        # return answer