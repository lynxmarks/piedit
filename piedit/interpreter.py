#!/usr/bin/env python

"""Interpreter for the Piet programming language. Can be run directly or 
imported and used by the GUI"""

import sys
import gtk
import PIL.Image
import colors
import unionfind
import getchr

__author__ = "Steven Anderson"
__copyright__ = "Steven Anderson 2008"
__credits__ = ["Steven Anderson"]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Steven Anderson"
__email__ = "steven.james.anderson@googlemail.com"
__status__ = "Production"

def print_usage():
    """Prints usage string for command line"""
    print "Usage: interpreter.py image"
        

class Interpreter:
    """The Piet interpreter class"""
    def __init__(self):
        """Sets up object properties"""
        self.current_pixel = None
        self.dp = 0
        self.cc = 0
        self.switch_cc = True
        self.step = 0 #0 for just moved into color block, 1 for moved to edge
        self.times_stopped = 0
        self.max_steps = 1000000
        self.stack = []
        self.color_blocks = {}
            #Indexed by hue and light change
        self.operations = {
            (1,0):("Add",self.op_add),
            (2,0):("Divide",self.op_divide),
            (3,0):("Greater",self.op_greater),
            (4,0):("Duplicate",self.op_duplicate),
            (5,0):("IN(char)",self.op_in_char),
            (0,1):("Push",self.op_push),
            (1,1):("Subtract",self.op_subtract),
            (2,1):("Mod",self.op_mod),
            (3,1):("Pointer",self.op_pointer),
            (4,1):("Roll",self.op_roll),
            (5,1):("OUT(Number)",self.op_out_number),
            (0,2):("Pop",self.op_pop),
            (1,2):("Multiply",self.op_multiply),
            (2,2):("Not",self.op_not),
            (3,2):("Switch",self.op_switch),
            (4,2):("IN(Number)",self.op_in_number),
            (5,2):("OUT(Char)",self.op_out_char),
        }
    
    def run_program(self,path):
        """Runs a program at the given path"""
        print "Loading image"
        self.load_image(path)   
        print "Scanning color blocks"
        self.find_color_blocks()
        print "Starting execution"
        self.start_execution()
        
    def load_image(self,path):
        """Loads an image and puts pixel data into self.pixels"""
        try:
            self.image = PIL.Image.open(path)
            if self.image.mode != "RGB":
                self.image = self.image.convert("RGB")
        except IOError:
            raise IOError, "IMAGE_NOT_LOADED"
        
        (self.width, self.height) = self.image.size
        self.rawpixels = self.image.getdata()
        self.pixels = [[None for y in range(self.height)] for x in range(self.width)]
        i = 0
        for y in range(self.height):
            for x in range(self.width):
                self.pixels[x][y] = Pixel(x,y,self.rawpixels[i])
                #print self.rawpixels[i]
                i = i + 1
        self.current_pixel = self.pixels[0][0]
        
    def find_color_blocks(self):
        """Uses the connected component algorithm to build the program color blocks"""
        next_label = 0
        #Pass 1
        for y in range(self.height):
            for x in range(self.width):
                pixel = self.pixels[x][y]
                if not self.is_background(pixel.color):
                    neighbours = self.neighbours(pixel)
                    
                    if neighbours == []:
                        pixel.parent = self.pixels[x][y]
                        pixel.set_label = next_label
                        next_label = next_label + 1
                    else:
                        for n in neighbours:
                            unionfind.union(n,pixel)
        
        #Pass 2
        for y in range(self.height):
            for x in range(self.width):
                pixel = self.pixels[x][y]
                if not self.is_background(pixel.color):
                    root = unionfind.find(pixel)
                    pixel.set_size = root.set_size
                    pixel.set_label = root.set_label
                    #Build color block object
                    if not self.color_blocks.has_key(pixel.set_label):
                        self.color_blocks[pixel.set_label] = ColorBlock(pixel.set_size)
                    self.color_blocks[pixel.set_label].update_boundaries(pixel)
    
        #Debug
        #for i,color_block in self.color_blocks.items():
        #    bounds = color_block.boundary_pixels
        #    print "Color Block %s: Size=%s, maxRL=(%s,%s), maxRR=(%s,%s), maxDL=(%s,%s), maxDR=(%s,%s), maxLL=(%s,%s), maxLR=(%s,%s), maxUL=(%s,%s), maxUR=(%s,%s)" \
        #        % (i, color_block.size, 
        #           bounds[0][0].x,bounds[0][0].y, bounds[0][1].x, bounds[0][1].y,
        #           bounds[1][0].x,bounds[1][0].y, bounds[1][1].x, bounds[1][1].y,
        #           bounds[2][0].x,bounds[2][0].y, bounds[2][1].x, bounds[2][1].y,
        #           bounds[3][0].x,bounds[3][0].y, bounds[3][1].x, bounds[3][1].y)
                    
    def is_background(self,color):
        """Tells us if the given color is black or white"""
        if color == colors.white or color == colors.black:
            return True
        else:
            return False
        
    def neighbours(self,pixel):
        """Finds the neighbours of the given pixel with the same label."""
        neighbours = []
        index = 0;
        x = pixel.x
        y = pixel.y
            
        if y !=0 and self.pixels[x][y-1].color == pixel.color:
            #Add above pixel
            index = index + 1
            neighbours.append(self.pixels[x][y-1])
        
        if x != 0 and self.pixels[x-1][y].color == pixel.color:
            #Add left pixel
            neighbours.append(self.pixels[x-1][y])
            index = index + 1
            
        return neighbours      
    
    def start_execution(self):
        """Starts the execution of the program"""
        for i in range(self.max_steps):
            self.do_next_step()
            
    def do_next_step(self):     
        """Executes a step in the program."""
        #print "At (%s,%s)" % (self.current_pixel.x,self.current_pixel.y)
        if self.step == 0:
            self.current_pixel = \
                self.color_blocks[self.current_pixel.set_label] \
                .boundary_pixels[self.dp][self.cc]
            self.step = 1
        elif self.step == 1:
            next_pixel = self.next_pixel()
            if (not next_pixel and self.current_pixel.color == colors.white) or (next_pixel and next_pixel.color == colors.white):
                if self.current_pixel.color != colors.white:
                    self.switch_cc = True
                    self.times_stopped = 0
                #print "sliding trhu white"
                self.slide_thru_white()
                self.step = 1
            else:
                if next_pixel:
                    self.switch_cc = True
                    self.times_stopped = 0
                
                    if self.current_pixel.color != colors.white:
                        hue_light_diff = colors.hue_light_diff(self.current_pixel.color, next_pixel.color)
                        op_name, op = self.operations[hue_light_diff]
                        op()
                    
                    self.current_pixel = next_pixel
                else:
                    self.handle_stop()
                self.step = 0
        else:
            error_handler.handle_error("The step wasn't 0 or 1. That should never happen. This must be a bug in my code. Sorry")
    
    def next_pixel(self):
        """Returns the next pixel in the direction of the dp. If the next
        pixel is black or a wall, it returns None"""
        cp = self.current_pixel
        if self.dp == 0 \
            and cp.x+1 < self.width \
            and self.pixels[cp.x+1][cp.y].color != colors.black:
                return self.pixels[cp.x+1][cp.y]
        elif self.dp == 1 \
            and cp.y+1 < self.height \
            and self.pixels[cp.x][cp.y+1].color != colors.black:
                return self.pixels[cp.x][cp.y+1]
        elif self.dp == 2 \
            and cp.x-1 >= 0 \
            and self.pixels[cp.x-1][cp.y].color != colors.black:
                return self.pixels[cp.x-1][cp.y]
        elif self.dp == 3 \
            and cp.y-1 >= 0 \
            and self.pixels[cp.x][cp.y-1].color != colors.black:
                return self.pixels[cp.x][cp.y-1]
        else:
            return None
            
    def slide_thru_white(self):
        """Slides through a white block until an obstruction or new color
        block is reached"""
        next_pixel = self.next_pixel()
        if not next_pixel:
            self.times_stopped = self.times_stopped + 1
            if self.times_stopped >= 8:
                self.stop_execution
            self.toggle_cc()
            self.rotate_dp()
        while next_pixel and next_pixel.color == colors.white:
            self.current_pixel = next_pixel
            next_pixel = self.next_pixel()    
    
    def handle_stop(self):
        """Handles the case when an obstruction is the next pixel."""
        self.times_stopped = self.times_stopped + 1
        if (self.times_stopped >= 8):
            self.stop_execution()
        else:
            if self.switch_cc:
                self.toggle_cc()
                self.switch_cc = False
            else:
                self.rotate_dp(1)
                self.switch_cc = True
    
    def stop_execution(self):
        """Cancels execution of the program"""
        print "\nExecution finished"
        sys.exit(1)
        
    def toggle_cc(self):
        """Toggles the cc"""
        #print "Toggling cc"
        div,mod = divmod(1-self.cc,1)
        self.cc = div
    
    def rotate_dp(self,times=1):
        """Rotates the dp by the given number of times"""
        #print "Rotating dp"
        div,mod = divmod(self.dp+times,4)
        self.dp = mod
        
    #Below are the actual operation methods for the piet language.
    def op_add(self):
        """Piet Add operation"""
        if len(self.stack) >= 2:
            item1 = self.stack.pop()
            item2 = self.stack.pop()
            self.stack.append(item1+item2)
    
    def op_divide(self):
        """Piet Divide operation"""
        if len(self.stack) >= 2:
            top_item = self.stack.pop()
            second_item = self.stack.pop()
            self.stack.append(second_item/top_item)
    
    def op_greater(self):
        """Piet Greater operation"""
        if len(self.stack) >= 2:
            top_item = self.stack.pop()
            second_item = self.stack.pop()
            self.stack.append(int(second_item>top_item))
            
    def op_duplicate(self):
        """Piet Duplicate operation"""
        if len(self.stack) >=1:
            item = self.stack[-1]
            self.stack.append(item)
    
    def op_in_char(self):
        """Piet IN(CHAR) operation"""
        chr = getchr.get_chr()
        self.stack.append(ord(chr))
    
    def op_push(self):
        """Piet Push operation"""
        self.stack.append(self.current_pixel.set_size)
    
    def op_subtract(self):
        """Piet Subtract operation"""
        if len(self.stack) >= 2:
            top_item = self.stack.pop()
            second_item = self.stack.pop()
            self.stack.append(second_item-top_item)
    
    def op_mod(self):
        """Piet Mod operation"""
        if len(self.stack) >= 2:
            top_item = self.stack.pop()
            second_item = self.stack.pop()
            self.stack.append(second_item % top_item)
    
    def op_pointer(self):
        """Piet Pointer operation"""
        if len(self.stack) >= 1:
            item = self.stack.pop()
            self.rotate_dp(item)
    
    def op_roll(self):
        """Piet Roll operation"""
        if len(self.stack) >= 2:
            num_rolls = self.stack.pop()
            depth = self.stack.pop()    
            if depth >0:
                for i in range(abs(num_rolls)):
                    self.roll(depth,num_rolls<0)    
    
    def roll(self,depth,reverse):
        """Does a single roll"""
        if depth > len(self.stack):
            depth = len(self.stack)

        if reverse:
            bottom_item = self.stack[0]
            index = depth
            for i in range(index):
                self.stack[i] = self.stack[i+1]
            self.stack[index] = bottom_item
        else:
            top_item = self.stack[-1]
            index = len(self.stack)-depth
            for i in range(len(self.stack)-1,index,-1):
                self.stack[i] = self.stack[i-1]    
            self.stack[index] = top_item
    
    def op_out_number(self):
        """Piet OUT(NUM) operation"""
        if len(self.stack) >=1:
            item = self.stack.pop()
            sys.stdout.write(str(item))
    
    def op_pop(self):
        """Piet Pop operation"""
        if len(self.stack) >=1:
            self.stack.pop()
    
    def op_multiply(self):
        """Piet Multiply operation"""
        if len(self.stack) >= 2:
            item1 = self.stack.pop()
            item2 = self.stack.pop()
            self.stack.append(item1*item2)
    
    def op_not(self):
        """Piet Not operation"""
        if len(self.stack) >= 1:
            item = self.stack.pop()
            self.stack.append(int(not item))
    
    def op_switch(self):
        """Piet Switch operation"""
        if len(self.stack) >=1:
            item = self.stack.pop()
            for i in range(item):
                self.toggle_cc()
    
    def op_in_number(self):
        """Piet IN(NUM) operation"""
        char = getchr.get_chr()
        try:
            self.stack.append(int(char))
        except ValueError:
            pass      
    
    def op_out_char(self):
        """Piet OUT(CHAR) operation"""
        if len(self.stack) >=1:
            item = self.stack.pop()
            sys.stdout.write(chr(item))
    
    
class ColorBlock:
    """Class that represents a color block in a Piet program"""
    def __init__(self,size):
        """Sets the boundary pixels to None"""
        self.size = size
        #boundary_pixels = [[DPR_CCL,DPR_CCR],[DPD_CCL,DPD,CCR] ... etc.
        self.boundary_pixels = [[None,None] for i in range(4)]
        
    def update_boundaries(self,pixel):
        """Updates the boundary pixels of the current color block given a new pixel"""
        #If a new maximum (right, left)
        if self.boundary_pixels[0][0] == None or pixel.x > self.boundary_pixels[0][0].x:
            self.boundary_pixels[0][0] = pixel
            
        #If a new maximum (right, right)
        if self.boundary_pixels[0][1] == None or pixel.x >= self.boundary_pixels[0][1].x:
            self.boundary_pixels[0][1] = pixel
            
        #If a new maximum (down, right)
        if self.boundary_pixels[1][1] == None or pixel.y > self.boundary_pixels[1][1].y:
            self.boundary_pixels[1][1]= pixel
        
        #If a new maximum (down, left)
        if self.boundary_pixels[1][0] == None or pixel.y >= self.boundary_pixels[1][0].y:
            self.boundary_pixels[1][0] = pixel
            
        #If a new maximum (left, right)
        if self.boundary_pixels[2][1] == None or pixel.x < self.boundary_pixels[2][1].x:
            self.boundary_pixels[2][1] = pixel
        
        #If a new maximum (left, left)
        if self.boundary_pixels[2][0] == None or pixel.x <= self.boundary_pixels[2][0].x:
            self.boundary_pixels[2][0] = pixel
            
        #If a new maximum (up,left)
        if self.boundary_pixels[3][0] == None:
            self.boundary_pixels[3][0] = pixel
            
        #If a new maximum (up,right)
        if self.boundary_pixels[3][1] == None or pixel.y == self.boundary_pixels[3][1].y:
            self.boundary_pixels[3][1] = pixel
                
             
class Pixel:
    """Class that represents a pixel in a Piet program (stricly a codel, but 
    the convention is 1 pixel per codel"""
    
    def __init__(self,x,y,color):
        """Sets object properties. Sets color to white if it's a non-Piet color"""
        self.x = x
        self.y = y
        try:
            colors.color_mappings[colors.rgb_to_hex(color)]
            self.color = color
        except KeyError:
            self.color = colors.white
        self.parent = self   
        self.set_size = 1
        self.set_label = -1
        
    
class ErrorHandler:
    """Class that handles errors for the interpreter. Does it differently
    for UI and command line modes"""
    
    def __init__(self, isGUI=False):
        """Sets object properties"""
        self.isGUI = isGUI
        
    def handle_error(self,message):
        """Handles an error with the given message"""
        if not self.isGUI:
            raise SystemExit("\nError: "+message)
        else:
            pass
    
#Run the program if on command line
if __name__ == "__main__":
    error_handler = ErrorHandler(False)
    interpreter = Interpreter()
    if len(sys.argv)>1:
        interpreter.run_program(sys.argv[1])
    else:
        print_usage()