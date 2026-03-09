import serial

def crear_lista(cadena):
	lista = cadena.split('\r\n')
	return lista

latitud=''
longitud=''
altitud=''

while True:
	port='/dev/ttyS3'
	ser=serial.Serial(port,baudrate=38400,timeout=0.5)
	try:
		newdata=ser.read(400).decode('utf-8').strip()
		msg=crear_lista(str(newdata))
		newmsg= str(msg[2]).split(",")
	except Exception as e:
		print(e)
	
	try:
		if "$GNGGA" in newmsg and len(newmsg) == 15:
			print(f"LATITUD: {newmsg[2]}")
			print(f"LONGITUD: {newmsg[4]}")
			print(f"ALTITUD: {newmsg[9]}")
			latitud = newmsg[2]
			longitud = newmsg[4]
			altitud = newmsg[9]

		ser.close()
	except Exception as ex:
		print(ex)
