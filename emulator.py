import pygame
import io8080
import cpu
import sys
import serial

class Emulator:
    """
    
    Contains 8080 CPU that runs the Sol-20 CONSOL application and uses PyGame to display the 64 x 16 text screen.
    
    """

    TEXT_ADDRESS = 0xCC00
    ROM_ADDRESS = 0xC000
    BLACK = 0x000000
    WHITE = 0xFFFFFF
    GREEN = 0x00FF00
    AMBER = 0xFFBF00
    CAPTION_FORMAT = 'Sol-20 ({})'
    
    

    def __init__(self, path=None):
        self.io = io8080.IO()
        
        if path:
            # Load the default monitor program, normally Solos.
            memory = bytearray(65536)
            with open(path, 'rb') as f:
                memoryBytes = f.read()
                memory[self.ROM_ADDRESS:self.ROM_ADDRESS+len(memoryBytes)] = bytearray(memoryBytes)
            self._cpu = cpu.CPU(memory, self.io)
            self._cpu.init_instruction_table()

        else:
            self._cpu = None

        self._path = path
        
        # Class variables.
        self.character_width = 10
        self.character_height = 30                       
        self.display_height = self.character_height * 16
        self.display_width = self.character_width * 64
        display_size = (self.display_width, self.display_height)
        self.current_display_line = 0
        self.cursor_position = -1
        self.cursor_character = ''
        self.cursor_x = 0
        self.cusror_y = 0
        
        # Display settings.
        self.hide_control_characters = False
        self.invert_screen = False
        self.char_foreground_color = self.WHITE
        self.char_background_color = self.BLACK
        self.color_depth = 8
        self.is_cursor = False
        self.blinking_cursor = False
        self.rom_filename = "ROMs/6574.bin"
        self.full_screen = False
        
        # Load the switches configuration.
        with open("switches.cfg" ,'r') as f:
            baud = 9600
            bytesize = serial.EIGHTBITS
            parity = serial.PARITY_NONE
            stopbits = serial.STOPBITS_ONE
            sense_switch = 0
            sw42_value = 0
            
            lines = f.readlines()
            for line in lines:
                if line[0] == 'S':
                    line = line[0:10].strip().replace(' ', '')
                    switch = int(line[1])
                    bit = int(line[3])
                    value = int(line[5])
                    if switch == 1:
                        if bit == 1:
                            pass
                        elif bit == 2:
                            pass
                        elif bit == 3:
                            if value == 1:
                                self.hide_control_characters = True
                        elif bit == 4:
                            if value == 1:
                                self.invert_screen = True
                        elif bit == 5:
                            if value == 1:
                                self.is_cursor = True
                                self.blinking_cursor = True
                                from apscheduler.schedulers.background import BackgroundScheduler
                        elif bit == 6:
                            if value == 1:
                                self.is_cursor = True
                        elif bit == 7:
                            if value == 1:
                                self.char_foreground_color = self.GREEN
                                self.color_depth = 24
                            elif value == 2:
                                self.char_foreground_color = self.AMBER
                                self.color_depth = 24
                        elif bit == 8:
                            if value == 1:
                                self.rom_filename = "ROMs/6575.bin"
                        elif bit == 9:
                            if value == 1:
                                self.full_screen = True
                        else:
                            print("Bad configuration file. No bit "+bit+" for switch 1.")
                            sys.exit(1)
                            
                    elif switch == 2:
                        if bit == 1:
                            if value == 1:
                                sense_switch |= 0b00000001
                        elif bit == 2:
                            if value == 1:
                                sense_switch |= 0b00000010
                        elif bit == 3:
                            if value == 1:
                                sense_switch |= 0b00000100
                        elif bit == 4:
                            if value == 1:
                                sense_switch |= 0b00001000
                        elif bit == 5:
                            if value == 1:
                                sense_switch |= 0b00010000
                        elif bit == 6:
                            if value == 1:
                                sense_switch |= 0b00100000
                        elif bit == 7:
                            if value == 1:
                                sense_switch |= 0b01000000
                        elif bit == 8:
                            if value == 1:
                                sense_switch |= 0b10000000
                        else:
                            print("Bad configuration file. No bit "+bit+" for switch 2.")
                            sys.exit(1) 
                            
                    elif switch == 3:
                        if value > 0:
                            if bit == 1:
                                baud = 75
                            elif bit == 2:
                                baud = 110
                            elif bit == 3:
                                baud = 150
                            elif bit == 4:
                                baud = 300
                            elif bit == 5:
                                baud = 600
                            elif bit == 6:
                                baud = 1200
                            elif bit == 7:
                                if value == 1:
                                    baud = 2400
                                else:
                                    baud = 4800
                            elif bit == 8:
                                baud = 9600 
                            else:
                                print("Bad configuration file. No bit "+bit+" for switch 3.")
                                sys.exit(1) 
                                
                    elif switch == 4:
                        if bit == 1:
                            if value == 0:
                                parity = serial.PARITY_EVEN
                            else:
                                parity = serial.PARITY_ODD
                        elif bit == 2:
                            sw42_value = value
                        elif bit == 3:
                            if sw42_value == 0:
                                if value == 0:
                                    bytesize = serial.EIGHTBITS
                                else:
                                    bytesize = serial.SIXBITS
                            else:
                                if value == 0:
                                    bytesize = serial.SEVENBITS
                                else:
                                    bytesize = serial.FIVEBITS
                        elif bit == 4:
                            if value == 0:
                                if bytesize == serial.FIVEBITS:
                                    stopbits = serial.STOPBITS_ONE_POINT_FIVE
                                else:
                                    stopbits = serial.STOPBITS_TWO
                            else:
                                stopbits = serial.STOPBITS_ONE
                        elif bit == 5:
                            if value == 0:
                                parity = serial.PARITY_NONE
                        elif bit == 6:
                            pass # Not implemented in emulator.
                        else:
                            print("Bad configuration file. No bit "+bit+" for switch 4.")
                            sys.exit(1) 
                    else:
                        print("Bad configuration file. No switch "+switch+".")
                        sys.exit(1)
                        
            # Save the serial port settings.
            self.io.baud = baud
            self.io.bytesize = bytesize
            self.io.parity = parity
            self.io.stopbits = stopbits
            
            # Save the sense switch settings.
            self.io.sense_switch = sense_switch
            
        # Create the display characters based on the original Sol-20 ROM.
        self.characters = []
        fore = self.char_foreground_color
        back = self.char_background_color
        if self.invert_screen == True:
            fore = self.char_background_color
            back = self.char_foreground_color
            
        with open(self.rom_filename, 'rb') as f:
            romBytes = f.read()
            # Create the characters from the Sol-20 ROM.
            for c in range(0,128):
                image = pygame.Surface((self.character_width, self.character_height), depth=self.color_depth)
                image.fill(back)
                if c in (0x67, 0x6A, 0x70, 0x71, 0x79, 0x2C, 0x3B):
                    # Characters with descenders.
                    for row in range(5,14):
                        byte = romBytes[c*16+row-5]
                        bit = 0x80
                        for col in range(0,8):
                            if byte & bit > 0:
                                image.set_at((col+1, row*2+1), fore)
                                image.set_at((col+1, row*2+2), fore)
                            bit = bit >> 1
                else:
                    for row in range(2,14):
                        byte = romBytes[c*16+row-2]
                        bit = 0x80
                        for col in range(0,8):
                            if byte & bit > 0:
                                image.set_at((col+1, row*2), fore)
                                image.set_at((col+1, row*2+1), fore)
                            bit = bit >> 1
                self.characters.append(image)
                
            # Create inverted characters from the Sol-20 ROM.
            for c in range(0,128):
                image = pygame.Surface((self.character_width, self.character_height), depth=self.color_depth)
                image.fill(fore)
                if c in (0x67, 0x6A, 0x70, 0x71, 0x79, 0x2C, 0x3B):
                    for row in range(5,14):
                        byte = romBytes[c*16+row-5]
                        bit = 0x80
                        for col in range(0,8):
                            if byte & bit > 0:
                                image.set_at((col+1, row*2+1), back)
                                image.set_at((col+1, row*2+2), back)
                            bit = bit >> 1
                else:
                    for row in range(2,14):
                        byte = romBytes[c*16+row-2]
                        bit = 0x80
                        for col in range(0,8):
                            if byte & bit > 0:
                                image.set_at((col+1, row*2), back)
                                image.set_at((col+1, row*2+1), back)
                            bit = bit >> 1
                self.characters.append(image)
                
        # Have to map PyGame keys to ASCII characters.
        self.keymap = {
            pygame.K_BACKSPACE: (0x7F,0x5F,0x1F),
            pygame.K_TAB: (0x09,0x09,0x09),      
            pygame.K_CLEAR: (0,0,0),       
            pygame.K_RETURN: (0x0D,0x0D,0x0D),      
            pygame.K_PAUSE: (0,0,0),       
            pygame.K_ESCAPE: (0x1B,0x1B,0x1B),      
            pygame.K_SPACE: (0x20,0x20,0x20),
            pygame.K_PERIOD: (0x2C,0x3E,0x0C),
            pygame.K_COMMA: (0x2E,0x3C,0x0E),
            pygame.K_SLASH: (0x2F,0x3F,0x0F),
            pygame.K_1: (0x31,0x21,0x01), 
            pygame.K_2: (0x32,0x40,0x02), 
            pygame.K_3: (0x33,0x23,0x03), 
            pygame.K_4: (0x34,0x24,0x04), 
            pygame.K_5: (0x35,0x25,0x05), 
            pygame.K_6: (0x36,0x5E,0x06), 
            pygame.K_7: (0x37,0x26,0x07), 
            pygame.K_8: (0x38,0x2A,0x08), 
            pygame.K_9: (0x39,0x28,0x09), 
            pygame.K_0: (0x30,0x29,0x00),
            pygame.K_SEMICOLON: (0x3B,0x3A,0x0B),
            pygame.K_EQUALS: (0x3D,0x2B,0x0D),
            pygame.K_BACKSLASH: (0x2F,0x7C,0x0F),
            pygame.K_BACKQUOTE: (0x60,0x7E,0),
            pygame.K_a: (0x61,0x41,0x01),
            pygame.K_b: (0x62,0x42,0x02), 
            pygame.K_c: (0x63,0x43,0x03),
            pygame.K_d: (0x64,0x44,0x04), 
            pygame.K_e: (0x65,0x45,0x05), 
            pygame.K_f: (0x66,0x46,0x06), 
            pygame.K_g: (0x67,0x47,0x07), 
            pygame.K_h: (0x68,0x48,0x08), 
            pygame.K_i: (0x69,0x49,0x09), 
            pygame.K_j: (0x6A,0x4A,0x0A), 
            pygame.K_k: (0x6B,0x4B,0x0B), 
            pygame.K_l: (0x6C,0x4C,0x0C), 
            pygame.K_m: (0x6D,0x4D,0x0D), 
            pygame.K_n: (0x6E,0x4E,0x0E), 
            pygame.K_o: (0x6F,0x4F,0x0F), 
            pygame.K_p: (0x70,0x50,0x10), 
            pygame.K_q: (0x71,0x51,0x11), 
            pygame.K_r: (0x72,0x52,0x12), 
            pygame.K_s: (0x73,0x53,0x13), 
            pygame.K_t: (0x74,0x54,0x14), 
            pygame.K_u: (0x75,0x55,0x15), 
            pygame.K_v: (0x76,0x56,0x16), 
            pygame.K_w: (0x77,0x57,0x17), 
            pygame.K_x: (0x78,0x58,0x18), 
            pygame.K_y: (0x79,0x59,0x19), 
            pygame.K_z: (0x7A,0x5A,0x1A), 
            pygame.K_DELETE: (0x7F,0x7F,0x7F),
            pygame.K_MINUS: (0x2D,0x5F,0x0D), 
            pygame.K_KP0: (0x30,0x30,0x30),
            pygame.K_KP1: (0x31,0x31,0x31),
            pygame.K_KP2: (0x32,0x32,0x32),
            pygame.K_KP3: (0x33,0x33,0x33),
            pygame.K_KP4: (0x34,0x34,0x34),
            pygame.K_KP5: (0x35,0x35,0x35),
            pygame.K_KP6: (0x36,0x36,0x36),
            pygame.K_KP7: (0x37,0x37,0x37),
            pygame.K_KP8: (0x38,0x38,0x38),
            pygame.K_KP9: (0x39,0x39,0x39),
            pygame.K_KP_PERIOD: (0x2E,0x2E,0x2E),
            pygame.K_KP_DIVIDE: (0x2F,0x2F,0x2F),
            pygame.K_KP_MULTIPLY: (0x2A,0x2A,0x2A),
            pygame.K_KP_MINUS: (0x2D,0x2D,0x2D),
            pygame.K_KP_PLUS: (0x2B,0x2B,0x2B),
            pygame.K_UP: (0x97,0x97,0x97),
            pygame.K_QUOTE: (0x27,0x22,0x02),
            pygame.K_DOWN: (0x9A,0x9A,0x9A),
            pygame.K_RIGHT: (0x93,0x93,0x93),
            pygame.K_LEFT: (0x81,0x81,0x81),
            pygame.K_INSERT: (0x8C,0x8C,0x8C),
            pygame.K_HOME: (0x8E,0x8E,0x8E),
            pygame.K_END: (0x80,0x80,0x80),
            pygame.K_BREAK: (0x80,0x80,0x80)}
         
        # Create the screen.
        if self.full_screen:
            self.screen = pygame.display.set_mode(display_size, pygame.NOFRAME+pygame.FULLSCREEN)
            pygame.mouse.set_visible(0)
        else:
            self.screen = pygame.display.set_mode(display_size)
        pygame.display.set_caption(self.CAPTION_FORMAT.format(self._path))
        
        
        # Clear the screen.
        self.screen.fill(self.BLACK)
        
        # Watch the Display memory for changes.
        self._cpu.watch_memory(self.TEXT_ADDRESS, self.TEXT_ADDRESS + 1024)
        
        # Initialize the scheduler.
        if self.blinking_cursor:
            self.blink = BackgroundScheduler()
            self.blink.start()
            self.blink.add_job(self._invert_character, 'interval', seconds=.5, id='blink_cursor')
        
        # Define a buffer with the current screen contents.
        self.screen_buffer = bytearray(1024)
        
    # Blit the character passed to the display screen at the coordinates passed.
    def _blit_character(self, c, x, y):
        buffer_pos = int(x/self.character_width) + int((y/self.character_height)*64)
        buffer_c = self.screen_buffer[buffer_pos]
        if buffer_c != c:
            # Only blit the character to the screen if it's different than the current one.
            if self.hide_control_characters and c < 32:
                # Blank control characters if switch set.
                self.screen.blit(self.characters[32],(x,y))
            else:
                self.screen.blit(self.characters[c],(x,y))
            self.screen_buffer[buffer_pos] = c
    
    # Invert the character of the screen at the position specified.
    def _invert_character(self): 
        
        # Get the position and character at the cursor.
        c = self.cursor_character
        x = self.cursor_x
        y = self.cursor_y
        
        # Flip the cursor bit in the character.
        if c > 128:
            c = c & 0x7F
        else:
            c = c | 0x80
        self.cursor_character = c
        
        # Redraw the character.
        self._blit_character(c,x,y)
        
        # Show the changes.
        pygame.display.update()
        
    
    # Update the screen with the characters from the shared display memory.
    def _refresh(self):
        """
        Draw the 64 x 16 text array on the screen.

        """
       
        # Display from the current scroll line to the end of the character buffer.
        x = 0
        y = 0
        num_cursors = 0
        for i in range(0xCC00+self.io.start_display_line*64, 0xCC00+1024):
            # Get the next screen character.
            c = self._cpu.memory[i]
            
            # Save the position if it is the cursor.
            if c & 0x80 > 0:
                num_cursors += 1
                self.cursor_position = i - 0xCC00
                self.cursor_x = x
                self.cursor_y = y
                self.cursor_character = c
            
            # Blit the character to the display.
            self._blit_character(c,x,y)

            # Get ready for the next character.
            x += self.character_width;
            if x == self.character_width*64:
                x = 0;
                y += self.character_height
                
        # Display from the beginning of the character buffer to the current scroll line.
        x = 0
        for i in range(0xCC00,0xCC00+self.io.start_display_line*64):
            # Get the next screen character.
            c = self._cpu.memory[i]
            
            # Save the position if it is the cursor.
            if c & 0x80 > 0:
                num_cursors += 1
                self.cursor_position = i - 0xCC00
                self.cursor_character = c
                self.cursor_x = x
                self.cursor_y = y
            
            # Blit the character to the display.
            self._blit_character(c,x,y)
            
            # Get ready for the next character.
            x += self.character_width;
            if x == self.character_width*64:
                x = 0;
                y += self.character_height
                
        self.current_display_line = self.io.start_display_line
        
        # Check to see if there is a single character > 128. If there are many assume no cursor.
        if not self.is_cursor and num_cursors == 1:
            self._blit_character(self.cursor_character & 0x7f, self.cursor_x, self.cursor_y)
        
    def process_key(self, key, mod):
        keys = self.keymap.get(key)
        if keys != None:
            if mod & pygame.KMOD_CTRL > 0:
                key = keys[2]
            elif mod & pygame.KMOD_SHIFT > 0:
                key = keys[1]
            else:
                key = keys[0]
        else:
            key = 0
            
        if key == 0x80:
            # Mode - reset the tape head.
            self.io.tape_head = 0
        return key
         
    def _handle(self, event):
        """
        Get key presses and add them to a key buffer.
    
        """
        if event.type == pygame.QUIT:
            exit()
        if event.type == pygame.KEYDOWN:
            key = self.process_key(event.key, event.mod)
            if key != 0:
                self.io.buffer_key(key)

    def run(self):
        """
        Sets up display and starts game loop

        :return:
        """
        
        # Clear the screen.
        self.screen.fill(self.BLACK)
        pygame.display.update()

        # The ROM is at C000.
        self._cpu._pc = 0xC000
        
        # Main loop.
        while True:
            # Handle external events like keyboard.
            for event in pygame.event.get():
                self._handle(event)
            
            # This will run the CPU for about 4K cycles.
            self._cpu.run()
            
            if self._cpu.has_memory_changed() or self.current_display_line != self.io.start_display_line:
                if self.blinking_cursor:
                    self.blink.pause()
                self._refresh()
                pygame.display.update()
            elif self.cursor_position >= 0:
                # Schedule an interval to flip the cursor.
                if self.blinking_cursor:
                    self.blink.resume()
                self.cursor_position = -1
