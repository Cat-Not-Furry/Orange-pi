import serial

def crear_lista(cadena):
	lista = cadena.split('\r\n')
	return lista

#Variables que se van a ocupar
altitud = ''
latitud = ''
longitud = ''
infor = ''
def leer_datos_gps():
	global altitud,latitud,longitud,infor

	port ='/dev/ttyS3'
	ser = serial.Serial(port,baudrate=38400,timeout=0.5)

	try:
		newdata = ser.read(400).decode('utf-8').strip()
		msg = crear_lista(str(newdata))
		newmsg = str(msg[2]).split(",")

		if '$GNGGA' in newmsg and len(newmsg) == 15:
			latitud= newmsg[2]
			longitud=newmsg[4]
			altitud=newmsg[9]
			infor=':'+latitud+':'+longitud+':'+altitud
			print(infor)
			print('--------------')
#			print(len(infor))
		ser.close()
	except Exception as ex:
		print(ex)

leer_datos_gps()
