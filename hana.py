from hdbcli import dbapi
import param

class hdb:

    def __init__(self):
        # Connect to HANA
        self.conn = dbapi.connect(param.hana_ip, 39015, 'DEVELOPER', param.hana_passwd)
        self.conn.setautocommit(False)

    def table_update(self, db_data):
        # Update message table
        cursor = self.conn.cursor()

        sql_update = 'upsert "DEVELOPER"."ED.EXAMPLE::DD.BOT01" ' \
                     'values(?, ?, ?, ?, ?, ?) where CHATID = (?) and MESID = (?) and CHANNEL = (?)'

        cursor.execute(sql_update, (db_data['chat_id'], db_data['message_id'], db_data['channel_id'], db_data['user_name'] , db_data['time_stmp'],
                                    db_data['message_text'], db_data['chat_id'], db_data['message_id'], db_data['channel_id']))

        self.conn.commit()

        cursor.close()

    def get_statistics(self):
        # Get voting result
        cursor = self.conn.cursor()

        sql_select = 'select "MESS", COUNT(*)\
                      from "DEVELOPER"."ED.EXAMPLE::DD.BOT01"\
                      where "MESS" in (\'Great\', \'Not bad\', \'So so\')\
                      group by "MESS"\
                      order by "MESS"'

        cursor.execute(sql_select)
        data = cursor.fetchall()
        cursor.close()
        return data

    def get_data(self):
        # Get all table content
        cursor = self.conn.cursor()

        sql_select = 'select * ' \
                     'from "DEVELOPER"."ED.EXAMPLE::DD.BOT01"'
        cursor.execute(sql_select)
        data = cursor.fetchall()
        cursor.close()
        return data