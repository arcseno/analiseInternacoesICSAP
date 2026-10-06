from ftplib import FTP

ftp = FTP('ftp.datasus.gov.br', timeout=60)
ftp.login()
ftp.cwd('/dissemin/publicos/SIHSUS/200801_/Dados/')
todos = ftp.nlst()

print('2022-05:', 'RDPR2205.dbc' in todos)
print('2022-06:', 'RDPR2206.dbc' in todos)
print('2023-07:', 'RDPR2307.dbc' in todos)
print('2024-08:', 'RDPR2408.dbc' in todos)
print('2025-10:', 'RDPR2510.dbc' in todos)
print('2026-01:', 'RDPR2601.dbc' in todos)
print('2026-02:', 'RDPR2602.dbc' in todos)

ftp.quit()