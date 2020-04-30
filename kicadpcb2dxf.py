#!/usr/bin/python
# -*- coding: utf-8 -*-
# 
## kicadpcb2dxf.py
#  creates DXF file of selected kicad pcb board
#  using r12writer from ezdxf modules included
#  this is a part of kicad StepUp tools; please refer to kicad StepUp tools 
#  for the full licence
# 
### Copyright (c) 2015 Maurice easyw@katamail.com
#****************************************************************************
## done:
# gr_line, gr_circle, gr_arc
# add footprint support fp_line, fp_circle, fp_arc
# add text support (mirror & alignement not supported)
# add multiline text support

## todo:
# add quote support

# Purpose: fast & simple but restricted DXF R12 writer, with no in-memory drawing, and without dependencies to other
# ezdxf modules. The created DXF file contains no HEADER, TABLES or BLOCKS section only the ENTITIES section is present.
# Created: 14.04.2016
# Copyright (C) 2016, Manfred Moitzi
# License: MIT License
from __future__ import unicode_literals
dxf_parser="r12writer from ezdxf 0.7.6"
__author__ = "mozman <mozman@gmx.at>"

script_name="kicadpcb2dxf"
__author_script__="easyw Maurice"
___version___=3.7

from contextlib import contextmanager

def rnd(x):  # adjust output precision of floats by changing 'ndigits'
    return round(x, ndigits=6)

TEXT_ALIGN_FLAGS = {
    'LEFT': (0, 0),
    'CENTER': (1, 0),
    'RIGHT': (2, 0),
    'BOTTOM_LEFT': (0, 1),
    'BOTTOM_CENTER': (1, 1),
    'BOTTOM_RIGHT': (2, 1),
    'MIDDLE_LEFT': (0, 2),
    'MIDDLE_CENTER': (1, 2),
    'MIDDLE_RIGHT': (2, 2),
    'TOP_LEFT': (0, 3),
    'TOP_CENTER': (1, 3),
    'TOP_RIGHT': (2, 3),
}


@contextmanager
def r12writer(stream, fixed_tables=False):
    if hasattr(stream, 'write'):
        writer = R12FastStreamWriter(stream, fixed_tables)
        yield writer
        writer.close()
    else:
        with open(stream, 'wt') as stream:
            writer = R12FastStreamWriter(stream, fixed_tables)
            yield writer
            writer.close()


class R12FastStreamWriter(object):
    def __init__(self, stream, fixed_tables=False):
        self.stream = stream
        if fixed_tables:
            stream.write(PREFACE)
        stream.write("0\nSECTION\n2\nENTITIES\n")  # write header

    def close(self):
        self.stream.write("0\nENDSEC\n0\nEOF\n")  # write tail

    def add_line(self, start, end, layer="0", color=None, linetype=None):
        dxf = ["0\nLINE\n"]
        dxf.append(dxf_attribs(layer, color, linetype))
        dxf.append(dxf_vertex(start, code=10))
        dxf.append(dxf_vertex(end, code=11))
        self.stream.write(''.join(dxf))

    def add_circle(self, center, radius, layer="0", color=None, linetype=None):
        dxf = ["0\nCIRCLE\n"]
        dxf.append(dxf_attribs(layer, color, linetype))
        dxf.append(dxf_vertex(center))
        dxf.append(dxf_tag(40, str(rnd(radius))))
        self.stream.write(''.join(dxf))

    def add_arc(self, center, radius, start=0, end=360, layer="0", color=None, linetype=None):
        dxf = ["0\nARC\n"]
        dxf.append(dxf_attribs(layer, color, linetype))
        dxf.append(dxf_vertex(center))
        dxf.append(dxf_tag(40, str(rnd(radius))))
        dxf.append(dxf_tag(50, str(rnd(start))))
        dxf.append(dxf_tag(51, str(rnd(end))))
        self.stream.write(''.join(dxf))

    def add_point(self, location, layer="0", color=None, linetype=None):
        dxf = ["0\nPOINT\n"]
        dxf.append(dxf_attribs(layer, color, linetype))
        dxf.append(dxf_vertex(location))
        self.stream.write(''.join(dxf))

    def add_3dface(self, vertices, invisible=0, layer="0", color=None, linetype=None):
        self._add_quadrilateral('3DFACE', vertices, invisible, layer, color, linetype)

    def add_solid(self, vertices, layer="0", color=None, linetype=None):
        self._add_quadrilateral('SOLID', vertices, 0, layer, color, linetype)

    def _add_quadrilateral(self, dxftype, vertices, flags, layer, color, linetype):
        dxf = ["0\n%s\n" % dxftype]
        dxf.append(dxf_attribs(layer, color, linetype))
        vertices = list(vertices)
        if len(vertices) < 3:
            raise ValueError("%s needs 3 ot 4 vertices." % dxftype)
        elif len(vertices) == 3:
            vertices.append(vertices[-1])  # double last vertex
        dxf.extend(dxf_vertex(vertex, code) for code, vertex in enumerate(vertices, start=10))
        if flags:
            dxf.append(dxf_tag(70, str(flags)))
        self.stream.write(''.join(dxf))

    def add_polyline(self, vertices, layer="0", color=None, linetype=None):
        def write_polyline(flags):
            dxf = ["0\nPOLYLINE\n"]
            dxf.append(dxf_attribs(layer, color, linetype))
            dxf.append(dxf_tag(66, "1"))  # entities follow
            dxf.append(dxf_tag(70, flags))
            self.stream.write(''.join(dxf))

        polyline_flags, vertex_flags = None, None
        for vertex in vertices:
            if polyline_flags is None:  # first vertex
                if len(vertex) == 3:  # 3d polyline
                    polyline_flags, vertex_flags = ('8', '32')
                else:  # 2d polyline
                    polyline_flags, vertex_flags = ('0', '0')
                write_polyline(polyline_flags)

            dxf = ["0\nVERTEX\n"]
            dxf.append(dxf_attribs(layer))
            dxf.append(dxf_tag(70, vertex_flags))
            dxf.append(dxf_vertex(vertex))
            self.stream.write(''.join(dxf))
        if polyline_flags is not None:
            self.stream.write("0\nSEQEND\n")

    def add_text(self, text, insert=(0, 0), height=1., width=1., align="LEFT", rotation=0., oblique=0., style='STANDARD',
                 layer="0", color=None):
        # text style is always STANDARD without a TABLES section
        dxf = ["0\nTEXT\n"]
        dxf.append(dxf_attribs(layer, color))
        dxf.append(dxf_vertex(insert, code=10))
        dxf.append(dxf_tag(1, str(text)))
        dxf.append(dxf_tag(40, str(rnd(height))))
        if width != 1.:
            dxf.append(dxf_tag(41, str(rnd(width))))
        if rotation != 0.:
            dxf.append(dxf_tag(50, str(rnd(rotation))))
        if oblique != 0.:
            dxf.append(dxf_tag(51, str(rnd(oblique))))
        if style != "STANDARD":
            dxf.append(dxf_tag(7, str(style)))
        halign, valign = TEXT_ALIGN_FLAGS[align.upper()]
        dxf.append(dxf_tag(72, str(halign)))
        dxf.append(dxf_tag(73, str(valign)))
        dxf.append(dxf_vertex(insert, code=11))  # align point
        self.stream.write(''.join(dxf))


def dxf_attribs(layer, color=None, linetype=None):
    dxf = ["8\n%s\n" % layer]  # layer is required
    if linetype is not None:
        dxf.append("6\n%s\n" % linetype)
    if color is not None:
        if 0 <= int(color) < 257:
            dxf.append("62\n%d\n" % color)
        else:
            raise ValueError("color has to be an integer in the range from 0 to 256.")
    return "".join(dxf)


def dxf_vertex(vertex, code=10):
    dxf = []
    for c in vertex:
        dxf.append("%d\n%s\n" % (code, str(rnd(c))))
        code += 10
    return "".join(dxf)


def dxf_tag(code, value):
    return "%d\n%s\n" % (code, value)

PREFACE = """  0
SECTION
  2
HEADER
  9
$ACADVER
  1
AC1009
  9
$DWGCODEPAGE
  3
ANSI_1252
  0
ENDSEC
  0
SECTION
  2
TABLES
  0
TABLE
  2
LTYPE
  5
431
 70
20
  0
LTYPE
  5
40F
  2
CONTINUOUS
 70
0
  3
Solid line
 72
65
 73
0
 40
0.0
  0
LTYPE
  5
410
  2
CENTER
 70
0
  3
Center ____ _ ____ _ ____ _ ____ _ ____ _ ____
 72
65
 73
4
 40
2.0
 49
1.25
 49
-0.25
 49
0.25
 49
-0.25
  0
LTYPE
  5
411
  2
DASHED
 70
0
  3
Dashed __ __ __ __ __ __ __ __ __ __ __ __ __ _
 72
65
 73
2
 40
0.75
 49
0.5
 49
-0.25
  0
LTYPE
  5
412
  2
PHANTOM
 70
0
  3
Phantom ______  __  __  ______  __  __  ______
 72
65
 73
6
 40
2.5
 49
1.25
 49
-0.25
 49
0.25
 49
-0.25
 49
0.25
 49
-0.25
  0
LTYPE
  5
413
  2
HIDDEN
 70
0
  3
Hidden __ __ __ __ __ __ __ __ __ __ __ __ __ __
 72
65
 73
2
 40
9.525
 49
6.345
 49
-3.175
  0
LTYPE
  5
43B
  2
CENTERX2
 70
0
  3
Center (2x) ________  __  ________  __  ________
 72
65
 73
4
 40
3.5
 49
2.5
 49
-0.25
 49
0.5
 49
-0.25
  0
LTYPE
  5
43C
  2
CENTER2
 70
0
  3
Center (.5x) ____ _ ____ _ ____ _ ____ _ ____
 72
65
 73
4
 40
1.0
 49
0.625
 49
-0.125
 49
0.125
 49
-0.125
  0
LTYPE
  5
43D
  2
DASHEDX2
 70
0
  3
Dashed (2x) ____  ____  ____  ____  ____  ____
 72
65
 73
2
 40
1.2
 49
1.0
 49
-0.2
  0
LTYPE
  5
43E
  2
DASHED2
 70
0
  3
Dashed (.5x) _ _ _ _ _ _ _ _ _ _ _ _ _ _
 72
65
 73
2
 40
0.3
 49
0.25
 49
-0.05
  0
LTYPE
  5
43F
  2
PHANTOMX2
 70
0
  3
Phantom (2x)____________    ____    ____    ____________
 72
65
 73
6
 40
4.25
 49
2.5
 49
-0.25
 49
0.5
 49
-0.25
 49
0.5
 49
-0.25
  0
LTYPE
  5
440
  2
PHANTOM2
 70
0
  3
Phantom (.5x) ___ _ _ ___ _ _ ___ _ _ ___ _ _ ___
 72
65
 73
6
 40
1.25
 49
0.625
 49
-0.125
 49
0.125
 49
-0.125
 49
0.125
 49
-0.125
  0
LTYPE
  5
441
  2
DASHDOT
 70
0
  3
Dash dot __ . __ . __ . __ . __ . __ . __ . __
 72
65
 73
4
 40
1.4
 49
1.0
 49
-0.2
 49
0.0
 49
-0.2
  0
LTYPE
  5
442
  2
DASHDOTX2
 70
0
  3
Dash dot (2x) ____  .  ____  .  ____  .  ____
 72
65
 73
4
 40
2.4
 49
2.0
 49
-0.2
 49
0.0
 49
-0.2
  0
LTYPE
  5
443
  2
DASHDOT2
 70
0
  3
Dash dot (.5x) _ . _ . _ . _ . _ . _ . _ . _
 72
65
 73
4
 40
0.7
 49
0.5
 49
-0.1
 49
0.0
 49
-0.1
  0
LTYPE
  5
444
  2
DOT
 70
0
  3
Dot .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
 72
65
 73
2
 40
0.2
 49
0.0
 49
-0.2
  0
LTYPE
  5
445
  2
DOTX2
 70
0
  3
Dot (2x) .    .    .    .    .    .    .    .
 72
65
 73
2
 40
0.4
 49
0.0
 49
-0.4
  0
LTYPE
  5
446
  2
DOT2
 70
0
  3
Dot (.5) . . . . . . . . . . . . . . . . . . .
 72
65
 73
2
 40
0.1
 49
0.0
 49
-0.1
  0
LTYPE
  5
447
  2
DIVIDE
 70
0
  3
Divide __ . . __ . . __ . . __ . . __ . . __
 72
65
 73
6
 40
1.6
 49
1.0
 49
-0.2
 49
0.0
 49
-0.2
 49
0.0
 49
-0.2
  0
LTYPE
  5
448
  2
DIVIDEX2
 70
0
  3
Divide (2x) ____  . .  ____  . .  ____  . .  ____
 72
65
 73
6
 40
2.6
 49
2.0
 49
-0.2
 49
0.0
 49
-0.2
 49
0.0
 49
-0.2
  0
LTYPE
  5
449
  2
DIVIDE2
 70
0
  3
Divide(.5x) _ . _ . _ . _ . _ . _ . _ . _
 72
65
 73
6
 40
0.8
 49
0.5
 49
-0.1
 49
0.0
 49
-0.1
 49
0.0
 49
-0.1
  0
ENDTAB
  0
TABLE
  2
STYLE
  5
433
 70
18
  0
STYLE
  5
417
  2
STANDARD
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
 42
0.2
  3
txt
  4

  0
STYLE
  5
44A
  2
ARIAL
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
 42
1.0
  3
arial.ttf
  4

  0
STYLE
  5
44F
  2
ARIAL_NARROW
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
 42
1.0
  3
arialn.ttf
  4

  0
STYLE
  5
453
  2
ISOCPEUR
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
 42
1.0
  3
isocpeur.ttf
  4

  0
STYLE
  5
455
  2
TIMES
 70
0
 40
0.0
 41
1.0
 50
0.0
 71
0
 42
1.0
  3
times.ttf
  4

  0
ENDTAB
  0
TABLE
  2
VIEW
  5
434
 70
0
  0
ENDTAB
  0
ENDSEC
"""

###################################################################
##real python code easyw

import re, os
from math import sqrt, atan2, degrees
import argparse
#import FreeCAD,FreeCADGui
# from dxfwrite import DXFEngine as dxf
#from r12writer import *

parser = argparse.ArgumentParser(description='kicadpcb2dxf converter')
parser.add_argument('-f','--file', help='.kicad_pcb file name', required=False)
#parser.add_argument('-c','--color', help='--color blue', required=False)

args = vars(parser.parse_args())
def say(msg):
    #FreeCAD.Console.PrintMessage(msg)
    #FreeCAD.Console.PrintMessage('\n')
    print(msg)

#say(len(args))
#if len(args) == 1:
#    #filename="C:/Cad/Progetti_K/test/test2-dxf.kicad_pcb"  
#    #path, fname = os.path.splitext(os.path.abspath(filename))
#    #say(fname)
#    say ("use kicadpcb3dxf pcbfile_name.kicad_pcb")
#    exit
if args['file'] == None:
    #filename="C:/Cad/Progetti_K/test/test2-dxf.kicad_pcb"  
    #path, fname = os.path.splitext(os.path.abspath(filename))
    #say(fname)
    say ("...\n   launch:\n          kicadpcb3dxf -f pcbfile_name.kicad_pcb")
    say("version "+str(___version___))
    quit()
else:
    filename=args['file']
    say(args['file'])
    dirpath = os.path.abspath(os.path.expanduser(filename))
    path, fname = os.path.split(dirpath)
    ext = os.path.splitext(os.path.basename(filename))[1]
    name = os.path.splitext(os.path.basename(filename))[0]

say ("reading from "+ dirpath)
#say ("path= "+ path)
#say("fname "+fname)
out_filename=path+os.sep+name+".dxf"
say("writing to "+out_filename)
content=[]
txtFile = open(filename,"r")
content = txtFile.readlines()
content.append(" ")
txtFile.close()
#say(content)

# quote_layer True to move all quote on special layer
quote_layer=False
align="LEFT"

with r12writer(out_filename) as dxf:
    data=[];createTxt=0;quote_color=127;dimension=0
    for line in content:
        if line.strip().startswith("(at ") and not "(at (xyz" in line:
            pos=line.split('(at ',1)[-1]
            plcmt=pos.split(" ")
            plcmt[1]=plcmt[1].split(')')[0] 
            #say("getting fp offset")
            #say (plcmt)
            #say (plcmt[0]+" x off");say (plcmt[1]+" y off")
        create=0
        if "fp_line" in line:
            if "Dwgs" in line:
                layer=0; color=None; create=1
            if "Cmts" in line:
                layer="Cmts"; color=1; create=1
            if "Edge" in line:
                layer="Edge"; color=2; create=1
            if "Eco1" in line:
                layer="Eco1"; color=3; create=1
            if "Eco2" in line:
                layer="Eco2"; color=4; create=1
            if "F.Fab" in line:
                layer="FFab"; color=5; create=1
            if "B.Fab" in line:
                layer="BFab"; color=6; create=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; create=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; create=1
            if create==1:
                coords=line.split('(',1)[-1]
                coords=coords.split(" ")
                #say(coords[4]+";"+coords[5][:-1]+" "+layer)
                #say(coords)
                xs=float(coords[2])+float(plcmt[0]);ys=-float(coords[3].split(')')[0])-float(plcmt[1])
                xe=float(coords[5])+float(plcmt[0]);ye=-float(coords[6].split(')')[0])-float(plcmt[1])
                #xs=float(coords[4]);ys=-float(coords[5][:-1])
                #xe=float(coords[7]);ye=-float(coords[8][:-1])
                #say (plcmt[0]+" x off")
                #say (str(float(plcmt[0]))+" x off")
                #say(str(xs)+";"+str(ys)+" module")
                #data.append(str(xs)+";"+str(ys))
                dxf.add_line((xs,ys), (xe,ye), layer, color, linetype=None)
        create=0
        if "fp_circle" in line:
            if "Dwgs" in line:
                layer=0; color=None; create=1
            if "Cmts" in line:
                layer="Cmts"; color=1; create=1
            if "Edge" in line:
                layer="Edge"; color=2; create=1
            if "Eco1" in line:
                layer="Eco1"; color=3; create=1
            if "Eco2" in line:
                layer="Eco2"; color=4; create=1
            if "F.Fab" in line:
                layer="FFab"; color=5; create=1
            if "B.Fab" in line:
                layer="BFab"; color=6; create=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; create=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; create=1
            if create==1:
                coords=line.split('(',1)[-1]
                coords=coords.split(" ")
                #say(coords[4]+";"+coords[5][:-1])
                cx=float(coords[2])+float(plcmt[0]);cy=-float(coords[3].split(')')[0])-float(plcmt[1])
                xe=float(coords[5])+float(plcmt[0]);ye=-float(coords[6].split(')')[0])-float(plcmt[1])
                #cx=float(coords[4]);cy=-float(coords[5][:-1])
                #xe=float(coords[7]);ye=-float(coords[8][:-1])
                data.append(str(cx)+";"+str(cy))
                r=sqrt((cx-xe)**2+(cy-ye)**2)
                dxf.add_circle((cx, cy), r, layer, color, linetype=None)
        create=0
        if "fp_arc" in line:
            if "Dwgs" in line:
                layer=0; color=None; create=1
            if "Cmts" in line:
                layer="Cmts"; color=1; create=1
            if "Edge" in line:
                layer="Edge"; color=2; create=1
            if "Eco1" in line:
                layer="Eco1"; color=3; create=1
            if "Eco2" in line:
                layer="Eco2"; color=4; create=1
            if "F.Fab" in line:
                layer="FFab"; color=5; create=1
            if "B.Fab" in line:
                layer="BFab"; color=6; create=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; create=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; create=1
            if create==1:
                coords=line.split('(',1)[-1]
                coords=coords.split(" ")
                #say(coords[4]+";"+coords[5][:-1])
                cx=float(coords[2])+float(plcmt[0]);cy=-float(coords[3].split(')')[0])-float(plcmt[1])
                xe=float(coords[5])+float(plcmt[0]);ye=-float(coords[6].split(')')[0])-float(plcmt[1])
                #cx=float(coords[4]);cy=-float(coords[5][:-1])
                #xe=float(coords[7]);ye=-float(coords[8][:-1])
                arc_angle=float(coords[8].split(')')[0])
                #arc_angle=float(coords[10][:-1])
                data.append(str(cx)+";"+str(cy))
                #endAngle = degrees(atan2(ye-cy, xe-cx))
                #startAngle = (endAngle-arc_angle)
                if arc_angle<0:
                    startAngle = degrees(atan2(ye-cy, xe-cx))
                    endAngle = (startAngle-arc_angle)
                else:
                    endAngle = degrees(atan2(ye-cy, xe-cx))
                    startAngle = (endAngle-arc_angle)
                center = (cx, cy, 0) # int or float
                r = sqrt((cx-xe)**2+(cy-ye)**2)
                #say(str(startAngle)+";"+str(endAngle))
                dxf.add_arc(center, r, startAngle, endAngle, layer, color, linetype=None)
        create=0
        if "gr_line" in line:
            if "Dwgs" in line:
                layer=0; color=None; create=1
            if "Cmts" in line:
                layer="Cmts"; color=1; create=1
            if "Edge" in line:
                layer="Edge"; color=2; create=1
            if "Eco1" in line:
                layer="Eco1"; color=3; create=1
            if "Eco2" in line:
                layer="Eco2"; color=4; create=1
            if "F.Fab" in line:
                layer="FFab"; color=5; create=1
            if "B.Fab" in line:
                layer="BFab"; color=6; create=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; create=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; create=1
            if create==1:
                coords=line.split('(',1)[-1]
                coords=coords.split(" ")
                #say(coords[4]+";"+coords[5][:-1]+" "+layer)
                #say(coords)
                xs=float(coords[2]);ys=-float(coords[3].split(')')[0])
                xe=float(coords[5]);ye=-float(coords[6].split(')')[0])
                #xs=float(coords[4]);ys=-float(coords[5][:-1])
                #xe=float(coords[7]);ye=-float(coords[8][:-1])
                #data.append(str(xs)+";"+str(ys))
                dxf.add_line((xs,ys), (xe,ye), layer, color, linetype=None)
        create=0
        if "gr_circle" in line:
            if "Dwgs" in line:
                layer=0; color=None; create=1
            if "Cmts" in line:
                layer="Cmts"; color=1; create=1
            if "Edge" in line:
                layer="Edge"; color=2; create=1
            if "Eco1" in line:
                layer="Eco1"; color=3; create=1
            if "Eco2" in line:
                layer="Eco2"; color=4; create=1
            if "F.Fab" in line:
                layer="FFab"; color=5; create=1
            if "B.Fab" in line:
                layer="BFab"; color=6; create=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; create=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; create=1
            if create==1:
                coords=line.split('(',1)[-1]
                coords=coords.split(" ")
                #say(coords[4]+";"+coords[5][:-1])
                cx=float(coords[2]);cy=-float(coords[3].split(')')[0])
                xe=float(coords[5]);ye=-float(coords[6].split(')')[0])
                #cx=float(coords[4]);cy=-float(coords[5][:-1])
                #xe=float(coords[7]);ye=-float(coords[8][:-1])
                data.append(str(cx)+";"+str(cy))
                r=sqrt((cx-xe)**2+(cy-ye)**2)
                dxf.add_circle((cx, cy), r, layer, color, linetype=None)
        create=0
        if "gr_arc" in line:
            if "Dwgs" in line:
                layer=0; color=None; create=1
            if "Cmts" in line:
                layer="Cmts"; color=1; create=1
            if "Edge" in line:
                layer="Edge"; color=2; create=1
            if "Eco1" in line:
                layer="Eco1"; color=3; create=1
            if "Eco2" in line:
                layer="Eco2"; color=4; create=1
            if "F.Fab" in line:
                layer="FFab"; color=5; create=1
            if "B.Fab" in line:
                layer="BFab"; color=6; create=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; create=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; create=1
            if create==1:
                coords=line.split('(',1)[-1]
                coords=coords.split(" ")
                #say(coords[4]+";"+coords[5][:-1])
                cx=float(coords[2]);cy=-float(coords[3].split(')')[0])
                xe=float(coords[5]);ye=-float(coords[6].split(')')[0])
                #cx=float(coords[4]);cy=-float(coords[5][:-1])
                #xe=float(coords[7]);ye=-float(coords[8][:-1])
                arc_angle=float(coords[8].split(')')[0])
                #say(arc_angle)
                #arc_angle=float(coords[10][:-1])
                data.append(str(cx)+";"+str(cy))
                #endAngle = degrees(atan2(ye-cy, xe-cx))
                #startAngle = (endAngle-arc_angle)
                if arc_angle<0:
                    startAngle = degrees(atan2(ye-cy, xe-cx))
                    endAngle = (startAngle-arc_angle)
                else:
                    endAngle = degrees(atan2(ye-cy, xe-cx))
                    startAngle = (endAngle-arc_angle)
                center = (cx, cy, 0) # int or float
                r = sqrt((cx-xe)**2+(cy-ye)**2)
                #say(str(startAngle)+";"+str(endAngle))
                dxf.add_arc(center, r, startAngle, endAngle, layer, color, linetype=None)
        #createTxt=0
        if "gr_text" in line:
            if "Dwgs" in line:
                layer=0; color=None; createTxt=1
            if "Cmts" in line:
                layer="Cmts"; color=1; createTxt=1
            if "Edge" in line:
                layer="Edge"; color=2; createTxt=1
            if "Eco1" in line:
                layer="Eco1"; color=3; createTxt=1
            if "Eco2" in line:
                layer="Eco2"; color=4; createTxt=1
            if "F.Fab" in line:
                layer="FFab"; color=5; createTxt=1
            if "B.Fab" in line:
                layer="BFab"; color=6; createTxt=1
            if "F.CrtYd" in line:
                layer="FCrtYd"; color=7; createTxt=1
            if "B.CrtYd" in line:
                layer="BCrtYd"; color=8; createTxt=1
            if createTxt==1:        
                #(gr_text Rotate (at 325.374 52.705 15) (layer Eco2.User)
                line=line.strip().split("(gr_text ")[1].split("(at")
                text=line[0].replace("\"", "").replace("\'", "")
                #say(line[1].split(" "))
                px=line[1].split(" ")[1];py=line[1].split(" ")[2].replace(")", "")
                if "layer" not in line[1].split(" ")[3]:
                    rot=line[1].split(" ")[3].replace(")", "")
                else:
                    rot="0"
                #say(line);say(text);say(px+";"+py+";"+rot)
        if "(effects" in line and createTxt==1:
            createTxt=0
            size=(line.split("(size ")[1].split(" "))
            #say (line)
            #sizeX=int(round(float(size[0])))
            #sizeY=int(round(float(size[1].replace(")", ""))))
            sizeX=(float(size[0]))
            sizeY=(float(size[1].replace(")", "")))
            #say(sizeX);say(sizeY)
            text1=text.split("\\n")
            #say (text1)
            #say (len(text1))
            posY=-float(py)
            # multiline support
            if dimension==1 and quote_layer:
                color=quote_color
                layer="Quote"
                dimension=0
            for txt in text1:
                dxf.add_text(txt,(float(px),posY),sizeX,sizeY,align,float(rot),0.,'SIMPLEX',layer,color)
                posY=posY-sizeY*1.3
            align="LEFT"
            # dxf.add_text(text,(float(px),-float(py)),sizeX,sizeY,"LEFT",float(rot),0.,'STANDARD',layer,color)
        if "(dimension" in line:
            dimension=1;align="MIDDLE_CENTER"
        if "(feature" in line or "(crossbar" in line or "(arrow" in line:
            dimension_bar=line.split("(xy")
            #say(dimension_bar)
            dsx=float(dimension_bar[1].split(" ")[1])
            dsy=float(dimension_bar[1].split(" ")[2].replace(")",""))
            dex=float(dimension_bar[2].split(" ")[1])
            dey=float(dimension_bar[2].split(" ")[2].replace(")",""))
            #say(str(dsx)+";"+str(dsy)+";;"+str(dex)+";"+str(dey))
            dxf.add_line((dsx,-dsy), (dex,-dey), layer, color, linetype=None)
    #say (data)
    
say("--> "+out_filename+" written")

