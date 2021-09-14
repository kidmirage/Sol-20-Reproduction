class IOException(Exception):
    pass

class IO:
    """
    Input and output ports for 8080
    """
    
    # Status register bits.
    KDR  = 1    # KEYBOARD DATA READY
    PDR  = 2    # PARALLEL DATA READY
    PXDR = 4    # PARALLEL DEVICE READY
    TFE  = 8    # TAPE FRAMING ERROR
    TOE  = 16   # TAPE OVERFLOW ERROR
    TDR  = 64   # TAPE DATA READY
    TTBE = 128  # TRANSMITTER BUFFER EMPTY
    SOK  = 1    # SCROLL OK
    
    TT1  = 128  # Turn on tape 1.  = 128  # Turn on tape 1.
    TT2  = 64   # Turn on tape 2.
    
    def calculate_crc(self, d, c):
        # SUB C  
        d = (d - c) & 0xFF
        # MOV C,A
        c = d
        # XRA C
        d = d ^ c
        # CHA
        d = d ^ 0xFF
        # SUB C  
        d = (d - c) & 0xFF
        # MOV C,A
        c = d
        
        return c
    
    def add_tape_byte(self, tape, b, crc):
        crc = self.calculate_crc(b, crc)
        tape.append(b)
        return crc
    
    def add_tape_word(self, tape, w, crc):
        low = int(w[2:4],16)
        crc = self.add_tape_byte(tape, low, crc)
        high = int(w[0:2],16)
        crc = self.add_tape_byte(tape, high, crc)
        return crc
        
    def emit_header(self, tape, name, program_type, data_size, start_address, exec_address): 
        # Add leading nulls plus nulls terminator.
        for i in range(0,30):
            tape.append(0x00)
        tape.append(0x01)
        
        # Have to calculate the CRC.
        crc = 0
        
        # Emit the name. Pad to 6 characters with zeros.
        for i in range (0, len(name)):
            crc = self.add_tape_byte(tape, ord(name[i]), crc)
        for i in range (len(name), 6):
            crc = self.add_tape_byte(tape, 0x00, crc)
            
        # Emit the type.
        crc = self.add_tape_byte(tape, program_type, crc)
        
        # Emit the size of the data block.
        crc = self.add_tape_word(tape, data_size, crc)
        
        # Emit the start address of the data block.
        crc = self.add_tape_word(tape, start_address, crc)
        
        # Emit the execution address of the program.
        crc = self.add_tape_word(tape, exec_address, crc)
        
        # Pad with 3 nulls.
        for i in range (0, 3):
            crc = self.add_tape_byte(tape, 0x00, crc) 
            
        # Add the CRC.
        tape.append(crc)
        
    def write_data_with_crc(self, tape, data):
        crc_count = 0
        crc = 0
        for b in data:
            crc = self.add_tape_byte(tape, b, crc)
            crc_count += 1
            if crc_count == 256:
                tape.append(crc)
                crc_count = 0
                crc = 0
                                        
        # Write the last CRC.
        tape.append(crc)
        
    def load_viurtual_tape(self, f, tape):
            
            # Process all the  D lines in a block.
            processing_data = False
            data_bytes = bytearray()
 
            # For each line.
            for line in f:
                # Remove leading and trailing white spaces.
                line = line.strip().upper()
                
                # Skip empty lines and comments.
                if len(line) == 0 or line[0] == ";":
                    continue
                
                # Write out the data to the virtual tape.
                if processing_data and line[0] != "D":
                    self.write_data_with_crc(tape, data_bytes)
                    data_bytes.clear()
                    processing_data = False
                
                 # Ignore all but the header, data, and file lines.
                if line[0] in ("S", "R" , "L", "B", "C"):                    
                    continue
                
                # Add a program from an external file.
                if line[0] == "F":     
                    file_name = line.split(" ")[1]
                    if file_name.endswith(".ENT"):
                        with open("TAPEs/"+file_name, 'r') as f:
                            file_bytes = bytearray()
                            data_count = 0
                            old_address = 0
                           
                            # For each line.
                            for inline in f:
                                inline = inline.strip()
                                if len(inline) == 0:
                                    continue
                                if inline[0] == "E":
                                    start_address = inline.split(" ")[1].strip().zfill(4)
                                else:
                                    # Assume bytes are contiguous.
                                    tokens = inline.split(":")
                                    address = int(tokens[0], 16)
                                    if old_address > 0 and address - old_address != 16:
                                        print("not contiguous", hex(address), hex(old_address))
                                    old_address = address
                                    data = tokens[1].strip().split(" ")
                                    for i in range(0, len(data)): 
                                        file_bytes.append(int(data[i].replace('/', ''), 16))
                                        data_count += 1
                                        
                            # Program name can only be 5 characters.
                            name = file_name.split(".")[0].upper()
                            name = name[0:5]
                            data_size = hex(data_count)[2:].zfill(4)
                            self.emit_header(tape, name, ord('C'), data_size, start_address, start_address)
                            
                            # Now write the data.
                            self.write_data_with_crc(tape, file_bytes)                       
                    elif file_name.endswith(".HEX"):
                        with open("TAPEs/"+file_name, 'rb') as f:
                            tape.extend(f.read(-1))
                            
                # Process headers.
                if line[0] == "H":      
                    
                    # Add leading nulls plus nulls terminator.
                    for i in range(0,30):
                        tape.append(0x00)
                    tape.append(0x01)
                          
                    # Parse out the command line arguments.
                    tokens = line.split()
                    name = tokens[1]
                    program_type = int(tokens[2], 16)
                    data_size = tokens[3]
                    start_address = tokens[4]
                    exec_address = tokens[5]
                    self.emit_header(tape, name, program_type, data_size, start_address, exec_address)
                    
                # Process data lines.
                if line[0] == "D":
                    
                    # Data is assumed to be in hex pairs.
                    data = line.split( )[1]
                                            
                    # Emit the data.
                    for i in range(0, len(data), 2):
                        data_bytes.append(int(data[i]+data[i+1], 16))
                        
                    # Set the processing data flag.
                    processing_data = True  
                    
    def write_saved_program(self):
        # Have to find the file name.
        for i in range(0, len(self.virtual_tape_out)):
            # Skip the leader.
            if self.virtual_tape_out[i] < 2:
                continue
        
            # Should be at the first letter of the name.
            file_name = ""
            while self.virtual_tape_out[i] > 0:
                file_name = file_name + chr(self.virtual_tape_out[i])
                i += 1
            break
        
        # Now write the "program" out as a hex file.
        file_name = file_name + ".HEX"
        with open("TAPEs/"+file_name, 'wb') as f:
             f.write(self.virtual_tape_out)
             f.close()
        
        # See if there is an entry in the TAPE file and add one if there isn't.
        if self.current_tape == self.virtual_tape_1:
            tape_name = "TAPEs/TAPE1.svt"
        else:
            tape_name = "TAPEs/TAPE2.svt"
        with open(tape_name, 'r+') as f:
            # See if the filename is already there.
            has_file_name = False
            for line in f:
                if file_name in line.upper():
                    has_file_name = True
                    break
            f.close()
            if not has_file_name:
                with open(tape_name, 'a') as f:
                    f.write("\n")
                    f.write("F " + file_name)
                    f.close()
        
        # Reload the current virtual tape.      
        self.current_tape.clear()
        try:
            with open(tape_name, 'r') as f:
                self.load_viurtual_tape(f, self.current_tape)
        except FileNotFoundError:
            print("Problem updating virtual tape.")
                
        
    def __init__(self):
        
        # Used for virtual keyboard.      
        self.key_buffer = bytearray(10)
        self.next_key = 0
        self.add_key = 0
        self.num_keys = 0
        
        # Used by virtual display to control scrolling.
        self.start_display_line = 0
        
        # Load the data here for the virtual tape drives.
        self.virtual_tape_1 = bytearray()
        self.virtual_tape_2 = bytearray()
        self.current_tape = self.virtual_tape_1
        
        # Store save data here before writing to disk.
        self.virtual_tape_out = bytearray()
        self.tape_on = False
        
        # Points to the current position on the tapes.
        self.tape_head = 0
        
        # Load the virtual cassette tapes.
        try:
            with open("TAPEs/TAPE1.svt", 'r') as f:
                self.load_viurtual_tape(f, self.virtual_tape_1)
        except FileNotFoundError:
            print("There is no virtual cassette tape 1.")
        
        try:
            with open("TAPEs/TAPE2.svt", 'r') as f:
                self.load_viurtual_tape(f, self.virtual_tape_2)
        except FileNotFoundError:
            print("There is no virtual cassette tape 2.")
            
        
    def buffer_key(self, key):
        if (self.num_keys < 10):
            self.key_buffer[self.add_key] = key
            self.add_key = (self.add_key + 1) % 10
            self.num_keys = self.num_keys + 1

    def output(self, port, value):
        if port == 0xFE:
            # Display scrolling control.
            self.start_display_line = value
        elif port == 0xFA:
            if value == self.TT1:
                # Turn on the tape.
                self.tape_head = 0
                self.current_tape = self.virtual_tape_1
                self.virtual_tape_out.clear()
                self.tape_on = True
                
            elif value == self.TT2:
                # Turn on the tape.
                self.tape_head = 0
                self.current_tape = self.virtual_tape_2
                self.virtual_tape_out.clear()
                self.tape_on = True
            else:
                # Turn the tape off.
                if self.tape_on and  len(self.virtual_tape_out) > 0:
                    self.write_saved_program()
                self_tape_on = False
                
        elif port == 0xFB:
            # Write the byte to the virtual tape out.
            self.virtual_tape_out.append(value)
        elif port == 0xF8:
            print("control" + hex(value))
        else:
            print("O:", hex(port), hex(value))
        

    def input(self, port):
        result = 0
        if port == 0xFF:
            result = 0xFF
        elif port == 0xFA:
            is_key = self.KDR
            if self.num_keys > 0:
                is_key = 0
            is_tape = 0
            if self.tape_head < len(self.current_tape):
                is_tape = is_tape | self.TDR | self.TTBE
            result = is_key | is_tape
        elif port == 0xFB:
            result = self.current_tape[self.tape_head]
            self.tape_head = self.tape_head + 1   
        elif port == 0xFC:
            result = self.key_buffer[self.next_key]
            self.num_keys -= 1
            self.next_key = (self.next_key + 1) % 10
        elif port == 0xFE:
            result = self.SOK
        else:
            print("I:", hex(port))
    
        if result > 255:
            raise IOException('Invalid result={}'.format(result))

        return result
    
