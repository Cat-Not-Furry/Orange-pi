import asyncio
from serial import Serial
from lora_param import RYLR
import time

async def main(rylr):
	await rylr.init()
	while True:
		# Variables para controlar el tiempo de lectura
		last_time = time.ticks_ms()
		current_time = 0

		dato=666
		trans= "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s" % (str(dato),str(dato),str(dato),str(dato),str(dato),str(dato),str(dato),str(dato),str(dato),str(dato),str(dato),str(dato))
		#print(trans)
		await rylr.send(trans)
		await asyncio.sleep(0.1)

# UART1 para RYLR

uart = Serial(port='/dev/ttyS5',baudrate=115200,timeout=0.5)
uart.write(b'AT+ADDRESS=1\r\n')

#UART2 para GPS
gpsModule = Serial(port='/dev/ttyS3',baudrate=38400,timeout=0.5)


rylr = RYLR(gpsModule, uart)

loop = asyncio.get_event_loop()


# Create RYLR background task
loop.create_task(rylr.loop())


# Create main task
loop.create_task(main(rylr))

# Start IO loop
loop.run_forever()
