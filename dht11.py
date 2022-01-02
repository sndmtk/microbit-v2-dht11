# Add your Python code here. E.g.
from microbit import *
import time

DEGREES = u'\xb0'

class DHT11:
    def __init__(self, pin):
        self.pin = pin
        self.temp = -1
        self.humid = -1
              
    def read(self):
        pin2bit = self._pin2bit()
        buffer_ = bytearray(320)
        length = (len(buffer_) // 4) * 4

        for i in range(length, len(buffer_)):
            buffer_[i] = 1

        self._set_write_config(pin2bit * 4)
        self._block_irq()

        self._write_digital_high(1 << pin2bit)
        time.sleep_ms(50)

        self._write_digital_low(1 << pin2bit)
        time.sleep_ms(20)
        
        self._set_read_config(pin2bit * 4)
        self._grab_bits(pin2bit, buffer_, length)
        self._unblock_irq()
        
        data = self._parse_data(buffer_)
        
        del buffer_
        
        if data is None or len(data) != 40:
            if data is None:
                bits = 0
            else:
                bits = len(data)
            print("Too many or too few bits " + str(bits))
            return
            
        data = self._calc_bytes(data)

        checksum = self._calc_checksum(data)
        if data[4] != checksum:
            print("Checksum invalid.")
            return

        self.temp=data[2] + (data[3] / 10)
        self.humid=data[0] + (data[1] / 10)
        
    def _pin2bit(self):
        # this is a dictionary, microbit.pinX can't be a __hash__
        pin = self.pin
        if pin == pin0:
            shift = 2
        elif pin == pin1:
            shift = 3
        elif pin == pin2:
            shift = 4
        elif pin == pin5:
            shift = 14
        elif pin == pin8:
            shift = 10
        elif pin == pin9:
            shift = 9
        elif pin == pin11:
            shift = 23
        elif pin == pin12:
            shift = 12
        elif pin == pin13:
            shift = 17
        elif pin == pin14:
            shift = 1
        elif pin == pin15:
            shift = 13
        else:
            raise ValueError('function not suitable for this pin')

        return shift
        
    @staticmethod
    @micropython.asm_thumb
    def _set_write_config(r0):
        mov(r1, 0x50)      # r3=0x50
        lsl(r1, r1, 16)    # r3=0x500000
        add(r1, 0x07)      # r3=0x500007
        lsl(r1, r1, 8)     # r3=0x50000700 -- this points to GPIO CNF registers
        add(r1, r1, r0)
        mov(r0, 0b0001)
        str(r0, [r1, 0])

    @staticmethod
    @micropython.asm_thumb
    def _set_read_config(r0):
        mov(r1, 0x50)      # r3=0x50
        lsl(r1, r1, 16)    # r3=0x500000
        add(r1, 0x07)      # r3=0x500007
        lsl(r1, r1, 8)     # r3=0x50000700 -- this points to GPIO CNF registers
        add(r1, r1, r0)
        mov(r0, 0b1100)
        str(r0, [r1, 0])
    
    @staticmethod
    @micropython.asm_thumb
    def _write_digital_high(r0):
        mov(r1, 0x50)      # r3=0x50
        lsl(r1, r1, 16)    # r3=0x500000
        add(r1, 0x05)      # r3=0x500005
        lsl(r1, r1, 8)     # r3=0x50000500 -- this points to GPIO registers
        add(r1, 0x08)      # r3=0x50000508 -- this points to GPIO OUTSET registers
        str(r0, [r1, 0])
    
    @staticmethod
    @micropython.asm_thumb
    def _write_digital_low(r0):
        mov(r1, 0x50)      # r3=0x50
        lsl(r1, r1, 16)    # r3=0x500000
        add(r1, 0x05)      # r3=0x500005
        lsl(r1, r1, 8)     # r3=0x50000500 -- this points to GPIO registers
        add(r1, 0x0C)      # r3=0x5000050C -- this points to GPIO OUTCLR registers
        str(r0, [r1, 0])
    
    @staticmethod
    @micropython.asm_thumb
    def _block_irq():
        cpsid('i')          # disable interrupts to go really fast

    @staticmethod
    @micropython.asm_thumb
    def _unblock_irq():
        cpsie('i')          # enable interupts nolonger time critical

    # r0 - pin bit id
    # r1 - byte array
    # r2 - len byte array, must be a multiple of 4
    @staticmethod
    @micropython.asm_thumb
    def _grab_bits(r0, r1, r2):
        b(START)
    
        # DELAY routine
        label(DELAY)
        mov(r7, 0xb4)
        label(delay_loop)
        sub(r7, 1)
        bne(delay_loop)
        bx(lr)
    
        label(READ_PIN)
        mov(r3, 0x50)      # r3=0x50
        lsl(r3, r3, 16)    # r3=0x500000
        add(r3, 0x05)      # r3=0x500005
        lsl(r3, r3, 8)     # r3=0x50000500 -- this points to GPIO registers
        add(r3, 0x10)      # r3=0x50000510 -- points to read_digital bits
        ldr(r4, [r3, 0])   # move memory@r3 to r4
        mov(r3, 0x01)      # create bit mask in r3  
        lsr(r4, r0)
        and_(r4, r3)
        bx(lr)
    
        label(START)
        mov(r5, 0x00)      # r5 - byte array index 
        label(again)
        mov(r6, 0x00)      # r6 - current word
        bl(READ_PIN)
        orr(r6,  r4)       # bitwise or the pin into current word
        bl(DELAY)
        bl(READ_PIN)
        lsl(r4, r4, 8)     # move it left 1 byte
        orr(r6,  r4)       # bitwise or the pin into current word
        bl(DELAY)
        bl(READ_PIN)
        lsl(r4, r4, 16)     # move it left 2 bytes
        orr(r6,  r4)       # bitwise or the pin into current word
        bl(DELAY)
        bl(READ_PIN)
        lsl(r4, r4, 24)     # move it left 3 bytes
        orr(r6,  r4)       # bitwise or the pin into current word
        bl(DELAY)
    
        add(r1, r1, r5)   # add the index to the bytearra addres
        str(r6, [r1, 0])  # now 4 have been read store it
        sub(r1, r1, r5)   # reset the address
        add(r5, r5, 4)    # increase array index
        sub(r4, r2, r5)   # r4 - is now beig used to count bytes written
        bne(again)

        label(RETURN)
        mov(r0, r5)       # return number of bytes written

    def _parse_data(self, buffer_):
        # changed initial states, tyey are lost in the change over
        INIT_PULL_DOWN = 1
        INIT_PULL_UP = 2
        DATA_1_PULL_DOWN = 3
        DATA_PULL_UP = 4
        DATA_PULL_DOWN = 5

        #state = INIT_PULL_DOWN
        state = INIT_PULL_UP

        max_bits = 100
        bits = bytearray(max_bits)
        length = 0
        bit_ = 0
        
        for i in range(len(buffer_)):

            current = buffer_[i]
            length += 1

            if state == INIT_PULL_DOWN:
                if current == 0:
                    state = INIT_PULL_UP
                    continue
                else:
                    continue
            if state == INIT_PULL_UP:
                if current == 1:
                    state = DATA_1_PULL_DOWN
                    continue
                else:
                    continue
            if state == DATA_1_PULL_DOWN:
                if current == 0:
                    state = DATA_PULL_UP
                    continue
                else:
                    continue
            if state == DATA_PULL_UP:
                if current == 1:
                    length = 0
                    state = DATA_PULL_DOWN
                    continue
                else:
                    continue
            if state == DATA_PULL_DOWN:
                if current == 0:
                    bits[bit_] = length
                    bit_ += 1
                    state = DATA_PULL_UP
                    continue
                else:
                    continue

            if bit_ >= max_bits:
                break

        if bit_ == 0:
            return None
        
        results = bytearray(bit_)
        for i in range(bit_):
            results[i] = bits[i]
        return results
        
    def _calc_bytes(self, pull_up_lengths):

        shortest = 1000
        longest = 0

        for i in range(0, len(pull_up_lengths)):
            length = pull_up_lengths[i]
            if length < shortest:
                shortest = length
            if length > longest:
                longest = length

        halfway = shortest + (longest - shortest) / 2
        data = bytearray(5)
        did = 0
        byte = 0

        for i in range(len(pull_up_lengths)):
            byte = byte << 1
            
            if pull_up_lengths[i] > halfway:
                byte = byte | 1

            if ((i + 1) % 8 == 0):
                data[did] = byte
                did += 1
                byte = 0
                
        return data

    def _calc_checksum(self, data):
        return data[0] + data[1] + data[2] + data[3] & 0xff
        
        
sensor = DHT11(pin0)
sleep(1000)

while True:
    sensor.read()
    print(sensor.temp, sensor.humid)
    sleep(2000)