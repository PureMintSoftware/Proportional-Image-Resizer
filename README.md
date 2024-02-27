Proportional Image Resizer  
by Pure Mint Software  
--------------------------

Resizes a folder of images to a new user determined size, whilst keeping the proportions of the original images.   
It outputs the resized images to a new "Resized" folder inside the original image folder.  

Example 
-------

You have a folder called "Cat Memes", and the images are a mix of sizes and proportions (portrait, landscape, square). 
You want to resize them (whether up or down) so that their longest sides all become 1000 pixels, whilst maintaining their original proportionality.  
  
A 2000 x 1000 (Landscape Image) will become 1000 x 500 ... Scaled Down.  
A 300 x 400 (Portrait Image) will become 1000 x 750 ... Scaled Up.  
A 1583 x 1583 (Square Image) will become 1000 x 1000 ... Scaled Down.  
A 500 x 1000 (Portrait Image) will remain 500 x 1000 ... No Scaling Required.  

Required Libraries 
------------------

It just requires Pillow, because OS and Tkinter should already be installed in any Python installation.  
Open "CMD" from the Windows Start Menu, type the line below into the Windows Terminal, and press enter.

>pip install pillow tk
