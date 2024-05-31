import cx_Oracle
import main


oracle_user = 'abertura_os'
oracle_password = 'Dti*dec*++os@'
oracle_dsn = '10.222.0.17:1521/medbd.set.edu.br'

try:
    connection = cx_Oracle.connect(oracle_user, oracle_password, oracle_dsn)
    print("Conexão ao banco de dados Oracle bem-sucedida!")
    connection.close()
except cx_Oracle.Error as error:
    print(f"Erro ao conectar ao banco de dados Oracle: {error}")