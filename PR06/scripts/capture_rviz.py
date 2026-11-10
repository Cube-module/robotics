#!/usr/bin/env python3
"""Capture the real RViz X11 backing pixmap; never synthesize image contents."""
import ctypes as c
import re
import subprocess
import sys
from PIL import Image
x = c.CDLL('libX11.so.6'); comp = c.CDLL('libXcomposite.so.1')
x.XOpenDisplay.argtypes=[c.c_char_p]; x.XOpenDisplay.restype=c.c_void_p
display=x.XOpenDisplay(None)
assert display
text=subprocess.check_output(['xwininfo','-root','-tree'],text=True)
match=re.search(r'(0x[0-9a-f]+) "[^"\n]* - RViz"[^\n]*? (\d+)x(\d+)',text)
assert match,text
window=int(match[1],16); width=int(match[2]); height=int(match[3])
comp.XCompositeNameWindowPixmap.argtypes=[c.c_void_p,c.c_ulong]
comp.XCompositeNameWindowPixmap.restype=c.c_ulong
pixmap=comp.XCompositeNameWindowPixmap(display,window)
class XImage(c.Structure):
    _fields_=[('width',c.c_int),('height',c.c_int),('xoffset',c.c_int),('format',c.c_int),
              ('data',c.c_void_p),('byte_order',c.c_int),('bitmap_unit',c.c_int),
              ('bitmap_bit_order',c.c_int),('bitmap_pad',c.c_int),('depth',c.c_int),
              ('bytes_per_line',c.c_int),('bits_per_pixel',c.c_int)]
x.XGetImage.argtypes=[c.c_void_p,c.c_ulong,c.c_int,c.c_int,c.c_uint,c.c_uint,c.c_ulong,c.c_int]
x.XGetImage.restype=c.POINTER(XImage)
image=x.XGetImage(display,pixmap,0,0,width,height,c.c_ulong(-1),2)
assert image
im=image.contents
print(im.width,im.height,im.bytes_per_line,im.bits_per_pixel)
assert im.bits_per_pixel==32
shot=Image.frombytes('RGB',(width,height),c.string_at(im.data,im.bytes_per_line*height),'raw','BGRX',im.bytes_per_line)
print('extrema',shot.getextrema())
assert any(high>low for low,high in shot.getextrema()),'Empty capture'
shot.save(sys.argv[1])
x.XDestroyImage.argtypes=[c.POINTER(XImage)]; x.XDestroyImage(image)
x.XFreePixmap.argtypes=[c.c_void_p,c.c_ulong]; x.XFreePixmap(display,pixmap)
x.XCloseDisplay.argtypes=[c.c_void_p]; x.XCloseDisplay(display)
