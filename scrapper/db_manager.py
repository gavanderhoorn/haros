import extractor
import db_control as dbc
import db_extract as dbe
import json_exp_db as j_exp


class DbManager:
    def __init__(self):
        self.con = None
        self.cur = None
        self.db = None
        self.user = None
        self.passwd = None
        self.host = None
        self.port = None

    def connect(self, db_user_file):
        self._loadUser(db_user_file)
        con, cur = dbc.conCur(user = self.user, passwd = self.passwd,
                db = self.db, host = self.host, port = self.port)
        self.passwd = None
        self.con = con
        self.cur = cur

    def disconnect(self):
        self.db = None
        self.host = None
        self.port = None
        self.user = None
        self.cur.close()
        self.cur = None
        self.con.close()
        self.con = None

    def insert(self, table, cols, data, truncate = False):
        dbc.insertRecords(self.con, self.cur,
                table, cols, data, truncate = truncate)

    def updateTable(self, table, cols, types, data = None,
                    pk = None, fk = None, fk_ref = None):
        dbc.upTruncTable(self.con, self.cur, table,
                cols, types, data,
                pk = pk, fk = fk, fk_ref = fk_ref)

    def get(self, table, cols):
        return dbe.getTable(self.cur, table, cols)

    def getNextId(self, table):
        return dbe.getMaxVal(self.cur, table, "id") + 1

    def truncate(self, table):
        dbc.safeTruncateTable(self.cur, table)
        self.con.commit()


    def _loadUser(self, db_user_file):
        lines = [line.strip() for line in open(db_user_file)]
        self.user = lines[0]
        self.passwd = lines[1]
        self.db = lines[2]
        self.host = lines[3]
        self.port = int(lines[4])

