import asyncio
import serial
from serial_asyncio import open_serial_connection

latitud = ''
longitud = ''
altitud = ''

async def read_serial(reader):
	while True:
		try:
			newdata = (await reader.readline()).decode('utf-8').strip()
			if newdata:
				msg = newdata.split('\r\n')
				newmsg = str(msg[0]).split(",")
				if '$GNGGA' in newmsg and len(newmsg) == 15:
					#print(f'LATITUD: {newmsg[2]}')
					#print(f'LONGITUD: {newmsg[4]}')
					#print(f'ALTITUD: {newmsg[9]}')
					latitud = newmsg[2]
					longitud = newmsg[4]
					altitud = newmsg[9]
					await send_lora(latitud,longitud,altitud)
		except Exception as ex:
			print(ex)

async def send_lora(latitud,longitud,altitud):
	lora_wrd=latitud+':'+longitud+':'+altitud
	lora_msg=f'AT+SEND='+lora_Rx_address+','+str(len(lora_wrd))+','+lora_wrd+'\r\n'
	with serl as serlora:
		serlora.write(lora_msg.encode())
		await asyncio.sleep(0.01)

async def main():
	global serl
	serl = serial.Serial('/dev/ttyS5',115200,timeout=0.01)
	serl.flush()
	serl.write((f'AT+PARAMETER=7,7,1,4\r\n').encode())
	await asyncio.sleep(0.01)
	reader, writer = await open_serial_connection(url='/dev/ttyS3',baudrate=38400,timeout=0.01)
	task = [ asyncio.create_task(read_serial(reader)), asyncio.create_task(send_lora(latitud,longitud,altitud))]
	await asyncio.gather(*task)

if __name__ == '__main__':
	lora_band = '915000000'
	lora_network = '6'
	lora_address = '1'
	lora_Rx_address = '0'
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print('Interrupted')
	finally:
		serl.close()
