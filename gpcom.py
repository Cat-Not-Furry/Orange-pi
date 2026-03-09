import serial
import time

def crear_lista(cadena):
	lista = cadena.split('\r\n')
	return lista

latitud=''
longitud=''
altitud=''
lora_band = "915000000"
lora_network = '6'
lora_address = '1'
lora_Rx_address = '0'

while True:
	port='/dev/ttyS3'
	ser=serial.Serial(port,baudrate=38400,timeout=0.4)
	serl=serial.Serial('/dev/ttyS5',115200,timeout=0.01)
	serl.flush()
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
#		if serl.isOpen():
#			r = enviar_datos('AT+BAND='+lora_band)
#			print(r)
#			r = enviar_datos('AT+ADDRESS='+lora_address)
#			print(r)
#			r = enviar_datos('AT+NETWORKID='+lora_network)
#			print(r)
			r = enviar_datos('AT+PARAMETER=7,7,1,4')
#			print(r)
			lora_wrd=latitud+' '+longitud+' '+altitud
			lora_msg='AT+SEND='+lora_Rx_address+','+str(len(lora_wrd))+','+str(lora_wrd)+'\r\n'
			serl.write(str(lora_msg).encode())
			print('Enviado')
		ser.close()
		serl.close()
	except Exception as ex:
		print(ex)
