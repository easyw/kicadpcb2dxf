# kicadpcb2dxf
**dxf exporter for mechanical layers of a kicad_pcb board**
- "Dwgs", "Cmts", "Edge", "Eco1", "Eco2", "F.Fab", "B.Fab"
- the dxf generated has single line draw as it should be for mechanical interchange (this option is missing in pcbnew plot)

how to launch:
python kicadpcb2dxf.py -f kicad-board.kicad_pcb

kicadpcb2dxf.py
  creates DXF file of selected kicad pcb board
  using r12writer from ezdxf modules included
  this is a part of kicad StepUp tools; please refer to kicad StepUp tools 
  for the full licence

 Copyright (c) 2015 Maurice easyw@katamail.com
 Copyright (C) 2016, Manfred Moitzi with MIT License
 dxf_parser="r12writer from ezdxf 0.7.6"

todo:
- [ ] add text support
- [ ] add quote support
- [ ] add fp support
