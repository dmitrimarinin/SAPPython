from pyrfc import Connection
import param

class nw:

    def __init__(self):
        # Connect to Netweaver
        self.conn = Connection(ashost=param.bw_ip, sysnr='00', client='001', user='BWDEVELOPER', passwd=param.bw_passwd)

    def dso_update(self, data):
        # Update DSO
        self.conn.call('Z_UPDATE_BOT_DSO', I_TABLE=data)

    def get_data(self):
        # Get DSO data
        result = self.conn.call('RFC_READ_TABLE', QUERY_TABLE=u'/BIC/AZBOT0100', DELIMITER=u';')
        data = result.get('DATA')
        return data